import json
import queue
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

try:
    from websockets.exceptions import ConnectionClosed
    from websockets.sync.client import connect as websocket_connect
except ImportError:
    ConnectionClosed = OSError
    websocket_connect = None


MAX_SERVER_EVENT_BYTES = 64 * 1024


def load_default_server_url():
    candidates = []
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        candidates.append(Path(bundle_dir) / "config" / "party-endpoint.json")
    candidates.append(Path(__file__).resolve().parents[2] / "private" / "party-endpoint.json")
    for path in candidates:
        try:
            value = str(json.loads(path.read_text(encoding="utf-8")).get("server_url", "")).strip().rstrip("/")
        except (OSError, ValueError, TypeError):
            continue
        if value.startswith(("https://", "http://")):
            return value
    return ""


DEFAULT_SERVER_URL = load_default_server_url()


class PartyClientError(Exception):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


class PartyClient:
    def __init__(
        self,
        installation_id: str,
        dispatch: Callable[[Callable[[], None]], None],
        on_event: Callable[[dict], None] | None = None,
        on_state: Callable[[str, str], None] | None = None,
        server_url: str | None = None,
        dispatch_events: bool = True,
    ):
        self.installation_id = installation_id
        self.dispatch = dispatch
        self.on_event = on_event or (lambda _event: None)
        self.on_state = on_state or (lambda _state, _detail: None)
        self.dispatch_events = bool(dispatch_events)
        self.server_url = str(server_url or DEFAULT_SERVER_URL).strip().rstrip("/")
        self.websocket_url = self.server_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        self.room_id = None
        self.member_id = None
        self.member_token = None
        self.expires_at = None
        self.connected = False
        self.desired = False
        self.socket = None
        self.socket_thread = None
        self.outgoing = queue.Queue(maxsize=100)
        self.lock = threading.RLock()
        self.send_lock = threading.Lock()

    @property
    def has_session(self):
        with self.lock:
            return bool(self.desired and self.room_id and self.member_token)

    def create_room(self, profile, on_success, on_error):
        self._request_async("/api/v1/rooms", profile, on_success, on_error)

    def join_room(self, room_id, profile, on_success, on_error):
        self._request_async("/api/v1/rooms/join", {**profile, "room_id": room_id}, on_success, on_error)

    def resume_session(self, session):
        required = ("room_id", "member_id", "member_token", "expires_at")
        if not isinstance(session, dict) or any(not session.get(key) for key in required):
            return False
        if float(session["expires_at"]) <= time.time():
            return False
        self._start_session(session)
        return True

    def _request_async(self, path, payload, on_success, on_error):
        body = {**payload, "installation_id": self.installation_id}

        def work():
            try:
                if not self.server_url:
                    raise PartyClientError("파티 서버 설정이 없습니다.")
                result = self._post(path, body)
                self._start_session(result)
                self.dispatch(lambda: on_success(result))
            except Exception as error:
                client_error = error if isinstance(error, PartyClientError) else PartyClientError("파티 서버에 연결할 수 없습니다.")
                self.dispatch(lambda: on_error(client_error))

        threading.Thread(target=work, name="godinavi-party-http", daemon=True).start()

    def _post(self, path, payload):
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.server_url}{path}",
            data=encoded,
            headers={"Content-Type": "application/json", "User-Agent": "GodiNavi-Party/0.1"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10, context=ssl.create_default_context()) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            retry_after = int(error.headers.get("Retry-After", "0") or 0)
            try:
                detail = json.loads(error.read().decode("utf-8")).get("detail")
            except (ValueError, UnicodeDecodeError):
                detail = None
            raise PartyClientError(detail or "파티 서버 요청에 실패했습니다.", retry_after) from error
        except (OSError, ValueError, urllib.error.URLError) as error:
            raise PartyClientError("파티 서버에 연결할 수 없습니다.") from error

    def _start_session(self, result):
        with self.lock:
            self.room_id = str(result["room_id"])
            self.member_id = str(result["member_id"])
            self.member_token = str(result["member_token"])
            self.expires_at = float(result["expires_at"])
            self.desired = True
            self.connected = False
        self._emit_state("connecting", self.room_id)
        if not self.socket_thread or not self.socket_thread.is_alive():
            self.socket_thread = threading.Thread(target=self._socket_worker, name="godinavi-party-ws", daemon=True)
            self.socket_thread.start()

    def _socket_worker(self):
        retry_delay = 1.0
        while self.has_session:
            if self.expires_at and time.time() >= self.expires_at:
                self._clear_session()
                self._emit_state("expired", "")
                break
            if websocket_connect is None:
                self._emit_state("error", "WebSocket 모듈을 불러올 수 없습니다.")
                return
            try:
                with websocket_connect(
                    f"{self.websocket_url}/api/v1/ws",
                    open_timeout=10,
                    close_timeout=3,
                    max_size=MAX_SERVER_EVENT_BYTES,
                    user_agent_header="GodiNavi-Party/0.1",
                ) as socket:
                    with self.lock:
                        self.socket = socket
                        room_id, member_token = self.room_id, self.member_token
                    socket.send(json.dumps({
                        "type": "authenticate", "room_id": room_id, "member_token": member_token,
                    }, separators=(",", ":")))
                    retry_delay = 1.0
                    last_heartbeat = time.monotonic()
                    while self.has_session:
                        self._drain_outgoing(socket)
                        if time.monotonic() - last_heartbeat >= 25:
                            self._send(socket, {"type": "heartbeat"})
                            last_heartbeat = time.monotonic()
                        try:
                            raw = socket.recv(timeout=0.5)
                        except TimeoutError:
                            continue
                        event = json.loads(raw)
                        if event.get("type") == "room_snapshot":
                            with self.lock:
                                self.connected = True
                            self._emit_state("connected", self.room_id or "")
                        elif event.get("type") == "room_closed":
                            self._clear_session()
                            self._emit_state("closed", str(event.get("reason", "")))
                        if self.dispatch_events:
                            self.dispatch(lambda current=event: self.on_event(current))
            except (ConnectionClosed, OSError, TimeoutError, ValueError) as error:
                with self.lock:
                    self.connected = False
                    self.socket = None
                if not self.has_session:
                    break
                if getattr(error, "code", None) in {4003, 4004, 4005, 4006}:
                    self._clear_session()
                    code = getattr(error, "code", None)
                    self._emit_state("removed" if code in {4005, 4006} else "closed", "ban" if code == 4006 else "remove" if code == 4005 else str(error))
                    break
                self._emit_state("reconnecting", str(error))
                time.sleep(retry_delay)
                retry_delay = min(8.0, retry_delay * 2)
            finally:
                with self.lock:
                    self.socket = None
                    self.connected = False

    def _send(self, socket, payload):
        with self.send_lock:
            socket.send(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    def _drain_outgoing(self, socket):
        while True:
            try:
                payload = self.outgoing.get_nowait()
            except queue.Empty:
                return
            self._send(socket, payload)

    def send(self, payload):
        if not self.has_session:
            return False
        try:
            self.outgoing.put_nowait(dict(payload))
            return True
        except queue.Full:
            return False

    def leave(self):
        with self.lock:
            socket = self.socket
        if socket:
            try:
                self._send(socket, {"type": "leave_room"})
            except Exception:
                pass
        self._clear_session()
        if socket:
            try:
                socket.close()
            except Exception:
                pass
        self._emit_state("left", "")

    def close(self):
        with self.lock:
            socket = self.socket
        self._clear_session()
        if socket:
            try:
                socket.close()
            except Exception:
                pass

    def _clear_session(self):
        with self.lock:
            self.desired = False
            self.connected = False
            self.room_id = None
            self.member_id = None
            self.member_token = None
            self.expires_at = None
            self.socket = None
        while True:
            try:
                self.outgoing.get_nowait()
            except queue.Empty:
                break

    def _emit_state(self, state, detail):
        self.dispatch(lambda: self.on_state(state, detail))

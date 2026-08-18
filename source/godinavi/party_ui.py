import tkinter as tk
import time
import unicodedata
from collections.abc import Callable
from tkinter import ttk

from PIL import Image, ImageTk

from map_engine import BUNDLE_DIR, show_interactive_above_owner
from godinavi.window_attachment import attach_above, make_noactivate_toolwindow


BG = "#2a2118"
FIELD = "#3b3022"
HEADER = "#5a4932"
GOLD = "#d8b15a"
TEXT = "#f1e5c7"
RESOURCE_DIR = BUNDLE_DIR
PARTY_MEMBER_COLORS = (
    "#80FF44",  # lime
    "#FF5CCF",  # magenta
    "#FFE14A",  # yellow
    "#4D8DFF",  # blue
    "#FF4B55",  # red
    "#32E6D2",  # cyan
    "#FF9F1C",  # orange
    "#A66BFF",  # violet
)

JOBS = ("전사", "검투사", "성직자", "마법사", "도둑")
SUB_JOBS = ("바드", "연금술사", "재봉사", "대장장이")
NON_BUFF_SHARING_JOBS = frozenset(("성직자", "마법사"))
JOB_LABELS = {
    "KR": dict(zip(JOBS, JOBS)),
    "JP": {"전사": "戦士", "검투사": "剣闘士", "성직자": "聖職者", "마법사": "魔法使い", "도둑": "盗賊"},
    "EN": {"전사": "Warrior", "검투사": "Gladiator", "성직자": "Cleric", "마법사": "Mage", "도둑": "Thief"},
}
SUB_JOB_LABELS = {
    "KR": dict(zip(SUB_JOBS, SUB_JOBS)),
    "JP": {"바드": "バード", "연금술사": "錬金術師", "재봉사": "裁縫師", "대장장이": "鍛冶師"},
    "EN": {"바드": "Bard", "연금술사": "Alchemist", "재봉사": "Tailor", "대장장이": "Blacksmith"},
}
JOB_SHORT_LABELS = {
    "KR": {"전사": "전", "검투사": "검", "성직자": "성", "마법사": "마", "도둑": "도"},
    "JP": {"전사": "戦", "검투사": "剣", "성직자": "聖", "마법사": "魔", "도둑": "盗"},
    "EN": {"전사": "W", "검투사": "G", "성직자": "C", "마법사": "M", "도둑": "T"},
}
SUB_JOB_SHORT_LABELS = {
    "KR": {"바드": "바", "연금술사": "연", "재봉사": "재", "대장장이": "대"},
    "JP": {"바드": "鳥", "연금술사": "錬", "재봉사": "裁", "대장장이": "鍛"},
    "EN": {"바드": "B", "연금술사": "A", "재봉사": "T", "대장장이": "BS"},
}

PARTY_TEXTS = {
    "KR": {
        "party": "파티룸", "create": "파티룸 생성", "join": "파티룸 입실", "leave": "파티룸 퇴실",
        "settings": "파티룸 확인", "player_id": "ID", "player_hint": "인원을 식별할 이름 (약 5글자)",
        "job": "직업", "sub_job": "부직업", "room_id": "파티룸 ID", "room_hint": "파티장이 공유한 ID",
        "join_button": "참가", "close": "닫기", "invalid_room": "파티룸 ID를 확인해 주세요.",
        "invalid_player": "ID를 입력해 주세요.", "copy": "복사", "created": "파티룸을 생성했습니다.",
        "joined": "파티룸 {room_id}에 입실했습니다.", "left": "파티룸에서 퇴실했습니다.",
        "copied": "파티룸 ID를 복사했습니다.", "reconnecting": "파티 서버에 재연결 중입니다…",
        "room_closed": "파티룸이 종료되었습니다.", "connected_room": "파티룸 {room_id} 연결 완료",
        "admin_room_closed": "네트워크 에러로 인해 방이 폐쇄되었습니다.\n에러가 지속될 경우\n디스코드ID epica_nox 로 DM 부탁드립니다.",
        "waiting": "접속 정보를 기다리는 중…", "leader": "파티장", "member": "파티원", "member_count": "파티원 {count} / 8명{full}", "member_full": " (만실)",
        "online": "● 접속", "offline": "○ 연결 끊김", "no_location": "위치 정보 없음",
        "already_joined": "현재 파티룸에서 퇴실한 뒤 새 방을 생성할 수 있습니다.",
        "input_error": "입력값을 확인해 주세요.", "retry_later": "잠시 후 다시 시도해 주세요.",
        "rooms_full": "현재 생성 가능한 파티룸이 모두 사용 중입니다.",
        "server_unreachable": "파티 서버에 연결할 수 없습니다.", "request_failed": "파티 서버 요청에 실패했습니다.",
        "restoring": "직전 파티룸에 파티장으로 다시 연결합니다…", "expired": "직전 파티룸의 이용시간이 만료되었습니다.",
        "restoring_member": "직전 파티룸에 다시 연결합니다…", "removed": "파티룸에서 퇴실 처리되었습니다.",
        "banned": "파티룸에서 추방되었습니다.", "remove": "퇴실", "ban": "추방",
        "track_position": "위치 추적", "track_buff": "버프 추적", "enabled": "활성화", "disabled": "비활성화",
        "confirm_remove": "{name} 님을 현재 파티룸에서 퇴실시키겠습니까?", "confirm_ban": "{name} 님을 추방하고 이후 생성하는 방에서도 차단하겠습니까?",
        "transfer": "파티장 위임", "confirm_transfer": "{name} 님에게 파티장을 위임하시겠습니까?",
        "leader_leave_warning": "파티에서 퇴실할 경우 자동으로 파티장 목록 바로 아래의 파티원에게 파티장이 위임 됩니다.",
        "portal_copy": "포탈 명령어 복사", "portal_copied": "포탈 명령어를 복사했습니다.", "portal_unavailable": "상대방의 위치 정보가 없습니다.",
        "scroll_hint": "마우스 휠로 스크롤",
        "expires_in": "만료시간 : {hours:02d}시간 {minutes:02d}분",
        "log": "로그", "session_log": "세션 로그", "no_log": "기록이 없습니다.",
        "log_room_created": "방 생성: {room_id}", "log_joined": "입실: {name}", "log_left": "퇴실: {name}",
        "log_removed": "파티장 퇴실 처리: {name}", "log_banned": "파티장 강퇴 처리: {name}",
        "log_transferred": "파티장 위임: {name}",
        "buff_control": "버프창 제어", "leave_short": "퇴실",
        "party_buff_adjusting": "헤더 드래그로 이동 · 우하단 핸들로 크기 조절 · 휠로 투명도 조절",
        "party_buff_saved": "버프 확인창 위치·크기 저장 완료",
        "party_buff_opacity": "::  투명도 (휠 상하)",
        "disband": "해산", "confirm": "확인", "cancel": "취소", "warning": "경고",
        "confirm_disband": "정말 해산하시겠습니까?\n즉시 세션이 종료되며 모든 참가자들의 연결이 종료됩니다.",
        "experimental_title": "안내",
        "experimental_notice": "가디내비의 파티룸은 실험적 기능입니다.\n아직 정상적으로 동작하지 않을 수 있으니\n이용에 유의해 주세요.\n\n버그 제보나 개선 의견은 Discord ID epica_nox로\n편하게 연락해 주시면 감사하겠습니다.\n\n현재 파티룸은 개발자가 직접 운영하는 별도 서버의\n리소스를 사용하고 있습니다.\n서버 운영 환경에 문제가 발생하면 파티 멤버 간\n정보 교환이 느려지거나 연결이 중단될 수 있습니다.\n\n또한 운영상의 사정에 따라 서비스 제공이\n종료될 수 있는 점을 미리 양해 부탁드립니다.",
        "experimental_hide": "다음에 다시 보지 않기",
        "outdated_title": "주의",
        "outdated_notice": "가디내비가 최신 버전이 아닌 것 같습니다.\n파티룸 기능은 파티원끼리의 버전이 최신이 아닐 경우\n정상적으로 동작하지 않을 가능성이 높습니다.\n가능하면 톱니바퀴 아이콘을 통해 업데이트 진행 후 이용해 주세요.",
        "outdated_hide": "이번에 다시 보지 않기",
        "personal_buff_timer": "개인 버프 타이머", "fire_crystal": "불의 결정", "ice_crystal": "얼음의 결정",
        "count_seconds": "인식 시 카운트할 초", "timer_display": "타이머 표시",
        "timer_caution": "동작원리문제로 카운트가 부정확하므로 참고용도로만 써주세요",
        "invalid_seconds": "카운트 초수는 1~3600 사이의 숫자로 입력해 주세요.",
        "party_privacy_notice": "가디내비의 파티룸 기능을 이용하실 경우\n아래의 정보가 암호화된 상태로 외부서버를 경유하여\n같은 방의 파티원들에게 공유됩니다.\n- 입실 또는 개설시 입력한 캐릭터명\n- 직업과 부직업\n- 내 캐릭터의 실시간 위치정보\n- 내 캐릭터의 불/얼음 버프상태 정보\n파티룸을 나가거나 세션을 종료하면\n정보는 즉시 서버에서 파기됩니다.\n위 내용에 동의하시는 경우에만 이용 부탁드립니다.",
        "clear": "비우기",
    },
    "JP": {
        "party": "パーティールーム", "create": "パーティールーム作成", "join": "パーティールーム入室", "leave": "パーティールーム退出",
        "settings": "パーティールーム確認", "player_id": "ID", "player_hint": "メンバーを識別する名前（5文字程度）",
        "job": "職業", "sub_job": "副職業", "room_id": "ルームID", "room_hint": "リーダーから共有されたID",
        "join_button": "参加", "close": "閉じる", "invalid_room": "パーティールームIDが正しいか\nもう一度ご確認ください。",
        "invalid_player": "IDを入力してください。", "copy": "コピー", "created": "パーティールームを作成しました。",
        "joined": "パーティールーム {room_id} に参加しました。", "left": "パーティールームから退出しました。",
        "copied": "パーティールームIDをコピーしました。", "reconnecting": "パーティーサーバーに再接続中…",
        "room_closed": "パーティールームが終了しました。", "connected_room": "パーティールーム {room_id} に接続しました。",
        "admin_room_closed": "ネットワークエラーによりルームが閉鎖されました。\nエラーが続く場合は、Discord ID「epica_nox」まで\nDMでご連絡ください。",
        "waiting": "接続情報を待っています…", "leader": "リーダー", "member": "メンバー", "member_count": "PTメンバー {count} / 8人{full}", "member_full": "（満員）",
        "online": "● 接続中", "offline": "○ 切断", "no_location": "位置情報なし",
        "already_joined": "現在のパーティールームから退出してから新しいルームを作成できます。",
        "input_error": "入力内容を確認してください。", "retry_later": "しばらくしてからもう一度お試しください。",
        "rooms_full": "現在作成可能なパーティールームはすべて使用中です。",
        "server_unreachable": "パーティーサーバーに接続できません。", "request_failed": "パーティーサーバーへのリクエストに失敗しました。",
        "restoring": "前回のパーティールームにリーダーとして再接続します…", "expired": "前回のパーティールームは有効期限が切れました。",
        "restoring_member": "前回のパーティールームに再接続します…", "removed": "パーティールームから退出させられました。",
        "banned": "パーティールームから追放されました。", "remove": "退出", "ban": "追放",
        "track_position": "位置追跡", "track_buff": "バフ追跡", "enabled": "有効", "disabled": "無効",
        "confirm_remove": "{name} を現在のパーティールームから退出させますか？", "confirm_ban": "{name} を追放し、今後作成するルームでもブロックしますか？",
        "transfer": "リーダー委任", "confirm_transfer": "{name} にリーダーを委任しますか？",
        "leader_leave_warning": "パーティーから退出すると、リーダー一覧のすぐ下にいるメンバーへ自動的にリーダーが委任されます。",
        "portal_copy": "ポータルコマンドをコピー", "portal_copied": "ポータルコマンドをコピーしました。", "portal_unavailable": "相手の位置情報がありません。",
        "scroll_hint": "マウスホイールでスクロール",
        "expires_in": "部屋の有効期限 : {hours:02d}時間 {minutes:02d}分",
        "log": "ログ", "session_log": "セッションログ", "no_log": "記録はありません。",
        "log_room_created": "部屋を作成: {room_id}", "log_joined": "入室: {name}", "log_left": "退出: {name}",
        "log_removed": "リーダーによる退出処理: {name}", "log_banned": "リーダーによる追放処理: {name}",
        "log_transferred": "リーダー委任: {name}",
        "buff_control": "バフ画面制御", "leave_short": "退出",
        "party_buff_adjusting": "ヘッダーで移動・右下ハンドルでサイズ調整・ホイールで透明度調整",
        "party_buff_saved": "バフ確認画面の位置とサイズを保存しました",
        "party_buff_opacity": "::  透明度（ホイール上下）",
        "disband": "解散", "confirm": "確認", "cancel": "キャンセル", "warning": "警告",
        "confirm_disband": "本当に解散しますか？\nセッションは直ちに終了し、すべての参加者の接続が切断されます。",
        "experimental_title": "ご案内",
        "experimental_notice": "ガディナビのパーティールームは実験的な機能です。\n現時点では正常に動作しない場合がありますので\nご注意ください。\n\n不具合や改善点はDiscord ID「epica_nox」の\nDMまでお気軽にご連絡ください。\n\n現在、パーティールームは開発者が運営する別サーバーの\nリソースを利用しているため、サーバーの運営環境に\n問題が生じた場合、PTメンバー間の情報交換に遅延が\n生じたり、接続が切断されたりする可能性があります。\n\nなお、運営上の都合により、サービスの提供を終了する\n可能性がありますので、あらかじめご了承ください。",
        "experimental_hide": "次回から表示しない",
        "outdated_title": "注意",
        "outdated_notice": "ガディナビが最新バージョンではないようです。\n\nPTメンバーとバージョンが異なる場合\nパーティールーム機能が正常に動作しない可能性が\nあります。可能であればツールバーの歯車アイコンから\nバージョンを更新してからご利用ください。",
        "outdated_hide": "今回は表示しない",
        "personal_buff_timer": "個人バフタイマー", "fire_crystal": "炎の結晶", "ice_crystal": "氷の結晶",
        "count_seconds": "認識時のカウント秒数", "timer_display": "タイマー表示",
        "timer_caution": "動作原理上カウントは正確ではないため、参考用としてご利用ください。",
        "invalid_seconds": "カウント秒数は1～3600の数値で入力してください。",
        "party_privacy_notice": "ガディナビのパーティールーム機能を利用すると、\n下記の情報が暗号化され、外部サーバーを経由し\n同じ部屋のPTメンバーと共有されます。\n- 入室時に記入したキャラ名\n- 職業・副職業\n- キャラの位置情報(リアルタイム)\n- キャラの氷・炎バフ状態\n部屋を退出するか、セッションを終了すると\n情報は直ちにサーバーから破棄されます。\n上記に同意いただける場合のみご利用ください。",
        "clear": "クリア",
    },
    "EN": {
        "party": "Party Room", "create": "Create party room", "join": "Join party room", "leave": "Leave party room",
        "settings": "Party room overview", "player_id": "ID", "player_hint": "A short name identifying you",
        "job": "Class", "sub_job": "Sub-class", "room_id": "Party room ID", "room_hint": "ID shared by the leader",
        "join_button": "Join", "close": "Close", "invalid_room": "Please check the party room ID.",
        "invalid_player": "Please enter an ID.", "copy": "Copy", "created": "Party room created.",
        "joined": "Joined party room {room_id}.", "left": "Left the party room.",
        "copied": "Party room ID copied.", "reconnecting": "Reconnecting to the party server…",
        "room_closed": "The party room has closed.", "connected_room": "Connected to party room {room_id}.",
        "admin_room_closed": "The room was closed due to a network error.\nIf the error persists, please send a DM to\nDiscord ID epica_nox.",
        "waiting": "Waiting for connection information…", "leader": "Leader", "member": "Member", "member_count": "Members: {count} / 8{full}", "member_full": " (Full)",
        "online": "● Online", "offline": "○ Disconnected", "no_location": "Location unavailable",
        "already_joined": "Leave the current party room before creating a new one.",
        "input_error": "Please check the entered information.", "retry_later": "Please try again shortly.",
        "rooms_full": "All available party rooms are currently in use.",
        "server_unreachable": "Unable to connect to the party server.", "request_failed": "Party server request failed.",
        "restoring": "Reconnecting to the previous party room as leader…", "expired": "The previous party room has expired.",
        "restoring_member": "Reconnecting to the previous party room…", "removed": "You were removed from the party room.",
        "banned": "You were banned from the party room.", "remove": "Remove", "ban": "Ban",
        "track_position": "Track position", "track_buff": "Track buffs", "enabled": "On", "disabled": "Off",
        "confirm_remove": "Remove {name} from this party room?", "confirm_ban": "Ban {name} from this and all future rooms you create?",
        "transfer": "Transfer leader", "confirm_transfer": "Transfer party leadership to {name}?",
        "leader_leave_warning": "If you leave the party, leadership will automatically transfer to the member directly below the leader in the list.",
        "portal_copy": "Copy portal command", "portal_copied": "Portal command copied.", "portal_unavailable": "This member has no location information.",
        "scroll_hint": "Scroll with mouse wheel",
        "expires_in": "Expires in: {hours:02d}h {minutes:02d}m",
        "log": "Log", "session_log": "Session log", "no_log": "No events recorded.",
        "log_room_created": "Room created: {room_id}", "log_joined": "Joined: {name}", "log_left": "Left: {name}",
        "log_removed": "Removed by leader: {name}", "log_banned": "Banned by leader: {name}",
        "log_transferred": "Leadership transferred: {name}",
        "buff_control": "Buff Check", "leave_short": "Leave",
        "party_buff_adjusting": "Drag the header to move · Bottom-right handle resizes · Wheel adjusts opacity",
        "party_buff_saved": "Party buff window position and size saved",
        "party_buff_opacity": "::  Opacity (mouse wheel)",
        "disband": "Disband", "confirm": "Confirm", "cancel": "Cancel", "warning": "Warning",
        "confirm_disband": "Disband this room?\nThe session will end immediately and all participants will be disconnected.",
        "experimental_title": "Notice",
        "experimental_notice": "GodiNavi Party Rooms are an experimental feature.\nThey may not always work correctly at this time, so\nplease keep this in mind when using them.\n\nFor bug reports or suggestions, please feel free to contact\nDiscord ID “epica_nox” by DM.\n\nParty Rooms currently use resources on a separate server\noperated by the developer. If problems occur in the server\nenvironment, information exchange between party members may\nbe delayed or connections may be interrupted.\n\nPlease also understand that the service may be discontinued\ndue to operational circumstances.",
        "experimental_hide": "Don't show this again",
        "outdated_title": "Warning",
        "outdated_notice": "GodiNavi does not appear to be up to date.\nParty Rooms may not work correctly when party members use older versions.\nIf possible, please update from the gear icon before using this feature.",
        "outdated_hide": "Don't show again for this update",
        "personal_buff_timer": "Personal buff timer", "fire_crystal": "Fire Crystal", "ice_crystal": "Ice Crystal",
        "count_seconds": "Seconds to count when detected", "timer_display": "Show timer",
        "timer_caution": "Timing is approximate due to how detection works. Use it for reference only.",
        "invalid_seconds": "Enter a number from 1 to 3600 seconds.",
        "party_privacy_notice": "When using the GodiNavi Party Room feature, the following encrypted information\nis shared with members in the same room through an external server.\n- Character name entered when joining or creating a room\n- Class and sub-class\n- Your character's real-time location\n- Your character's Fire/Ice buff status\nWhen you leave the room or the session ends,\nthe information is immediately deleted from the server.\nPlease use this feature only if you agree to the above.",
        "clear": "Clear",
    },
}


def normalize_player_id(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).strip()
    return "".join(ch for ch in value if unicodedata.category(ch) not in {"Cc", "Cf"})[:8]


def shares_buff_status(job: str) -> bool:
    return job not in NON_BUFF_SHARING_JOBS


def bounded_seconds(value, fallback=598):
    try:
        return max(1, min(3600, int(value)))
    except (TypeError, ValueError):
        return fallback


class PartyUI:
    def __init__(
        self,
        root: tk.Misc,
        config: dict,
        save_config: Callable[[], None],
        language: Callable[[], str],
        client_rect: Callable[[], tuple[int, int, int, int] | None],
        owner_hwnd: Callable[[], int | None],
        party_client,
        message_callback: Callable[[str, int], None] | None = None,
        map_engine=None,
    ):
        self.root = root
        self.config = config
        self.save_config = save_config
        self.language = language
        self.client_rect = client_rect
        self.owner_hwnd = owner_hwnd
        self.party_client = party_client
        self.message_callback = message_callback or (lambda _text, _duration=1600: None)
        self.map_engine = map_engine
        self.members = {}
        self.session_color_assignments = {}
        self.member_list_frame = None
        self.member_row_widgets = {}
        self.member_marquee_states = {}
        self.member_marquee_job = None
        self.member_count_label = None
        self.expiration_label = None
        self.session_logs = []
        self.log_panel = None
        self.log_text = None
        self.log_visible = False
        self.settings_main_panel = None
        self.buff_bar_window = None
        self.buff_bar_images = []
        self.buff_timer_canvas_items = {}
        self.buff_bar_lock_window = None
        self.buff_bar_header_window = None
        self.buff_bar_grip_window = None
        self.buff_bar_adjusting = False
        self.buff_bar_drag_origin = None
        self.buff_bar_resize_origin = None
        self.buff_bar_scale = max(0.5, min(2.0, float(self.config.get("party_buff_bar_scale", 1.0))))
        self.buff_bar_opacity = max(50, min(100, int(self.config.get("party_buff_bar_opacity_percent", 100))))
        timer_config = self.config.setdefault("party_personal_buff_timer", {})
        self.personal_buff_durations = {
            "fire": bounded_seconds(timer_config.get("fire_seconds", 598)),
            "ice": bounded_seconds(timer_config.get("ice_seconds", 598)),
        }
        self.personal_buff_timer_visible = bool(timer_config.get("show_timer", False))
        self.personal_timer_window = None
        self.remote_buff_timers = {}
        self.local_buff_presence = None
        self.last_sent_buff_presence = object()
        self.last_position = None
        self.last_position_sent_at = 0.0
        self.tracking_preferences = self.config.setdefault("party_tracking_preferences", {})
        self.join_window: tk.Toplevel | None = None
        self.create_window: tk.Toplevel | None = None
        self.room_window: tk.Toplevel | None = None
        self.settings_window: tk.Toplevel | None = None
        self.notice_windows: list[tk.Toplevel] = []
        self.party_client.on_state = self._on_client_state
        self.party_client.on_event = self._on_client_event
        self.root.after(0, self._restore_session)
        self.root.after(500, self._tick_remote_buff_timers)

    @property
    def joined(self):
        return self.party_client.has_session

    @property
    def overview_open(self):
        return self._window_exists(self.settings_window)

    def texts(self):
        return PARTY_TEXTS.get(self.language(), PARTY_TEXTS["EN"])

    def join_action_text(self):
        texts = self.texts()
        return texts["leave"] if self.joined else texts["join"]

    def create_room(self):
        if self.joined:
            self.message_callback(self.texts()["already_joined"], 2400)
            return
        self.open_create_dialog()

    def join_or_leave(self):
        if self.joined:
            if self._is_leader() and len(self.members) > 1:
                if not self._confirm(
                    self.texts()["leave"], self.texts()["leader_leave_warning"],
                    show_header_close=False,
                ):
                    return
            self.config["party_last_room_id"] = self.party_client.room_id
            self.save_config()
            self.party_client.leave()
            self.message_callback(self.texts()["left"], 2000)
            return
        self.open_join_dialog()

    def toggle_settings(self):
        if self._window_exists(self.settings_window):
            try:
                self._save_dialog_position(self.settings_window)
                self.log_visible = False
                self._cancel_member_marquees()
                self.settings_window.destroy()
            except tk.TclError:
                pass
            return
        self.open_settings()

    def open_create_dialog(self):
        if self.joined:
            self.message_callback(self.texts()["already_joined"], 2400)
            return
        if self._show_existing(self.create_window):
            return
        texts = self.texts()
        profile = self._saved_profile()
        window, _content, body, close = self._create_dialog(texts["create"], 450, 500)
        self.create_window = window
        self._configure_form_style(window)
        body.configure(style="Party.TFrame")
        footer = self._privacy_footer(body, texts["party_privacy_notice"])
        form = ttk.Frame(body, style="Party.TFrame", padding=(16, 12, 16, 0))
        form.pack(side="top", fill="x")
        footer.pack(side="top", fill="both", expand=True, padx=16, pady=(2, 6))
        form.columnconfigure(0, weight=1)
        player_var = tk.StringVar(value=normalize_player_id(profile.get("player_id", "")))
        job_var = tk.StringVar(value=self._job_label(profile.get("job") if profile.get("job") in JOBS else JOBS[0]))
        sub_job_var = tk.StringVar(value=self._sub_job_label(profile.get("sub_job") if profile.get("sub_job") in SUB_JOBS else SUB_JOBS[0]))
        player_entry = self._add_field(form, 0, texts["player_id"], player_var, texts["player_hint"])
        self._add_compact_job_fields(form, 3, job_var, sub_job_var)
        player_var.trace_add("write", lambda *_args: self._limit_player_var(player_var))
        buttons = tk.Frame(footer, bg=BG)
        buttons.pack(side="bottom", anchor="e", pady=(4, 0))

        def success(result):
            self._remember_session(result, "leader")
            self._start_session_log()
            self._append_session_log("log_room_created", room_id=result["room_id"])
            if self._window_exists(window):
                close()
            self._show_room_dialog(result["room_id"])
            self.message_callback(texts["created"], 2200)

        def failure(error):
            if not self._window_exists(window):
                return
            create_button.configure(state="normal")
            self._alert(texts["create"], self._localized_error(error))

        def create():
            current = self._save_profile(player_var, job_var, sub_job_var, window)
            if current is None:
                return
            create_button.configure(state="disabled")
            self.party_client.create_room(current, success, failure)

        create_button = self._button(buttons, texts["create"], create)
        create_button.pack(side="left", padx=(0, 6))
        self._button(buttons, texts["close"], close).pack(side="left")
        window.bind("<Return>", lambda _event: create())
        window.after_idle(player_entry.focus_set)

    def open_join_dialog(self):
        if self._show_existing(self.join_window):
            return
        texts = self.texts()
        profile = self._saved_profile()
        window, content, body, close = self._create_dialog(texts["join"], 450, 600)
        self.join_window = window

        self._configure_form_style(window)

        body.configure(style="Party.TFrame")
        footer = self._privacy_footer(body, texts["party_privacy_notice"])
        form = ttk.Frame(body, style="Party.TFrame", padding=(16, 12, 16, 0))
        form.pack(side="top", fill="x")
        footer.pack(side="top", fill="both", expand=True, padx=16, pady=(2, 12))
        form.columnconfigure(0, weight=1)
        player_var = tk.StringVar(value=normalize_player_id(profile.get("player_id", "")))
        job_var = tk.StringVar(value=self._job_label(profile.get("job") if profile.get("job") in JOBS else JOBS[0]))
        sub_job_var = tk.StringVar(value=self._sub_job_label(profile.get("sub_job") if profile.get("sub_job") in SUB_JOBS else SUB_JOBS[0]))
        saved_room = str(self.config.get("party_last_room_id", ""))
        compact_room = "".join(ch for ch in saved_room.upper() if ch.isalnum())[:8]
        room_left_var = tk.StringVar(value=compact_room[:4])
        room_right_var = tk.StringVar(value=compact_room[4:8])

        player_entry = self._add_field(form, 0, texts["player_id"], player_var, texts["player_hint"])
        self._add_compact_job_fields(form, 3, job_var, sub_job_var)
        room_left_entry, room_right_entry = self._add_room_code_field(
            form, 7, texts["room_id"], room_left_var, room_right_var, texts["room_hint"]
        )

        def limit_player(*_args):
            self._limit_player_var(player_var)

        player_var.trace_add("write", limit_player)

        buttons = tk.Frame(footer, bg=BG)
        buttons.pack(side="bottom", anchor="e", pady=(4, 0))

        def join():
            current = self._save_profile(player_var, job_var, sub_job_var, window)
            if current is None:
                return
            room_id = f"{room_left_var.get()}-{room_right_var.get()}"
            if len(room_left_var.get()) != 4 or len(room_right_var.get()) != 4:
                self._alert(texts["join"], texts["invalid_room"])
                return
            join_button.configure(state="disabled")
            self.party_client.join_room(room_id, current, success, failure)

        def success(result):
            self.config["party_last_room_id"] = result["room_id"]
            self._remember_session(result, "member")
            self._start_session_log()
            self._append_session_log("log_joined", name=self._saved_profile().get("player_id", "?"))
            if self._window_exists(window):
                close()
            self.message_callback(texts["joined"].format(room_id=result["room_id"]), 2400)
            self.root.after_idle(self.open_settings)

        def failure(error):
            if not self._window_exists(window):
                return
            join_button.configure(state="normal")
            self._alert(texts["join"], self._localized_error(error))

        join_button = self._button(buttons, texts["join_button"], join)
        join_button.configure(pady=10)
        join_button.pack(side="left", padx=(0, 6))
        close_button = self._button(buttons, texts["close"], close)
        close_button.configure(pady=10)
        close_button.pack(side="left")
        window.bind("<Return>", lambda _event: join())
        window.after_idle((room_left_entry if profile.get("player_id") else player_entry).focus_set)

    def open_settings(self):
        if not self.joined:
            self.open_join_dialog()
            return
        if self._show_existing(self.settings_window):
            return
        self.log_visible = False
        texts = self.texts()
        window, _content, body, close = self._create_dialog(
            texts["settings"], 460, 580, show_header_close=False, modal=False,
            position_key="party_room_overview",
        )
        self.settings_window = window
        window.bind(
            "<Destroy>",
            lambda event: self._cancel_member_marquees() if event.widget is window else None,
            add="+",
        )
        style = ttk.Style(window)
        style.configure("Party.TFrame", background=BG)
        body.configure(style="Party.TFrame")
        main_panel = tk.Frame(body, bg=BG)
        self.settings_main_panel = main_panel
        main_panel.pack(side="left", fill="both", expand=True)
        self.log_panel = tk.Frame(body, bg="#17130f", width=290, highlightthickness=1,
                                  highlightbackground="#6f5c3e")
        self.log_panel.pack_propagate(False)
        tk.Label(
            self.log_panel, text=texts["session_log"], bg=HEADER, fg="#ffe3a1",
            font=("Malgun Gothic", 10, "bold"), anchor="w", padx=12, pady=8,
        ).pack(fill="x")
        self.log_text = tk.Text(
            self.log_panel, bg="#17130f", fg="#d7c59d", insertbackground="#d7c59d",
            relief="flat", bd=0, padx=10, pady=8, wrap="word", state="disabled",
            font=("Consolas", 9), cursor="arrow",
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.bind("<MouseWheel>", self._scroll_session_log)
        self.log_text.bind("<Prior>", lambda _event: self._scroll_session_log_page(-1))
        self.log_text.bind("<Next>", lambda _event: self._scroll_session_log_page(1))
        self._render_session_log()
        room_id = self.party_client.room_id or "-"
        room_header = tk.Frame(main_panel, bg=BG, padx=18, pady=7)
        room_header.pack(fill="x")
        tk.Label(room_header, text=f"{texts['room_id']} : {room_id}", bg=BG, fg="#ffe3a1",
                 font=("Consolas", 12, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
        copy_button = self._button(room_header, texts["copy"], lambda: self._copy_room_id(room_id, copy_button))
        copy_button.pack(side="right")
        self.expiration_label = tk.Label(
            main_panel, text="", bg=BG, fg="#cbb584", anchor="w", padx=18,
            font=("Malgun Gothic", 9, "bold"),
        )
        self.expiration_label.pack(side="top", fill="x", pady=(0, 4))
        self._update_expiration_label()
        footer = tk.Frame(main_panel, bg=BG)
        footer.pack(side="bottom", fill="x", padx=12, pady=(2, 8))

        def close_overview():
            if self.log_visible:
                self._toggle_log_panel(main_panel)
            self._cancel_member_marquees()
            close()

        self._button(footer, texts["log"], lambda: self._toggle_log_panel(main_panel)).pack(side="left")
        bulk_button = self._button(footer, texts["buff_control"], self._control_all_buff_tracking)
        bulk_button.pack(side="left", padx=(6, 0))
        self._button(footer, texts["close"], close_overview).pack(side="right")
        self._button(footer, texts["leave_short"], lambda: self._leave_from_settings(close_overview)).pack(
            side="right", padx=(0, 6),
        )
        list_header = tk.Frame(main_panel, bg=BG)
        list_header.pack(side="top", fill="x", padx=16, pady=(0, 4))
        self.member_count_label = tk.Label(
            list_header, text="", bg=BG, fg="#cbb584", anchor="w",
            font=("Malgun Gothic", 8),
        )
        self.member_count_label.pack(side="left")
        list_area = tk.Frame(main_panel, bg=BG)
        list_area.pack(side="top", fill="both", expand=True, padx=14, pady=(0, 6))
        canvas = tk.Canvas(list_area, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(
            list_area, orient="vertical", command=canvas.yview, width=16,
            bg="#8f7a52", troughcolor="#17130f", activebackground="#d8b15a",
            relief="flat", bd=0, highlightthickness=0,
        )
        self.member_list_frame = tk.Frame(canvas, bg=BG)
        inner_id = canvas.create_window((0, 0), window=self.member_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.member_list_frame.bind(
            "<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(inner_id, width=event.width))
        self._refresh_member_list()

    def refresh_language(self):
        if not self._window_exists(self.settings_window):
            return
        log_was_visible = self.log_visible
        try:
            self._save_dialog_position(self.settings_window)
            self.log_visible = False
            self._cancel_member_marquees()
            self.settings_window.destroy()
        except tk.TclError:
            return
        self.open_settings()
        if log_was_visible and self.settings_main_panel and self._window_exists(self.settings_window):
            self._toggle_log_panel(self.settings_main_panel)

    def _privacy_footer(self, body, notice):
        footer = tk.Frame(body, bg=BG)
        tk.Label(
            footer, text=notice, bg=BG, fg="#d8b15a", justify="left", anchor="w",
            wraplength=0, font=("Malgun Gothic", 7),
        ).pack(side="top", fill="x")
        return footer

    def _saved_profile(self):
        profile = self.config.get("party_profile", {})
        return profile if isinstance(profile, dict) else {}

    def _save_profile(self, player_var, job_var, sub_job_var, window):
        player_id = normalize_player_id(player_var.get())
        if not player_id:
            self._alert(self.texts()["party"], self.texts()["invalid_player"])
            return None
        profile = {"player_id": player_id, "job": self._canonical_job(job_var.get()),
                   "sub_job": self._canonical_sub_job(sub_job_var.get())}
        self.config["party_profile"] = profile
        self.save_config()
        return {"display_name": player_id, "job": profile["job"], "sub_job": profile["sub_job"]}

    def _limit_player_var(self, variable):
        cleaned = normalize_player_id(variable.get())
        if cleaned != variable.get():
            variable.set(cleaned)

    def _configure_form_style(self, window):
        style = ttk.Style(window)
        style.theme_use("clam")
        style.configure("Party.TFrame", background=BG)
        style.configure("Party.TLabel", background=BG, foreground=TEXT)
        style.configure(
            "Party.TEntry", fieldbackground=FIELD, foreground="#fff0c9", insertcolor="#fff0c9",
            bordercolor="#8f7a52", lightcolor="#8f7a52", darkcolor="#8f7a52",
        )
        style.configure(
            "Party.TCombobox", fieldbackground=FIELD, background=FIELD, foreground="#fff0c9",
            arrowcolor="#f1d28c", bordercolor="#8f7a52",
        )
        style.map(
            "Party.TCombobox", fieldbackground=[("readonly", FIELD)], background=[("readonly", FIELD)],
            foreground=[("readonly", "#fff0c9")], selectbackground=[("readonly", FIELD)],
            selectforeground=[("readonly", "#fff0c9")],
        )
        window.option_add("*TCombobox*Listbox.background", FIELD)
        window.option_add("*TCombobox*Listbox.foreground", "#fff0c9")
        window.option_add("*TCombobox*Listbox.selectBackground", HEADER)
        window.option_add("*TCombobox*Listbox.selectForeground", "#fff4d2")

    def _add_field(self, body, row, label, variable, hint="", values=None):
        ttk.Label(body, text=label, style="Party.TLabel").grid(row=row, column=0, sticky="w")
        widget = (
            ttk.Combobox(body, textvariable=variable, values=values, state="readonly", style="Party.TCombobox")
            if values else ttk.Entry(body, textvariable=variable, style="Party.TEntry")
        )
        widget.grid(row=row + 1, column=0, sticky="ew", pady=(4, 2))
        if hint:
            tk.Label(body, text=hint, bg=BG, fg="#a99570", anchor="w", font=("Malgun Gothic", 8)).grid(
                row=row + 2, column=0, sticky="w", pady=(0, 10)
            )
        return widget

    def _add_compact_job_fields(self, body, row, job_var, sub_job_var):
        texts = self.texts()
        holder = ttk.Frame(body, style="Party.TFrame")
        holder.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        holder.columnconfigure((0, 1), weight=1, uniform="party_job")
        ttk.Label(holder, text=texts["job"], style="Party.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(holder, text=texts["sub_job"], style="Party.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Combobox(
            holder, textvariable=job_var, values=tuple(self._job_label(job) for job in JOBS),
            state="readonly", style="Party.TCombobox",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Combobox(
            holder, textvariable=sub_job_var, values=tuple(self._sub_job_label(job) for job in SUB_JOBS),
            state="readonly", style="Party.TCombobox",
        ).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))

    def _add_room_code_field(self, body, row, label, left_var, right_var, hint):
        ttk.Label(body, text=label, style="Party.TLabel").grid(row=row, column=0, sticky="w")
        holder = tk.Frame(body, bg=BG)
        holder.grid(row=row + 1, column=0, sticky="ew", pady=(4, 2))
        holder.columnconfigure(0, weight=1)
        holder.columnconfigure(2, weight=1)
        left = ttk.Entry(holder, textvariable=left_var, justify="center", style="Party.TEntry", font=("Consolas", 13, "bold"))
        right = ttk.Entry(holder, textvariable=right_var, justify="center", style="Party.TEntry", font=("Consolas", 13, "bold"))
        left.grid(row=0, column=0, sticky="ew")
        tk.Label(holder, text="−", bg=BG, fg="#d8b15a", font=("Consolas", 15, "bold"), padx=8).grid(row=0, column=1)
        right.grid(row=0, column=2, sticky="ew")
        clear_button = tk.Button(
            holder, text=self.texts()["clear"], command=lambda: (left_var.set(""), right_var.set(""), left.focus_set()),
            bg=FIELD, fg="#f3d68f", activebackground=HEADER, activeforeground="#fff4d2",
            relief="flat", bd=0, padx=9, pady=3, font=("Malgun Gothic", 8, "bold"), cursor="hand2",
        )
        clear_button.grid(row=0, column=3, sticky="ns", padx=(8, 0))
        allowed = frozenset("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        changing = {"value": False}

        def normalize(source, other, move=False):
            if changing["value"]:
                return
            changing["value"] = True
            compact = "".join(ch for ch in unicodedata.normalize("NFKC", source.get()).upper() if ch in allowed)
            if len(compact) > 4 and not other.get():
                other.set(compact[4:8])
            source.set(compact[:4])
            changing["value"] = False
            if move and len(source.get()) == 4:
                right.focus_set()

        left_var.trace_add("write", lambda *_args: normalize(left_var, right_var, True))
        right_var.trace_add("write", lambda *_args: normalize(right_var, left_var))
        tk.Label(body, text=hint, bg=BG, fg="#a99570", anchor="w", font=("Malgun Gothic", 8)).grid(
            row=row + 2, column=0, sticky="w", pady=(0, 10)
        )
        return left, right

    def _copy_room_id(self, room_id, button=None):
        if not room_id or room_id == "-":
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(room_id)
        self.message_callback(self.texts()["copied"], 1800)
        if button and button.winfo_exists():
            original = button.cget("text")
            button.configure(text="COPY")
            self.root.after(900, lambda: button.winfo_exists() and button.configure(text=original))

    def _show_member_menu(self, event, member):
        texts = self.texts()
        member_id = member.get("member_id")
        buff_blocked = member.get("job") in NON_BUFF_SHARING_JOBS
        preferences = self.tracking_preferences.setdefault(
            member_id, {"position": True, "buff": self._default_buff_tracking(member)},
        )
        if buff_blocked:
            preferences["buff"] = False
        menu = tk.Menu(self.root, tearoff=False, bg=FIELD, fg=TEXT, activebackground=HEADER, activeforeground="#fff4d2")
        for key, label_key in (("position", "track_position"), ("buff", "track_buff")):
            status = texts["enabled"] if preferences.get(key, True) else texts["disabled"]
            menu.add_command(
                label=f"{texts[label_key]}: {status}",
                state="disabled" if key == "buff" and buff_blocked else "normal",
                command=lambda current=key: self._toggle_tracking(member_id, current),
            )
        state = member.get("state") or {}
        menu.add_command(label=texts["portal_copy"], state="normal" if state.get("map_id") else "disabled",
                         command=lambda: self._copy_portal_command(member))
        own = self.members.get(self.party_client.member_id) or {}
        if own.get("role") == "leader":
            menu.add_separator()
            menu.add_command(label=texts["transfer"], command=lambda: self._transfer_leader(member))
            menu.add_command(label=texts["remove"], command=lambda: self._manage_member(member, "remove"))
            menu.add_command(label=texts["ban"], command=lambda: self._manage_member(member, "ban"))
        menu.tk_popup(event.x_root, event.y_root)

    def _show_member_menu_for_button(self, button, member):
        event = type("MenuEvent", (), {"x_root": button.winfo_rootx(), "y_root": button.winfo_rooty() + button.winfo_height()})()
        self._show_member_menu(event, member)

    def _toggle_tracking(self, member_id, key):
        member = self.members.get(member_id) or {}
        preferences = self.tracking_preferences.setdefault(
            member_id, {"position": True, "buff": self._default_buff_tracking(member)},
        )
        preferences[key] = not preferences.get(key, True)
        self.save_config()
        if key == "position":
            self._apply_party_positions()
        elif key == "buff":
            self._refresh_buff_bar()

    def _leave_from_settings(self, close):
        was_joined = self.joined
        self.join_or_leave()
        if was_joined and not self.joined:
            close()

    def can_disband(self):
        return self.joined and self._is_leader()

    def disband_room(self):
        if not self._is_leader():
            return
        texts = self.texts()
        if self._confirm(texts["disband"], texts["confirm_disband"]):
            if not self.party_client.send({"type": "disband_room"}):
                self._alert(texts["disband"], texts["server_unreachable"])

    def _default_buff_tracking(self, member):
        own_job = self._saved_profile().get("job")
        return own_job == "마법사" and member.get("job") not in NON_BUFF_SHARING_JOBS

    def _control_all_buff_tracking(self):
        own_id = self.party_client.member_id
        self._initialize_member_tracking()
        eligible = [
            member for member in self.members.values()
            if member.get("member_id") != own_id and member.get("job") not in NON_BUFF_SHARING_JOBS
        ]
        any_enabled = any(
            self.tracking_preferences.get(member.get("member_id"), {}).get(
                "buff", self._default_buff_tracking(member),
            )
            for member in eligible
        )
        for member in eligible:
            preferences = self.tracking_preferences.setdefault(
                member.get("member_id"), {"position": True, "buff": False},
            )
            preferences["buff"] = not any_enabled
        self.save_config()
        self._refresh_buff_bar()

    def _transfer_leader(self, member):
        texts = self.texts()
        name = member.get("display_name", "?")
        if self._confirm(texts["party"], texts["confirm_transfer"].format(name=name)):
            self.party_client.send({"type": "transfer_leader", "target_id": member.get("member_id")})

    def _copy_portal_command(self, member):
        state = member.get("state") or {}
        map_id = state.get("map_id")
        record = next((item for item in self.map_engine.maps if str(item.get("id", "")) == str(map_id)), None) if self.map_engine else None
        if not record:
            self.message_callback(self.texts()["portal_unavailable"], 1800)
            return
        destination = self.map_engine.preferred_map_name(record, self.language()) or str(map_id)
        command = self.map_engine.favorite_command(destination, self.language())
        self.root.clipboard_clear()
        self.root.clipboard_append(command)
        self.message_callback(self.texts()["portal_copied"], 1800)

    def _manage_member(self, member, action):
        texts = self.texts()
        name = member.get("display_name", "?")
        prompt = texts["confirm_ban" if action == "ban" else "confirm_remove"].format(name=name)
        if not self._confirm(texts["party"], prompt):
            return
        self.party_client.send({"type": "manage_member", "action": action, "target_id": member.get("member_id")})

    def _show_room_dialog(self, room_id):
        texts = self.texts()
        window, _content, body, close = self._create_dialog(texts["create"], 420, 230)
        self.room_window = window
        style = ttk.Style(window)
        style.configure("Party.TFrame", background=BG)
        body.configure(style="Party.TFrame")
        tk.Label(body, text=texts["room_id"], bg=BG, fg="#a99570", font=("Malgun Gothic", 9)).pack(pady=(24, 6))
        tk.Label(body, text=room_id, bg=BG, fg="#ffe3a1", font=("Consolas", 22, "bold")).pack()

        buttons = tk.Frame(body, bg=BG)
        buttons.pack(anchor="e", padx=12, pady=(22, 12))
        copy_button = self._button(buttons, texts["copy"], lambda: self._copy_room_id(room_id, copy_button))
        copy_button.pack(side="left", padx=(0, 6))
        self._button(buttons, texts["close"], close).pack(side="left")

        def open_settings_after_close(event):
            if event.widget is window and self.joined:
                try:
                    self.root.after_idle(self.open_settings)
                except tk.TclError:
                    pass

        window.bind("<Destroy>", open_settings_after_close, add="+")

    def _on_client_state(self, state, detail):
        texts = self.texts()
        if state == "reconnecting":
            self.message_callback(texts["reconnecting"], 2200)
        elif state == "closed":
            if detail == "admin_disbanded":
                self._alert(texts["party"], texts["admin_room_closed"])
            else:
                self.message_callback(texts["room_closed"], 2400)
        elif state == "connected":
            self.message_callback(texts["connected_room"].format(room_id=detail), 1800)
            self._send_local_buff_presence(force=True)
        elif state == "expired":
            self.message_callback(texts["expired"], 2400)
        elif state == "removed":
            self.message_callback(texts["banned"] if detail == "ban" else texts["removed"], 2800)
        if state in {"left", "closed", "expired", "removed"}:
            self._forget_session()
            self.members.clear()
            self.session_color_assignments.clear()
            self.last_position = None
            self._apply_party_positions()
            self._refresh_member_list()
            self._clear_session_log()
            self.remote_buff_timers.clear()
            self.last_sent_buff_presence = object()
            self._refresh_buff_bar()

    def _on_client_event(self, event):
        event_type = event.get("type")
        if event_type == "room_snapshot":
            self._restore_server_session_logs(event.get("session_logs"))
            self.members = {
                member["member_id"]: member for member in event.get("members", [])
                if isinstance(member, dict) and member.get("member_id")
            }
            self._assign_party_member_colors()
            self._initialize_remote_buff_timers()
            self._sync_session_role()
        elif event_type == "member_connected":
            member = event.get("member")
            if isinstance(member, dict) and member.get("member_id"):
                is_new_member = member["member_id"] not in self.members
                self.members[member["member_id"]] = member
                self._assign_party_member_color(member)
                if is_new_member and member["member_id"] != self.party_client.member_id:
                    self._append_session_log("log_joined", name=member.get("display_name", "?"))
        elif event_type in {"member_disconnected", "member_left", "member_removed"}:
            member_id = event.get("member_id")
            member = self.members.get(member_id) or {}
            name = member.get("display_name", "?")
            if event_type in {"member_left", "member_removed"}:
                self.members.pop(member_id, None)
                self.session_color_assignments.pop(member_id, None)
                if event_type == "member_left":
                    self._append_session_log("log_left", name=name)
                else:
                    key = "log_banned" if event.get("reason") == "ban" else "log_removed"
                    self._append_session_log(key, name=name)
            elif member_id in self.members:
                self.members[member_id]["connected"] = False
        elif event_type == "position_update":
            member = self.members.get(event.get("member_id"))
            if member is not None:
                member.setdefault("state", {}).update({
                    "map_id": event.get("map_id"), "x": event.get("x"), "y": event.get("y"),
                })
                self._update_member_row(event.get("member_id"))
        elif event_type == "buff_state":
            member_id = event.get("member_id")
            member = self.members.get(member_id)
            if member is not None:
                present = event.get("present") is True and event.get("buff") in {"fire", "ice"}
                member.setdefault("state", {}).update({
                    "buff": event.get("buff") if present else None,
                    "buff_present": present,
                })
                self._update_remote_buff_timer(member_id, event.get("buff") if present else None)
        elif event_type == "leader_changed":
            successor_id = event.get("member_id")
            for member_id, member in self.members.items():
                member["role"] = "leader" if member_id == successor_id else "member"
            successor = self.members.get(successor_id) or {}
            self._append_session_log("log_transferred", name=successor.get("display_name", "?"))
            self._sync_session_role()
        if event_type != "position_update":
            self._initialize_member_tracking()
            self._refresh_member_list()
            self._refresh_buff_bar()
        self._apply_party_positions()

    def _assign_party_member_colors(self):
        active_ids = set(self.members)
        for member_id in list(self.session_color_assignments):
            if member_id not in active_ids:
                self.session_color_assignments.pop(member_id, None)
        members = sorted(
            self.members.values(),
            key=lambda item: (item.get("role") != "leader", item.get("display_name", "")),
        )
        for member in members:
            self._assign_party_member_color(member)

    def _assign_party_member_color(self, member):
        member_id = member.get("member_id")
        if not member_id:
            return
        color = self.session_color_assignments.get(member_id)
        if color is None:
            used = set(self.session_color_assignments.values())
            color = next((candidate for candidate in PARTY_MEMBER_COLORS if candidate not in used), PARTY_MEMBER_COLORS[0])
            self.session_color_assignments[member_id] = color
        member["color"] = color

    def _sync_session_role(self):
        own = self.members.get(self.party_client.member_id)
        session = self.config.get("party_session")
        if own and isinstance(session, dict) and session.get("role") != own.get("role"):
            session["role"] = own.get("role", "member")
            self.save_config()

    def _is_leader(self):
        return (self.members.get(self.party_client.member_id) or {}).get("role") == "leader"

    def sync_position(self):
        if not self.joined or not self.party_client.connected or not self.map_engine:
            return
        active_map = self.map_engine.active_map
        coordinate = self.map_engine.current_game_coordinate
        if not active_map or not coordinate:
            return
        position = (str(active_map.get("id", "")), int(coordinate[0]), int(coordinate[1]))
        now = time.monotonic()
        if position == self.last_position and now - self.last_position_sent_at < 5.0:
            return
        if now - self.last_position_sent_at < 0.5:
            return
        if self.party_client.send({"type": "position_update", "map_id": position[0], "x": position[1], "y": position[2]}):
            self.last_position = position
            self.last_position_sent_at = now
            own = self.members.get(self.party_client.member_id)
            if own is not None:
                own.setdefault("state", {}).update({"map_id": position[0], "x": position[1], "y": position[2]})
                self._update_member_row(self.party_client.member_id)

    def _apply_party_positions(self):
        if not self.map_engine:
            return
        positions = []
        for member_id, member in self.members.items():
            if member_id == self.party_client.member_id or not member.get("connected"):
                continue
            preferences = self.tracking_preferences.get(member_id, {})
            if preferences.get("position", True) is False:
                continue
            state = member.get("state") or {}
            if state.get("map_id") and isinstance(state.get("x"), int) and isinstance(state.get("y"), int):
                positions.append({
                    "member_id": member_id, "display_name": member.get("display_name", "?"),
                    "map_id": state["map_id"], "x": state["x"], "y": state["y"],
                    "color": member.get("color", "#39D6FF"),
                })
        self.map_engine.set_party_positions(positions)

    def _refresh_member_list(self):
        frame = self.member_list_frame
        if not self._window_exists(self.settings_window) or not frame or not frame.winfo_exists():
            return
        self._cancel_member_marquees()
        for child in frame.winfo_children():
            child.destroy()
        self.member_row_widgets.clear()
        members = list(self.members.values())
        texts = self.texts()
        if self.member_count_label and self.member_count_label.winfo_exists():
            self.member_count_label.configure(text=texts["member_count"].format(
                count=len(members), full=texts["member_full"] if len(members) >= 8 else "",
            ))
        if not members:
            tk.Label(frame, text=texts["waiting"], bg=BG, fg="#a99570").pack(pady=32)
            return
        members.sort(key=lambda item: (item.get("role") != "leader", item.get("display_name", "")))
        frame.columnconfigure(0, weight=1, uniform="party_member")
        frame.columnconfigure(1, weight=1, uniform="party_member")
        for index, member in enumerate(members):
            state = member.get("state") or {}
            connected = bool(member.get("connected"))
            row = tk.Frame(frame, bg=FIELD, highlightthickness=1, highlightbackground="#6f5c3e")
            row.grid(row=index // 2, column=index % 2, sticky="nsew", padx=3, pady=3)
            color = member.get("color", "#39D6FF")
            crown = tk.Label(
                row, text="♛" if member.get("role") == "leader" else "", bg=FIELD,
                fg="#ffd166", font=("Segoe UI Symbol", 11, "bold"), width=2,
            )
            crown.grid(row=0, column=0, sticky="nw", padx=(4, 0), pady=(3, 0))
            name_label = tk.Label(row, text=member.get("display_name", "?"), bg=FIELD, fg=TEXT,
                                  font=("Malgun Gothic", 10, "bold"), anchor="w", padx=2, pady=4)
            name_label.configure(fg=color)
            name_label.grid(row=0, column=1, sticky="w")
            job_label = tk.Label(
                row, text=self._short_job_text(member), bg=FIELD, fg="#cbb584",
                anchor="e", padx=7, font=("Malgun Gothic", 9, "bold"),
            )
            job_label.grid(row=0, column=2, sticky="e")
            location_frame = tk.Frame(row, bg=FIELD, height=27)
            location_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(2, 4))
            location_frame.grid_propagate(False)
            location_frame.columnconfigure(1, weight=1)
            status_color = "#72e6a4" if connected else "#9b8b78"
            indicator_label = tk.Label(
                location_frame, text="●" if connected else "○", bg=FIELD, fg=status_color,
                anchor="w", padx=0, pady=0,
            )
            indicator_label.grid(row=0, column=0, sticky="w", padx=(0, 7))
            map_canvas = tk.Canvas(
                location_frame, bg=FIELD, height=25, width=1, bd=0,
                highlightthickness=0, relief="flat",
            )
            map_canvas.grid(row=0, column=1, sticky="ew")
            map_text_item = map_canvas.create_text(
                0, 12, text="", fill=status_color, anchor="w", font=("Malgun Gothic", 9),
            )
            coordinate_label = tk.Label(
                location_frame, text="", bg=FIELD, fg="#d8b15a", anchor="e",
                padx=0, pady=0, font=("Malgun Gothic", 9),
            )
            coordinate_label.grid(row=0, column=2, sticky="e", padx=(7, 0))
            member_id = member.get("member_id")
            self.member_row_widgets[member_id] = {
                "indicator": indicator_label,
                "map_canvas": map_canvas,
                "map_item": map_text_item,
                "coordinate": coordinate_label,
                "map_text": None,
            }
            self._update_member_row(member_id)
            row.columnconfigure(1, weight=1)
            own_card = member.get("member_id") == self.party_client.member_id
            cursor = "arrow" if own_card else "hand2"
            widgets = (
                row, crown, name_label, job_label, location_frame, indicator_label,
                map_canvas, coordinate_label,
            )
            for widget in widgets:
                widget.configure(cursor=cursor)
                widget.bind("<Enter>", lambda _event, card=row, children=widgets: self._schedule_member_card_hover(card, children))
                widget.bind("<Leave>", lambda _event, card=row, children=widgets: self._schedule_member_card_hover(card, children))
                if not own_card:
                    widget.bind("<Button-1>", lambda event, current=member: self._show_member_menu(event, current))

    def _schedule_member_card_hover(self, card, widgets):
        try:
            card.after_idle(lambda: self._sync_member_card_hover(card, widgets))
        except tk.TclError:
            pass

    @staticmethod
    def _sync_member_card_hover(card, widgets):
        try:
            pointer_x, pointer_y = card.winfo_pointerxy()
            left, top = card.winfo_rootx(), card.winfo_rooty()
            hovered = left <= pointer_x < left + card.winfo_width() and top <= pointer_y < top + card.winfo_height()
            background = HEADER if hovered else FIELD
            card.configure(bg=background, highlightbackground=GOLD if hovered else "#6f5c3e")
            for widget in widgets[1:]:
                widget.configure(bg=background)
        except tk.TclError:
            pass

    def _short_job_text(self, member):
        language = self.language()
        job = JOB_SHORT_LABELS.get(language, JOB_SHORT_LABELS["EN"]).get(member.get("job"), "?")
        sub_job = SUB_JOB_SHORT_LABELS.get(language, SUB_JOB_SHORT_LABELS["EN"]).get(member.get("sub_job"), "?")
        return f"{job} · {sub_job}"

    def _member_location_text(self, member):
        state = member.get("state") or {}
        if state.get("map_id") and isinstance(state.get("x"), int) and isinstance(state.get("y"), int):
            return f"{self._localized_map_name(state['map_id'])}  {state['x']}:{state['y']}"
        return self.texts()["no_location"]

    def _member_location_parts(self, member):
        state = member.get("state") or {}
        if state.get("map_id") and isinstance(state.get("x"), int) and isinstance(state.get("y"), int):
            return self._localized_map_name(state["map_id"]), f"{state['x']}:{state['y']}"
        return self.texts()["no_location"], ""

    def _cancel_member_marquee(self, member_id):
        self.member_marquee_states.pop(member_id, None)

    def _cancel_member_marquees(self):
        self.member_marquee_states.clear()
        if self.member_marquee_job:
            try:
                self.root.after_cancel(self.member_marquee_job)
            except (tk.TclError, ValueError):
                pass
            self.member_marquee_job = None

    def _start_member_marquee(self, member_id):
        self._cancel_member_marquee(member_id)
        widgets = self.member_row_widgets.get(member_id)
        if not widgets:
            return
        canvas = widgets["map_canvas"]
        item = widgets["map_item"]
        try:
            canvas.coords(item, 0, 12)
        except tk.TclError:
            return
        self.member_marquee_states[member_id] = {
            "canvas": canvas,
            "item": item,
            "x": 0,
            "phase": "initial_pause",
            "resume_at": time.monotonic() + 1.3,
        }
        self._ensure_member_marquee_tick()

    def _ensure_member_marquee_tick(self):
        if self.member_marquee_job is not None or not self.member_marquee_states:
            return
        try:
            self.member_marquee_job = self.root.after(45, self._tick_member_marquees)
        except tk.TclError:
            self.member_marquee_job = None

    def _tick_member_marquees(self):
        self.member_marquee_job = None
        now = time.monotonic()
        for member_id, state in tuple(self.member_marquee_states.items()):
            widgets = self.member_row_widgets.get(member_id)
            canvas = state["canvas"]
            item = state["item"]
            if not widgets or widgets.get("map_canvas") is not canvas:
                self.member_marquee_states.pop(member_id, None)
                continue
            try:
                if not canvas.winfo_exists():
                    self.member_marquee_states.pop(member_id, None)
                    continue
                if not canvas.winfo_ismapped():
                    continue
                bounds = canvas.bbox(item)
                viewport = canvas.winfo_width()
                if not bounds or viewport <= 1:
                    continue
                text_width = bounds[2] - bounds[0]
                if text_width <= viewport:
                    canvas.coords(item, 0, 12)
                    self.member_marquee_states.pop(member_id, None)
                    continue
                if now < state["resume_at"]:
                    continue
                if state["phase"] == "end_pause":
                    state.update(x=0, phase="initial_pause", resume_at=now + 1.3)
                    canvas.coords(item, 0, 12)
                    continue
                end_x = viewport - text_width
                state["x"] = max(end_x, state["x"] - 1)
                canvas.coords(item, state["x"], 12)
                if state["x"] <= end_x:
                    state.update(phase="end_pause", resume_at=now + 1.1)
            except tk.TclError:
                self.member_marquee_states.pop(member_id, None)
        self._ensure_member_marquee_tick()

    def _update_member_row(self, member_id):
        widgets = self.member_row_widgets.get(member_id)
        member = self.members.get(member_id)
        if not widgets or not member:
            return
        try:
            connected = bool(member.get("connected"))
            color = "#72e6a4" if connected else "#9b8b78"
            map_text, coordinate = self._member_location_parts(member)
            widgets["indicator"].configure(text="●" if connected else "○", fg=color)
            widgets["coordinate"].configure(text=coordinate, fg="#d8b15a")
            widgets["map_canvas"].itemconfigure(widgets["map_item"], fill=color)
            if widgets.get("map_text") != map_text:
                widgets["map_text"] = map_text
                widgets["map_canvas"].itemconfigure(widgets["map_item"], text=map_text)
                widgets["map_canvas"].coords(widgets["map_item"], 0, 12)
                self._start_member_marquee(member_id)
        except tk.TclError:
            self._cancel_member_marquee(member_id)
            self.member_row_widgets.pop(member_id, None)

    def _update_expiration_label(self):
        label = self.expiration_label
        if not label or not self._window_exists(self.settings_window):
            return
        try:
            remaining = max(0.0, float(self.party_client.expires_at or 0) - time.time())
            total_minutes = int((remaining + 59) // 60)
            hours, minutes = divmod(total_minutes, 60)
            label.configure(text=self.texts()["expires_in"].format(hours=hours, minutes=minutes))
            self.settings_window.after(1000, self._update_expiration_label)
        except (tk.TclError, TypeError, ValueError):
            return

    def _start_session_log(self):
        self.session_logs.clear()
        self.log_visible = False
        self.tracking_preferences.clear()
        self.save_config()
        self._render_session_log()

    def _initialize_member_tracking(self):
        own_id = self.party_client.member_id
        current_ids = {
            member_id for member_id in self.members
            if member_id and member_id != own_id
        }
        # The current room snapshot is the source of truth. Preferences left by a
        # previous room/member incarnation must never replace current members.
        for member_id in list(self.tracking_preferences):
            if member_id not in current_ids:
                self.tracking_preferences.pop(member_id, None)
        for member_id, member in self.members.items():
            if member_id == own_id:
                continue
            preferences = self.tracking_preferences.setdefault(
                member_id, {"position": True, "buff": self._default_buff_tracking(member)},
            )
            if member.get("job") in NON_BUFF_SHARING_JOBS:
                preferences["buff"] = False
        self.save_config()

    def _clear_session_log(self):
        self.session_logs.clear()
        self.log_visible = False
        panel = self.log_panel
        if panel and self._window_exists(self.settings_window):
            try:
                panel.pack_forget()
                window = self.settings_window
                rect = self.client_rect()
                target_width = 460
                current_width = window.winfo_width()
                x, y = window.winfo_x() + max(0, current_width - target_width), window.winfo_y()
                if rect:
                    left, top, right, bottom = rect
                    target_width = min(target_width, max(320, right - left - 24))
                    x = max(left, min(x, right - target_width))
                    y = max(top, min(y, bottom - window.winfo_height()))
                    window._party_offset = (x - left, y - top)
                window.geometry(f"{target_width}x{window.winfo_height()}+{x}+{y}")
            except tk.TclError:
                pass
        self._render_session_log()

    def _append_session_log(self, key, **values):
        template = self.texts().get(key, key)
        try:
            message = template.format(**values)
        except (KeyError, ValueError):
            message = template
        self.session_logs.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        del self.session_logs[:-200]
        self._render_session_log()

    def _restore_server_session_logs(self, records):
        if not isinstance(records, list):
            return
        key_by_event = {
            "room_created": "log_room_created",
            "joined": "log_joined",
            "left": "log_left",
            "removed": "log_removed",
            "banned": "log_banned",
            "transferred": "log_transferred",
        }
        restored = []
        for record in records[-200:]:
            if not isinstance(record, dict):
                continue
            key = key_by_event.get(record.get("event"))
            template = self.texts().get(key or "")
            if not template:
                continue
            name = str(record.get("name", "?"))[:64]
            values = {"room_id": name} if record.get("event") == "room_created" else {"name": name}
            try:
                message = template.format(**values)
                timestamp = time.strftime("%H:%M:%S", time.localtime(float(record.get("timestamp", 0))))
            except (KeyError, ValueError, TypeError, OverflowError, OSError):
                continue
            restored.append(f"[{timestamp}] {message}")
        self.session_logs[:] = restored
        self._render_session_log()

    def _render_session_log(self):
        widget = self.log_text
        if not widget:
            return
        try:
            if not widget.winfo_exists():
                return
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("end", "\n".join(self.session_logs) if self.session_logs else self.texts()["no_log"])
            widget.configure(state="disabled")
            widget.see("end")
        except tk.TclError:
            return

    def _scroll_session_log(self, event):
        widget = self.log_text
        if widget and event.delta:
            try:
                widget.yview_scroll(-3 if event.delta > 0 else 3, "units")
            except tk.TclError:
                pass
        return "break"

    def _scroll_session_log_page(self, direction):
        widget = self.log_text
        if widget:
            try:
                widget.yview_scroll(direction, "pages")
            except tk.TclError:
                pass
        return "break"

    def _toggle_log_panel(self, main_panel):
        panel = self.log_panel
        window = self.settings_window
        if not panel or not self._window_exists(window):
            return
        try:
            window.update_idletasks()
            current_width = window.winfo_width()
            current_height = window.winfo_height()
            current_x, current_y = window.winfo_x(), window.winfo_y()
            self.log_visible = not self.log_visible
            if self.log_visible:
                panel.pack(side="left", fill="both", before=main_panel)
                target_width = 750
            else:
                panel.pack_forget()
                target_width = 460
            window.update_idletasks()
            rect = self.client_rect()
            # Keep the party member panel anchored and grow/collapse the log toward the left.
            target_x = current_x - (target_width - current_width)
            if rect:
                left, top, right, bottom = rect
                target_width = min(target_width, max(320, right - left - 24))
                target_x = current_x - (target_width - current_width)
                current_x = max(left, min(target_x, right - target_width))
                current_y = max(top, min(current_y, bottom - current_height))
                window._party_offset = (current_x - left, current_y - top)
            else:
                current_x = max(0, target_x)
            window.geometry(f"{target_width}x{current_height}+{current_x}+{current_y}")
        except tk.TclError:
            return

    def _tracked_buff_members(self):
        if not self.joined:
            return []
        own_id = self.party_client.member_id
        tracked = []
        for member in self.members.values():
            member_id = member.get("member_id")
            if member_id == own_id or member.get("job") in NON_BUFF_SHARING_JOBS:
                continue
            preferences = self.tracking_preferences.get(member_id, {})
            if preferences.get("buff", self._default_buff_tracking(member)):
                tracked.append(member)
        tracked.sort(key=lambda item: (item.get("role") != "leader", item.get("display_name", "")))
        return tracked

    def update_local_buff_presence(self, buff_key):
        self.local_buff_presence = buff_key if buff_key in {"fire", "ice"} else None
        self._send_local_buff_presence()

    def _send_local_buff_presence(self, force=False):
        if not self.joined or not shares_buff_status(self._saved_profile().get("job")):
            return
        if not force and self.local_buff_presence == self.last_sent_buff_presence:
            return
        payload = {
            "type": "buff_state", "present": self.local_buff_presence is not None,
            "buff": self.local_buff_presence,
        }
        if self.party_client.send(payload):
            self.last_sent_buff_presence = self.local_buff_presence

    def _initialize_remote_buff_timers(self):
        self.remote_buff_timers.clear()
        if not self.personal_buff_timer_visible:
            return
        own_id = self.party_client.member_id
        for member_id, member in self.members.items():
            state = member.get("state") or {}
            buff = state.get("buff") if state.get("buff_present") else None
            if member_id != own_id and buff in {"fire", "ice"}:
                self._update_remote_buff_timer(member_id, buff)

    def _update_remote_buff_timer(self, member_id, buff_key):
        if member_id == self.party_client.member_id:
            return
        if not self.personal_buff_timer_visible or buff_key not in {"fire", "ice"}:
            self.remote_buff_timers.pop(member_id, None)
            return
        duration = self.personal_buff_durations.get(buff_key, 598)
        self.remote_buff_timers[member_id] = {
            "buff": buff_key, "end_time": time.monotonic() + duration,
        }

    def _tick_remote_buff_timers(self):
        try:
            now = time.monotonic()
            expired = [
                member_id for member_id, timer in self.remote_buff_timers.items()
                if timer.get("end_time", 0) <= now
            ]
            for member_id in expired:
                self.remote_buff_timers.pop(member_id, None)
            self._update_buff_bar_countdowns(now)
            self.root.after(500, self._tick_remote_buff_timers)
        except tk.TclError:
            return

    def _update_buff_bar_countdowns(self, now=None):
        now = time.monotonic() if now is None else now
        for member_id, items in list(self.buff_timer_canvas_items.items()):
            canvas, shadow_item, text_item = items
            timer = self.remote_buff_timers.get(member_id)
            remaining = max(0, int(timer.get("end_time", 0) - now + 0.999)) if timer else 0
            label = str(remaining) if timer and remaining > 0 else ""
            try:
                canvas.itemconfigure(shadow_item, text=label)
                canvas.itemconfigure(text_item, text=label)
            except tk.TclError:
                self.buff_timer_canvas_items.pop(member_id, None)

    def open_personal_buff_timer(self):
        if self._show_existing(self.personal_timer_window):
            return
        texts = self.texts()
        window, _content, body, close = self._create_dialog(
            texts["personal_buff_timer"], 440, 420, show_header_close=False, modal=False,
        )
        self.personal_timer_window = window
        self._configure_form_style(window)
        body.configure(style="Party.TFrame")
        footer = tk.Frame(body, bg=BG)
        footer.pack(side="bottom", fill="x", padx=18, pady=(6, 14))
        form = ttk.Frame(body, style="Party.TFrame", padding=(18, 14, 18, 0))
        form.pack(side="top", fill="both", expand=True)
        form.columnconfigure(0, weight=1)
        fire_var = tk.StringVar(value=str(self.personal_buff_durations["fire"]))
        ice_var = tk.StringVar(value=str(self.personal_buff_durations["ice"]))
        show_var = tk.BooleanVar(value=self.personal_buff_timer_visible)
        self._add_field(form, 0, texts["fire_crystal"], fire_var, texts["count_seconds"])
        self._add_field(form, 3, texts["ice_crystal"], ice_var, texts["count_seconds"])
        tk.Checkbutton(
            form, text=texts["timer_display"], variable=show_var, bg=BG, fg=TEXT,
            activebackground=BG, activeforeground="#fff4d2", selectcolor=FIELD,
            font=("Malgun Gothic", 9, "bold"), anchor="w",
        ).grid(row=6, column=0, sticky="w", pady=(5, 12))

        def save_and_close():
            try:
                fire_seconds, ice_seconds = int(fire_var.get()), int(ice_var.get())
            except ValueError:
                self._alert(texts["personal_buff_timer"], texts["invalid_seconds"])
                return
            if not 1 <= fire_seconds <= 3600 or not 1 <= ice_seconds <= 3600:
                self._alert(texts["personal_buff_timer"], texts["invalid_seconds"])
                return
            self.personal_buff_durations = {"fire": fire_seconds, "ice": ice_seconds}
            was_visible = self.personal_buff_timer_visible
            self.personal_buff_timer_visible = bool(show_var.get())
            self.config["party_personal_buff_timer"] = {
                "fire_seconds": fire_seconds, "ice_seconds": ice_seconds,
                "show_timer": self.personal_buff_timer_visible,
            }
            self.save_config()
            if self.personal_buff_timer_visible and not was_visible:
                self._initialize_remote_buff_timers()
            elif not self.personal_buff_timer_visible:
                self.remote_buff_timers.clear()
            self._refresh_buff_bar()
            close()

        self._button(footer, texts["close"], save_and_close).pack(side="right")
        tk.Label(
            footer, text=texts["timer_caution"], bg=BG, fg="#d8b15a", justify="left",
            wraplength=285, anchor="w", font=("Malgun Gothic", 8),
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))
        window.bind("<Return>", lambda _event: save_and_close())

    def _ensure_buff_bar_window(self):
        if self._window_exists(self.buff_bar_window):
            return self.buff_bar_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg="#17130f")
        window.withdraw()
        window._party_dragging = False
        window._party_offset = None
        self.buff_bar_window = window
        make_noactivate_toolwindow(window)
        return window

    def _refresh_buff_bar(self):
        # Member/state events may arrive while the user is dragging. Rebuilding the
        # canvases then would lose the release event and let owner-follow snap it back.
        if self.buff_bar_drag_origin and self._window_exists(self.buff_bar_window):
            return
        members = self._tracked_buff_members()
        if self.buff_bar_adjusting:
            members = list(members[:7])
            while len(members) < 7:
                slot = len(members) + 1
                members.append({
                    "member_id": f"preview-{slot}", "display_name": f"SLOT {slot}",
                    "job": "전사", "color": "#ffe3a1", "state": {}, "placeholder": True,
                })
        if not members:
            if self._window_exists(self.buff_bar_window):
                self.buff_bar_window.withdraw()
            self._hide_buff_bar_lock()
            return
        window = self._ensure_buff_bar_window()
        was_visible = bool(window.winfo_viewable())
        previous_position = (window.winfo_x(), window.winfo_y()) if was_visible else None
        for child in window.winfo_children():
            child.destroy()
        window.configure(bg=GOLD if self.buff_bar_adjusting else "#17130f")
        window.attributes("-alpha", self.buff_bar_opacity / 100.0)
        card_holder = tk.Frame(window, bg="#17130f")
        card_holder.pack(side="top", fill="both", expand=True)
        self.buff_bar_images.clear()
        self.buff_timer_canvas_items.clear()
        scale = self.buff_bar_scale
        # Keep visual dimensions proportional all the way down to the supported
        # 50% scale. Larger hard minimums create a dead zone when growing again.
        card_width = max(46, round(92 * scale))
        tag_height = max(13, round(25 * scale))
        blank_height = max(43, round(86 * scale))
        card_height = tag_height + blank_height
        blank_path = RESOURCE_DIR / "assets" / "icons" / "godinavi" / "blank.jpg"
        fire_path = RESOURCE_DIR / "assets" / "buff_timer" / "fire_display.png"
        ice_path = RESOURCE_DIR / "assets" / "buff_timer" / "ice_display.png"
        try:
            with Image.open(blank_path) as source:
                background = ImageTk.PhotoImage(source.convert("RGB").resize(
                    (card_width, blank_height), Image.Resampling.LANCZOS,
                ))
            icon_size = max(19, round(38 * scale))
            icons = {}
            for key, path in (("fire", fire_path), ("ice", ice_path)):
                with Image.open(path) as source:
                    icons[key] = ImageTk.PhotoImage(source.convert("RGBA").resize(
                        (icon_size, icon_size), Image.Resampling.LANCZOS,
                    ))
        except OSError:
            return
        self.buff_bar_images.extend((background, icons["fire"], icons["ice"]))
        for member in members:
            card = tk.Canvas(
                card_holder, bg="#17130f", width=card_width, height=card_height,
                highlightthickness=0, bd=0, cursor="arrow",
            )
            card.pack(side="left", padx=0, pady=0)
            card.create_rectangle(1, 1, card_width - 2, tag_height - 1, fill=HEADER, outline=GOLD, width=1)
            card.create_text(
                card_width // 2, tag_height // 2,
                text=member.get("display_name", "?"), fill=member.get("color", TEXT),
                font=("Malgun Gothic", max(7, round(9 * scale)), "bold"), anchor="center",
            )
            card.create_image(0, tag_height, image=background, anchor="nw")
            state = member.get("state") or {}
            active = state.get("buff") if state.get("buff_present") else None
            keys = (active,) if active in icons else (("fire", "ice") if member.get("placeholder") else ())
            gap = max(3, round(4 * scale))
            total_width = len(keys) * icon_size + max(0, len(keys) - 1) * gap
            start_x = (card_width - total_width) // 2 + icon_size // 2
            icon_y = tag_height + round(blank_height * 0.43)
            for index, key in enumerate(keys):
                card.create_image(start_x + index * (icon_size + gap), icon_y, image=icons[key], anchor="center")
            timer = self.remote_buff_timers.get(member.get("member_id"))
            if self.personal_buff_timer_visible and timer and timer.get("buff") == active:
                remaining = max(0, int(timer.get("end_time", 0) - time.monotonic() + 0.999))
                timer_y = card_height - max(5, round(8 * scale))
                timer_font = ("Consolas", max(17, round(23 * scale)), "bold")
                shadow_item = card.create_text(
                    card_width // 2 + 1, timer_y + 1, text=str(remaining),
                    fill="#18120c", font=timer_font, anchor="s",
                )
                text_item = card.create_text(
                    card_width // 2, timer_y, text=str(remaining),
                    fill="#ffffff", font=timer_font, anchor="s",
                )
                self.buff_timer_canvas_items[member.get("member_id")] = (card, shadow_item, text_item)
            card.bind("<MouseWheel>", self._adjust_buff_bar_opacity)
        window.bind("<MouseWheel>", self._adjust_buff_bar_opacity)
        window.update_idletasks()
        rect = self.client_rect()
        width, height = window.winfo_reqwidth(), window.winfo_reqheight()
        if previous_position:
            x, y = previous_position
        elif rect:
            left, top, right, _bottom = rect
            saved_x = self.config.get("party_buff_bar_offset_x")
            saved_y = self.config.get("party_buff_bar_offset_y")
            x = left + int(saved_x) if saved_x is not None else left + max(0, (right - left - width) // 2)
            y = top + int(saved_y) if saved_y is not None else top + 14
        else:
            x, y = 100, 100
        if rect:
            left, top, right, bottom = rect
            x = max(left, min(x, right - width))
            y = max(top, min(y, bottom - height))
            window._party_offset = (x - left, y - top)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.deiconify()
        owner = self.owner_hwnd()
        if owner:
            attach_above(window, owner, window.winfo_x(), window.winfo_y())
        if self.buff_bar_adjusting:
            self._show_buff_edit_chrome()

    def toggle_buff_bar_adjustment(self):
        self.buff_bar_adjusting = not self.buff_bar_adjusting
        if self.buff_bar_adjusting:
            self._refresh_buff_bar()
            self.message_callback(self.texts()["party_buff_adjusting"], 3200)
        else:
            self.buff_bar_drag_origin = None
            self.buff_bar_resize_origin = None
            if self._window_exists(self.buff_bar_window):
                self.buff_bar_window._party_dragging = False
            self._hide_buff_edit_chrome()
            self.config["party_buff_bar_scale"] = self.buff_bar_scale
            self.config["party_buff_bar_opacity_percent"] = self.buff_bar_opacity
            self.save_config()
            self._refresh_buff_bar()
            self.message_callback(self.texts()["party_buff_saved"], 2200)
        return self.buff_bar_adjusting

    def _begin_buff_bar_drag(self, event):
        if not self.buff_bar_adjusting or not self._window_exists(self.buff_bar_window):
            return
        self.buff_bar_window._party_dragging = True
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass
        self.buff_bar_drag_origin = (
            event.x_root, event.y_root, self.buff_bar_window.winfo_x(), self.buff_bar_window.winfo_y(),
        )

    def _drag_buff_bar(self, event):
        if not self.buff_bar_adjusting or not self.buff_bar_drag_origin:
            return
        start_x, start_y, origin_x, origin_y = self.buff_bar_drag_origin
        x, y = origin_x + event.x_root - start_x, origin_y + event.y_root - start_y
        rect = self.client_rect()
        if rect:
            left, top, right, bottom = rect
            x = max(left, min(x, right - self.buff_bar_window.winfo_width()))
            y = max(top, min(y, bottom - self.buff_bar_window.winfo_height()))
        self.buff_bar_window.geometry(f"+{round(x)}+{round(y)}")
        if rect:
            self.buff_bar_window._party_offset = (round(x - rect[0]), round(y - rect[1]))
        self._position_buff_edit_chrome()

    def _end_buff_bar_drag(self, _event):
        if not self.buff_bar_drag_origin:
            return
        self.buff_bar_drag_origin = None
        try:
            _event.widget.grab_release()
        except tk.TclError:
            pass
        if self._window_exists(self.buff_bar_window):
            self.buff_bar_window._party_dragging = False
        self._save_buff_bar_position()

    def _adjust_buff_bar_opacity(self, event):
        if not self.buff_bar_adjusting or not event.delta:
            return None
        self.buff_bar_opacity = max(50, min(100, self.buff_bar_opacity + (5 if event.delta > 0 else -5)))
        self.config["party_buff_bar_opacity_percent"] = self.buff_bar_opacity
        if self._window_exists(self.buff_bar_window):
            self.buff_bar_window.attributes("-alpha", self.buff_bar_opacity / 100.0)
        return "break"

    def _begin_buff_bar_resize(self, event):
        if not self.buff_bar_adjusting or not self._window_exists(self.buff_bar_window):
            return
        self.buff_bar_window._party_dragging = True
        self.buff_bar_resize_origin = (
            event.x_root, event.y_root, self.buff_bar_scale,
            self.buff_bar_window.winfo_x(), self.buff_bar_window.winfo_y(),
            self.buff_bar_window.winfo_width(), self.buff_bar_window.winfo_height(),
        )
        try:
            event.widget.grab_set_global()
        except tk.TclError:
            try:
                event.widget.grab_set()
            except tk.TclError:
                pass

    def _drag_buff_bar_resize(self, event):
        if not self.buff_bar_resize_origin:
            return
        start_x, start_y, start_scale, window_x, window_y, start_width, start_height = self.buff_bar_resize_origin
        dx, dy = event.x_root - start_x, event.y_root - start_y
        horizontal_ratio = (start_width + dx) / max(1, start_width)
        vertical_ratio = (start_height + dy) / max(1, start_height)
        ratio = (horizontal_ratio + vertical_ratio) / 2.0
        pending_scale = max(0.5, min(2.0, round(start_scale * ratio, 2)))
        if abs(pending_scale - self.buff_bar_scale) < 0.01:
            return
        self.buff_bar_scale = pending_scale
        self.config["party_buff_bar_scale"] = self.buff_bar_scale
        self._refresh_buff_bar()

    def _end_buff_bar_resize(self, event):
        if not self.buff_bar_resize_origin:
            return
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.buff_bar_resize_origin = None
        if self._window_exists(self.buff_bar_window):
            self.buff_bar_window._party_dragging = False
        self.config["party_buff_bar_scale"] = self.buff_bar_scale
        self._position_buff_edit_chrome()
        self._save_buff_bar_position()

    def _save_buff_bar_position(self):
        if not self._window_exists(self.buff_bar_window):
            return
        rect = self.client_rect()
        if rect:
            self.config["party_buff_bar_offset_x"] = self.buff_bar_window.winfo_x() - rect[0]
            self.config["party_buff_bar_offset_y"] = self.buff_bar_window.winfo_y() - rect[1]
            self.buff_bar_window._party_offset = (
                self.config["party_buff_bar_offset_x"], self.config["party_buff_bar_offset_y"],
            )
        self.save_config()

    def _ensure_buff_bar_lock(self):
        if self._window_exists(self.buff_bar_lock_window):
            return self.buff_bar_lock_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        tk.Button(
            window, text="🔓", command=self.toggle_buff_bar_adjustment,
            bg=FIELD, fg="#fff1c9", activebackground=HEADER, activeforeground="#ffffff",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=("Segoe UI Emoji", 12),
        ).pack(fill="both", expand=True, padx=1, pady=1)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.buff_bar_lock_window = window
        return window

    def _ensure_buff_bar_header(self):
        if self._window_exists(self.buff_bar_header_window):
            return self.buff_bar_header_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        label = tk.Label(
            window, text=self.texts()["party_buff_opacity"], bg=HEADER, fg="#fff1c9",
            anchor="w", padx=8, pady=4, cursor="fleur", font=("Malgun Gothic", 8, "bold"),
        )
        label.pack(fill="both", expand=True, padx=1, pady=1)
        label.bind("<ButtonPress-1>", self._begin_buff_bar_drag)
        label.bind("<B1-Motion>", self._drag_buff_bar)
        label.bind("<ButtonRelease-1>", self._end_buff_bar_drag)
        label.bind("<MouseWheel>", self._adjust_buff_bar_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.buff_bar_header_window = window
        return window

    def _ensure_buff_bar_grip(self):
        if self._window_exists(self.buff_bar_grip_window):
            return self.buff_bar_grip_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        grip = tk.Canvas(
            window, width=16, height=16, bg=HEADER, highlightthickness=1,
            highlightbackground=GOLD, cursor="size_nw_se",
        )
        grip.pack(fill="both", expand=True)
        grip.create_line(4, 14, 14, 4, fill="#fff1c9", width=1)
        grip.create_line(9, 14, 14, 9, fill="#fff1c9", width=1)
        grip.bind("<ButtonPress-1>", self._begin_buff_bar_resize)
        grip.bind("<B1-Motion>", self._drag_buff_bar_resize)
        grip.bind("<ButtonRelease-1>", self._end_buff_bar_resize)
        grip.bind("<MouseWheel>", self._adjust_buff_bar_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.buff_bar_grip_window = window
        return window

    def _show_buff_edit_chrome(self):
        windows = (self._ensure_buff_bar_header(), self._ensure_buff_bar_grip(), self._ensure_buff_bar_lock())
        self._position_buff_edit_chrome()
        owner = self.owner_hwnd()
        for window in windows:
            window.deiconify()
            if owner:
                attach_above(window, owner, window.winfo_x(), window.winfo_y())

    def _position_buff_edit_chrome(self):
        bar = self.buff_bar_window
        if not self._window_exists(bar):
            return
        header = self._ensure_buff_bar_header()
        grip = self._ensure_buff_bar_grip()
        header_height = 28
        x, y, width, height = bar.winfo_x(), bar.winfo_y(), bar.winfo_width(), bar.winfo_height()
        rect = self.client_rect()
        header_y = y - header_height - 4
        if rect and header_y < rect[1]:
            header_y = y + height + 4
        header.geometry(f"{max(80, width)}x{header_height}+{x}+{header_y}")
        grip.update_idletasks()
        grip_width, grip_height = grip.winfo_reqwidth(), grip.winfo_reqheight()
        grip.geometry(f"+{x + width - grip_width}+{y + height - grip_height}")
        self._position_buff_bar_lock()

    def _hide_buff_edit_chrome(self):
        for window in (self.buff_bar_header_window, self.buff_bar_grip_window, self.buff_bar_lock_window):
            if self._window_exists(window):
                window.withdraw()

    def _show_buff_bar_lock(self):
        lock = self._ensure_buff_bar_lock()
        self._position_buff_bar_lock()
        lock.deiconify()
        owner = self.owner_hwnd()
        if owner:
            attach_above(lock, owner, lock.winfo_x(), lock.winfo_y())

    def _position_buff_bar_lock(self):
        if not self._window_exists(self.buff_bar_window) or not self._window_exists(self.buff_bar_lock_window):
            return
        self.buff_bar_lock_window.update_idletasks()
        x = self.buff_bar_window.winfo_x() + self.buff_bar_window.winfo_width() + 6
        y = self.buff_bar_window.winfo_y()
        rect = self.client_rect()
        if rect:
            left, top, right, bottom = rect
            lock_width = self.buff_bar_lock_window.winfo_reqwidth()
            lock_height = self.buff_bar_lock_window.winfo_reqheight()
            if x + lock_width > right:
                x = self.buff_bar_window.winfo_x() - lock_width - 6
            x = max(left, min(x, right - lock_width))
            y = max(top, min(y, bottom - lock_height))
        self.buff_bar_lock_window.geometry(f"+{x}+{y}")

    def _hide_buff_bar_lock(self):
        if self._window_exists(self.buff_bar_lock_window):
            self.buff_bar_lock_window.withdraw()

    def _localized_map_name(self, map_id):
        if self.map_engine:
            record = next((item for item in self.map_engine.maps if str(item.get("id", "")) == str(map_id)), None)
            if record:
                return self.map_engine.preferred_map_name(record, self.language()) or str(map_id)
        return str(map_id)

    def _job_label(self, value):
        return JOB_LABELS.get(self.language(), JOB_LABELS["EN"]).get(value, value)

    def _sub_job_label(self, value):
        return SUB_JOB_LABELS.get(self.language(), SUB_JOB_LABELS["EN"]).get(value, value)

    def _canonical_job(self, label):
        labels = JOB_LABELS.get(self.language(), JOB_LABELS["EN"])
        return next((key for key, value in labels.items() if value == label), JOBS[0])

    def _canonical_sub_job(self, label):
        labels = SUB_JOB_LABELS.get(self.language(), SUB_JOB_LABELS["EN"])
        return next((key for key, value in labels.items() if value == label), SUB_JOBS[0])

    def _localized_error(self, error):
        texts = self.texts()
        key_by_message = {
            "입력값을 확인해 주세요.": "input_error",
            "잠시 후 다시 시도해 주세요.": "retry_later",
            "현재 생성 가능한 파티룸이 모두 사용 중입니다.": "rooms_full",
            "파티룸 ID를 확인해 주세요.": "invalid_room",
            "파티 서버에 연결할 수 없습니다.": "server_unreachable",
            "파티 서버 요청에 실패했습니다.": "request_failed",
        }
        return texts.get(key_by_message.get(str(error), ""), str(error))

    def _remember_session(self, result, role):
        self.config["party_session"] = {
            "role": role, "room_id": str(result["room_id"]),
            "member_id": str(result["member_id"]), "member_token": str(result["member_token"]),
            "started_at": time.time(), "expires_at": float(result["expires_at"]),
        }
        self.save_config()

    def _forget_session(self):
        changed = self.config.pop("party_session", None) is not None
        changed = self.config.pop("party_leader_session", None) is not None or changed
        if changed:
            self.save_config()

    def _restore_session(self):
        session = self.config.get("party_session") or self.config.get("party_leader_session")
        if not isinstance(session, dict) or session.get("role") not in {"leader", "member"}:
            return
        try:
            valid = float(session.get("expires_at", 0)) > time.time()
        except (TypeError, ValueError):
            valid = False
        if not valid:
            self._forget_session()
            return
        if self.party_client.resume_session(session):
            key = "restoring" if session.get("role") == "leader" else "restoring_member"
            self.message_callback(self.texts()[key], 2400)
        else:
            self._forget_session()

    def follow_owner(self, client_rect, owner_hwnd):
        if not client_rect or not owner_hwnd:
            return
        left, top, _right, _bottom = client_rect
        for window in (
            self.join_window, self.create_window, self.room_window, self.settings_window,
            self.personal_timer_window,
            self.buff_bar_window,
            *tuple(self.notice_windows),
        ):
            if not window or not window.winfo_exists() or not window.winfo_viewable():
                continue
            if not getattr(window, "_party_dragging", False):
                offset = getattr(window, "_party_offset", None)
                if offset:
                    window.geometry(f"+{left + offset[0]}+{top + offset[1]}")
        if self.buff_bar_adjusting:
            self._position_buff_edit_chrome()

    def _show_existing(self, window):
        if not self._window_exists(window):
            return False
        owner = self.owner_hwnd()
        if owner:
            show_interactive_above_owner(window, owner)
        return True

    def _message_parent(self):
        """Return only a live Tk window; destroyed dialog references raise TclError."""
        for window in (
            getattr(self, "personal_timer_window", None), self.settings_window, self.room_window,
            self.join_window, self.create_window,
        ):
            if self._window_exists(window):
                return window
        return self.root

    @staticmethod
    def _window_exists(window):
        if not window:
            return False
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False

    def _confirm(self, title, message, show_header_close=True):
        texts = self.texts()
        window, _content, body, close = self._create_dialog(
            title, 440, 235, show_header_close=show_header_close,
        )
        self._track_follow_window(window)
        body.configure(style="Party.TFrame", padding=18)
        result = {"value": False}
        tk.Label(
            body, text=message, bg=BG, fg="#f1e5c7", justify="left", anchor="w",
            wraplength=390, font=("Malgun Gothic", 10), padx=8, pady=18,
        ).pack(fill="both", expand=True)
        buttons = tk.Frame(body, bg=BG)
        buttons.pack(side="bottom", anchor="e")

        def finish(value):
            result["value"] = value
            close()

        self._button(buttons, texts["confirm"], lambda: finish(True)).pack(side="left", padx=(0, 6))
        self._button(buttons, texts["cancel"], lambda: finish(False)).pack(side="left")
        window.bind("<Return>", lambda _event: finish(True))
        window.bind("<Escape>", lambda _event: finish(False))
        window.wait_window()
        return result["value"]

    def _alert(self, title, message):
        texts = self.texts()
        window, _content, body, close = self._create_dialog(title or texts["warning"], 420, 220)
        self._track_follow_window(window)
        body.configure(style="Party.TFrame", padding=18)
        tk.Label(
            body, text=message, bg=BG, fg="#f1e5c7", justify="left", anchor="w",
            wraplength=370, font=("Malgun Gothic", 10), padx=8, pady=18,
        ).pack(fill="both", expand=True)
        self._button(body, texts["confirm"], close).pack(side="bottom", anchor="e")
        window.bind("<Return>", lambda _event: close())
        window.bind("<Escape>", lambda _event: close())
        window.wait_window()

    def show_entry_notices(self, latest_version=None):
        self.show_experimental_notice()
        self.show_outdated_notice(latest_version)

    def show_experimental_notice(self):
        if not self.config.get("party_experimental_notice_hidden", False):
            self._show_dismissible_notice(
                self.texts()["experimental_title"],
                self.texts()["experimental_notice"],
                self.texts()["experimental_hide"],
                "party_experimental_notice_hidden",
                True,
                520,
                500,
            )

    def show_outdated_notice(self, latest_version=None, force=False):
        latest_version = str(latest_version or "").strip()
        if (
            latest_version
            and (force or self.config.get("party_outdated_notice_hidden_version") != latest_version)
        ):
            self._show_dismissible_notice(
                self.texts()["outdated_title"],
                self.texts()["outdated_notice"],
                self.texts()["outdated_hide"],
                None if force else "party_outdated_notice_hidden_version",
                latest_version,
                500,
                390,
            )

    def _show_dismissible_notice(self, title, message, checkbox_text, config_key, hidden_value, width, height):
        window, _content, body, close = self._create_dialog(
            title, width, height, show_header_close=False,
        )
        self._track_follow_window(window)

        self._configure_form_style(window)
        body.configure(style="Party.TFrame")
        footer = tk.Frame(body, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=(10, 18))
        dismissed = tk.BooleanVar(value=False)
        tk.Checkbutton(
            footer, text=checkbox_text, variable=dismissed, bg=BG, fg="#d8b15a",
            activebackground=BG, activeforeground="#ffe3a1", selectcolor=FIELD,
            font=("Malgun Gothic", 9), cursor="hand2", highlightthickness=0, bd=0,
        ).pack(side="left")

        def finish():
            if dismissed.get() and config_key:
                self.config[config_key] = hidden_value
                self.save_config()
            close()

        close_button = self._button(footer, self.texts()["close"], finish)
        close_button.configure(pady=9)
        close_button.pack(side="right")
        message_area = tk.Frame(body, bg=BG)
        message_area.pack(side="top", fill="both", expand=True, padx=20, pady=(18, 6))
        tk.Label(
            message_area, text=message, bg=BG, fg="#f1e5c7", justify="left", anchor="nw",
            wraplength=max(320, width - 54), font=("Malgun Gothic", 9),
        ).pack(fill="both", expand=True)
        window.bind("<Return>", lambda _event: finish())
        window.bind("<Escape>", lambda _event: finish())
        window.wait_window()

    def _track_follow_window(self, window):
        if window not in self.notice_windows:
            self.notice_windows.append(window)

        def forget_notice(event):
            if event.widget is window:
                try:
                    self.notice_windows.remove(window)
                except ValueError:
                    pass

        window.bind("<Destroy>", forget_notice, add="+")

    def _button(self, parent, text, command):
        return tk.Button(
            parent, text=text, command=command, bg=FIELD, fg="#f3d68f",
            activebackground=HEADER, activeforeground="#fff4d2", relief="flat", bd=0,
            padx=14, pady=7, font=("Malgun Gothic", 9, "bold"), cursor="hand2",
        )

    def _save_dialog_position(self, window):
        key = getattr(window, "_party_position_key", None)
        rect = self.client_rect()
        if not key or not rect or not self._window_exists(window):
            return
        try:
            actual_offset_x = window.winfo_x() - rect[0]
            actual_offset_y = window.winfo_y() - rect[1]
            # The session log unfolds to the left. Persist the main room panel's
            # anchor so reopening the normal-width overview does not jump left.
            stored_offset_x = actual_offset_x
            if key == "party_room_overview" and self.log_visible:
                stored_offset_x += max(0, window.winfo_width() - 460)
            self.config[f"{key}_offset_x"] = stored_offset_x
            self.config[f"{key}_offset_y"] = actual_offset_y
            window._party_offset = (actual_offset_x, actual_offset_y)
            self.save_config()
        except tk.TclError:
            pass

    def _create_dialog(self, title, width, height, show_header_close=True, modal=True, position_key=None):
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        previous_grab = self.root.grab_current() if modal else None
        if modal:
            window.grab_set()
        content = tk.Frame(window, bg=BG)
        content.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(content, bg=HEADER, height=40, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title_label = tk.Label(
            header, text=title, bg=HEADER, fg="#ffe3a1", font=("Malgun Gothic", 10, "bold"), padx=12,
        )
        title_label.pack(side="left", fill="y")
        close_button = tk.Button(
            header, text="×", bg=BG, fg=TEXT, activebackground="#6a3028", activeforeground="white",
            relief="flat", bd=0, width=4, font=("Segoe UI", 12, "bold"),
        )
        if show_header_close:
            close_button.pack(side="right", fill="y")
        body = ttk.Frame(content)
        body.pack(fill="both", expand=True)

        def close():
            self._save_dialog_position(window)
            if modal:
                try:
                    window.grab_release()
                except tk.TclError:
                    pass
            window.destroy()
            if modal and previous_grab and self._window_exists(previous_grab):
                try:
                    previous_grab.grab_set()
                except tk.TclError:
                    pass

        close_button.configure(command=close)
        window.protocol("WM_DELETE_WINDOW", close)
        rect = self.client_rect()
        if rect:
            left, top, right, bottom = rect
            width = min(width, max(320, right - left - 24))
            height = min(height, max(180, bottom - top - 24))
            saved_x = self.config.get(f"{position_key}_offset_x") if position_key else None
            saved_y = self.config.get(f"{position_key}_offset_y") if position_key else None
            if isinstance(saved_x, (int, float)) and isinstance(saved_y, (int, float)):
                x = max(left, min(left + round(saved_x), right - width))
                y = max(top, min(top + round(saved_y), bottom - height))
            else:
                x = left + max(0, (right - left - width) // 2)
                y = top + max(0, (bottom - top - height) // 2)
        else:
            x = max(0, (window.winfo_screenwidth() - width) // 2)
            y = max(0, (window.winfo_screenheight() - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window._party_offset = (x - rect[0], y - rect[1]) if rect else None
        window._party_position_key = position_key
        window._party_dragging = False

        drag = {"start": None, "origin": None}

        def start_drag(event):
            window._party_dragging = True
            drag["start"] = (event.x_root, event.y_root)
            drag["origin"] = (window.winfo_x(), window.winfo_y())

        def move_drag(event):
            if not drag["start"] or not drag["origin"]:
                return
            sx, sy = drag["start"]
            ox, oy = drag["origin"]
            nx, ny = ox + event.x_root - sx, oy + event.y_root - sy
            rect_now = self.client_rect()
            if rect_now:
                left, top, right, bottom = rect_now
                nx = max(left, min(nx, right - window.winfo_width()))
                ny = max(top, min(ny, bottom - window.winfo_height()))
            window.geometry(f"+{round(nx)}+{round(ny)}")

        def stop_drag(_event):
            window._party_dragging = False
            rect_now = self.client_rect()
            if rect_now:
                window._party_offset = (window.winfo_x() - rect_now[0], window.winfo_y() - rect_now[1])
            self._save_dialog_position(window)

        for widget in (header, title_label):
            widget.bind("<ButtonPress-1>", start_drag)
            widget.bind("<B1-Motion>", move_drag)
            widget.bind("<ButtonRelease-1>", stop_drag)
        owner = self.owner_hwnd()
        if owner:
            show_interactive_above_owner(window, owner)
        return window, content, body, close

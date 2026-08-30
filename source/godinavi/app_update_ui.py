from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import certifi

from app_update_checker import APP_VERSION, extract_patch_notes, fetch_latest_release, is_newer_version
from .window_attachment import attach_above
from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, modal_font_family, place_modal


TEXTS = {
    "KR": {
        "title": "GodiNavi 업데이트", "current": "현재 버전", "latest": "최신 버전", "size": "다운로드 크기",
        "heading": "GodiNavi 2 업데이트", "description": "{current}에서 {target}(으)로 업데이트합니다.",
        "notes": "패치노트", "checking": "새 버전을 확인하고 있습니다...", "latest_status": "현재 최신 버전입니다.",
        "available": "업데이트 내용을 확인한 후 진행해주세요.", "downloading": "새 버전을 다운로드하고 있습니다...",
        "ready": "검증이 완료되었습니다. 가디내비를 재시작해 업데이트합니다.",
        "failed": "업데이트를 확인하거나 다운로드하지 못했습니다.", "missing": "이 릴리스에는 업데이트 EXE 또는 SHA-256 파일이 없습니다.",
        "no_notes": "이 버전에는 패치노트가 제공되지 않았습니다.", "update": "업데이트 시작",
        "later": "나중에", "retry": "다시 시도", "close": "닫기", "release": "GitHub에서 전체 내용 보기",
        "prompt_message": "새로운 업데이트가 감지되었습니다.\n지금 설치하시겠습니까?",
        "prompt_yes": "예", "prompt_tomorrow": "내일 다시 알림",
    },
    "JP": {
        "title": "GodiNaviアップデート", "current": "現在のバージョン", "latest": "最新バージョン", "size": "ダウンロードサイズ",
        "heading": "GodiNavi 2 アップデート", "description": "{current}から{target}へアップデートします。",
        "notes": "パッチノート", "checking": "新しいバージョンを確認しています...", "latest_status": "現在のバージョンは最新です。",
        "available": "更新内容を確認してから実行してください。", "downloading": "新しいバージョンをダウンロードしています...",
        "ready": "検証が完了しました。GodiNaviを再起動して更新します。",
        "failed": "更新の確認またはダウンロードに失敗しました。", "missing": "このリリースには更新EXEまたはSHA-256ファイルがありません。",
        "no_notes": "このバージョンにはパッチノートがありません。", "update": "アップデート開始",
        "later": "後で", "retry": "再試行", "close": "閉じる", "release": "GitHubで全文を見る",
        "prompt_message": "新しいアップデートが見つかりました。\n今すぐインストールしますか？",
        "prompt_yes": "はい", "prompt_tomorrow": "明日もう一度通知",
    },
    "EN": {
        "title": "GodiNavi Update", "current": "Current version", "latest": "Latest version", "size": "Download size",
        "heading": "GodiNavi 2 Update", "description": "Updating from {current} to {target}.",
        "notes": "Patch notes", "checking": "Checking for a new version...", "latest_status": "GodiNavi is up to date.",
        "available": "Review the changes before installing the update.", "downloading": "Downloading the new version...",
        "ready": "Verification complete. GodiNavi will restart to update.",
        "failed": "Could not check or download the update.", "missing": "This release has no updater EXE or SHA-256 file.",
        "no_notes": "No patch notes were provided for this version.", "update": "Start update",
        "later": "Later", "retry": "Retry", "close": "Close", "release": "View full notes on GitHub",
        "prompt_message": "A new update is available.\nWould you like to install it now?",
        "prompt_yes": "Yes", "prompt_tomorrow": "Remind me tomorrow",
    },
}


def reminder_path():
    return Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi" / "update-reminder.json"


def update_prompt_is_snoozed(path=None, today=None):
    path = Path(path) if path else reminder_path()
    today = today or date.today()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        remind_after = date.fromisoformat(str(payload.get("remindAfter", "")))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, AttributeError):
        return False
    return today < remind_after


def snooze_update_prompt(path=None, today=None):
    path = Path(path) if path else reminder_path()
    today = today or date.today()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"remindAfter": (today + timedelta(days=1)).isoformat()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class AppUpdateUI:
    def __init__(self, root, app_dir, language_provider, state_callback=None, shutdown_callback=None, target_rect_provider=None, owner_hwnd_provider=None, prompt_decision_callback=None, preview_decision_callback=None):
        self.root = root
        self.app_dir = Path(app_dir)
        self.language_provider = language_provider
        self.state_callback = state_callback
        self.shutdown_callback = shutdown_callback
        self.target_rect_provider = target_rect_provider
        self.owner_hwnd_provider = owner_hwnd_provider
        self.prompt_decision_callback = prompt_decision_callback
        self.preview_decision_callback = preview_decision_callback
        self.drag_origin = None
        self.state = "idle"
        self.release = None
        self.error = ""
        self.progress = 0
        self.busy = False
        self.window = None
        self.labels = {}
        self.notes = None
        self.progress_canvas = None
        self.primary_button = None
        self.secondary_button = None
        self.prompt_window = None
        self.prompt_preview = False

    @property
    def update_available(self):
        return self.state in ("available", "downloading", "ready")

    def language(self):
        value = self.language_provider()
        return value if value in TEXTS else "EN"

    def check(self, show_window=False):
        if show_window:
            self.open()
        if self.busy:
            return
        self.busy = True
        self.state = "checking"
        self.error = ""
        self._changed()
        threading.Thread(target=self._check_worker, daemon=True, name="godinavi-app-check").start()

    def _check_worker(self):
        try:
            release = fetch_latest_release()
            state = "available" if release.get("update_available", is_newer_version(release["version"])) else "latest"
            self.root.after(0, lambda: self._finish_check(release, state, ""))
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            self.root.after(0, lambda: self._finish_check(None, "error", detail))

    def _finish_check(self, release, state, error):
        self.busy = False
        self.release = release
        self.state = state
        self.error = error
        self._changed()

    def _update_window_visible(self):
        return bool(self.window and self.window.winfo_exists() and self.window.winfo_viewable())

    def _show_update_prompt(self, force=False, preview=False):
        if not force and (self.state != "available" or update_prompt_is_snoozed()):
            return
        if self.prompt_window and self.prompt_window.winfo_exists():
            self.prompt_window.deiconify()
            self.prompt_window.lift()
            activate_modal(self.prompt_window)
            return
        text = TEXTS[self.language()]
        self.prompt_preview = preview
        win = tk.Toplevel(self.root)
        self.prompt_window = win
        win.overrideredirect(True)
        win.configure(bg="#17130f")
        win.transient(self.root)
        frame = tk.Frame(win, bg="#17130f", padx=10, pady=10, highlightbackground="#d8b15a", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        family = modal_font_family(win, self.language())
        header = tk.Frame(frame, bg="#5a4932")
        header.pack(fill="x", pady=(0, 14))
        title = tk.Label(header, text=text["title"], bg="#5a4932", fg="#ffe09a", anchor="w", padx=14, pady=10, font=(family, 12, "bold"))
        title.pack(fill="x")
        message = tk.Label(frame, text=text["prompt_message"], bg="#17130f", fg="#f1e5c7", anchor="w", justify="left", padx=8, pady=10, font=(family, 10))
        message.pack(fill="both", expand=True)
        footer = tk.Frame(frame, bg="#17130f")
        footer.pack(side="bottom", fill="x", pady=(14, 0))
        tk.Button(footer, text=text["prompt_yes"], command=self._accept_update_prompt, relief="flat", bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff", padx=18, pady=7, font=(family, 9, "bold")).pack(side="right")
        tk.Button(footer, text=text["prompt_tomorrow"], command=self._snooze_update_prompt, relief="flat", bg="#2a2118", fg="#f1e5c7", activebackground="#443422", activeforeground="#ffffff", padx=14, pady=7, font=(family, 9)).pack(side="right", padx=(0, 8))
        _owner, bounds = place_modal(win, minimum_width=440, minimum_height=210, position_key="app_update_prompt")
        bind_modal_drag(win, (header, title), lambda: bounds, position_key="app_update_prompt")
        bind_modal_escape(win, self._close_update_prompt)

    def show_update_prompt(self, force=False, preview=False):
        self._show_update_prompt(force, preview)

    def _close_update_prompt(self):
        if self.prompt_window and self.prompt_window.winfo_exists():
            self.prompt_window.destroy()
        self.prompt_window = None

    def _accept_update_prompt(self):
        self._close_update_prompt()
        if self.prompt_preview:
            self.prompt_preview = False
            if self.preview_decision_callback:
                self.preview_decision_callback("accepted")
            return
        if self.prompt_decision_callback:
            self.prompt_decision_callback("accepted")
        # Let Windows finish destroying the owned prompt before attaching the
        # details window. Replacing one owned overlay synchronously can leave
        # the new window behind Godius until the owner is activated again.
        self.root.after_idle(self.open)

    def _snooze_update_prompt(self):
        if self.prompt_preview:
            self._close_update_prompt()
            self.prompt_preview = False
            if self.preview_decision_callback:
                self.preview_decision_callback("declined")
            return
        snooze_update_prompt()
        self._close_update_prompt()
        if self.prompt_decision_callback:
            self.prompt_decision_callback("declined")

    def download(self):
        self._close_update_prompt()
        if self.busy or not self.release:
            return
        if self.release.get("v2"):
            install_root = self.app_dir.parent if self.app_dir.name.lower() == "data" else self.app_dir
            launcher = install_root / "GodiNavi.exe"
            if not launcher.is_file():
                self._download_failed(f"GodiNavi.exe not found: {launcher}")
                return
            subprocess.Popen([str(launcher), "--update"], cwd=str(install_root), close_fds=True)
            if self.shutdown_callback:
                self.shutdown_callback()
            return
        if not self.release.get("exe_url") or not self.release.get("checksum_url"):
            self.state = "missing"
            self._changed()
            return
        if not getattr(sys, "frozen", False):
            self.state = "error"
            self.error = "The EXE patcher is available only in a packaged GodiNavi build."
            self._changed()
            return
        self.busy = True
        self.state = "downloading"
        self.progress = 0
        self._changed()
        threading.Thread(target=self._download_worker, daemon=True, name="godinavi-app-download").start()

    def _download_worker(self):
        try:
            stage_dir = Path(os.environ.get("LOCALAPPDATA", self.app_dir)) / "GodiNavi" / "update-stage"
            stage_dir.mkdir(parents=True, exist_ok=True)
            staged = stage_dir / f"GodiNavi-{self.release['version']}.exe"
            context = ssl.create_default_context(cafile=certifi.where())
            checksum_request = urllib.request.Request(self.release["checksum_url"], headers={"User-Agent": "GodiNavi-Updater/1.0"})
            with urllib.request.urlopen(checksum_request, timeout=30, context=context) as response:
                checksum_text = response.read(4096).decode("ascii", errors="strict")
            match = re.search(r"\b([0-9a-fA-F]{64})\b", checksum_text)
            if not match:
                raise ValueError("Invalid SHA-256 file.")
            expected = match.group(1).lower()
            request = urllib.request.Request(self.release["exe_url"], headers={"User-Agent": "GodiNavi-Updater/1.0"})
            digest = hashlib.sha256()
            downloaded = 0
            total = int(self.release.get("size", 0))
            with urllib.request.urlopen(request, timeout=90, context=context) as response, staged.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > 512 * 1024 * 1024:
                        raise ValueError("The update EXE is too large.")
                    output.write(chunk)
                    digest.update(chunk)
                    self.progress = max(0, min(100, round(downloaded * 100 / total))) if total else 0
                    self.root.after(0, self._refresh)
            if total and downloaded != total:
                raise ValueError("Downloaded EXE size mismatch.")
            if digest.hexdigest().lower() != expected:
                staged.unlink(missing_ok=True)
                raise ValueError("Downloaded EXE SHA-256 mismatch.")
            self.root.after(0, lambda: self._download_ready(staged))
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            self.root.after(0, lambda: self._download_failed(detail))

    def _download_failed(self, error):
        self.busy = False
        self.state = "error"
        self.error = error
        self._changed()

    def _download_ready(self, staged):
        self.busy = False
        self.state = "ready"
        self.progress = 100
        self._changed()
        self.root.after(500, lambda: self._launch_patcher(staged))

    def _launch_patcher(self, staged):
        updater = self.app_dir / "GodiNaviUpdater.exe"
        target = Path(sys.executable).resolve()
        if not updater.is_file():
            self._download_failed(f"GodiNaviUpdater.exe not found: {updater}")
            return
        subprocess.Popen(
            [str(updater), "--staged", str(staged), "--target", str(target), "--pid", str(os.getpid())],
            cwd=str(self.app_dir), close_fds=True,
        )
        if self.shutdown_callback:
            self.shutdown_callback()
        # Tk windows can be gone while OCR executor threads still keep the
        # frozen process alive.  The legacy patcher owns this exact PID and
        # cannot replace GodiNavi.exe until it exits, so finish the update
        # hand-off deterministically after application cleanup.
        os._exit(0)

    def open(self):
        if self.window and self.window.winfo_exists():
            self._present_window()
            self._refresh(); return
        win = tk.Toplevel(self.root)
        self.window = win
        bind_modal_escape(win, self.close)
        win.overrideredirect(True)
        win.configure(bg="#17130f")
        win.geometry("660x560")
        win.minsize(660, 560)
        win.transient(self.root)
        frame = tk.Frame(win, bg="#17130f", padx=14, pady=14, highlightbackground="#d8b15a", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg="#5a4932")
        header.pack(fill="x", pady=(0, 12))
        self.labels["title"] = tk.Label(header, bg="#5a4932", fg="#ffe09a", anchor="w", padx=12, pady=9, font=("Noto Sans KR", 12, "bold"))
        self.labels["title"].pack(side="left", fill="x", expand=True)
        tk.Button(header, text="×", command=self.close, bg="#5a4932", fg="#ffffff", activebackground="#6b5537", activeforeground="#ffffff", relief="flat", bd=0, padx=12, font=("Noto Sans KR", 13, "bold")).pack(side="right", fill="y")
        for widget in (header, self.labels["title"]):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
        self.labels["heading"] = tk.Label(frame, bg="#17130f", fg="#ffe09a", anchor="w", font=("Noto Sans KR", 16, "bold"))
        self.labels["heading"].pack(fill="x")
        self.labels["description"] = tk.Label(frame, bg="#17130f", fg="#f1e5c7", anchor="w", justify="left", font=("Noto Sans KR", 10))
        self.labels["description"].pack(fill="x", pady=(6, 12))
        for key in ("current", "latest", "size"):
            row = tk.Frame(frame, bg="#17130f")
            self.labels[key + "_name"] = tk.Label(row, bg="#17130f", fg="#bda982", anchor="w", width=17, font=("Noto Sans KR", 9))
            self.labels[key + "_name"].pack(side="left")
            self.labels[key] = tk.Label(row, bg="#2a2118", fg="#fff1c9", anchor="w", padx=9, pady=4, font=("Noto Sans KR", 9, "bold"))
            self.labels[key].pack(side="left", fill="x", expand=True)
        self.labels["status"] = tk.Label(frame, bg="#2a2118", fg="#e9bd55", anchor="w", justify="left", padx=10, pady=7, font=("Noto Sans KR", 10, "bold"))
        self.labels["status"].pack(fill="x")
        # Reserve the action area before the expandable patch-note body.  Tk's
        # packer may otherwise clip widgets packed after an expanding Text when
        # the game client is shorter than the requested dialog height.
        buttons = tk.Frame(frame, bg="#17130f")
        buttons.pack(side="bottom", fill="x")
        self.labels["release"] = tk.Label(buttons, bg="#17130f", fg="#72b7e8", cursor="hand2", font=("Noto Sans KR", 8, "underline"))
        self.labels["release"].pack(side="left"); self.labels["release"].bind("<Button-1>", lambda _e: self._open_release())
        self.primary_button = tk.Button(buttons, relief="flat", bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff", padx=14, pady=6, font=("Noto Sans KR", 9, "bold"))
        self.primary_button.pack(side="right")
        self.secondary_button = tk.Button(buttons, command=self.close, relief="flat", bg="#2a2118", fg="#f1e5c7", activebackground="#443422", activeforeground="#ffffff", padx=14, pady=6, font=("Noto Sans KR", 9))
        self.secondary_button.pack(side="right", padx=(0, 7))
        self.progress_canvas = tk.Canvas(frame, height=14, bg="#2a2118", highlightthickness=1, highlightbackground="#5a4932")
        self.progress_canvas.pack(side="bottom", fill="x", pady=(10, 8))
        self.labels["notes_name"] = tk.Label(frame, bg="#17130f", fg="#e9bd55", anchor="w", font=("Noto Sans KR", 10, "bold"))
        notes_frame = tk.Frame(frame, bg="#2a2118")
        notes_frame.pack(fill="both", expand=True, pady=(12, 0))
        scroll = tk.Scrollbar(notes_frame)
        scroll.pack(side="right", fill="y")
        self.notes = tk.Text(notes_frame, bg="#211a14", fg="#f1e5c7", insertbackground="#f1e5c7", relief="flat", wrap="word", padx=10, pady=8, font=("Noto Sans KR", 9), yscrollcommand=scroll.set)
        self.notes.pack(fill="both", expand=True); scroll.configure(command=self.notes.yview)
        self.notes.configure(state="disabled")
        self._center_window()
        self._refresh()
        self._present_window()

    def _present_window(self):
        """Raise the details window above Godius even when opened from an overlay."""
        if not self.window or not self.window.winfo_exists():
            return
        self.window.deiconify()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(self.window, owner, self.window.winfo_x(), self.window.winfo_y())
        self.window.attributes("-topmost", True)
        self.window.lift()
        activate_modal(self.window)

        def restore_owned_z_order():
            if not self.window or not self.window.winfo_exists():
                return
            self.window.attributes("-topmost", False)
            current_owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
            if current_owner:
                attach_above(self.window, current_owner, self.window.winfo_x(), self.window.winfo_y())
            self.window.lift()
            activate_modal(self.window)

        self.window.after(120, restore_owned_z_order)

    def _center_window(self):
        self.window.update_idletasks()
        width, height = self.window.winfo_width(), self.window.winfo_height()
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            left, top, right, bottom = rect
            width = min(width, max(500, right - left - 24))
            height = min(height, max(420, bottom - top - 24))
            x, y = left + (right - left - width) // 2, top + (bottom - top - height) // 2
        else:
            x, y = (self.window.winfo_screenwidth() - width) // 2, (self.window.winfo_screenheight() - height) // 2
        self.window.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def _start_drag(self, event):
        self.drag_origin = event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y()

    def _drag(self, event):
        if self.drag_origin:
            sx, sy, wx, wy = self.drag_origin
            self.window.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")

    def _open_release(self):
        if self.release and self.release.get("url"):
            import webbrowser
            webbrowser.open(self.release["url"], new=2)

    def close(self):
        if self.window and self.window.winfo_exists(): self.window.withdraw()

    def _refresh(self):
        if not self.window or not self.window.winfo_exists(): return
        text = TEXTS[self.language()]
        self.labels["title"].configure(text=text["title"])
        self.labels["heading"].configure(text=text["heading"])
        for key in ("current", "latest", "size"): self.labels[key + "_name"].configure(text=text[key])
        current_version = self.release.get("current_version", APP_VERSION) if self.release else APP_VERSION
        self.labels["current"].configure(text=current_version)
        self.labels["latest"].configure(text=self.release["version"] if self.release else "-")
        target_version = self.release["version"] if self.release else "-"
        self.labels["description"].configure(text=text["description"].format(current=current_version, target=target_version))
        size = int(self.release.get("size", 0)) if self.release else 0
        self.labels["size"].configure(text=f"{size / 1024 / 1024:.1f} MB" if size else "-")
        self.labels["notes_name"].configure(text=text["notes"]); self.labels["release"].configure(text=text["release"])
        notes = extract_patch_notes(self.release.get("body", ""), self.language()) if self.release else ""
        self.notes.configure(state="normal"); self.notes.delete("1.0", "end"); self.notes.insert("1.0", notes or text["no_notes"]); self.notes.configure(state="disabled")
        key = "latest_status" if self.state == "latest" else (self.state if self.state in text else "checking")
        status = text[key]
        if self.state == "downloading": status += f"  {self.progress}%"
        if self.state == "error" and self.error: status += f"\n{self.error}"
        self.labels["status"].configure(text=status, fg="#ff7770" if self.state in ("error", "missing") else "#e9bd55")
        self.progress_canvas.delete("all"); self.progress_canvas.update_idletasks()
        width = max(1, self.progress_canvas.winfo_width() - 2)
        fill = self.progress if self.state == "downloading" else (100 if self.state in ("latest", "ready") else 0)
        self.progress_canvas.create_rectangle(1, 1, 1 + width * fill / 100, 13, fill="#d8b15a", outline="")
        if self.state == "available":
            self.primary_button.configure(text=text["update"], command=self.download, state="normal"); self.secondary_button.configure(text=text["later"])
        elif self.state in ("error", "missing"):
            self.primary_button.configure(text=text["retry"], command=lambda: self.check(False), state="normal"); self.secondary_button.configure(text=text["close"])
        else:
            self.primary_button.configure(text=text["update"], command=self.download, state="disabled"); self.secondary_button.configure(text=text["close"])

    def _changed(self):
        if self.state_callback: self.state_callback()
        self._refresh()

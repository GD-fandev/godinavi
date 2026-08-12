from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path

from map_updater import download_and_install, fetch_manifest, load_local_version, update_is_available


TEXTS = {
    "KR": {
        "title": "지도 데이터 업데이트", "current": "현재 지도 버전", "latest": "최신 지도 버전",
        "size": "다운로드 크기", "checking": "업데이트를 확인하고 있습니다...",
        "latest_status": "현재 최신 지도입니다.", "available": "새 지도 데이터가 있습니다.",
        "downloading": "지도 데이터를 다운로드하고 있습니다...", "installed": "지도 업데이트가 완료되었습니다.",
        "failed": "지도 업데이트를 확인하거나 설치하지 못했습니다.", "update": "업데이트",
        "later": "나중에", "retry": "다시 시도", "close": "닫기",
    },
    "JP": {
        "title": "マップデータ更新", "current": "現在のマップバージョン", "latest": "最新のマップバージョン",
        "size": "ダウンロードサイズ", "checking": "更新を確認しています...",
        "latest_status": "マップは最新です。", "available": "新しいマップデータがあります。",
        "downloading": "マップデータをダウンロードしています...", "installed": "マップ更新が完了しました。",
        "failed": "マップ更新を確認またはインストールできませんでした。", "update": "更新",
        "later": "後で", "retry": "再試行", "close": "閉じる",
    },
    "EN": {
        "title": "Map Data Update", "current": "Current map version", "latest": "Latest map version",
        "size": "Download size", "checking": "Checking for map updates...",
        "latest_status": "Your maps are up to date.", "available": "New map data is available.",
        "downloading": "Downloading map data...", "installed": "Map update completed.",
        "failed": "Could not check or install the map update.", "update": "Update",
        "later": "Later", "retry": "Retry", "close": "Close",
    },
}


class MapUpdateUI:
    def __init__(self, root, app_dir, language_provider, state_callback=None, installed_callback=None):
        self.root = root
        self.app_dir = Path(app_dir)
        self.language_provider = language_provider
        self.state_callback = state_callback
        self.installed_callback = installed_callback
        self.state = "idle"
        self.manifest = None
        self.error = ""
        self.progress = 0
        self.window = None
        self.labels = {}
        self.progress_canvas = None
        self.primary_button = None
        self.secondary_button = None
        self.busy = False

    @property
    def update_available(self):
        return self.state == "available"

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
        threading.Thread(target=self._check_worker, daemon=True, name="godinavi-map-check").start()

    def _check_worker(self):
        try:
            manifest = fetch_manifest()
            state = "available" if update_is_available(load_local_version(self.app_dir), manifest) else "latest"
            self.root.after(0, lambda: self._finish_check(manifest, state, ""))
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            self.root.after(0, lambda: self._finish_check(None, "error", detail))

    def _finish_check(self, manifest, state, error):
        self.busy = False
        self.manifest = manifest
        self.state = state
        self.error = error
        self._changed()

    def install(self):
        if self.busy or not self.manifest:
            return
        self.busy = True
        self.state = "downloading"
        self.progress = 0
        self._changed()
        threading.Thread(target=self._install_worker, daemon=True, name="godinavi-map-install").start()

    def _install_worker(self):
        try:
            result = download_and_install(self.manifest, self.app_dir, self._record_progress)
            self.root.after(0, lambda: self._finish_install(result, ""))
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            self.root.after(0, lambda: self._finish_install(None, detail))

    def _record_progress(self, downloaded, total):
        value = max(0, min(100, round(downloaded * 100 / total))) if total else 0
        if value != self.progress:
            self.progress = value
            self.root.after(0, self._refresh)

    def _finish_install(self, result, error):
        self.busy = False
        self.error = error
        self.state = "installed" if result else "error"
        if result and self.installed_callback:
            self.installed_callback()
        self._changed()

    def _changed(self):
        if self.state_callback:
            self.state_callback()
        self._refresh()

    def open(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self._refresh()
            return
        win = tk.Toplevel(self.root)
        self.window = win
        win.title(TEXTS[self.language()]["title"])
        win.configure(bg="#17130f")
        win.resizable(False, False)
        win.transient(self.root)
        win.protocol("WM_DELETE_WINDOW", self.close)
        frame = tk.Frame(win, bg="#17130f", padx=14, pady=14, highlightbackground="#d8b15a", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        self.labels["title"] = tk.Label(frame, bg="#2a2118", fg="#e9bd55", anchor="w", padx=12, pady=9, font=("Malgun Gothic", 13, "bold"))
        self.labels["title"].pack(fill="x", pady=(0, 12))
        for key in ("current", "latest", "size"):
            row = tk.Frame(frame, bg="#17130f")
            row.pack(fill="x", pady=3)
            self.labels[key + "_name"] = tk.Label(row, bg="#17130f", fg="#bda982", anchor="w", width=19, font=("Malgun Gothic", 9))
            self.labels[key + "_name"].pack(side="left")
            self.labels[key] = tk.Label(row, bg="#2a2118", fg="#fff1c9", anchor="w", padx=9, pady=4, width=24, font=("Malgun Gothic", 9, "bold"))
            self.labels[key].pack(side="left", fill="x", expand=True)
        self.labels["status"] = tk.Label(frame, bg="#17130f", fg="#f1e5c7", anchor="w", justify="left", wraplength=410, pady=12, font=("Malgun Gothic", 9))
        self.labels["status"].pack(fill="x")
        self.progress_canvas = tk.Canvas(frame, height=14, bg="#2a2118", highlightthickness=1, highlightbackground="#5a4932")
        self.progress_canvas.pack(fill="x", pady=(0, 12))
        buttons = tk.Frame(frame, bg="#17130f")
        buttons.pack(fill="x")
        self.primary_button = tk.Button(buttons, relief="flat", bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff", padx=18, pady=6, font=("Malgun Gothic", 9, "bold"))
        self.primary_button.pack(side="right")
        self.secondary_button = tk.Button(buttons, command=self.close, relief="flat", bg="#2a2118", fg="#f1e5c7", activebackground="#443422", activeforeground="#ffffff", padx=18, pady=6, font=("Malgun Gothic", 9))
        self.secondary_button.pack(side="right", padx=(0, 7))
        win.update_idletasks()
        x = max(10, self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = max(10, self.root.winfo_rooty() - win.winfo_reqheight() - 12)
        win.geometry(f"+{x}+{y}")
        self._refresh()

    def close(self):
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

    def _refresh(self):
        if not self.window or not self.window.winfo_exists():
            return
        text = TEXTS[self.language()]
        self.window.title(text["title"])
        self.labels["title"].configure(text=text["title"])
        for key in ("current", "latest", "size"):
            self.labels[key + "_name"].configure(text=text[key])
        self.labels["current"].configure(text=load_local_version(self.app_dir))
        self.labels["latest"].configure(text=self.manifest["version"] if self.manifest else "-")
        size = self.manifest["size"] if self.manifest else 0
        self.labels["size"].configure(text=f"{size / 1024 / 1024:.1f} MB" if size else "-")
        status_key = "latest_status" if self.state == "latest" else (self.state if self.state in text else "checking")
        status = text[status_key]
        if self.state == "downloading":
            status += f"  {self.progress}%"
        elif self.state == "error" and self.error:
            status += f"\n{self.error}"
        self.labels["status"].configure(text=status, fg="#ff7770" if self.state == "error" else "#f1e5c7")
        self.progress_canvas.delete("all")
        self.progress_canvas.update_idletasks()
        width = max(1, self.progress_canvas.winfo_width() - 2)
        fill = self.progress if self.state == "downloading" else (100 if self.state in ("latest", "installed") else 0)
        self.progress_canvas.create_rectangle(1, 1, 1 + width * fill / 100, 13, fill="#d8b15a", outline="")
        if self.state == "available":
            self.primary_button.configure(text=text["update"], command=self.install, state="normal")
            self.secondary_button.configure(text=text["later"])
        elif self.state == "error":
            self.primary_button.configure(text=text["retry"], command=lambda: self.check(False), state="normal")
            self.secondary_button.configure(text=text["close"])
        else:
            self.primary_button.configure(text=text["update"], command=self.install, state="disabled")
            self.secondary_button.configure(text=text["close"])

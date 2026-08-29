"""Visible V1-to-V2 bridge. It only verifies and starts Updater v2."""

from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from v2_contracts import validate_channel, validate_history, validate_manifest
from v2_network import download, fetch_json
from v2_modal_window import bind_modal_drag, modal_font_family, place_modal
from v2_updater_app import history_text, language


BRIDGE_TEXT = {
    "KR": {
        "window_title": "GodiNavi 1.x → 2.x",
        "heading": "GodiNavi 2 마이그레이션",
        "description": "기존 설정을 보존하면서 새로운 구성요소 설치 구조로 전환합니다.",
        "checking": "업데이트 정보를 확인하고 있습니다…",
        "target": "설치 대상: {client} / 콘텐츠 {content}",
        "downloading": "Updater v2 다운로드 중… {percent}%",
        "file_progress": "현재 파일: {name}  {percent}%",
        "overall_progress": "전체 진행률: {current}/{total}",
        "continue": "업데이트 시작",
        "cancel_update": "업데이트 중단",
        "cancelling": "업데이트를 중단하고 있습니다…",
        "cancelled": "업데이트가 중단되었습니다.",
        "close": "닫기",
        "cancel": "취소",
        "error": "V2 설치 준비에 실패했습니다.",
    },
    "JP": {
        "window_title": "GodiNavi 1.x → 2.x",
        "heading": "GodiNavi 2 マイグレーション",
        "description": "既存の設定を保持したまま、新しいコンポーネント構成へ移行します。",
        "checking": "アップデート情報を確認しています…",
        "target": "インストール対象: {client} / コンテンツ {content}",
        "downloading": "Updater v2 をダウンロード中… {percent}%",
        "file_progress": "現在のファイル: {name}  {percent}%",
        "overall_progress": "全体の進行状況: {current}/{total}",
        "continue": "アップデート開始",
        "cancel_update": "アップデート中止",
        "cancelling": "アップデートを中止しています…",
        "cancelled": "アップデートを中止しました。",
        "close": "閉じる",
        "cancel": "キャンセル",
        "error": "V2 インストールの準備に失敗しました。",
    },
    "EN": {
        "window_title": "GodiNavi 1.x → 2.x",
        "heading": "GodiNavi 2 Migration",
        "description": "Move to the new component layout while preserving your existing settings.",
        "checking": "Checking for update information…",
        "target": "Install target: {client} / Content {content}",
        "downloading": "Downloading Updater v2… {percent}%",
        "file_progress": "Current file: {name}  {percent}%",
        "overall_progress": "Overall progress: {current}/{total}",
        "continue": "Start update",
        "cancel_update": "Cancel update",
        "cancelling": "Cancelling the update…",
        "cancelled": "The update was cancelled.",
        "close": "Close",
        "cancel": "Cancel",
        "error": "Could not prepare the V2 installation.",
    },
}


def resource(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / name


class BridgeWindow:
    def __init__(self):
        self.install_root = Path(sys.executable).resolve().parent
        self.code = language()
        self.text = BRIDGE_TEXT[self.code]
        self.root = tk.Tk()
        self.font = modal_font_family(self.root, self.code)
        self.root.title(self.text["window_title"])
        self.events = queue.Queue()
        self.channel = None
        self.manifest = None
        self.history = None
        self.drag_origin = None
        self.cancel_event = threading.Event()
        self.busy = False
        self._build()
        _owner, self.modal_bounds = place_modal(self.root, 660, 560, "bridge")
        threading.Thread(target=self._load, daemon=True).start()
        self.root.after(100, self._poll)

    def _build(self):
        self.root.overrideredirect(True)
        self.root.configure(bg="#17130f")
        frame = tk.Frame(self.root, bg="#17130f", padx=14, pady=14, highlightbackground="#d8b15a", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg="#5a4932")
        header.pack(fill="x", pady=(0, 12))
        title = tk.Label(header, text=self.text["window_title"], bg="#5a4932", fg="#ffe09a", anchor="w", padx=12, pady=9, font=(self.font, 12, "bold"))
        title.pack(side="left", fill="x", expand=True)
        bind_modal_drag(self.root, (header, title), lambda: self.modal_bounds, "bridge")
        tk.Label(frame, text=self.text["heading"], bg="#17130f", fg="#ffe09a", anchor="w", font=(self.font, 16, "bold")).pack(fill="x")
        tk.Label(frame, text=self.text["description"], bg="#17130f", fg="#f1e5c7", anchor="w", justify="left", font=(self.font, 10)).pack(fill="x", pady=(6, 12))
        self.status = tk.Label(frame, text=self.text["checking"], bg="#2a2118", fg="#e9bd55", anchor="w", padx=10, pady=7, font=(self.font, 10, "bold"))
        self.status.pack(fill="x")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("GodiNavi.Horizontal.TProgressbar", troughcolor="#2a2118", background="#d8b15a", bordercolor="#5a4932", lightcolor="#d8b15a", darkcolor="#d8b15a")
        buttons = tk.Frame(frame, bg="#17130f")
        buttons.pack(side="bottom", fill="x")
        self.continue_button = tk.Button(buttons, text=self.text["continue"], command=self.start, state="disabled", bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff", disabledforeground="#8f8068", relief="flat", bd=0, padx=14, pady=7, font=(self.font, 10, "bold"))
        self.continue_button.pack(side="right")
        self.overall_label = tk.Label(frame, text=self.text["overall_progress"].format(current=0, total=1), bg="#17130f", fg="#bda982", anchor="w", font=(self.font, 9))
        self.overall_label.pack(side="bottom", fill="x")
        self.overall_progress = ttk.Progressbar(frame, maximum=100, style="GodiNavi.Horizontal.TProgressbar")
        self.overall_progress.pack(side="bottom", fill="x", pady=(2, 8))
        self.file_label = tk.Label(frame, text=self.text["file_progress"].format(name="GodiNaviUpdater.exe", percent=0), bg="#17130f", fg="#bda982", anchor="w", font=(self.font, 9))
        self.file_label.pack(side="bottom", fill="x")
        self.file_progress = ttk.Progressbar(frame, maximum=100, style="GodiNavi.Horizontal.TProgressbar")
        self.file_progress.pack(side="bottom", fill="x", pady=(2, 8))
        notes_frame = tk.Frame(frame, bg="#211a14")
        notes_frame.pack(fill="both", expand=True, pady=(12, 0))
        scrollbar = tk.Scrollbar(notes_frame)
        scrollbar.pack(side="right", fill="y")
        self.notes = tk.Text(notes_frame, height=12, spacing1=2, spacing3=3, wrap="char", state="disabled", bg="#211a14", fg="#f1e5c7", insertbackground="#f1e5c7", relief="flat", padx=10, pady=8, font=(self.font, 10), yscrollcommand=scrollbar.set)
        self.notes.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.notes.yview)

    def _load(self):
        try:
            self.channel = validate_channel(json.loads(resource("update-channel.json").read_text(encoding="utf-8-sig")))
            self.manifest = validate_manifest(fetch_json(self.channel["manifestUrl"]))
            self.history = validate_history(fetch_json(self.manifest["historyUrl"]))
            self.events.put(("loaded",))
        except Exception as exc:
            self.events.put(("error", exc))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "loaded":
                    self.status.configure(text=self.text["target"].format(
                        client=self.manifest["clientVersion"], content=self.manifest["snapshotVersion"]
                    ))
                    self.notes.configure(state="normal")
                    self.notes.insert("1.0", history_text(self.history, self.code))
                    self.notes.configure(state="disabled")
                    self.continue_button.configure(state="normal")
                    self.root.after_idle(self.start)
                elif event[0] == "progress":
                    percent = event[1]
                    self.file_progress["value"] = percent
                    self.overall_progress["value"] = percent
                    self.file_label.configure(text=self.text["file_progress"].format(name="GodiNaviUpdater.exe", percent=percent))
                    self.overall_label.configure(text=self.text["overall_progress"].format(current=1 if percent == 100 else 0, total=1))
                    self.status.configure(text=self.text["downloading"].format(percent=percent))
                elif event[0] == "ready":
                    self._launch(event[1], event[2])
                elif event[0] == "cancelled":
                    self.busy = False
                    self.status.configure(text=self.text["cancelled"])
                    self.continue_button.configure(text=self.text["close"], command=self.root.destroy, state="normal")
                elif event[0] == "error":
                    self.busy = False
                    self.status.configure(text=f"{self.text['error']}\n{type(event[1]).__name__}: {event[1]}")
                    self.continue_button.configure(text=self.text["close"], command=self.root.destroy, state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def start(self):
        if self.busy:
            return
        self.busy = True
        self.cancel_event.clear()
        self.continue_button.configure(state="disabled")
        self.continue_button.configure(text=self.text["cancel_update"], command=self.cancel, state="normal")
        threading.Thread(target=self._download_updater, daemon=True).start()

    def cancel(self):
        self.cancel_event.set()
        self.status.configure(text=self.text["cancelling"])
        self.continue_button.configure(state="disabled")

    def _download_updater(self):
        try:
            item = self.manifest["components"]["updater"]
            stage = Path(os.environ.get("LOCALAPPDATA", self.install_root)) / "GodiNavi" / "bridge-stage"
            stage.mkdir(parents=True, exist_ok=True)
            updater = stage / "GodiNaviUpdater.exe"
            channel_file = stage / "update-channel.json"
            def report(current, total):
                if self.cancel_event.is_set():
                    raise RuntimeError("The update was cancelled.")
                self.events.put(("progress", round(current * 100 / total)))
            download(item["url"], updater, item["size"], report)
            if hashlib.sha256(updater.read_bytes()).hexdigest() != item["sha256"]:
                updater.unlink(missing_ok=True)
                raise ValueError("Updater v2 checksum mismatch.")
            shutil.copy2(resource("update-channel.json"), channel_file)
            self.events.put(("ready", updater, channel_file))
        except Exception as exc:
            self.events.put(("cancelled",) if self.cancel_event.is_set() else ("error", exc))

    def _launch(self, updater, channel_file):
        subprocess.Popen([
            str(updater), "--channel-file", str(channel_file),
            "--install-root", str(self.install_root),
            "--legacy-install", str(self.install_root),
            "--wait-pid", str(os.getpid()),
        ], cwd=str(self.install_root), close_fds=True)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    BridgeWindow().run()

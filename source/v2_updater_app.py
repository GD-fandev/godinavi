"""Visible unified updater for V1 migration and all GodiNavi 2.x updates."""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from v2_contracts import validate_channel, validate_history, validate_manifest
from v2_modal_window import bind_modal_drag, modal_font_family, place_modal
from v2_network import download, fetch_json
from v2_process import check_core
from v2_settings import backup_settings, migrate_legacy_settings, restore_settings
from v2_updater_engine import TransactionalInstaller, UpdateCancelled, load_installation, required_components
from v2_wait import wait_for_pid
from app_update_checker import v2_history_text


LEGACY_BACKUP_DIR = ".godinavi-v1-backup"


TEXT = {
    "KR": {"title": "GodiNavi 2 업데이트", "description": "{current}에서 {target}(으)로 업데이트합니다.", "current": "현재 버전", "target": "대상 버전", "components": "업데이트 구성요소", "changes": "변경 내용", "ready": "업데이트를 준비하고 있습니다…", "update": "업데이트 시작", "cancel": "업데이트 중단", "cancelling": "업데이트를 중단하고 기존 상태로 복구하고 있습니다…", "cancelled": "업데이트가 중단되었으며 기존 상태로 복구되었습니다.", "restart": "업데이트 완료 및 재시작", "restart_old": "GodiNavi 재시작", "close": "닫기", "done": "업데이트가 완료되었습니다.", "failed": "업데이트에 실패했습니다.", "file": "현재 파일", "overall": "전체 진행률", "downloading": "다운로드 중"},
    "JP": {"title": "GodiNavi 2 アップデート", "description": "{current}から{target}へアップデートします。", "current": "現在のバージョン", "target": "対象バージョン", "components": "更新コンポーネント", "changes": "変更内容", "ready": "アップデートを準備しています…", "update": "アップデート開始", "cancel": "アップデート中止", "cancelling": "アップデートを中止し、以前の状態に戻しています…", "cancelled": "アップデートを中止し、以前の状態に戻しました。", "restart": "アップデート完了・再起動", "restart_old": "GodiNaviを再起動", "close": "閉じる", "done": "アップデートが完了しました。", "failed": "アップデートに失敗しました。", "file": "現在のファイル", "overall": "全体の進行状況", "downloading": "ダウンロード中"},
    "EN": {"title": "GodiNavi 2 Update", "description": "Updating from {current} to {target}.", "current": "Current version", "target": "Target version", "components": "Components", "changes": "Changes", "ready": "Preparing the update…", "update": "Start update", "cancel": "Cancel update", "cancelling": "Cancelling the update and restoring the previous state…", "cancelled": "The update was cancelled and the previous state was restored.", "restart": "Finish update and restart", "restart_old": "Restart GodiNavi", "close": "Close", "done": "The update completed.", "failed": "The update failed.", "file": "Current file", "overall": "Overall progress", "downloading": "Downloading"},
}


def language(local_appdata=None):
    path = Path(local_appdata or os.environ.get("LOCALAPPDATA", "")) / "GodiNavi" / "godinavi-config.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig")).get("ui_language", "KR")
    except Exception:
        value = "KR"
    return value if value in TEXT else "KR"


history_text = v2_history_text


def legacy_launcher_backup(install_root):
    return Path(install_root).resolve() / LEGACY_BACKUP_DIR / "GodiNavi.exe"


def restore_legacy_launcher(install_root):
    root = Path(install_root).resolve()
    backup = legacy_launcher_backup(root)
    if not backup.is_file() or backup.stat().st_size <= 0:
        return False
    target = root / "GodiNavi.exe"
    target.unlink(missing_ok=True)
    os.replace(backup, target)
    backup.parent.rmdir()
    return True


def discard_legacy_launcher_backup(install_root):
    backup = legacy_launcher_backup(install_root)
    try:
        backup.unlink(missing_ok=True)
    except OSError:
        return
    try:
        backup.parent.rmdir()
    except OSError:
        pass


class UpdaterWindow:
    def __init__(self, args):
        self.args = args
        self.root = tk.Tk()
        self.code = language()
        self.text = TEXT[self.code]
        self.font = modal_font_family(self.root, self.code)
        self.events = queue.Queue()
        self.manifest = None
        self.history = None
        self.names = []
        self.component_rows = {}
        self.current = None
        self.busy = False
        self.cancel_event = threading.Event()
        self.drag_origin = None
        self._build()
        _owner, self.modal_bounds = place_modal(self.root, 660, 560, "updater")
        threading.Thread(target=self._load, daemon=True).start()
        self.root.after(100, self._poll)

    def _build(self):
        self.root.title(self.text["title"])
        self.root.overrideredirect(True)
        self.root.configure(bg="#17130f")
        frame = tk.Frame(self.root, bg="#17130f", padx=14, pady=14, highlightbackground="#d8b15a", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg="#5a4932")
        header.pack(fill="x", pady=(0, 12))
        title = tk.Label(header, text=self.text["title"], bg="#5a4932", fg="#ffe09a", anchor="w", padx=12, pady=9, font=(self.font, 12, "bold"))
        title.pack(side="left", fill="x", expand=True)
        bind_modal_drag(self.root, (header, title), lambda: self.modal_bounds, "updater")
        tk.Label(frame, text=self.text["title"], bg="#17130f", fg="#ffe09a", anchor="w", font=(self.font, 16, "bold")).pack(fill="x")
        self.description = tk.Label(frame, text="", bg="#17130f", fg="#f1e5c7", anchor="w", justify="left", font=(self.font, 10))
        self.description.pack(fill="x", pady=(6, 12))
        self.status = tk.Label(frame, text="…", bg="#2a2118", fg="#e9bd55", anchor="w", padx=10, pady=7, font=(self.font, 10, "bold"))
        self.status.pack(fill="x")
        versions = tk.Frame(frame, bg="#17130f")
        tk.Label(versions, text=self.text["current"], bg="#17130f", fg="#bda982", width=18, anchor="w").grid(row=0, column=0, sticky="w", pady=2)
        tk.Label(versions, text=self.text["target"], bg="#17130f", fg="#bda982", width=18, anchor="w").grid(row=1, column=0, sticky="w", pady=2)
        self.current_label = tk.Label(versions, text="-", bg="#2a2118", fg="#fff1c9", anchor="w", padx=9, pady=4, font=(self.font, 10, "bold"))
        self.target_label = tk.Label(versions, text="-", bg="#2a2118", fg="#fff1c9", anchor="w", padx=9, pady=4, font=(self.font, 10, "bold"))
        self.current_label.grid(row=0, column=1, sticky="w", padx=12)
        self.target_label.grid(row=1, column=1, sticky="w", padx=12)
        self.components = tk.Listbox(frame, height=6, bg="#211a14", fg="#f1e5c7", selectbackground="#5a4932", selectforeground="#fff1c9", relief="flat", highlightthickness=1, highlightbackground="#5a4932", font=(self.font, 10))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("GodiNavi.Horizontal.TProgressbar", troughcolor="#2a2118", background="#d8b15a", bordercolor="#5a4932", lightcolor="#d8b15a", darkcolor="#d8b15a")
        buttons = tk.Frame(frame, bg="#17130f")
        buttons.pack(side="bottom", fill="x")
        self.start_button = tk.Button(buttons, text=self.text["update"], command=self.start, state="disabled", bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff", disabledforeground="#8f8068", relief="flat", bd=0, padx=14, pady=7, font=(self.font, 10, "bold"))
        self.close_button = tk.Button(buttons, text=self.text["close"], command=self._close, bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=7, font=(self.font, 10, "bold"))
        self.close_button.pack(side="right", padx=8)
        self.overall_label = tk.Label(frame, text=f"{self.text['overall']}: 0%", bg="#17130f", fg="#bda982", anchor="w", font=(self.font, 9))
        self.overall_label.pack(side="bottom", fill="x")
        self.overall_progress = ttk.Progressbar(frame, mode="determinate", maximum=100, style="GodiNavi.Horizontal.TProgressbar")
        self.overall_progress.pack(side="bottom", fill="x", pady=(2, 7))
        self.file_label = tk.Label(frame, text=f"{self.text['file']}: -", bg="#17130f", fg="#bda982", anchor="w", font=(self.font, 9))
        self.file_label.pack(side="bottom", fill="x")
        self.file_progress = ttk.Progressbar(frame, mode="determinate", maximum=100, style="GodiNavi.Horizontal.TProgressbar")
        self.file_progress.pack(side="bottom", fill="x", pady=(2, 8))
        notes_frame = tk.Frame(frame, bg="#211a14")
        notes_frame.pack(fill="both", expand=True, pady=(12, 0))
        scrollbar = tk.Scrollbar(notes_frame)
        scrollbar.pack(side="right", fill="y")
        self.notes = tk.Text(notes_frame, height=12, spacing1=2, spacing3=3, wrap="char", state="disabled", bg="#211a14", fg="#f1e5c7", insertbackground="#f1e5c7", relief="flat", padx=10, pady=8, font=(self.font, 10), yscrollcommand=scrollbar.set)
        self.notes.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.notes.yview)

    def _close(self):
        if not self.busy:
            self.root.destroy()

    def _load(self):
        try:
            channel = validate_channel(json.loads(Path(self.args.channel_file).read_text(encoding="utf-8-sig")))
            manifest = validate_manifest(fetch_json(channel["manifestUrl"]))
            if manifest["channel"] != channel["channel"]:
                raise ValueError("Channel and manifest do not match.")
            history = validate_history(fetch_json(manifest["historyUrl"]))
            current = load_installation(self.args.install_root)
            names = required_components(manifest, current)
            self.events.put(("loaded", channel, manifest, history, current, names))
        except Exception as exc:
            self.events.put(("error", exc))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "loaded":
                    _, self.channel, self.manifest, self.history, self.current, self.names = event
                    self.current_label.configure(text=self.current["clientVersion"] if self.current else "1.x")
                    self.target_label.configure(text=self.manifest["clientVersion"])
                    current_version = self.current["clientVersion"] if self.current else "1.x"
                    self.description.configure(text=self.text["description"].format(
                        current=current_version, target=self.manifest["clientVersion"],
                    ))
                    self.components.delete(0, "end")
                    self.component_rows = {}
                    for row, name in enumerate(self.names):
                        item = self.manifest["components"][name]
                        self.component_rows[name] = row
                        self.components.insert("end", self._component_text(name, 0))
                    self.notes.configure(state="normal")
                    self.notes.delete("1.0", "end")
                    self.notes.insert("1.0", history_text(self.history, self.code))
                    self.notes.configure(state="disabled")
                    self.status.configure(text=self.text["ready"] if self.names else self.text["done"])
                    self.start_button.configure(state="normal" if self.names else "disabled")
                    if self.names:
                        self.root.after_idle(self.start)
                elif kind == "file_progress":
                    _, name, file_percent, overall_percent = event
                    text = f"{self.text['downloading']} {name}"
                    self.status.configure(text=text)
                    self.file_progress["value"] = file_percent
                    self.overall_progress["value"] = overall_percent
                    self.file_label.configure(text=f"{self.text['file']}: {name}  {file_percent}%")
                    self.overall_label.configure(text=f"{self.text['overall']}: {overall_percent}%")
                    row = self.component_rows.get(name)
                    if row is not None:
                        self.components.delete(row)
                        self.components.insert(row, self._component_text(name, file_percent))
                elif kind == "phase":
                    self.status.configure(text=event[1])
                elif kind == "done":
                    self.busy = False
                    self.file_progress["value"] = 100
                    self.overall_progress["value"] = 100
                    self.overall_label.configure(text=f"{self.text['overall']}: 100%")
                    self.status.configure(text=self.text["done"])
                    self.close_button.configure(text=self.text["restart"], command=self._restart, state="normal")
                elif kind == "cancelled":
                    self.busy = False
                    self.status.configure(text=self.text["cancelled"])
                    self.close_button.configure(text=self.text["restart_old"], command=self._restart, state="normal")
                elif kind == "error":
                    self.busy = False
                    self.status.configure(text=f"{self.text['failed']}\n{type(event[1]).__name__}: {event[1]}")
                    self.close_button.configure(text=self.text["restart_old"], command=self._restart, state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def start(self):
        if self.busy or not self.manifest:
            return
        self.busy = True
        self.cancel_event.clear()
        self.start_button.configure(state="disabled")
        self.close_button.configure(text=self.text["cancel"], command=self.cancel, state="normal")
        threading.Thread(target=self._install, daemon=True).start()

    def cancel(self):
        if not self.busy:
            return
        self.cancel_event.set()
        self.status.configure(text=self.text["cancelling"])
        self.close_button.configure(state="disabled")

    def _restart(self):
        launcher = Path(self.args.install_root) / "GodiNavi.exe"
        subprocess.Popen([str(launcher)], cwd=str(launcher.parent), close_fds=True)
        self.root.destroy()

    def _component_text(self, name, percent):
        item = self.manifest["components"][name]
        return f"{name}  →  {item['version']}  ({item['size'] / 1024 / 1024:.1f} MB)  [{percent}%]"

    def _install(self):
        backup = None
        migrated = []
        try:
            if not wait_for_pid(self.args.wait_pid, 60, self.cancel_event.is_set):
                if self.cancel_event.is_set():
                    raise UpdateCancelled("The update was cancelled.")
                raise TimeoutError("The previous GodiNavi process did not close.")
            backup = backup_settings()
            migrated = migrate_legacy_settings(self.args.legacy_install)
            component_progress = {name: 0 for name in self.names}
            total_bytes = sum(self.manifest["components"][name]["size"] for name in self.names)
            urls = {self.manifest["components"][name]["url"]: name for name in self.names}

            def downloader(url, destination, size):
                name = urls[url]
                def report(received, total):
                    if self.cancel_event.is_set():
                        raise UpdateCancelled("The update was cancelled.")
                    component_progress[name] = min(received, size)
                    file_percent = round(received * 100 / total)
                    overall_percent = round(sum(component_progress.values()) * 100 / max(1, total_bytes))
                    self.events.put(("file_progress", name, file_percent, overall_percent))
                download(url, destination, size, report)

            def progress(event, **detail):
                if event in {"prepare", "applied"}:
                    self.events.put(("phase", f"{event}: {detail.get('name', '')}"))

            installer = TransactionalInstaller(
                self.args.install_root, downloader, progress,
                cancelled=self.cancel_event.is_set,
            )
            installer.install(
                self.manifest,
                manifest_url=self.channel["manifestUrl"],
                health_check=lambda state, transaction: check_core(self.args.install_root, state, transaction),
            )
            if self.args.legacy_install:
                discard_legacy_launcher_backup(self.args.install_root)
            self.events.put(("done",))
        except Exception as exc:
            try:
                restore_settings(backup)
                for path in migrated:
                    Path(path).unlink(missing_ok=True)
                if self.args.legacy_install:
                    restore_legacy_launcher(self.args.install_root)
            except Exception as restore_exc:
                exc = RuntimeError(f"{exc}; settings restore failed: {restore_exc}")
            self.events.put(("cancelled",) if isinstance(exc, UpdateCancelled) else ("error", exc))

    def run(self):
        self.root.mainloop()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-file", required=True)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--legacy-install")
    parser.add_argument("--wait-pid", type=int, default=0)
    return parser.parse_args()


if __name__ == "__main__":
    UpdaterWindow(parse_args()).run()

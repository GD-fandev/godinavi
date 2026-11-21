"""Run the catalog on its own UI process, independent of capture/OCR callbacks."""

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from types import SimpleNamespace

from config_store import load_section, save_section


class ArmorCatalogHost:
    def __init__(self, master, project_dir, language_provider):
        self.master = master
        self.project_dir = str(project_dir)
        self.language_provider = language_provider
        self.process = None
        self.visible = False
        self.events = queue.Queue()
        self.poll_job = None
        self.reader = None
        # Preserve the main application's visibility and shutdown interface.
        self.window = self
        self.store = SimpleNamespace(close=self.shutdown)

    def winfo_exists(self):
        return self.process is not None and self.process.poll() is None

    def winfo_viewable(self):
        return self.visible and self.winfo_exists()

    def _send(self, action, **values):
        if not self.winfo_exists():
            return
        try:
            self.process.stdin.write(json.dumps({'action': action, **values}) + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError):
            self.visible = False

    def open(self):
        language = self.language_provider() if self.language_provider else 'KR'
        if self.winfo_exists():
            self._send('open', language=language)
        else:
            if self.process is not None:
                self.process.stdin.close()
                if self.reader is not None:
                    self.reader.join(timeout=1)
            self._drain_events()
            args = [sys.executable]
            if not getattr(sys, 'frozen', False):
                args.append(str(Path(__file__).resolve().parents[1] / 'godinavi_launcher.py'))
            args += ['--equipment-catalog', '--project-dir', self.project_dir, '--language', language]
            self.process = subprocess.Popen(
                args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            self.reader = threading.Thread(target=self._read_events, args=(self.process,), daemon=True)
            self.reader.start()
        self.visible = True
        if self.poll_job is None:
            self.poll_job = self.master.after(50, self._poll_events)

    def _read_events(self, process):
        try:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                self.events.put(event)
        finally:
            process.stdout.close()

    def _drain_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return
            # Save on the parent's UI loop, alongside other settings writes.
            if event.get('action') == 'save' and event.get('key') in {'armor_catalog_preferences', 'modal_positions'}:
                value = event.get('value')
                if isinstance(value, dict):
                    if event['key'] == 'modal_positions':
                        value = {**load_section('modal_positions', {}), **value}
                    save_section(event['key'], value)
            elif event.get('action') == 'error':
                from tkinter import messagebox
                messagebox.showerror('GodiNavi', event.get('message', 'Equipment catalog failed.'), parent=self.master)
            elif event.get('action') == 'state':
                self.visible = bool(event.get('visible'))
                self.built_language = event.get('language')

    def _poll_events(self):
        self.poll_job = None
        self._drain_events()
        if self.winfo_exists():
            self.poll_job = self.master.after(50, self._poll_events)
        else:
            self.visible = False

    def close(self):
        self.visible = False
        self._send('hide')

    def shutdown(self):
        if self.poll_job is not None:
            self.master.after_cancel(self.poll_job)
            self.poll_job = None
        self._send('quit')
        if self.process is not None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=2)
            if self.reader is not None:
                self.reader.join(timeout=1)
        self._drain_events()
        self.visible = False


def ensure_catalog_stdio():
    """Windowed Python/PyInstaller sets sys.std* to None despite inherited pipes."""
    if os.name != 'nt':
        return
    import ctypes
    import msvcrt
    get_handle = ctypes.windll.kernel32.GetStdHandle
    get_handle.argtypes = [ctypes.c_ulong]
    get_handle.restype = ctypes.c_void_p
    if sys.stdin is None:
        descriptor = msvcrt.open_osfhandle(get_handle(-10), os.O_RDONLY)
        sys.stdin = os.fdopen(descriptor, 'r', encoding='utf-8')
    if sys.stdout is None:
        descriptor = msvcrt.open_osfhandle(get_handle(-11), os.O_WRONLY)
        sys.stdout = os.fdopen(descriptor, 'w', encoding='utf-8', buffering=1)


def run_catalog_process(project_dir, language):
    """No imports of the main app or OCR engines on this entry path."""
    import tkinter as tk
    import config_store
    import modal_window
    from . import armor_catalog_ui

    ensure_catalog_stdio()
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()

    commands = queue.Queue()
    cached_sections = {}

    def emit(event):
        sys.stdout.write(json.dumps(event, ensure_ascii=True) + '\n')
        sys.stdout.flush()

    def load_section(key, default=None, legacy_paths=()):
        # Read only in this process. All shared-config mutations stay in the
        # parent, preventing simultaneous writes from the two UI loops.
        result = dict(default or {})
        for path in legacy_paths:
            try:
                value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
                if isinstance(value, dict):
                    result.update(value)
            except (OSError, ValueError):
                pass
        value = config_store._read().get(key)
        if isinstance(value, dict):
            result.update(value)
        result.update(cached_sections.get(key, {}))
        return result

    def save_section_remote(key, value):
        previous = load_section(key)
        cached_sections[key] = dict(value)
        if key == 'modal_positions':
            value = {name: position for name, position in value.items() if previous.get(name) != position}
        emit({'action': 'save', 'key': key, 'value': value})

    armor_catalog_ui.load_section = modal_window.load_section = load_section
    armor_catalog_ui.save_section = modal_window.save_section = save_section_remote
    root = tk.Tk()
    root.withdraw()
    current_language = [language]
    ui = armor_catalog_ui.ArmorCatalogUI(root, project_dir, lambda: current_language[0])
    original_close = ui.close

    def quit_catalog():
        original_close()
        ui.store.close()
        root.destroy()

    ui.close = quit_catalog

    def report_state():
        emit({'action': 'state', 'visible': ui.window.state() != 'withdrawn',
              'language': current_language[0]})

    def read_commands():
        pending = b''
        while True:
            chunk = os.read(sys.stdin.fileno(), 4096)
            if not chunk:
                break
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                try:
                    commands.put(json.loads(line))
                except ValueError:
                    continue
        commands.put({'action': 'quit'})

    def poll_commands():
        while not commands.empty():
            command = commands.get_nowait()
            if command.get('action') == 'quit':
                quit_catalog()
                return
            if command.get('action') == 'hide':
                original_close()
                report_state()
            elif command.get('action') == 'open':
                current_language[0] = command.get('language', current_language[0])
                ui.open()
                report_state()
        root.after(20, poll_commands)

    threading.Thread(target=read_commands, daemon=True).start()
    try:
        ui.open()
        report_state()
        root.after(20, poll_commands)
        root.mainloop()
    except Exception as exc:
        emit({'action': 'error', 'message': str(exc)})
        ui.store.close()
        root.destroy()

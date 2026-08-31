"""Shared GodiNavi modal placement, typography, and drag behavior."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tkinter import font as tkfont

from godinavi.window_attachment import (
    attach_above, client_screen_rect, find_godius_window, make_activatable_toolwindow,
)
from config_store import load_section, save_section


POSITION_PATH = Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi" / "modal-positions.json"
V2_POSITION_PATH = POSITION_PATH.with_name("v2-modal-positions.json")


def select_font_family(code, available):
    choices = {
        "KR": ("Noto Sans KR", "Malgun Gothic", "Segoe UI"),
        "JP": ("Noto Sans JP", "Yu Gothic UI", "Meiryo UI", "Segoe UI"),
        "EN": ("Noto Sans", "Segoe UI", "Arial"),
    }.get(code, ("Noto Sans", "Segoe UI"))
    names = {str(name).casefold(): str(name) for name in available}
    return next((names[name.casefold()] for name in choices if name.casefold() in names), "TkDefaultFont")


def modal_font_family(window, code):
    return select_font_family(code, tkfont.families(window))


def _positions():
    if POSITION_PATH == Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi" / "modal-positions.json":
        return load_section("modal_positions", {}, (POSITION_PATH, V2_POSITION_PATH))
    try:
        value = json.loads(POSITION_PATH.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _save_position(key, x, y, bounds):
    if not key:
        return
    positions = _positions()
    positions[key] = {"x": round(x - bounds[0]), "y": round(y - bounds[1])}
    if POSITION_PATH == Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi" / "modal-positions.json":
        save_section("modal_positions", positions)
        return
    POSITION_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = POSITION_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(positions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, POSITION_PATH)


def modal_geometry(requested_width, requested_height, bounds, saved_offset=None, margin=12):
    left, top, right, bottom = bounds
    available_width = max(320, right - left - margin * 2)
    available_height = max(240, bottom - top - margin * 2)
    width = min(max(320, requested_width), available_width)
    height = min(max(240, requested_height), available_height)
    if saved_offset:
        x = left + round(saved_offset[0])
        y = top + round(saved_offset[1])
    else:
        x = left + (right - left - width) // 2
        y = top + (bottom - top - height) // 2
    x = max(left + margin, min(x, right - margin - width))
    y = max(top + margin, min(y, bottom - margin - height))
    return width, height, x, y


def place_modal(window, minimum_width=600, minimum_height=500, position_key=None):
    window.update_idletasks()
    requested_width = max(minimum_width, window.winfo_reqwidth())
    requested_height = max(minimum_height, window.winfo_reqheight())
    owner = find_godius_window()
    bounds = client_screen_rect(owner) if owner else None
    if not bounds:
        bounds = (0, 0, window.winfo_screenwidth(), window.winfo_screenheight())
    saved = _positions().get(position_key, {}) if position_key else {}
    offset = (saved.get("x"), saved.get("y")) if isinstance(saved.get("x"), (int, float)) and isinstance(saved.get("y"), (int, float)) else None
    width, height, x, y = modal_geometry(requested_width, requested_height, bounds, offset)
    window.geometry(f"{width}x{height}+{x}+{y}")
    if owner:
        attach_above(window, owner, x, y)
    return owner, bounds


def bind_modal_drag(window, widgets, bounds_provider, position_key=None):
    drag = {"start": None, "origin": None}

    def start(event):
        drag["start"] = event.x_root, event.y_root
        drag["origin"] = window.winfo_x(), window.winfo_y()

    def move(event):
        if not drag["start"] or not drag["origin"]:
            return
        sx, sy = drag["start"]
        ox, oy = drag["origin"]
        x, y = ox + event.x_root - sx, oy + event.y_root - sy
        left, top, right, bottom = bounds_provider()
        x = max(left, min(x, right - window.winfo_width()))
        y = max(top, min(y, bottom - window.winfo_height()))
        window.geometry(f"+{round(x)}+{round(y)}")

    def stop(_event):
        drag["start"] = None
        drag["origin"] = None
        _save_position(position_key, window.winfo_x(), window.winfo_y(), bounds_provider())

    for widget in widgets:
        widget.bind("<ButtonPress-1>", start)
        widget.bind("<B1-Motion>", move)
        widget.bind("<ButtonRelease-1>", stop)


def activate_modal(window):
    """Enable modal input without locking Windows focus to the game group."""
    try:
        if not window.winfo_exists():
            return
        # Modal entry normally follows a direct user click. Removing
        # WS_EX_NOACTIVATE is sufficient; SetForegroundWindow + focus_force
        # can leave a game-owned popup fighting subsequent clicks on unrelated
        # applications. Keep focus local to Tk instead.
        make_activatable_toolwindow(window, request_foreground=False)
        window.focus_set()
        if not getattr(window, "_modal_cleanup_bound", False):
            def cleanup(event):
                if event.widget is not window:
                    return
                try:
                    grabbed = window.grab_current()
                    if grabbed is not None and str(grabbed).startswith(str(window)):
                        grabbed.grab_release()
                except Exception:
                    pass

            window.bind("<Destroy>", cleanup, add="+")
            window._modal_cleanup_bound = True
    except Exception:
        pass


def bind_modal_escape(window, close_callback):
    """Apply the shared rule that a focused GodiNavi modal closes on Escape."""
    def close(_event=None):
        close_callback()
        return "break"

    window.bind("<Escape>", close, add="+")
    try:
        window.after_idle(lambda: activate_modal(window))
    except Exception:
        activate_modal(window)

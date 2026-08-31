import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageTk

from .actions import DockItem
from .window_attachment import attach_above, make_noactivate_toolwindow, native_window_handle


BG = "#17130f"
PANEL = "#2a2118"
PANEL_HOVER = "#443422"
GOLD = "#d8b15a"
TEXT = "#f1e5c7"
MUTED = "#a99570"
TRANSPARENT = "#ff00ff"
BASE_ICON_SIZE = (75, 70)
MIN_ICON_SCALE = 0.75
MAX_ICON_SCALE = 1.50
ICON_SCALE_STEP = 0.25
MIN_OPACITY_PERCENT = 50
MAX_OPACITY_PERCENT = 100
FLYOUT_WIDTH = 212
FLYOUT_HEADER_HEIGHT = 34
FLYOUT_ROW_HEIGHT = 36
FLYOUT_ROWS = 3

DOCK_EDIT_TEXTS = {
    "KR": "::  투명도 (휠 상하)",
    "JP": "::  透明度（ホイール上下）",
    "EN": "::  Opacity (mouse wheel)",
}

DOCK_EDIT_COLLAPSED_TEXTS = {
    "KR": "⠿  이동 영역 · 드래그\n마우스 휠 · 크기 조절",
    "JP": "⠿  移動エリア · ドラッグ\nマウスホイール · サイズ調整",
    "EN": "⠿  Move area · Drag\nMouse wheel · Resize",
}

DOCK_EDIT_COLLAPSED_VERTICAL_TEXTS = {
    "KR": "이  크\n동  기\n·  ·\n드  휠\n래    \n그    ",
    "JP": "移  サ\n動  イ\n·  ズ\nド  ·\nラ  ホ\nッ  イ\nグ  ｜\n    ル",
    "EN": "M  S\nO  I\nV  Z\nE  E\n·  ·\nD  W\nR  H\nA  E\nG  E\n   L",
}

DOCK_EDIT_VERTICAL_TEXTS = {
    "KR": "⠿\n이\n동\n·\n드\n래\n그\n\n크\n기\n·\n휠",
    "JP": "⠿\n移\n動\n・\nド\nラ\nッ\nグ\n\nサ\nイ\nズ\n・\nホ\nイ\n｜\nル",
    "EN": "⠿\nM\nO\nV\nE\n\nS\nI\nZ\nE\n·\nW\nH\nE\nE\nL",
}


def collapse_edge_for_position(
    orientation: str,
    client_rect: tuple[int, int, int, int],
    bar_rect: tuple[int, int, int, int],
    current_edge: str,
) -> str:
    left, top, right, bottom = client_rect
    bar_left, bar_top, bar_right, bar_bottom = bar_rect
    if orientation == "horizontal":
        center = (left + right) / 2
        bar_center = (bar_left + bar_right) / 2
        dead_zone = max(1, (right - left) * 0.05)
        return "right" if bar_center < center - dead_zone else "left" if bar_center > center + dead_zone else current_edge
    center = (top + bottom) / 2
    bar_center = (bar_top + bar_bottom) / 2
    dead_zone = max(1, (bottom - top) * 0.05)
    return "bottom" if bar_center < center - dead_zone else "top" if bar_center > center + dead_zone else current_edge


def vertical_flyout_position(
    owner_rect: tuple[int, int, int, int],
    flyout_size: tuple[int, int],
    client_rect: tuple[int, int, int, int],
    gap: int = 6,
) -> tuple[int, int]:
    owner_left, owner_top, owner_right, owner_bottom = owner_rect
    flyout_width, flyout_height = flyout_size
    client_left, client_top, client_right, client_bottom = client_rect
    owner_center = (owner_left + owner_right) / 2
    client_center = (client_left + client_right) / 2
    left_x = owner_left - flyout_width - gap
    right_x = owner_right + gap
    prefer_right = owner_center <= client_center
    preferred = right_x if prefer_right else left_x
    alternate = left_x if prefer_right else right_x
    preferred_fits = client_left <= preferred and preferred + flyout_width <= client_right
    alternate_fits = client_left <= alternate and alternate + flyout_width <= client_right
    x = preferred if preferred_fits or not alternate_fits else alternate
    x = (
        client_left
        if flyout_width >= client_right - client_left
        else max(client_left, min(x, client_right - flyout_width))
    )
    y = owner_top + ((owner_bottom - owner_top) - flyout_height) // 2
    y = (
        client_top
        if flyout_height >= client_bottom - client_top
        else max(client_top, min(y, client_bottom - flyout_height))
    )
    return round(x), round(y)


class OverlayDock:
    """Small, movable prototype dock with hover quick actions."""

    def __init__(
        self,
        root: tk.Tk,
        items: list[DockItem],
        on_orientation_changed: Callable[[str], None] | None = None,
        on_moved: Callable[[int, int], None] | None = None,
        on_scale_changed: Callable[[float], None] | None = None,
        on_opacity_changed: Callable[[int], None] | None = None,
        on_collapsed_changed: Callable[[bool], None] | None = None,
        focus_callback: Callable[[], None] | None = None,
        client_rect_provider: Callable[[], tuple[int, int, int, int] | None] | None = None,
        initial_orientation: str = "horizontal",
        initial_icon_scale: float = 1.0,
        initial_opacity_percent: int = 94,
        initial_collapsed: bool = False,
        initial_collapse_edge: str | None = None,
        initial_ui_language: str = "KR",
    ):
        self.root = root
        self.items = items
        self.on_orientation_changed = on_orientation_changed
        self.on_moved = on_moved
        self.on_scale_changed = on_scale_changed
        self.on_opacity_changed = on_opacity_changed
        self.on_collapsed_changed = on_collapsed_changed
        self.focus_callback = focus_callback
        self.client_rect_provider = client_rect_provider
        self.orientation = initial_orientation if initial_orientation in ("horizontal", "vertical") else "horizontal"
        self.icon_scale = max(MIN_ICON_SCALE, min(MAX_ICON_SCALE, float(initial_icon_scale)))
        self.opacity_percent = max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(initial_opacity_percent)))
        self.locked = True
        self.temporarily_disabled = False
        self.collapsed = bool(initial_collapsed)
        valid_edges = ("left", "right") if self.orientation == "horizontal" else ("top", "bottom")
        self.collapse_edge = initial_collapse_edge if initial_collapse_edge in valid_edges else valid_edges[0]
        self.ui_language = initial_ui_language if initial_ui_language in DOCK_EDIT_TEXTS else "KR"
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.flyout_show_job: str | None = None
        self.flyout_show_owner: tk.Widget | None = None
        self.hide_job: str | None = None
        self.status_hide_job: str | None = None
        self.flyout: tk.Toplevel | None = None
        self.icon_cache: dict[tuple[str, int, int, bool | str | None], tuple[ImageTk.PhotoImage, ImageTk.PhotoImage]] = {}
        self.item_buttons: dict[str, tk.Button] = {}
        self.collapse_handle: tk.Canvas | None = None
        self.collapsed_alert_window: tk.Toplevel | None = None
        self.collapsed_alert_label: tk.Label | None = None
        self.collapsed_alert_geometry: str | None = None
        self.restoring_anchor = False
        self.resize_origin = None
        self.edit_header_window = None
        self.edit_grip_window = None

        root.title("GodiNavi")
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT)
        root.geometry("+80+80")
        try:
            root.attributes("-alpha", self.opacity_percent / 100.0)
            root.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass

        self.frame = tk.Frame(root, bg=TRANSPARENT, padx=0, pady=0)
        self.frame.pack(fill="both", expand=True)

        self.drag_handle = tk.Label(
            self.frame,
            text=DOCK_EDIT_TEXTS[self.ui_language],
            bg="#5a4932",
            fg="#fff1c9",
            padx=16,
            pady=8,
            cursor="fleur",
            font=("Noto Sans KR", 9, "bold"),
        )
        self.button_frame = tk.Frame(self.frame, bg=TRANSPARENT)
        self.button_frame.pack(fill="both", expand=True)
        for widget in (self.frame, self.drag_handle):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<ButtonRelease-1>", self._stop_drag)
            widget.bind("<MouseWheel>", self._mousewheel_scale)

        self.status_window = tk.Toplevel(root)
        self.status_window.overrideredirect(True)
        self.status_window.configure(bg=GOLD)
        self.status_window.transient(root)
        self.status = tk.Label(
            self.status_window,
            text="",
            bg="#0e0c09",
            fg=TEXT,
            padx=8,
            pady=4,
            font=("Noto Sans KR", 9),
        )
        self.status.pack(padx=1, pady=1)
        self.status_window.withdraw()
        self._build_buttons()
        make_noactivate_toolwindow(self.root)
        make_noactivate_toolwindow(self.status_window)
        self.root.after(150, self._refresh_state_badges)

    @staticmethod
    def _window_exists(window):
        try:
            return bool(window and window.winfo_exists())
        except tk.TclError:
            return False

    def _ensure_edit_header(self):
        if self._window_exists(self.edit_header_window):
            return self.edit_header_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        label = tk.Label(
            window, text=DOCK_EDIT_TEXTS[self.ui_language], bg="#5a4932", fg="#fff1c9",
            anchor="w", padx=8, pady=4, cursor="fleur", font=("Noto Sans KR", 8, "bold"),
        )
        label.pack(fill="both", expand=True, padx=1, pady=1)
        label.bind("<ButtonPress-1>", self._start_drag)
        label.bind("<B1-Motion>", self._drag)
        label.bind("<ButtonRelease-1>", self._stop_drag)
        label.bind("<MouseWheel>", self._mousewheel_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.edit_header_window = window
        return window

    def _ensure_edit_grip(self):
        if self._window_exists(self.edit_grip_window):
            return self.edit_grip_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        grip = tk.Canvas(
            window, width=16, height=16, bg="#35291c", highlightthickness=1,
            highlightbackground=GOLD, cursor="size_nw_se",
        )
        grip.pack(fill="both", expand=True)
        grip.create_line(4, 14, 14, 4, fill="#fff1c9", width=1)
        grip.create_line(9, 14, 14, 9, fill="#fff1c9", width=1)
        grip.bind("<ButtonPress-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._resize)
        grip.bind("<ButtonRelease-1>", self._stop_resize)
        grip.bind("<MouseWheel>", self._mousewheel_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.edit_grip_window = window
        return window

    def _show_edit_chrome(self):
        windows = (self._ensure_edit_header(), self._ensure_edit_grip())
        self._position_edit_chrome()
        owner = native_window_handle(self.root)
        for window in windows:
            window.deiconify()
            attach_above(window, owner, window.winfo_x(), window.winfo_y())

    def _hide_edit_chrome(self):
        for window in (self.edit_header_window, self.edit_grip_window):
            if self._window_exists(window):
                window.withdraw()

    def _position_edit_chrome(self):
        if self.locked or not self.root.winfo_viewable():
            return
        left, top, right, bottom = self.button_bar_screen_rect()
        client = self.client_rect_provider() if self.client_rect_provider else None
        header = self._ensure_edit_header()
        grip = self._ensure_edit_grip()
        header_height = 28
        header_y = top - header_height - 4
        if client and header_y < client[1]:
            header_y = bottom + 4
        header.geometry(f"{max(80, right - left)}x{header_height}+{left}+{header_y}")
        grip.update_idletasks()
        grip.geometry(f"+{right - grip.winfo_reqwidth()}+{bottom - grip.winfo_reqheight()}")

    def _build_buttons(self):
        for child in self.button_frame.winfo_children():
            child.destroy()

        self.item_buttons.clear()
        side = "left" if self.orientation == "horizontal" else "top"
        icon_width, icon_height = self.icon_size()
        handle_first = self.collapse_edge in ("left", "top")
        if handle_first:
            self._build_collapse_handle(side, icon_width, icon_height)
        for item in self._visible_items():
            state = self._item_state(item)
            normal_icon, hover_icon = self._load_icon(item, state)
            button = tk.Button(
                self.button_frame,
                text="" if normal_icon else item.symbol,
                image=normal_icon or "",
                command=lambda current=item: self._invoke_primary(current),
                bg=PANEL,
                fg=TEXT,
                activebackground=PANEL_HOVER,
                activeforeground="#fff7df",
                relief="flat",
                bd=0,
                highlightthickness=0,
                width=icon_width if normal_icon else 3,
                height=icon_height if normal_icon else 1,
                padx=0 if normal_icon else 2,
                pady=0 if normal_icon else 5,
                cursor="hand2",
                font=("Segoe UI Emoji", 14),
                state="normal" if item.key == "quit" or not self.temporarily_disabled else "disabled",
            )
            button._normal_icon = normal_icon
            button._hover_icon = hover_icon
            button._state_value = state
            self.item_buttons[item.key] = button
            button.pack(side=side, padx=1, pady=1)
            button.bind("<Enter>", lambda _event, current=item, owner=button: self._button_enter(current, owner))
            button.bind("<Leave>", lambda event, owner=button: self._button_leave(event, owner))
            button.bind("<Button-3>", lambda _event, current=item: self._run_settings(current))
            button.bind("<MouseWheel>", self._mousewheel_opacity)
        if not handle_first:
            self._build_collapse_handle(side, icon_width, icon_height)

    def _visible_items(self):
        if not self.collapsed:
            return self.items
        return [item for item in self.items if item.key in {"settings", "quit"}]

    def _build_collapse_handle(self, side, icon_width, icon_height):
        horizontal = self.orientation == "horizontal"
        width = max(16, round(18 * self.icon_scale)) if horizontal else icon_width
        height = icon_height if horizontal else max(16, round(18 * self.icon_scale))
        handle = tk.Canvas(
            self.button_frame, width=width, height=height, bg=PANEL,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        handle.pack(side=side, padx=1, pady=1)
        self.collapse_handle = handle
        self._draw_collapse_handle(PANEL)
        handle.bind("<Button-1>", lambda _event: self.toggle_collapsed())
        handle.bind("<Enter>", lambda _event: self._draw_collapse_handle(PANEL_HOVER))
        handle.bind("<Leave>", lambda _event: self._draw_collapse_handle(PANEL))
        handle.bind("<MouseWheel>", self._mousewheel_opacity)

    def _draw_collapse_handle(self, background):
        if not self.collapse_handle:
            return
        handle = self.collapse_handle
        handle.configure(bg=background)
        handle.delete("all")
        width = int(handle.cget("width"))
        height = int(handle.cget("height"))
        if self.orientation == "horizontal":
            points_right = self.collapsed != (self.collapse_edge == "left")
            if points_right:
                points = (width * 0.35, height * 0.38, width * 0.35, height * 0.62, width * 0.72, height * 0.50)
            else:
                points = (width * 0.65, height * 0.38, width * 0.65, height * 0.62, width * 0.28, height * 0.50)
        else:
            points_down = self.collapsed != (self.collapse_edge == "top")
            if points_down:
                points = (width * 0.38, height * 0.35, width * 0.62, height * 0.35, width * 0.50, height * 0.72)
            else:
                points = (width * 0.38, height * 0.65, width * 0.62, height * 0.65, width * 0.50, height * 0.28)
        handle.create_polygon(*points, fill=TEXT, outline=GOLD)

    def _ensure_collapsed_alert(self):
        if self._window_exists(self.collapsed_alert_window):
            return self.collapsed_alert_window
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=TRANSPARENT)
        window.transient(self.root)
        label = tk.Label(
            window, text="⚠️", bg=TRANSPARENT, fg="#ffdc37", bd=0,
            padx=0, pady=0, font=("Segoe UI Emoji", max(20, round(25 * self.icon_scale))),
        )
        label.pack()
        try:
            window.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.collapsed_alert_window = window
        self.collapsed_alert_label = label
        return window

    def _collapsed_alert_opacity(self):
        if not self.collapsed:
            return None
        visible_keys = {item.key for item in self._visible_items()}
        opacity = None
        for item in self.items:
            if item.key in visible_keys or item.alert is None:
                continue
            try:
                alert = item.alert() if callable(item.alert) else item.alert
            except Exception:
                continue
            if isinstance(alert, tuple) and len(alert) == 2:
                if alert[0]:
                    value = max(0, min(100, int(alert[1])))
                    opacity = value if opacity is None else max(opacity, value)
            elif alert:
                opacity = 100
        return opacity

    def _refresh_collapsed_alert(self):
        opacity = self._collapsed_alert_opacity()
        if opacity is None or not self.root.winfo_viewable() or not self.collapse_handle:
            if self._window_exists(self.collapsed_alert_window):
                self.collapsed_alert_window.withdraw()
            self.collapsed_alert_geometry = None
            return
        window = self._ensure_collapsed_alert()
        if self.collapsed_alert_label:
            self.collapsed_alert_label.configure(
                font=("Segoe UI Emoji", max(20, round(25 * self.icon_scale)))
            )
        window.update_idletasks()
        handle = self.collapse_handle
        gap = max(2, round(3 * self.icon_scale))
        badge_width = window.winfo_reqwidth()
        badge_height = window.winfo_reqheight()
        handle_left = handle.winfo_rootx()
        handle_top = handle.winfo_rooty()
        handle_right = handle_left + handle.winfo_width()
        handle_bottom = handle_top + handle.winfo_height()
        if self.collapse_edge == "right":
            x = handle_right + gap
            y = handle_top + (handle.winfo_height() - badge_height) // 2
        elif self.collapse_edge == "left":
            x = handle_left - badge_width - gap
            y = handle_top + (handle.winfo_height() - badge_height) // 2
        elif self.collapse_edge == "bottom":
            x = handle_left + (handle.winfo_width() - badge_width) // 2
            y = handle_bottom + gap
        else:
            x = handle_left + (handle.winfo_width() - badge_width) // 2
            y = handle_top - badge_height - gap
        geometry = f"+{x}+{y}"
        if geometry != self.collapsed_alert_geometry:
            window.geometry(geometry)
            self.collapsed_alert_geometry = geometry
        window.attributes("-alpha", (opacity / 100.0) * (self.opacity_percent / 100.0))
        if not window.winfo_viewable():
            window.deiconify()
        # The game regains focus after toolbar actions and can otherwise cover
        # this separate alert window. Keep it immediately above the dock
        # without activating it, just like the other attached overlays.
        attach_above(window, native_window_handle(self.root), x, y)

    def toggle_collapsed(self):
        if not self.locked:
            return
        self.root.update_idletasks()
        anchor = self._outer_anchor()
        self.collapsed = not self.collapsed
        self._destroy_flyout()
        self._build_buttons()
        if not self.locked:
            self._layout_unlocked()
        self._restore_outer_anchor(anchor)
        if self.on_collapsed_changed:
            self.on_collapsed_changed(self.collapsed)
        self._request_game_focus()

    def update_collapse_edge(self, client_rect: tuple[int, int, int, int] | None):
        """Put the fold handle toward the game center and keep edge changes stable."""
        if not client_rect:
            return
        desired = collapse_edge_for_position(
            self.orientation, client_rect, self.button_bar_screen_rect(), self.collapse_edge
        )
        if desired == self.collapse_edge:
            return
        anchor = self._outer_anchor()
        self.collapse_edge = desired
        self._build_buttons()
        if not self.locked:
            self._layout_unlocked()
        self._restore_outer_anchor(anchor)

    def set_items(self, items: list[DockItem]):
        self._destroy_flyout()
        self.items = items
        self._build_buttons()

    def set_ui_language(self, language: str):
        self.ui_language = language if language in DOCK_EDIT_TEXTS else "KR"
        self._configure_drag_handle()

    def _configure_drag_handle(self):
        vertical = self.orientation == "vertical"
        collapsed_horizontal = self.collapsed and not vertical
        collapsed_vertical = self.collapsed and vertical
        self.drag_handle.configure(
            text=(
                DOCK_EDIT_COLLAPSED_VERTICAL_TEXTS[self.ui_language]
                if collapsed_vertical
                else DOCK_EDIT_VERTICAL_TEXTS[self.ui_language]
                if vertical
                else DOCK_EDIT_COLLAPSED_TEXTS[self.ui_language]
                if collapsed_horizontal
                else DOCK_EDIT_TEXTS[self.ui_language]
            ),
            padx=5 if collapsed_vertical else 6 if vertical else 8 if collapsed_horizontal else 16,
            pady=5 if self.collapsed else 8,
            justify="center",
            font=("MS Gothic", 9, "bold") if collapsed_vertical else ("Noto Sans KR", 9, "bold"),
        )
        if self._window_exists(self.edit_header_window):
            self.edit_header_window.winfo_children()[0].configure(text=DOCK_EDIT_TEXTS[self.ui_language])

    def _layout_unlocked(self):
        self.drag_handle.pack_forget()
        self.button_frame.pack_forget()
        self.frame.configure(bg=GOLD, padx=1, pady=1)
        self.button_frame.configure(bg=BG)
        self.button_frame.pack(fill="both", expand=True)
        self._position_edit_chrome()

    def _item_state(self, item: DockItem):
        alert = None
        if item.alert is not None:
            try:
                alert = item.alert() or ""
            except Exception:
                alert = ""
        if item.badge is not None:
            try:
                return str(item.badge()), alert
            except Exception:
                return "", alert
        if item.state is None:
            return None, alert
        try:
            return bool(item.state()), alert
        except Exception:
            return False, alert

    def _load_icon(self, item: DockItem, state=None):
        if not item.icon_path:
            return None, None
        icon_width, icon_height = self.icon_size()
        cache_key = (item.icon_path, icon_width, icon_height, state, item.icon_text, item.icon_bottom_text)
        cached = self.icon_cache.get(cache_key)
        if cached:
            return cached
        try:
            with Image.open(item.icon_path) as source:
                normal = source.convert("RGB").resize((icon_width, icon_height), Image.Resampling.LANCZOS)
            if item.icon_text:
                self._draw_icon_text(normal, item.icon_text)
            if item.icon_bottom_text:
                self._draw_icon_bottom_text(normal, item.icon_bottom_text)
            base_state, alert = state if isinstance(state, tuple) else (state, "")
            if base_state is not None:
                self._draw_state_badge(normal, base_state)
            if alert:
                self._draw_alert_badge(normal, alert)
            hover = ImageEnhance.Brightness(normal).enhance(1.16)
            images = ImageTk.PhotoImage(normal), ImageTk.PhotoImage(hover)
            self.icon_cache[cache_key] = images
            return images
        except (OSError, ValueError, tk.TclError):
            return None, None

    def _draw_icon_text(self, image: Image.Image, label: str):
        draw = ImageDraw.Draw(image)
        font_size = max(9, round(12 * self.icon_scale))
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), label, font=font)
        width = box[2] - box[0]
        height = box[3] - box[1]
        x = (image.width - width) // 2
        y = (image.height - height) // 2 - box[1]
        draw.text((x + 1, y + 1), label, font=font, fill="#17130f")
        draw.text((x, y), label, font=font, fill="#f1e5c7")

    def _draw_icon_bottom_text(self, image: Image.Image, label: str):
        draw = ImageDraw.Draw(image)
        font_size = max(7, round(9 * self.icon_scale))
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), label, font=font, stroke_width=2)
        width = box[2] - box[0]
        height = box[3] - box[1]
        x = (image.width - width) // 2 - box[0]
        y = image.height - height - max(2, round(3 * self.icon_scale)) - box[1]
        draw.text(
            (x, y), label, font=font, fill="#ffffff",
            stroke_width=max(1, round(2 * self.icon_scale)), stroke_fill="#000000",
        )

    def _draw_state_badge(self, image: Image.Image, state: bool | str):
        draw = ImageDraw.Draw(image)
        label = str(state) if isinstance(state, str) else ("ON" if state else "OFF")
        font_size = max(8, round(9 * self.icon_scale))
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        text_box = draw.textbbox((0, 0), label, font=font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        pad_x = max(3, round(3 * self.icon_scale))
        pad_y = max(2, round(2 * self.icon_scale))
        badge_width = text_width + pad_x * 2
        badge_height = text_height + pad_y * 2
        left = max(2, round(3 * self.icon_scale))
        bottom = image.height - max(2, round(3 * self.icon_scale))
        right = left + badge_width
        top = bottom - badge_height
        if isinstance(state, str):
            fill, outline = {
                "KR": ("#245b92", "#b9dcff"),
                "JP": ("#a52d33", "#ffd1d1"),
                "EN": ("#151515", "#ffffff"),
            }.get(state, ("#3b3022", "#d8b15a"))
        else:
            fill = "#256b3b" if state else "#762f2b"
            outline = "#8ee6a5" if state else "#ef9a91"
        draw.rounded_rectangle((left, top, right, bottom), radius=3, fill=fill, outline=outline, width=1)
        draw.text((left + pad_x, top + pad_y - text_box[1]), label, font=font, fill="#ffffff")

    def _draw_alert_badge(self, image: Image.Image, label):
        if isinstance(label, tuple) and len(label) == 2:
            text, opacity = str(label[0]), max(0, min(100, int(label[1])))
            if not text or opacity <= 0:
                return
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            font_size = max(32, round(42 * self.icon_scale))
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
            stroke_width = max(2, round(3 * self.icon_scale))
            box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
            text_width = box[2] - box[0]
            text_height = box[3] - box[1]
            x = (image.width - text_width) // 2 - box[0]
            y = (image.height - text_height) // 2 - box[1]
            alpha = round(255 * opacity / 100)
            draw.text(
                (x, y), text, font=font, fill=(255, 220, 55, alpha),
                stroke_width=stroke_width, stroke_fill=(35, 26, 8, alpha),
            )
            image.paste(overlay, (0, 0), overlay)
            return
        label = str(label)
        draw = ImageDraw.Draw(image)
        right = image.width - max(2, round(3 * self.icon_scale))
        top = max(2, round(3 * self.icon_scale))
        try:
            font = ImageFont.truetype("arialbd.ttf", max(7, round(8 * self.icon_scale)))
        except OSError:
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), label, font=font)
        pad_x = max(3, round(3 * self.icon_scale))
        pad_y = max(2, round(2 * self.icon_scale))
        width = box[2] - box[0] + pad_x * 2
        height = box[3] - box[1] + pad_y * 2
        left = right - width
        bottom = top + height
        draw.rounded_rectangle((left, top, right, bottom), radius=3, fill="#a52d33", outline="#ffd1d1", width=1)
        draw.text((left + pad_x, top + pad_y - box[1]), label, font=font, fill="#ffffff")

    def _invoke_primary(self, item: DockItem):
        if self.temporarily_disabled and item.key != "quit":
            return
        if not self.locked and item.key != "settings":
            return
        item.primary()
        if item.focus_after_primary:
            self._request_game_focus()
        self.root.after_idle(lambda: self._refresh_state_badges(schedule_next=False))

    def _request_game_focus(self):
        if self.focus_callback:
            self.root.after_idle(self.focus_callback)

    def _refresh_state_badges(self, schedule_next=True):
        try:
            for item in self.items:
                if item.state is None and item.badge is None and item.alert is None:
                    continue
                button = self.item_buttons.get(item.key)
                if button is None:
                    continue
                state = self._item_state(item)
                if button._state_value == state:
                    continue
                normal_icon, hover_icon = self._load_icon(item, state)
                button._state_value = state
                button._normal_icon = normal_icon
                button._hover_icon = hover_icon
                button.configure(image=normal_icon or "")
            self._refresh_collapsed_alert()
            if schedule_next:
                self.root.after(50, self._refresh_state_badges)
            if not self.locked:
                self._position_edit_chrome()
        except tk.TclError:
            pass

    def set_message(self, text: str, duration: int = 1600):
        self.status.configure(text=text)
        self.status_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - self.status_window.winfo_reqwidth()) // 2
        above_y = self.root.winfo_y() - self.status_window.winfo_reqheight() - 6
        y = above_y if above_y >= 4 else self.root.winfo_y() + self.root.winfo_height() + 6
        self.status_window.geometry(f"+{max(4, x)}+{max(4, y)}")
        self.status_window.deiconify()
        self.status_window.lift(self.root)
        if self.status_hide_job:
            self.root.after_cancel(self.status_hide_job)
        self.status_hide_job = self.root.after(duration, self._hide_status)

    def set_center_message(self, text: str, duration: int = 1600):
        """Show a transient notice in the center of the Godius client."""
        self.status.configure(text=text)
        self.status_window.update_idletasks()
        rect = self.client_rect_provider() if self.client_rect_provider else None
        if rect:
            left, top, right, bottom = rect
            x = left + ((right - left) - self.status_window.winfo_reqwidth()) // 2
            y = top + ((bottom - top) - self.status_window.winfo_reqheight()) // 2
        else:
            x = self.root.winfo_x() + (self.root.winfo_width() - self.status_window.winfo_reqwidth()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - self.status_window.winfo_reqheight()) // 2
        self.status_window.geometry(f"+{max(0, x)}+{max(0, y)}")
        attach_above(
            self.status_window,
            native_window_handle(self.root),
            max(0, x),
            max(0, y),
        )
        if self.status_hide_job:
            self.root.after_cancel(self.status_hide_job)
        self.status_hide_job = self.root.after(duration, self._hide_status)

    def _hide_status(self):
        self.status_hide_job = None
        self.status_window.withdraw()

    def toggle_lock(self):
        anchor = self._button_anchor()
        self.locked = not self.locked
        self.root.configure(bg=GOLD if not self.locked else TRANSPARENT)
        if self.locked:
            self.button_frame.pack_forget()
            self.button_frame.pack(fill="both", expand=True)
            self.frame.configure(bg=TRANSPARENT, padx=0, pady=0)
            self.button_frame.configure(bg=TRANSPARENT)
            self._hide_edit_chrome()
        else:
            self._destroy_flyout()
            self.drag_handle.pack_forget()
            self.frame.configure(bg=GOLD, padx=1, pady=1)
            self.button_frame.configure(bg=BG)
            self.button_frame.pack_forget()
            self.button_frame.pack(fill="both", expand=True)
        self._restore_button_anchor(anchor)
        if not self.locked:
            self._show_edit_chrome()

    def toggle_orientation(self):
        anchor = self._button_anchor()
        self.orientation = "vertical" if self.orientation == "horizontal" else "horizontal"
        self.collapse_edge = "top" if self.orientation == "vertical" else "left"
        self._build_buttons()
        if not self.locked:
            self._layout_unlocked()
        self._restore_button_anchor(anchor)
        if self.on_orientation_changed:
            self.on_orientation_changed(self.orientation)
        self.set_message("세로형 도크" if self.orientation == "vertical" else "가로형 도크")

    def icon_size(self):
        return tuple(max(1, round(value * self.icon_scale)) for value in BASE_ICON_SIZE)

    def can_increase_icon_scale(self):
        return self.icon_scale < MAX_ICON_SCALE - 0.001

    def can_decrease_icon_scale(self):
        return self.icon_scale > MIN_ICON_SCALE + 0.001

    def increase_icon_scale(self):
        self.set_icon_scale(self.icon_scale + ICON_SCALE_STEP)

    def decrease_icon_scale(self):
        self.set_icon_scale(self.icon_scale - ICON_SCALE_STEP)

    def set_icon_scale(self, scale):
        scale = max(MIN_ICON_SCALE, min(MAX_ICON_SCALE, round(float(scale), 2)))
        if abs(scale - self.icon_scale) < 0.001:
            return
        anchor = self._button_anchor()
        self.icon_scale = scale
        self.icon_cache.clear()
        self._build_buttons()
        self._restore_button_anchor(anchor)
        if self.on_scale_changed:
            self.on_scale_changed(self.icon_scale)
        if not self.locked:
            self._position_edit_chrome()
        self.set_message(f"버튼 크기 {round(self.icon_scale * 100)}%")

    def _mousewheel_scale(self, event):
        if self.locked or not event.delta:
            return
        direction = ICON_SCALE_STEP if event.delta > 0 else -ICON_SCALE_STEP
        self.set_icon_scale(self.icon_scale + direction)
        return "break"

    def set_opacity_percent(self, value):
        value = max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(value)))
        if value == self.opacity_percent:
            return
        self.opacity_percent = value
        self.root.attributes("-alpha", value / 100.0)
        if self.on_opacity_changed:
            self.on_opacity_changed(value)
        self.set_message(f"툴바 투명도 {value}%")

    def _mousewheel_opacity(self, event):
        if self.locked or not event.delta:
            return
        self.set_opacity_percent(self.opacity_percent + (5 if event.delta > 0 else -5))
        return "break"

    def _start_resize(self, event):
        if self.locked:
            return
        left, top, right, bottom = self.button_bar_screen_rect()
        self.resize_origin = (
            event.x_root, event.y_root, self.icon_scale,
            max(1, right - left), max(1, bottom - top), self._button_anchor(),
        )
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def _resize(self, event):
        if self.locked or not self.resize_origin:
            return
        start_x, start_y, start_scale, width, height, anchor = self.resize_origin
        ratio_x = (width + event.x_root - start_x) / width
        ratio_y = (height + event.y_root - start_y) / height
        self.set_icon_scale(start_scale * (ratio_x + ratio_y) / 2.0)
        self._restore_button_anchor(anchor)

    def _stop_resize(self, event):
        if not self.resize_origin:
            return
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.resize_origin = None
        self._position_edit_chrome()

    def _start_drag(self, event):
        if self.locked:
            return
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag(self, event):
        if not self.drag_origin:
            return
        start_x, start_y, window_x, window_y = self.drag_origin
        self.root.geometry(f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}")
        self._position_edit_chrome()

    def _stop_drag(self, _event):
        if self.drag_origin and self.on_moved:
            self.on_moved(self.root.winfo_x(), self.root.winfo_y())
        self.drag_origin = None
        self._position_edit_chrome()

    def _run_settings(self, item: DockItem):
        if self.temporarily_disabled and item.key != "quit":
            return
        if not self.locked and item.key != "quit":
            return
        if item.secondary is not None:
            item.secondary()
        elif item.quick_actions:
            item.quick_actions[0].callback()
        else:
            self.set_message(f"{item.label}: 세부 설정 준비 중")
        if item.focus_after_secondary:
            self._request_game_focus()

    def _button_anchor(self) -> tuple[int, int]:
        self.root.update_idletasks()
        buttons = self.button_frame.winfo_children()
        anchor_widget = buttons[0] if buttons else self.button_frame
        return anchor_widget.winfo_rootx(), anchor_widget.winfo_rooty()

    def button_bar_screen_rect(self) -> tuple[int, int, int, int]:
        """Return the real icon bounds, excluding the oversized edit backdrop."""
        self.root.update_idletasks()
        buttons = self.button_frame.winfo_children()
        if not buttons:
            x = self.button_frame.winfo_rootx()
            y = self.button_frame.winfo_rooty()
            return x, y, x + self.button_frame.winfo_width(), y + self.button_frame.winfo_height()
        left = min(button.winfo_rootx() for button in buttons)
        top = min(button.winfo_rooty() for button in buttons)
        right = max(button.winfo_rootx() + button.winfo_width() for button in buttons)
        bottom = max(button.winfo_rooty() + button.winfo_height() for button in buttons)
        return left, top, right, bottom

    def _restore_button_anchor(self, anchor: tuple[int, int]):
        self.root.update_idletasks()
        buttons = self.button_frame.winfo_children()
        anchor_widget = buttons[0] if buttons else self.button_frame
        self._restore_widget_anchor(anchor, anchor_widget)

    def _restore_widget_anchor(self, anchor: tuple[int, int], anchor_widget: tk.Widget | None):
        self.root.update_idletasks()
        anchor_widget = anchor_widget or self.button_frame
        current_x = anchor_widget.winfo_rootx()
        current_y = anchor_widget.winfo_rooty()
        new_x = self.root.winfo_x() + anchor[0] - current_x
        new_y = self.root.winfo_y() + anchor[1] - current_y
        self.root.geometry(f"+{new_x}+{new_y}")
        self.root.update_idletasks()
        if self.on_moved:
            self.on_moved(new_x, new_y)

    def _outer_anchor(self) -> tuple[str, int]:
        left, top, right, bottom = self.button_bar_screen_rect()
        if self.orientation == "horizontal":
            return ("left", left) if self.collapse_edge == "right" else ("right", right)
        return ("top", top) if self.collapse_edge == "bottom" else ("bottom", bottom)

    def _restore_outer_anchor(self, anchor: tuple[str, int]):
        self.root.update_idletasks()
        left, top, right, bottom = self.button_bar_screen_rect()
        edge, position = anchor
        current = {"left": left, "right": right, "top": top, "bottom": bottom}[edge]
        delta = position - current
        x = self.root.winfo_x() + (delta if edge in ("left", "right") else 0)
        y = self.root.winfo_y() + (delta if edge in ("top", "bottom") else 0)
        self.restoring_anchor = True
        try:
            self.root.geometry(f"+{x}+{y}")
            self.root.update_idletasks()
        finally:
            self.restoring_anchor = False
        # Collapsing changes the bar's top-left coordinate even though its
        # outer edge stays fixed. Persist that adjusted coordinate before the
        # client-follow loop can restore the pre-collapse offset.
        if self.on_moved:
            self.on_moved(x, y)

    def _button_enter(self, item: DockItem, button: tk.Button):
        button.configure(bg=PANEL_HOVER, fg="#fff7df")
        if button._hover_icon:
            button.configure(image=button._hover_icon)
        if self.locked and not self.temporarily_disabled and item.show_flyout:
            self._schedule_show_flyout(item, button)

    def set_temporarily_disabled(self, disabled):
        self.temporarily_disabled = bool(disabled)
        self._destroy_flyout()
        for key, button in self.item_buttons.items():
            button.configure(
                state="normal" if key == "quit" or not self.temporarily_disabled else "disabled",
                cursor="hand2" if key == "quit" or not self.temporarily_disabled else "arrow",
            )
        self._draw_collapse_handle(PANEL)

    def _button_leave(self, event, button: tk.Button):
        button.configure(bg=PANEL, fg=TEXT)
        if button._normal_icon:
            button.configure(image=button._normal_icon)
        self._cancel_show_flyout(button)
        if self.locked and self.flyout is not None:
            self._schedule_hide(event)

    def _schedule_show_flyout(self, item: DockItem, owner: tk.Widget):
        self._cancel_show_flyout()
        self._cancel_hide()
        self.flyout_show_owner = owner

        def show_if_still_hovered():
            self.flyout_show_job = None
            self.flyout_show_owner = None
            try:
                hovered = owner.winfo_containing(
                    owner.winfo_pointerx(), owner.winfo_pointery()
                )
            except tk.TclError:
                return
            if hovered is owner:
                self._show_flyout(item, owner)

        # Long enough to ignore an accidental pass, but still responsive when
        # the user deliberately rests the pointer on a toolbar button.
        self.flyout_show_job = self.root.after(280, show_if_still_hovered)

    def _cancel_show_flyout(self, owner: tk.Widget | None = None):
        if owner is not None and self.flyout_show_owner is not owner:
            return
        if self.flyout_show_job:
            try:
                self.root.after_cancel(self.flyout_show_job)
            except tk.TclError:
                pass
        self.flyout_show_job = None
        self.flyout_show_owner = None

    def _show_flyout(self, item: DockItem, owner: tk.Widget):
        if not self.locked:
            return
        self._cancel_hide()
        self._destroy_flyout()
        flyout = tk.Toplevel(self.root)
        self.flyout = flyout
        flyout.withdraw()
        flyout.overrideredirect(True)
        flyout.configure(bg=GOLD)
        flyout.bind("<Enter>", lambda _event: self._cancel_hide())
        flyout.bind("<Leave>", self._schedule_hide)

        actions = list(item.quick_actions)
        resolved_labels = [
            action.label() if callable(action.label) else action.label
            for action in actions
        ]
        ui_family = tkfont.nametofont("TkDefaultFont", root=self.root).actual("family")
        label_font = tkfont.Font(root=self.root, family=ui_family, size=9)
        header_font = tkfont.Font(root=self.root, family=ui_family, size=9, weight="bold")
        widest_text = max(
            [header_font.measure(item.label), *(label_font.measure(label) for label in resolved_labels)],
            default=0,
        )
        # Keep the compact Korean baseline, but let longer localized labels
        # determine the actual menu width instead of clipping them.
        panel_width = max(FLYOUT_WIDTH, widest_text + 42)
        panel = tk.Frame(flyout, bg=BG, padx=5, pady=5)
        panel.pack(padx=1, pady=1)
        # Let Tk derive the outer height from the real font metrics and every
        # child row. Fixed row-count arithmetic clips localized labels when a
        # bundled font requests even a few more vertical pixels.
        panel.grid_columnconfigure(0, weight=1, minsize=panel_width)
        panel.grid_rowconfigure(0, minsize=FLYOUT_HEADER_HEIGHT)
        tk.Label(
            panel, text=item.label, bg=BG, fg=GOLD,
            anchor="center", font=(ui_family, 9, "bold"),
        ).grid(row=0, column=0, sticky="nsew")
        displayed_actions = actions
        for row, action in enumerate(displayed_actions, start=1):
            panel.grid_rowconfigure(row, minsize=FLYOUT_ROW_HEIGHT)
            if action is None:
                tk.Label(
                    panel,
                    text="",
                    anchor="w",
                    bg=PANEL,
                    fg=MUTED,
                    padx=10,
                    font=(ui_family, 9),
                ).grid(row=row, column=0, sticky="nsew", pady=1)
                continue
            action_enabled = action.enabled is None or action.enabled()
            resolved_label = resolved_labels[row - 1]
            action_button = tk.Button(
                panel,
                text=resolved_label,
                command=lambda current=action: self._invoke_quick_action(current.callback),
                anchor="w",
                bg=PANEL,
                fg=TEXT,
                activebackground=PANEL_HOVER,
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=10,
                font=(ui_family, 9),
                state="normal" if action_enabled else "disabled",
                disabledforeground=MUTED,
                cursor="hand2" if action_enabled else "arrow",
            )
            action_button.grid(row=row, column=0, sticky="nsew", pady=1)
            if action_enabled:
                action_button.bind("<Enter>", lambda _event, current=action_button: current.configure(bg=PANEL_HOVER, fg="#fff7df"))
                action_button.bind("<Leave>", lambda _event, current=action_button: current.configure(bg=PANEL, fg=TEXT))

        flyout.update_idletasks()
        flyout_width = flyout.winfo_width()
        flyout_height = flyout.winfo_height()
        screen_width = flyout.winfo_screenwidth()
        screen_height = flyout.winfo_screenheight()
        if self.orientation == "horizontal":
            x = owner.winfo_rootx() + (owner.winfo_width() - flyout_width) // 2
            above_y = owner.winfo_rooty() - flyout_height - 6
            below_y = owner.winfo_rooty() + owner.winfo_height() + 6
            client_rect = self.client_rect_provider() if self.client_rect_provider else None
            if client_rect:
                client_left, client_top, client_right, client_bottom = client_rect
                above_fits = above_y >= client_top
                below_fits = below_y + flyout_height <= client_bottom
                y = above_y if above_fits or not below_fits else below_y
                x = max(client_left, min(x, client_right - flyout_width))
                y = max(client_top, min(y, client_bottom - flyout_height))
            else:
                y = above_y if above_y >= 4 else below_y
        else:
            owner_rect = (
                owner.winfo_rootx(), owner.winfo_rooty(),
                owner.winfo_rootx() + owner.winfo_width(),
                owner.winfo_rooty() + owner.winfo_height(),
            )
            client_rect = self.client_rect_provider() if self.client_rect_provider else None
            if client_rect:
                x, y = vertical_flyout_position(
                    owner_rect, (flyout_width, flyout_height), client_rect
                )
            else:
                left_x = owner.winfo_rootx() - flyout_width - 6
                right_x = owner.winfo_rootx() + owner.winfo_width() + 6
                x = left_x if left_x >= 4 else right_x
                y = owner.winfo_rooty() + (owner.winfo_height() - flyout_height) // 2
        x = max(4, min(x, screen_width - flyout_width - 4))
        y = max(4, min(y, screen_height - flyout_height - 4))
        flyout.geometry(f"+{x}+{y}")
        make_noactivate_toolwindow(flyout, topmost=True)
        flyout.deiconify()

    def _invoke_quick_action(self, callback: Callable[[], None]):
        self._destroy_flyout()
        callback()
        self.root.after_idle(lambda: self._refresh_state_badges(schedule_next=False))

    def _schedule_hide(self, _event=None):
        self._cancel_hide()
        self.hide_job = self.root.after(450, self._destroy_flyout)

    def _cancel_hide(self):
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
            self.hide_job = None

    def _destroy_flyout(self):
        self._cancel_show_flyout()
        self._cancel_hide()
        if self.flyout is not None:
            try:
                self.flyout.destroy()
            except tk.TclError:
                pass
            self.flyout = None

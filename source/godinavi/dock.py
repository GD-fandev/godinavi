import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageTk

from .actions import DockItem


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
FLYOUT_WIDTH = 212
FLYOUT_HEADER_HEIGHT = 34
FLYOUT_ROW_HEIGHT = 36
FLYOUT_ROWS = 3

DOCK_EDIT_TEXTS = {
    "KR": "⠿  이동 영역 · 드래그  |  마우스 휠 · 크기 조절",
    "JP": "⠿  移動エリア・ドラッグ  |  マウスホイール・サイズ調整",
    "EN": "⠿  Move area · Drag  |  Mouse wheel · Resize",
}

DOCK_EDIT_VERTICAL_TEXTS = {
    "KR": "⠿\n이\n동\n·\n드\n래\n그\n\n크\n기\n·\n휠",
    "JP": "⠿\n移\n動\n・\nド\nラ\nッ\nグ\n\nサ\nイ\nズ\n・\nホ\nイ\nー\nル",
    "EN": "⠿\nM\nO\nV\nE\n\nS\nI\nZ\nE\n·\nW\nH\nE\nE\nL",
}


class OverlayDock:
    """Small, movable prototype dock with hover quick actions."""

    def __init__(
        self,
        root: tk.Tk,
        items: list[DockItem],
        on_orientation_changed: Callable[[str], None] | None = None,
        on_moved: Callable[[int, int], None] | None = None,
        on_scale_changed: Callable[[float], None] | None = None,
        on_collapsed_changed: Callable[[bool], None] | None = None,
        initial_orientation: str = "horizontal",
        initial_icon_scale: float = 1.0,
        initial_collapsed: bool = False,
        initial_ui_language: str = "KR",
    ):
        self.root = root
        self.items = items
        self.on_orientation_changed = on_orientation_changed
        self.on_moved = on_moved
        self.on_scale_changed = on_scale_changed
        self.on_collapsed_changed = on_collapsed_changed
        self.orientation = initial_orientation if initial_orientation in ("horizontal", "vertical") else "horizontal"
        self.icon_scale = max(MIN_ICON_SCALE, min(MAX_ICON_SCALE, float(initial_icon_scale)))
        self.locked = True
        self.collapsed = bool(initial_collapsed)
        self.ui_language = initial_ui_language if initial_ui_language in DOCK_EDIT_TEXTS else "KR"
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.hide_job: str | None = None
        self.status_hide_job: str | None = None
        self.flyout: tk.Toplevel | None = None
        self.icon_cache: dict[tuple[str, int, int, bool | str | None], tuple[ImageTk.PhotoImage, ImageTk.PhotoImage]] = {}
        self.item_buttons: dict[str, tk.Button] = {}
        self.collapse_handle: tk.Canvas | None = None

        root.title("GodiNavi")
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT)
        root.geometry("+80+80")
        try:
            root.attributes("-alpha", 0.94)
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
            font=("Malgun Gothic", 9, "bold"),
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
            font=("Malgun Gothic", 9),
        )
        self.status.pack(padx=1, pady=1)
        self.status_window.withdraw()
        self._build_buttons()
        self.root.after(150, self._refresh_state_badges)

    def _build_buttons(self):
        for child in self.button_frame.winfo_children():
            child.destroy()

        self.item_buttons.clear()
        side = "left" if self.orientation == "horizontal" else "top"
        icon_width, icon_height = self.icon_size()
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
            )
            button._normal_icon = normal_icon
            button._hover_icon = hover_icon
            button._state_value = state
            self.item_buttons[item.key] = button
            button.pack(side=side, padx=1, pady=1)
            button.bind("<Enter>", lambda _event, current=item, owner=button: self._button_enter(current, owner))
            button.bind("<Leave>", lambda event, owner=button: self._button_leave(event, owner))
            button.bind("<Button-3>", lambda _event, current=item: self._run_settings(current))
            button.bind("<MouseWheel>", self._mousewheel_scale)

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
        handle.bind("<MouseWheel>", self._mousewheel_scale)

    def _draw_collapse_handle(self, background):
        if not self.collapse_handle:
            return
        handle = self.collapse_handle
        handle.configure(bg=background)
        handle.delete("all")
        width = int(handle.cget("width"))
        height = int(handle.cget("height"))
        if self.orientation == "horizontal":
            if self.collapsed:
                points = (width * 0.65, height * 0.38, width * 0.65, height * 0.62, width * 0.28, height * 0.50)
            else:
                points = (width * 0.35, height * 0.38, width * 0.35, height * 0.62, width * 0.72, height * 0.50)
        else:
            if self.collapsed:
                points = (width * 0.38, height * 0.65, width * 0.62, height * 0.65, width * 0.50, height * 0.28)
            else:
                points = (width * 0.38, height * 0.35, width * 0.62, height * 0.35, width * 0.50, height * 0.72)
        handle.create_polygon(*points, fill=TEXT, outline=GOLD)

    def toggle_collapsed(self):
        quit_button = self.item_buttons.get("quit")
        self.root.update_idletasks()
        anchor = (
            (quit_button.winfo_rootx(), quit_button.winfo_rooty())
            if quit_button is not None
            else self._button_anchor()
        )
        self.collapsed = not self.collapsed
        self._destroy_flyout()
        self._build_buttons()
        self._restore_widget_anchor(anchor, self.item_buttons.get("quit"))
        if self.on_collapsed_changed:
            self.on_collapsed_changed(self.collapsed)

    def set_items(self, items: list[DockItem]):
        self._destroy_flyout()
        self.items = items
        self._build_buttons()

    def set_ui_language(self, language: str):
        self.ui_language = language if language in DOCK_EDIT_TEXTS else "KR"
        self._configure_drag_handle()

    def _configure_drag_handle(self):
        vertical = self.orientation == "vertical"
        self.drag_handle.configure(
            text=(DOCK_EDIT_VERTICAL_TEXTS if vertical else DOCK_EDIT_TEXTS)[self.ui_language],
            padx=6 if vertical else 16,
            pady=8,
            justify="center",
        )

    def _layout_unlocked(self):
        self.drag_handle.pack_forget()
        self.button_frame.pack_forget()
        self._configure_drag_handle()
        if self.orientation == "vertical":
            self.drag_handle.pack(fill="y", side="left", padx=(0, 8))
            self.button_frame.pack(fill="both", expand=True, side="left")
        else:
            self.drag_handle.pack(fill="x", side="top", pady=(0, 8))
            self.button_frame.pack(fill="both", expand=True, side="top")

    def _item_state(self, item: DockItem):
        if item.badge is not None:
            try:
                return str(item.badge())
            except Exception:
                return ""
        if item.state is None:
            return None
        try:
            return bool(item.state())
        except Exception:
            return False

    def _load_icon(self, item: DockItem, state=None):
        if not item.icon_path:
            return None, None
        icon_width, icon_height = self.icon_size()
        cache_key = (item.icon_path, icon_width, icon_height, state)
        cached = self.icon_cache.get(cache_key)
        if cached:
            return cached
        try:
            with Image.open(item.icon_path) as source:
                normal = source.convert("RGB").resize((icon_width, icon_height), Image.Resampling.LANCZOS)
            if state is not None:
                self._draw_state_badge(normal, state)
            hover = ImageEnhance.Brightness(normal).enhance(1.16)
            images = ImageTk.PhotoImage(normal), ImageTk.PhotoImage(hover)
            self.icon_cache[cache_key] = images
            return images
        except (OSError, ValueError, tk.TclError):
            return None, None

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

    def _invoke_primary(self, item: DockItem):
        item.primary()
        self.root.after_idle(lambda: self._refresh_state_badges(schedule_next=False))

    def _refresh_state_badges(self, schedule_next=True):
        try:
            for item in self.items:
                if item.state is None and item.badge is None:
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
            if schedule_next:
                self.root.after(150, self._refresh_state_badges)
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

    def _hide_status(self):
        self.status_hide_job = None
        self.status_window.withdraw()

    def toggle_lock(self):
        anchor = self._button_anchor()
        self.locked = not self.locked
        self.root.configure(bg=GOLD if not self.locked else TRANSPARENT)
        if self.locked:
            self.drag_handle.pack_forget()
            self.button_frame.pack_forget()
            self.button_frame.pack(fill="both", expand=True)
            self.frame.configure(bg=TRANSPARENT, padx=0, pady=0)
            self.button_frame.configure(bg=TRANSPARENT)
        else:
            self._destroy_flyout()
            self.frame.configure(bg="#3b3022", padx=12, pady=12)
            self.button_frame.configure(bg=BG)
            self._layout_unlocked()
        self._restore_button_anchor(anchor)
        state = "잠금 · 게임 조작 우선" if self.locked else "편집 · 빈 공간을 드래그하여 이동"
        self.set_message(state, 2400)

    def toggle_orientation(self):
        anchor = self._button_anchor()
        self.orientation = "vertical" if self.orientation == "horizontal" else "horizontal"
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
        self.set_message(f"버튼 크기 {round(self.icon_scale * 100)}%")

    def _mousewheel_scale(self, event):
        if self.locked or not event.delta:
            return
        direction = ICON_SCALE_STEP if event.delta > 0 else -ICON_SCALE_STEP
        self.set_icon_scale(self.icon_scale + direction)
        return "break"

    def _start_drag(self, event):
        if self.locked:
            return
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag(self, event):
        if not self.drag_origin:
            return
        start_x, start_y, window_x, window_y = self.drag_origin
        self.root.geometry(f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}")

    def _stop_drag(self, _event):
        if self.drag_origin and self.on_moved:
            self.on_moved(self.root.winfo_x(), self.root.winfo_y())
        self.drag_origin = None

    def _run_settings(self, item: DockItem):
        if item.secondary is not None:
            item.secondary()
        elif item.quick_actions:
            item.quick_actions[0].callback()
        else:
            self.set_message(f"{item.label}: 세부 설정 준비 중")

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

    def _button_enter(self, item: DockItem, button: tk.Button):
        button.configure(bg=PANEL_HOVER, fg="#fff7df")
        if button._hover_icon:
            button.configure(image=button._hover_icon)
        if self.locked and item.show_flyout:
            self._show_flyout(item, button)

    def _button_leave(self, event, button: tk.Button):
        button.configure(bg=PANEL, fg=TEXT)
        if button._normal_icon:
            button.configure(image=button._normal_icon)
        if self.locked and self.flyout is not None:
            self._schedule_hide(event)

    def _show_flyout(self, item: DockItem, owner: tk.Widget):
        if not self.locked:
            return
        self._cancel_hide()
        self._destroy_flyout()
        flyout = tk.Toplevel(self.root)
        self.flyout = flyout
        flyout.overrideredirect(True)
        flyout.attributes("-topmost", True)
        flyout.configure(bg=GOLD)
        flyout.bind("<Enter>", lambda _event: self._cancel_hide())
        flyout.bind("<Leave>", self._schedule_hide)

        actions = list(item.quick_actions)
        resolved_labels = [
            action.label() if callable(action.label) else action.label
            for action in actions[:FLYOUT_ROWS]
        ]
        label_font = tkfont.Font(family="Malgun Gothic", size=9)
        header_font = tkfont.Font(family="Malgun Gothic", size=9, weight="bold")
        widest_text = max(
            [header_font.measure(item.label), *(label_font.measure(label) for label in resolved_labels)],
            default=0,
        )
        # Keep the compact Korean baseline, but let longer localized labels
        # determine the actual menu width instead of clipping them.
        panel_width = max(FLYOUT_WIDTH, widest_text + 42)
        visible_rows = FLYOUT_ROWS if actions else 0
        panel_height = FLYOUT_HEADER_HEIGHT + FLYOUT_ROW_HEIGHT * visible_rows + 16
        panel = tk.Frame(flyout, bg=BG, width=panel_width, height=panel_height, padx=5, pady=5)
        panel.pack(padx=1, pady=1)
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, minsize=FLYOUT_HEADER_HEIGHT)
        tk.Label(
            panel, text=item.label, bg=BG, fg=GOLD,
            anchor="center", font=("Malgun Gothic", 9, "bold"),
        ).grid(row=0, column=0, sticky="nsew")
        displayed_actions = actions[:FLYOUT_ROWS] + [None] * max(0, FLYOUT_ROWS - len(actions)) if actions else []
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
                    font=("Malgun Gothic", 9),
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
                font=("Malgun Gothic", 9),
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
            y = above_y if above_y >= 4 else below_y
        else:
            left_x = owner.winfo_rootx() - flyout_width - 6
            right_x = owner.winfo_rootx() + owner.winfo_width() + 6
            x = left_x if left_x >= 4 else right_x
            y = owner.winfo_rooty() + (owner.winfo_height() - flyout_height) // 2
        x = max(4, min(x, screen_width - flyout_width - 4))
        y = max(4, min(y, screen_height - flyout_height - 4))
        flyout.geometry(f"+{x}+{y}")

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
        self._cancel_hide()
        if self.flyout is not None:
            try:
                self.flyout.destroy()
            except tk.TclError:
                pass
            self.flyout = None

import tkinter as tk

from modal_window import activate_modal, bind_modal_escape

from PIL import Image, ImageTk

from .window_attachment import attach_above, native_window_handle


BG = "#17130f"
PANEL = "#2a2118"
FIELD = "#3b3022"
HEADER = "#5a4932"
GOLD = "#d8b15a"
TEXT = "#f1e5c7"
MUTED = "#bda982"
ROW_HEIGHT = 46
ROW_STEP = 50
ROW_AREA_WIDTH = 430

TEXTS = {
    "KR": {"title": "툴바 커스터마이즈", "use": "사용", "apply": "적용", "close": "닫기"},
    "JP": {"title": "ツールバーカスタマイズ", "use": "使用", "apply": "適用", "close": "閉じる"},
    "EN": {"title": "Customize toolbar", "use": "Enabled", "apply": "Apply", "close": "Close"},
}


class ToolbarCustomizeUI:
    """Portal-style owned modal: no title-bar X, footer actions, client-relative position."""

    def __init__(self, master, language_provider, client_rect_provider, owner_provider, config, save_callback, apply_callback):
        self.master = master
        self.language_provider = language_provider
        self.client_rect_provider = client_rect_provider
        self.owner_provider = owner_provider
        self.config = config
        self.save_callback = save_callback
        self.apply_callback = apply_callback
        self.window = None
        self.rows = []
        self.drag_origin = None
        self.last_client_rect = None
        self.current_position = (0, 0)
        self.row_widgets = []
        self.icon_images = []
        self.dragged_row_index = None
        self.drop_row_index = None
        self.drag_ghost = None
        self.drag_ghost_image = None
        self.drag_motion_binding = None
        self.drag_release_binding = None
        self.dragged_row = None
        self.drag_preview_rows = None
        self.row_frames = {}
        self.row_positions = {}
        self.row_targets = {}
        self.row_animation_job = None
        self.drop_placeholder = None

    def texts(self):
        return TEXTS.get(self.language_provider(), TEXTS["KR"])

    def open(self, items):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            activate_modal(self.window)
            return
        self.rows = [
            {
                "key": item.key,
                "label": item.label,
                "icon_path": item.icon_path,
                "enabled": tk.BooleanVar(value=True),
            }
            for item in items if item.key not in {"settings", "quit"}
        ]
        disabled_value = self.config.get("toolbar_disabled_items", [])
        disabled = set(disabled_value if isinstance(disabled_value, list) else [])
        for row in self.rows:
            row["enabled"].set(row["key"] not in disabled)
        self._build()

    def _build(self):
        text = self.texts()
        win = tk.Toplevel(self.master)
        self.window = win
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=GOLD)
        win.protocol("WM_DELETE_WINDOW", self.close)
        bind_modal_escape(win, self.close)

        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=2, pady=2)
        header = tk.Frame(body, bg=HEADER, height=50, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(header, text=text["title"], bg=HEADER, fg="#ffe09a", font=("Noto Sans KR", 13, "bold"), padx=14)
        title.pack(side="left", fill="y")
        for widget in (header, title):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)

        self.list_frame = tk.Frame(body, bg=BG, padx=14, pady=12)
        self.list_frame.pack(fill="both", expand=True)
        self.rows_frame = tk.Frame(
            self.list_frame, bg=BG, width=ROW_AREA_WIDTH,
        )
        self.rows_frame.pack(fill="x")
        self.rows_frame.pack_propagate(False)
        self._render_rows()

        footer = tk.Frame(body, bg=PANEL, padx=12, pady=10)
        footer.pack(fill="x")
        self._button(footer, text["close"], self.close).pack(side="right", padx=(6, 0))
        self._button(footer, text["apply"], self.apply, primary=True).pack(side="right")
        win.update_idletasks()
        self._restore_position()
        # A withdrawn Toplevel can keep reporting winfo_x/y as 0,0 even after
        # geometry() was assigned. Pass the calculated coordinates directly.
        attach_above(win, self.owner_provider(), *self.current_position)
        self.last_client_rect = self.client_rect_provider()
        win.after(150, self._follow_owner)

    def _render_rows(self):
        for child in self.rows_frame.winfo_children():
            child.destroy()
        self.row_widgets.clear()
        self.row_frames.clear()
        self.row_positions.clear()
        self.row_targets.clear()
        self.icon_images.clear()
        self.rows_frame.configure(
            width=ROW_AREA_WIDTH,
            height=max(1, len(self.rows) * ROW_STEP),
        )
        text = self.texts()
        for index, row in enumerate(self.rows):
            line = tk.Frame(self.rows_frame, bg=FIELD, padx=8, pady=5, cursor="fleur")
            line.place(x=0, y=index * ROW_STEP, relwidth=1, height=ROW_HEIGHT)
            self.row_widgets.append(line)
            self.row_frames[row["key"]] = line
            self.row_positions[row["key"]] = float(index * ROW_STEP)
            tk.Checkbutton(line, text=text["use"], variable=row["enabled"], bg=FIELD, fg=TEXT, activebackground=FIELD, activeforeground=TEXT, selectcolor=PANEL, font=("Noto Sans KR", 9)).pack(side="left")
            icon_label = tk.Label(line, bg=FIELD, width=32, height=32, bd=0, cursor="fleur")
            icon_label.pack(side="left", padx=(8, 10))
            photo = self._row_icon(row.get("icon_path"))
            if photo:
                icon_label.configure(image=photo)
                self.icon_images.append(photo)
            name_label = tk.Label(line, text=row["label"], bg=FIELD, fg=TEXT, anchor="w", font=("Noto Sans KR", 10, "bold"), cursor="fleur")
            name_label.pack(side="left", fill="x", expand=True)
            grip = tk.Label(line, text="≡", bg=FIELD, fg=GOLD, font=("Arial", 17, "bold"), cursor="fleur", padx=8)
            grip.pack(side="right")
            for widget in (line, icon_label, name_label, grip):
                widget.bind("<ButtonPress-1>", lambda event, i=index: self._row_drag_start(event, i))

    def _button(self, parent, label, command, primary=False, compact=False):
        return tk.Button(parent, text=label, command=command, bg=GOLD if primary else HEADER, fg="#17130f" if primary else TEXT, activebackground="#e4c574", activeforeground="#17130f", relief="flat", bd=0, padx=9 if compact else 16, pady=4 if compact else 6, font=("Noto Sans KR", 9, "bold"), cursor="hand2")

    def _row_icon(self, path):
        if not path:
            return None
        try:
            with Image.open(path) as source:
                image = source.convert("RGB").resize((32, 32), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except (OSError, ValueError, tk.TclError):
            return None

    def _row_drag_start(self, event, index):
        self._finish_drag_bindings()
        self.dragged_row_index = index
        self.drop_row_index = index
        self.dragged_row = self.rows[index]
        self.drag_preview_rows = list(self.rows)
        dragged_frame = self.row_frames.get(self.dragged_row["key"])
        if dragged_frame:
            dragged_frame.place_forget()
        self.drop_placeholder = tk.Frame(
            self.rows_frame, bg=PANEL, highlightbackground=GOLD,
            highlightthickness=2,
        )
        self.drop_placeholder.place(
            x=0, y=index * ROW_STEP, relwidth=1, height=ROW_HEIGHT,
        )
        self._create_drag_ghost(self.dragged_row, event.x_root, event.y_root)
        self.drag_motion_binding = self.window.bind_all(
            "<B1-Motion>", self._row_drag_motion, add="+"
        )
        self.drag_release_binding = self.window.bind_all(
            "<ButtonRelease-1>", self._row_drag_end, add="+"
        )

    def _row_drag_motion(self, event):
        if self.dragged_row_index is None:
            return
        self._move_drag_ghost(event.x_root, event.y_root)
        local_y = event.y_root - self.rows_frame.winfo_rooty()
        target = max(0, min(len(self.rows) - 1, int((local_y + ROW_STEP / 2) // ROW_STEP)))
        if target != self.drop_row_index:
            self.drop_row_index = target
            remaining = [row for row in self.rows if row is not self.dragged_row]
            remaining.insert(target, self.dragged_row)
            self.drag_preview_rows = remaining
            self._animate_drag_layout()

    def _row_drag_end(self, _event=None):
        if self.drag_preview_rows is not None:
            self.rows = list(self.drag_preview_rows)
        self.dragged_row_index = None
        self.drop_row_index = None
        self.dragged_row = None
        self.drag_preview_rows = None
        if self.row_animation_job and self.window:
            try:
                self.window.after_cancel(self.row_animation_job)
            except tk.TclError:
                pass
        self.row_animation_job = None
        if self.drop_placeholder and self.drop_placeholder.winfo_exists():
            self.drop_placeholder.destroy()
        self.drop_placeholder = None
        self._destroy_drag_ghost()
        self._finish_drag_bindings()
        if self.window and self.window.winfo_exists():
            self._render_rows()
            self.window.update_idletasks()

    def _animate_drag_layout(self):
        if not self.drag_preview_rows or not self.dragged_row:
            return
        if self.drop_placeholder and self.drop_placeholder.winfo_exists():
            self.drop_placeholder.place_configure(y=self.drop_row_index * ROW_STEP)
        self.row_targets = {
            row["key"]: float(index * ROW_STEP)
            for index, row in enumerate(self.drag_preview_rows)
            if row is not self.dragged_row
        }
        if self.row_animation_job is None:
            self._animation_step()

    def _animation_step(self):
        self.row_animation_job = None
        moving = False
        for key, target in self.row_targets.items():
            frame = self.row_frames.get(key)
            if not frame or not frame.winfo_exists():
                continue
            current = self.row_positions.get(key, target)
            delta = target - current
            if abs(delta) <= 0.6:
                current = target
            else:
                current += delta * 0.38
                moving = True
            self.row_positions[key] = current
            frame.place_configure(y=round(current))
        if moving and self.window and self.window.winfo_exists():
            self.row_animation_job = self.window.after(15, self._animation_step)

    def _create_drag_ghost(self, row, pointer_x, pointer_y):
        ghost = tk.Toplevel(self.window)
        self.drag_ghost = ghost
        ghost.withdraw()
        ghost.overrideredirect(True)
        ghost.transient(self.window)
        ghost.configure(bg=GOLD)
        try:
            ghost.attributes("-alpha", 0.9)
        except tk.TclError:
            pass
        card = tk.Frame(ghost, bg=HEADER, padx=10, pady=7)
        card.pack(padx=2, pady=2)
        photo = self._row_icon(row.get("icon_path"))
        self.drag_ghost_image = photo
        tk.Label(card, image=photo if photo else "", bg=HEADER, width=32, height=32).pack(side="left")
        tk.Label(
            card, text=row["label"], bg=HEADER, fg="#fff1c9",
            width=24, anchor="w", padx=10, font=("Noto Sans KR", 10, "bold"),
        ).pack(side="left")
        ghost.update_idletasks()
        self._move_drag_ghost(pointer_x, pointer_y)
        attach_above(ghost, native_window_handle(self.window), *ghost._drag_position)

    def _move_drag_ghost(self, pointer_x, pointer_y):
        ghost = self.drag_ghost
        if not ghost or not ghost.winfo_exists():
            return
        x = pointer_x + 18
        y = pointer_y - ghost.winfo_reqheight() // 2
        rect = self.client_rect_provider()
        if rect:
            left, top, right, bottom = rect
            x = max(left, min(x, right - ghost.winfo_reqwidth()))
            y = max(top, min(y, bottom - ghost.winfo_reqheight()))
        ghost._drag_position = (int(x), int(y))
        ghost.geometry(f"+{int(x)}+{int(y)}")

    def _destroy_drag_ghost(self):
        ghost = self.drag_ghost
        self.drag_ghost = None
        self.drag_ghost_image = None
        if ghost and ghost.winfo_exists():
            ghost.destroy()

    def _finish_drag_bindings(self):
        for sequence, binding in (
            ("<B1-Motion>", self.drag_motion_binding),
            ("<ButtonRelease-1>", self.drag_release_binding),
        ):
            if binding:
                try:
                    self.window._unbind(("bind", "all", sequence), binding)
                except tk.TclError:
                    pass
        self.drag_motion_binding = None
        self.drag_release_binding = None

    def apply(self):
        order = [row["key"] for row in self.rows]
        enabled = {row["key"] for row in self.rows if row["enabled"].get()}
        previous_value = self.config.get("toolbar_disabled_items", [])
        previous_disabled = set(previous_value if isinstance(previous_value, list) else [])
        self.config["toolbar_item_order"] = order
        self.config["toolbar_disabled_items"] = [key for key in order if key not in enabled]
        self.save_callback()
        self.apply_callback(order, enabled, previous_disabled)

    def _drag_start(self, event):
        self.drag_origin = event.x_root - self.window.winfo_x(), event.y_root - self.window.winfo_y()

    def _drag_move(self, event):
        if not self.drag_origin:
            return
        self._place(event.x_root - self.drag_origin[0], event.y_root - self.drag_origin[1])

    def _drag_end(self, _event=None):
        self.drag_origin = None
        self._save_position()

    def _place(self, x, y):
        rect = self.client_rect_provider()
        self.window.update_idletasks()
        if rect:
            left, top, right, bottom = rect
            x = max(left, min(int(x), right - self.window.winfo_width()))
            y = max(top, min(int(y), bottom - self.window.winfo_height()))
        self.current_position = int(x), int(y)
        self.window.geometry(f"+{int(x)}+{int(y)}")

    def _restore_position(self):
        rect = self.client_rect_provider()
        if not rect:
            self._place(100, 100)
            return
        left, top, right, bottom = rect
        default_x = left + ((right - left) - self.window.winfo_reqwidth()) // 2
        default_y = top + ((bottom - top) - self.window.winfo_reqheight()) // 2
        self._place(left + int(self.config.get("toolbar_customize_offset_x", default_x - left)), top + int(self.config.get("toolbar_customize_offset_y", default_y - top)))

    def _save_position(self):
        rect = self.client_rect_provider()
        if not rect or not self.window:
            return
        x, y = self.current_position
        self.config["toolbar_customize_offset_x"] = x - rect[0]
        self.config["toolbar_customize_offset_y"] = y - rect[1]
        self.save_callback()

    def _follow_owner(self):
        win = self.window
        if not win or not win.winfo_exists():
            return
        rect = self.client_rect_provider()
        if rect and rect != self.last_client_rect and not self.drag_origin:
            left, top, _right, _bottom = rect
            self._place(
                left + int(self.config.get("toolbar_customize_offset_x", 0)),
                top + int(self.config.get("toolbar_customize_offset_y", 0)),
            )
            attach_above(win, self.owner_provider(), *self.current_position)
        self.last_client_rect = rect
        win.after(150, self._follow_owner)

    def close(self):
        if not self.window:
            return
        self._row_drag_end()
        self._save_position()
        self.window.destroy()
        self.window = None

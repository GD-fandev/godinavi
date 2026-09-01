import ctypes
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import tkinter as tk
import re

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, ImageTk

from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, place_modal
from .round_slider import RoundSlider
from .window_attachment import (
    attach_above, focus_native_window, make_noactivate_toolwindow,
    native_window_handle, owner_group_is_foreground,
)


TRANSPARENT = "#ff00ff"
GOLD = "#d8b15a"
HEADER = "#5a4932"
CLOCK_BASE_SCALE = 2.27


def format_clock_time(now, use_24_hour=False):
    if use_24_hour:
        return f"{now.hour:02d}:{now.minute:02d}"
    period = "AM" if now.hour < 12 else "PM"
    hour = now.hour % 12 or 12
    return f"{period} {hour:02d}:{now.minute:02d}"

CLOCK_TEXTS = {
    "KR": {
        "on": "시계 표시 ON", "off": "시계 표시 OFF", "adjust": "드래그 이동 · 휠로 투명도 조절",
        "title": "시계", "alarm": "알람 설정", "stopwatch": "스톱워치", "alarm_pending": "알람을 최대 5개까지 설정할 수 있습니다.",
        "alarm_add": "+ 알람 추가", "alarm_time": "시간", "alarm_memo": "메모", "alarm_sound": "알람음",
        "alarm_enabled": "사용", "alarm_delete": "삭제", "alarm_stop": "STOP", "alarm_snooze": "+5min",
        "alarm_default_memo": "알람", "alarm_max": "알람은 최대 5개까지 설정할 수 있습니다.",
        "hours": "시간", "minutes": "분", "seconds": "초", "start": "시작", "resume": "재생",
        "pause": "일시정지", "stop": "중단", "close": "닫기", "invalid_time": "1초 이상의 시간을 설정해주세요.",
        "overlay_on": "오버레이 ON", "overlay_off": "오버레이 OFF", "sound_volume": "음량",
        "five_second_alert": "5초 전 알림",
        "xp_mode_on": "경험치 측정 ON", "xp_mode_off": "경험치 측정 OFF", "xp_region": "영역 설정",
        "xp_meter_on": "미터기 표시 ON", "xp_meter_off": "미터기 표시 OFF",
        "xp_recognized": "현재 인식: {value}", "xp_no_value": "인식 대기 중", "xp_recent": "최근 측정값",
        "xp_clear": "측정값 초기화", "xp_empty": "측정 기록이 없습니다.", "xp_done": "설정 완료",
    },
    "JP": {
        "on": "時計表示 ON", "off": "時計表示 OFF", "adjust": "ドラッグで移動・ホイールで透明度調整",
        "title": "時計", "alarm": "アラーム設定", "stopwatch": "ストップウォッチ", "alarm_pending": "アラームは5件まで設定できます。",
        "alarm_add": "+ アラーム追加", "alarm_time": "時刻", "alarm_memo": "メモ", "alarm_sound": "アラーム音",
        "alarm_enabled": "使用", "alarm_delete": "削除", "alarm_stop": "STOP", "alarm_snooze": "+5min",
        "alarm_default_memo": "アラーム", "alarm_max": "アラームは5件まで設定できます。",
        "hours": "時間", "minutes": "分", "seconds": "秒", "start": "開始", "resume": "再生",
        "pause": "一時停止", "stop": "中止", "close": "閉じる", "invalid_time": "1秒以上の時間を設定してください。",
        "overlay_on": "オーバーレイ ON", "overlay_off": "オーバーレイ OFF", "sound_volume": "音量",
        "five_second_alert": "5秒前通知",
        "xp_mode_on": "経験値測定 ON", "xp_mode_off": "経験値測定 OFF", "xp_region": "範囲設定",
        "xp_meter_on": "メーター表示 ON", "xp_meter_off": "メーター表示 OFF",
        "xp_recognized": "現在の認識: {value}", "xp_no_value": "認識待機中", "xp_recent": "最近の測定値",
        "xp_clear": "測定値を消去", "xp_empty": "測定履歴がありません。", "xp_done": "設定完了",
    },
    "EN": {
        "on": "Clock display ON", "off": "Clock display OFF", "adjust": "Drag to move · Wheel adjusts opacity",
        "title": "Clock", "alarm": "Alarm", "stopwatch": "Stopwatch", "alarm_pending": "You can configure up to 5 alarms.",
        "alarm_add": "+ Add alarm", "alarm_time": "Time", "alarm_memo": "Memo", "alarm_sound": "Sound",
        "alarm_enabled": "On", "alarm_delete": "Delete", "alarm_stop": "STOP", "alarm_snooze": "+5min",
        "alarm_default_memo": "Alarm", "alarm_max": "You can configure up to 5 alarms.",
        "hours": "Hours", "minutes": "Minutes", "seconds": "Seconds", "start": "Start", "resume": "Play",
        "pause": "Pause", "stop": "Stop", "close": "Close", "invalid_time": "Set a duration of at least one second.",
        "overlay_on": "Overlay ON", "overlay_off": "Overlay OFF", "sound_volume": "Volume",
        "five_second_alert": "5-second warning",
        "xp_mode_on": "EXP tracking ON", "xp_mode_off": "EXP tracking OFF", "xp_region": "Set region",
        "xp_meter_on": "Meter display ON", "xp_meter_off": "Meter display OFF",
        "xp_recognized": "Recognized: {value}", "xp_no_value": "Waiting for recognition", "xp_recent": "Recent measurements",
        "xp_clear": "Clear measurements", "xp_empty": "No measurements yet.", "xp_done": "Done",
    },
}


class ClockOverlay:
    def __init__(
        self, master, bundle_dir, settings, save_settings, language_provider,
        target_rect_provider, owner_hwnd_provider, map_engine=None,
    ):
        self.master = master
        self.bundle_dir = Path(bundle_dir)
        self.settings = settings
        self.save_settings_callback = save_settings
        self.language_provider = language_provider
        self.target_rect_provider = target_rect_provider
        self.owner_hwnd_provider = owner_hwnd_provider
        self.map_engine = map_engine
        self.enabled = bool(settings.get("clock_overlay_enabled", False))
        if not settings.get("clock_overlay_scale_normalized", False):
            # The initially tuned 227% size becomes the new user-facing 100%
            # baseline. This feature has not shipped with the old scale yet,
            # so normalize any development-era value once on startup.
            settings["clock_overlay_scale"] = 1.0
            settings["clock_overlay_scale_normalized"] = True
            if save_settings:
                save_settings()
        self.scale = max(0.5, min(3.0, float(settings.get("clock_overlay_scale", 1.0))))
        self.opacity = max(50, min(100, int(settings.get("clock_overlay_opacity_percent", 100))))
        self.use_24_hour = bool(settings.get("clock_24_hour_format", False))
        self.window = None
        self.label = None
        self.photo = None
        self.header_window = None
        self.header_label = None
        self.grip_window = None
        self.lock_window = None
        self.editing = False
        self.drag_origin = None
        self.resize_origin = None
        self.last_time = None
        self.temporarily_hidden = False
        self.temporarily_hidden_control_visible = False
        self.temporarily_hidden_control_had_grab = False
        self.control_window = None
        self.control_tab = "stopwatch"
        self.control_body = None
        self.control_tab_buttons = {}
        self.alarm_rows = []
        self.alarms = list(settings.get("clock_alarms", []))[:5]
        self.alarm_draft = None
        self.alarm_draft_volume = None
        self.active_alarm = None
        self.alarm_window = None
        self.alarm_memo_label = None
        self.alarm_snooze_button = None
        self.alarm_snooze_until = None
        self.alarm_last_trigger = {}
        self.alarm_flash_on = False
        self.alarm_last_flash_at = 0.0
        self.alarm_repeat_after = None
        self.alarm_sound_volume = max(0, min(100, int(settings.get("clock_alarm_sound_volume", 60))))
        self.alarm_volume_scale = None
        self.stopwatch_display = None
        self.stopwatch_start_button = None
        self.stopwatch_pause_button = None
        self.stopwatch_input_vars = []
        self.stopwatch_inputs = []
        self.stopwatch_state = "idle"
        self.stopwatch_remaining = 0.0
        self.stopwatch_end_at = None
        self.stopwatch_configured_duration = max(
            0, int(settings.get("clock_stopwatch_last_duration", 0) or 0)
        )
        self.stopwatch_remaining = float(self.stopwatch_configured_duration)
        self.stopwatch_window = None
        self.stopwatch_overlay_label = None
        self.stopwatch_overlay_panel = None
        self.stopwatch_xp_gain_window = None
        self.stopwatch_xp_gain_label = None
        self.stopwatch_xp_rate_label = None
        self.stopwatch_xp_gain_visible = False
        self.stopwatch_xp_gain_hide_after = None
        self.stopwatch_overlay_buttons = []
        self.stopwatch_overlay_start_button = None
        self.stopwatch_overlay_pause_button = None
        self.stopwatch_overlay_enabled = bool(settings.get("clock_stopwatch_overlay_enabled", False))
        self.stopwatch_overlay_scale = max(0.5, min(2.0, float(settings.get("clock_stopwatch_overlay_scale", 1.0))))
        self.stopwatch_overlay_opacity = max(50, min(100, int(settings.get("clock_stopwatch_overlay_opacity_percent", 100))))
        self.stopwatch_overlay_editing = False
        self.stopwatch_overlay_drag_origin = None
        self.stopwatch_overlay_resize_origin = None
        self.stopwatch_header_window = None
        self.stopwatch_header_label = None
        self.stopwatch_grip_window = None
        self.stopwatch_lock_window = None
        self.stopwatch_overlay_toggle_button = None
        self.stopwatch_sound_volume = max(0, min(100, int(settings.get("clock_stopwatch_sound_volume", 60))))
        self.stopwatch_five_second_alert = bool(settings.get("clock_stopwatch_five_second_alert", False))
        self.stopwatch_five_second_alert_var = None
        self.stopwatch_countdown_played = set()
        self.stopwatch_countdown_timers = []
        self.stopwatch_warning_after = None
        self.stopwatch_warning_remaining = 0
        self.stopwatch_warning_flashing_until = 0.0
        self.stopwatch_warning_flash_on = False
        self.stopwatch_warning_last_flash_at = 0.0
        self.stopwatch_volume_scale = None
        self.alarm_volume_scale = None
        self.stopwatch_sound_lock = threading.Lock()
        self.xp_mode_enabled = bool(settings.get("clock_xp_tracking_enabled", False))
        self.xp_meter_enabled = bool(settings.get("clock_xp_meter_enabled", False))
        self.xp_current_value = None
        self.xp_start_value = None
        self.xp_finished_start_value = None
        self.xp_finished_duration = 0
        self.xp_finish_pending = False
        self.xp_discard_future = False
        self.xp_future = None
        self.xp_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="godinavi-xp-ocr")
        self.xp_last_capture_at = 0.0
        self.xp_history = list(settings.get("clock_xp_measurements", []))[-10:]
        self.xp_status_label = None
        self.xp_history_frame = None
        self.xp_history_list = None
        self.xp_toggle_button = None
        self.xp_meter_toggle_button = None
        self.xp_region_window = None
        self.xp_region_lock_window = None
        self.xp_region_editing = False
        self.xp_region_drag_origin = None
        self.xp_region_drag_mode = None
        self.source_image = None
        try:
            with Image.open(self.bundle_dir / "assets" / "icons" / "godinavi" / "clock_display.png") as source:
                self.source_image = source.convert("RGBA")
        except (OSError, ValueError):
            pass
        self.master.after(250, self.tick)

    def language(self):
        value = self.language_provider() if self.language_provider else "KR"
        return value if value in CLOCK_TEXTS else "EN"

    def menu_text(self):
        return CLOCK_TEXTS[self.language()]["on" if self.enabled else "off"]

    @staticmethod
    def exists(window):
        try:
            return bool(window and window.winfo_exists())
        except tk.TclError:
            return False

    def game_group_is_foreground(self, window):
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if not owner or not self.exists(window):
            return True
        try:
            return owner_group_is_foreground(owner, native_window_handle(window))
        except (OSError, tk.TclError):
            return False

    def toggle(self):
        self.enabled = not self.enabled
        self.settings["clock_overlay_enabled"] = self.enabled
        if not self.enabled:
            self.editing = False
            self.hide()
        else:
            self.last_time = None
            self.show()
        self.save()

    def save(self):
        self.settings["clock_overlay_enabled"] = self.enabled
        self.settings["clock_overlay_scale"] = self.scale
        self.settings["clock_overlay_opacity_percent"] = self.opacity
        if self.save_settings_callback:
            self.save_settings_callback()

    def ensure_window(self):
        if self.exists(self.window):
            return self.window
        window = tk.Toplevel(self.master)
        self.window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg=TRANSPARENT)
        try:
            window.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        window.attributes("-alpha", self.opacity / 100.0)
        label = tk.Label(window, bg=TRANSPARENT, bd=0, highlightthickness=0, cursor="arrow")
        label.pack()
        self.label = label
        for widget in (window, label):
            widget.bind("<Button-3>", self.toggle_editing)
            widget.bind("<MouseWheel>", self.adjust_opacity)
            widget.bind("<Button-1>", self.open_control_modal)
        make_noactivate_toolwindow(window)
        return window

    def render(self):
        if self.source_image is None:
            return
        window = self.ensure_window()
        previous_x, previous_y = window.winfo_x(), window.winfo_y()
        render_scale = self.scale * CLOCK_BASE_SCALE
        width = max(41, round(self.source_image.width * render_scale))
        height = max(12, round(self.source_image.height * render_scale))
        image = self.source_image.resize((width, height), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(image)
        font_size = max(7, round(11 * render_scale))
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        now = datetime.now()
        clock_color = "#ff4545" if self.active_alarm and self.alarm_flash_on else (
            "#ffd84d" if self.active_alarm else "#fff1c9"
        )
        draw.text(
            (width // 2, height // 2), format_clock_time(now, self.use_24_hour),
            anchor="mm", font=font, fill=clock_color,
            stroke_width=max(1, round(render_scale)), stroke_fill="#24170e",
        )
        self.photo = ImageTk.PhotoImage(image, master=window)
        self.label.configure(image=self.photo)
        window.geometry("")
        window.update_idletasks()
        window.geometry(f"+{previous_x}+{previous_y}")

    def show(self):
        if not self.enabled or self.temporarily_hidden or self.source_image is None:
            return
        window = self.ensure_window()
        if not self.game_group_is_foreground(window):
            return
        current = datetime.now().strftime("%H:%M")
        if current != self.last_time or self.photo is None:
            self.last_time = current
            self.render()
        window.deiconify()
        self.position()
        if self.editing:
            self.show_edit_chrome()

    def hide(self):
        self.hide_edit_chrome()
        self.hide_stopwatch_overlay()
        if self.exists(self.alarm_window):
            self.alarm_window.withdraw()
        if self.exists(self.window):
            self.window.withdraw()

    def tick(self):
        try:
            self.update_alarms()
            self.update_xp_ocr()
            self.update_stopwatch()
            if self.enabled and not self.temporarily_hidden:
                self.show()
                self.show_stopwatch_overlay()
            else:
                self.hide()
                self.hide_stopwatch_overlay()
            self.master.after(250, self.tick)
        except tk.TclError:
            pass

    def texts(self):
        return CLOCK_TEXTS[self.language()]

    @staticmethod
    def format_duration(seconds):
        total = max(0, int(seconds + 0.999))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def open_control_modal(self, _event=None):
        if self.exists(self.control_window):
            self.control_window.deiconify()
            self.control_window.lift()
            activate_modal(self.control_window)
            return "break"
        text = self.texts()
        self.alarm_draft = [dict(alarm) for alarm in self.alarms]
        self.alarm_draft_volume = self.alarm_sound_volume
        window = tk.Toplevel(self.master)
        self.control_window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        outer = tk.Frame(window, bg="#17130f", padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(outer, bg=HEADER, height=44, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(
            header, text=text["title"], bg=HEADER, fg="#ffe09a", anchor="w",
            padx=14, font=("Noto Sans KR", 11, "bold"), cursor="fleur",
        )
        title.pack(side="left", fill="both", expand=True)
        format_buttons = {}

        def select_hour_format(value):
            self.use_24_hour = bool(value)
            self.settings["clock_24_hour_format"] = self.use_24_hour
            self.last_time = None
            self.save()
            if self.enabled:
                self.render()
            for mode, button in format_buttons.items():
                active = mode == self.use_24_hour
                button.configure(
                    bg="#9a7632" if active else "#3b3022",
                    fg="#fff1c9" if active else "#c8b58e",
                )

        for value, label in ((True, "24H"), (False, "12H")):
            button = tk.Button(
                header, text=label, command=lambda current=value: select_hour_format(current),
                bg="#9a7632" if self.use_24_hour == value else "#3b3022",
                fg="#fff1c9" if self.use_24_hour == value else "#c8b58e",
                activebackground="#b18a3d", activeforeground="#fff8df",
                relief="flat", bd=0, padx=10, pady=3,
                font=("Noto Sans KR", 9, "bold"), cursor="hand2",
            )
            button.pack(side="left", padx=(0, 3 if value else 10), pady=7)
            format_buttons[value] = button
        tabs = tk.Frame(outer, bg="#17130f")
        tabs.pack(fill="x", padx=12, pady=(12, 0))
        self.control_tab_buttons = {}
        for key, label in (("alarm", text["alarm"]), ("stopwatch", text["stopwatch"])):
            button = tk.Button(
                tabs, text=label, command=lambda current=key: self.select_control_tab(current),
                relief="flat", bd=0, padx=18, pady=7, cursor="hand2",
                font=("Noto Sans KR", 9, "bold"),
            )
            button.pack(side="left", padx=(0, 4))
            self.control_tab_buttons[key] = button
        self.control_body = tk.Frame(outer, bg="#2a2118", padx=18, pady=18)
        self.control_body.pack(fill="both", expand=True, padx=12, pady=10)
        footer = tk.Frame(outer, bg="#2a2118", padx=12, pady=10)
        # Reserve the action footer before the expandable body. Otherwise a
        # populated measurement list can consume the remaining height and
        # push the Close button outside a screen-constrained modal.
        footer.pack(side="bottom", fill="x", padx=12, pady=(0, 12), before=self.control_body)
        tk.Button(
            footer, text=text["close"], command=self.close_control_modal,
            bg="#3b3022", fg="#f3d68f", activebackground=HEADER, activeforeground="#fff4d2",
            relief="flat", bd=0, padx=18, pady=6, font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        ).pack(side="right")
        bind_modal_drag(window, (header, title), lambda: self.target_rect_provider() or (0, 0, window.winfo_screenwidth(), window.winfo_screenheight()), "clock_control")
        bind_modal_escape(window, self.close_control_modal)
        self.select_control_tab(self.control_tab)
        place_modal(window, minimum_width=720, minimum_height=690, position_key="clock_control")
        activate_modal(window)
        return "break"

    def close_control_modal(self):
        if self.alarm_rows:
            self.save_alarm_rows()
        if self.alarm_draft is not None:
            self.alarms = [dict(alarm) for alarm in self.alarm_draft[:5]]
            self.settings["clock_alarms"] = self.alarms
        if self.alarm_draft_volume is not None:
            self.alarm_sound_volume = int(self.alarm_draft_volume)
            self.settings["clock_alarm_sound_volume"] = self.alarm_sound_volume
        if self.alarm_draft is not None or self.alarm_draft_volume is not None:
            self.save()
        self.alarm_draft = None
        self.alarm_draft_volume = None
        if self.exists(self.control_window):
            self.control_window.destroy()
        self.control_window = None
        self.control_body = None
        self.control_tab_buttons = {}
        self.stopwatch_display = None
        self.stopwatch_start_button = None
        self.stopwatch_pause_button = None
        self.stopwatch_input_vars = []
        self.stopwatch_inputs = []
        self.stopwatch_overlay_toggle_button = None
        self.stopwatch_volume_scale = None
        self.alarm_volume_scale = None
        self.xp_status_label = None
        self.xp_history_list = None
        self.xp_toggle_button = None
        self.alarm_rows = []

    def select_control_tab(self, tab):
        if self.alarm_rows:
            self.save_alarm_rows()
        self.control_tab = tab if tab in ("alarm", "stopwatch") else "stopwatch"
        for key, button in self.control_tab_buttons.items():
            selected = key == self.control_tab
            button.configure(
                bg="#6b5537" if selected else "#3b3022",
                fg="#fff1c9" if selected else "#bda982",
                activebackground="#806846", activeforeground="#ffffff",
            )
        if not self.control_body:
            return
        for child in self.control_body.winfo_children():
            child.destroy()
        if self.control_tab == "alarm":
            self.build_alarm_tab()
            return
        self.build_stopwatch_tab()

    def build_alarm_tab(self):
        text = self.texts()
        tk.Label(
            self.control_body, text=text["alarm_pending"], bg="#2a2118", fg="#bda982",
            anchor="w", font=("Noto Sans KR", 9),
        ).pack(fill="x", pady=(0, 10))
        self.alarm_rows = []
        rows = tk.Frame(self.control_body, bg="#17130f", padx=8, pady=8)
        rows.pack(fill="both", expand=True)
        alarm_source = self.alarm_draft if self.alarm_draft is not None else self.alarms
        for index, alarm in enumerate(alarm_source):
            self.build_alarm_row(rows, index, alarm)
        footer = tk.Frame(self.control_body, bg="#2a2118")
        footer.pack(fill="x", pady=(10, 0))
        add = tk.Button(
            footer, text=text["alarm_add"], command=self.add_alarm,
            state="normal" if len(alarm_source) < 5 else "disabled",
            bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff",
            relief="flat", bd=0, padx=14, pady=6, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        )
        add.pack(side="left")
        alarm_volume = tk.Frame(footer, bg="#2a2118")
        alarm_volume.pack(side="right")
        tk.Label(alarm_volume, text=text["sound_volume"], bg="#2a2118", fg="#bda982",
                 font=("Noto Sans KR", 9)).pack(side="left", padx=(0, 6))
        self.alarm_volume_scale = RoundSlider(
            alarm_volume, value=self.alarm_draft_volume if self.alarm_draft_volume is not None else self.alarm_sound_volume, length=120,
            background="#2a2118", trough="#17130f", fill=GOLD,
        )
        self.alarm_volume_scale.pack(side="left")
        self.alarm_volume_scale.bind("<ButtonRelease-1>", self.preview_alarm_volume)

    def build_alarm_row(self, parent, index, alarm):
        text = self.texts()
        row = tk.Frame(parent, bg="#2a2118", padx=6, pady=6)
        row.pack(fill="x", pady=3)
        enabled = tk.BooleanVar(value=bool(alarm.get("enabled", True)))
        hour = tk.StringVar(value=f"{int(alarm.get('hour', 0)):02d}")
        minute = tk.StringVar(value=f"{int(alarm.get('minute', 0)):02d}")
        memo = tk.StringVar(value=str(alarm.get("memo", text["alarm_default_memo"])))
        sound = tk.StringVar(value="warn")
        tk.Checkbutton(
            row, variable=enabled, text=text["alarm_enabled"], command=self.save_alarm_rows,
            bg="#2a2118", fg="#fff1c9", selectcolor="#17130f", activebackground="#2a2118",
            activeforeground="#ffffff", font=("Noto Sans KR", 8),
        ).pack(side="left", padx=(0, 6))
        hour_box = tk.Spinbox(row, from_=0, to=23, textvariable=hour, width=3, format="%02.0f",
                              bg="#3b3022", fg="#fff1c9", buttonbackground=HEADER, justify="center")
        hour_box.pack(side="left")
        tk.Label(row, text=":", bg="#2a2118", fg="#fff1c9").pack(side="left")
        minute_box = tk.Spinbox(row, from_=0, to=59, textvariable=minute, width=3, format="%02.0f",
                                bg="#3b3022", fg="#fff1c9", buttonbackground=HEADER, justify="center")
        minute_box.pack(side="left", padx=(0, 8))
        entry = tk.Entry(row, textvariable=memo, bg="#3b3022", fg="#fff1c9", insertbackground="#fff1c9",
                         relief="flat", width=24, font=("Noto Sans KR", 9))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)
        menu = tk.OptionMenu(row, sound, "warn", command=lambda _value: self.save_alarm_rows())
        menu.configure(bg="#3b3022", fg="#fff1c9", activebackground=HEADER, relief="flat", bd=0,
                       highlightthickness=0, width=6, font=("Noto Sans KR", 8))
        menu["menu"].configure(bg="#3b3022", fg="#fff1c9")
        menu.pack(side="left", padx=(0, 6))
        tk.Button(
            row, text=text["alarm_delete"], command=lambda i=index: self.delete_alarm(i),
            bg="#762f2b", fg="#fff1c9", activebackground="#923b35", activeforeground="#ffffff",
            relief="flat", bd=0, padx=8, pady=3, cursor="hand2", font=("Noto Sans KR", 8),
        ).pack(side="left")
        values = (enabled, hour, minute, memo, sound)
        self.alarm_rows.append(values)
        for variable in (hour, minute, memo):
            variable.trace_add("write", lambda *_args: self.save_alarm_rows())
        for widget in (hour_box, minute_box, entry):
            widget.bind("<FocusOut>", lambda _event: self.save_alarm_rows())

    def alarm_row_values(self):
        alarms = []
        for enabled, hour, minute, memo, sound in self.alarm_rows:
            try:
                hour_value = max(0, min(23, int(hour.get() or 0)))
                minute_value = max(0, min(59, int(minute.get() or 0)))
            except (ValueError, tk.TclError):
                continue
            alarms.append({
                "enabled": bool(enabled.get()), "hour": hour_value, "minute": minute_value,
                "memo": memo.get().strip() or self.texts()["alarm_default_memo"], "sound": "warn",
            })
        return alarms[:5]

    def save_alarm_rows(self):
        if self.alarm_rows:
            self.alarm_draft = self.alarm_row_values()

    def save_alarm_volume(self, _event=None):
        if self.alarm_volume_scale and self.alarm_volume_scale.winfo_exists():
            self.alarm_draft_volume = int(self.alarm_volume_scale.get())

    def preview_alarm_volume(self, _event=None):
        self.save_alarm_volume()
        volume = int(self.alarm_draft_volume if self.alarm_draft_volume is not None else self.alarm_sound_volume)
        sound_path = self.bundle_dir / "assets" / "warn.mp3"
        if volume <= 0 or not sound_path.is_file():
            return

        def play():
            with self.stopwatch_sound_lock:
                try:
                    send = ctypes.windll.winmm.mciSendStringW
                    send("close godinavi_alarm_preview", None, 0, None)
                    send(f'open "{sound_path}" type mpegvideo alias godinavi_alarm_preview', None, 0, None)
                    send(f"setaudio godinavi_alarm_preview volume to {volume * 10}", None, 0, None)
                    send("play godinavi_alarm_preview", None, 0, None)
                except (AttributeError, OSError):
                    return

        threading.Thread(target=play, name="godinavi-alarm-preview", daemon=True).start()

    def add_alarm(self):
        self.save_alarm_rows()
        if self.alarm_draft is None:
            self.alarm_draft = [dict(alarm) for alarm in self.alarms]
        if len(self.alarm_draft) >= 5:
            return
        now = datetime.now()
        self.alarm_draft.append({"enabled": False, "hour": now.hour, "minute": now.minute, "memo": self.texts()["alarm_default_memo"], "sound": "warn"})
        self.alarm_rows = []
        self.select_control_tab("alarm")

    def delete_alarm(self, index):
        self.save_alarm_rows()
        if self.alarm_draft is None:
            self.alarm_draft = [dict(alarm) for alarm in self.alarms]
        if 0 <= index < len(self.alarm_draft):
            self.alarm_draft.pop(index)
        self.alarm_rows = []
        self.select_control_tab("alarm")

    def build_stopwatch_tab(self):
        text = self.texts()
        display_value = self.stopwatch_remaining
        if self.stopwatch_state == "idle":
            display_value = int(self.settings.get("clock_stopwatch_last_duration", 0) or 0)
        self.stopwatch_display = tk.Label(
            self.control_body, text=self.format_duration(display_value), bg="#17130f", fg="#ffe09a",
            padx=20, pady=12, font=("Consolas", 24, "bold"),
        )
        self.stopwatch_display.pack(fill="x", pady=(0, 18))
        controls = tk.Frame(self.control_body, bg="#2a2118")
        controls.pack()
        volume = tk.Frame(controls, bg="#2a2118")
        volume.pack(side="left", padx=(0, 12))
        tk.Label(
            volume, text=text["sound_volume"], bg="#2a2118", fg="#bda982", font=("Noto Sans KR", 9),
        ).pack(side="left", padx=(0, 6))
        self.stopwatch_volume_scale = RoundSlider(
            volume, value=self.stopwatch_sound_volume, length=105,
            background="#2a2118", trough="#17130f", fill=GOLD,
        )
        self.stopwatch_volume_scale.pack(side="left")
        self.stopwatch_volume_scale.bind("<ButtonRelease-1>", self.preview_stopwatch_sound)
        last = int(self.settings.get("clock_stopwatch_last_duration", 0) or 0)
        initial = (last // 3600, (last % 3600) // 60, last % 60)
        self.stopwatch_input_vars = []
        self.stopwatch_inputs = []
        for index, (label, maximum) in enumerate(((text["hours"], 99), (text["minutes"], 59), (text["seconds"], 59))):
            cell = tk.Frame(controls, bg="#2a2118")
            cell.pack(side="left", padx=6)
            variable = tk.StringVar(value=str(initial[index]))
            self.stopwatch_input_vars.append(variable)
            spinbox = tk.Spinbox(
                cell, from_=0, to=maximum, textvariable=variable, width=4, justify="center",
                bg="#3b3022", fg="#fff1c9", buttonbackground=HEADER, relief="flat", bd=1,
                font=("Consolas", 14, "bold"),
            )
            spinbox.pack()
            self.stopwatch_inputs.append(spinbox)
            tk.Label(cell, text=label, bg="#2a2118", fg="#bda982", font=("Noto Sans KR", 9)).pack(pady=(5, 0))
        self.stopwatch_overlay_toggle_button = tk.Button(
            controls, command=self.toggle_stopwatch_overlay, bg="#3b3022", fg="#fff1c9",
            activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
            padx=10, pady=6, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        )
        self.stopwatch_overlay_toggle_button.pack(side="left", padx=(10, 0))
        for variable in self.stopwatch_input_vars:
            variable.trace_add("write", self.on_stopwatch_input_changed)
        self.on_stopwatch_input_changed()
        buttons = tk.Frame(self.control_body, bg="#2a2118")
        buttons.pack(pady=(22, 0))
        self.stopwatch_start_button = tk.Button(
            buttons, command=self.start_stopwatch, bg="#6b5537", fg="#fff1c9",
            activebackground="#806846", activeforeground="#ffffff", relief="flat", bd=0,
            padx=18, pady=7, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        )
        self.stopwatch_start_button.pack(side="left", padx=4)
        self.stopwatch_pause_button = tk.Button(
            buttons, text=text["pause"], command=self.pause_stopwatch, bg="#3b3022", fg="#fff1c9",
            activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
            padx=18, pady=7, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        )
        self.stopwatch_pause_button.pack(side="left", padx=4)
        tk.Button(
            buttons, text=text["stop"], command=self.stop_stopwatch, bg="#762f2b", fg="#fff1c9",
            activebackground="#923b35", activeforeground="#ffffff", relief="flat", bd=0,
            padx=18, pady=7, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        ).pack(side="left", padx=4)
        self.stopwatch_five_second_alert_var = tk.BooleanVar(value=self.stopwatch_five_second_alert)
        tk.Checkbutton(
            self.control_body, text=text["five_second_alert"], variable=self.stopwatch_five_second_alert_var,
            command=self.toggle_five_second_alert, bg="#2a2118", fg="#fff1c9", selectcolor="#17130f",
            activebackground="#2a2118", activeforeground="#ffffff", font=("Noto Sans KR", 9),
        ).pack(pady=(12, 0))
        xp_panel = tk.Frame(self.control_body, bg="#17130f", padx=10, pady=9)
        xp_panel.pack(fill="both", expand=True, pady=(16, 0))
        xp_controls = tk.Frame(xp_panel, bg="#17130f")
        xp_controls.pack(fill="x")
        self.xp_toggle_button = tk.Button(
            xp_controls, command=self.toggle_xp_mode, bg="#3b3022", fg="#fff1c9",
            activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
            padx=12, pady=5, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        )
        self.xp_toggle_button.pack(side="left")
        tk.Button(
            xp_controls, text=text["xp_region"], command=self.open_xp_region_editor,
            bg="#3b3022", fg="#fff1c9", activebackground=HEADER, activeforeground="#ffffff",
            relief="flat", bd=0, padx=12, pady=5, cursor="hand2", font=("Noto Sans KR", 9),
        ).pack(side="left", padx=(6, 0))
        self.xp_meter_toggle_button = tk.Button(
            xp_controls, command=self.toggle_xp_meter, bg="#3b3022", fg="#fff1c9",
            activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
            padx=12, pady=5, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
        )
        self.xp_meter_toggle_button.pack(side="left", padx=(6, 0))
        self.xp_status_label = tk.Label(
            xp_controls, bg="#17130f", fg="#ffe09a", anchor="e", font=("Noto Sans KR", 9, "bold"),
        )
        self.xp_status_label.pack(side="right", fill="x", expand=True)
        history_header = tk.Frame(xp_panel, bg="#17130f")
        history_header.pack(fill="x", pady=(8, 3))
        tk.Label(
            history_header, text=text["xp_recent"], bg="#17130f", fg="#bda982", font=("Noto Sans KR", 9, "bold"),
        ).pack(side="left")
        tk.Button(
            history_header, text=text["xp_clear"], command=self.clear_xp_history,
            bg="#3b3022", fg="#bda982", activebackground=HEADER, activeforeground="#ffffff",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2", font=("Noto Sans KR", 8),
        ).pack(side="right")
        self.xp_history_list = tk.Listbox(
            xp_panel, height=5, bg="#2a2118", fg="#f1e5c7", selectbackground=HEADER,
            selectforeground="#ffffff", relief="flat", bd=0, highlightthickness=0,
            activestyle="none", font=("Consolas", 9),
        )
        self.xp_history_list.pack(fill="both", expand=True)
        self.refresh_stopwatch_controls()
        self.refresh_xp_ui()

    @staticmethod
    def format_xp(value):
        if value is None:
            return "-"
        return f"{float(value):.5f}%"

    @staticmethod
    def xp_per_hour(gain, elapsed_seconds):
        try:
            elapsed = float(elapsed_seconds)
            return float(gain) * 3600.0 / elapsed if elapsed > 0 else None
        except (TypeError, ValueError):
            return None

    def refresh_xp_ui(self):
        text = self.texts()
        if self.xp_toggle_button and self.xp_toggle_button.winfo_exists():
            self.xp_toggle_button.configure(
                text=text["xp_mode_on" if self.xp_mode_enabled else "xp_mode_off"],
                bg="#8a6a36" if self.xp_mode_enabled else "#3b3022",
            )
        if self.xp_meter_toggle_button and self.xp_meter_toggle_button.winfo_exists():
            self.xp_meter_toggle_button.configure(
                text=text["xp_meter_on" if self.xp_meter_enabled else "xp_meter_off"],
                bg="#8a6a36" if self.xp_meter_enabled else "#3b3022",
            )
        if self.xp_status_label and self.xp_status_label.winfo_exists():
            status = (
                text["xp_recognized"].format(value=self.format_xp(self.xp_current_value))
                if self.xp_current_value is not None else text["xp_no_value"]
            )
            self.xp_status_label.configure(text=status)
        if self.xp_history_list and self.xp_history_list.winfo_exists():
            self.xp_history_list.delete(0, "end")
            if not self.xp_history:
                self.xp_history_list.insert("end", text["xp_empty"])
            else:
                for item in reversed(self.xp_history[-10:]):
                    duration = self.format_duration(float(item.get("duration", 0)))
                    start = self.format_xp(item.get("start"))
                    end = self.format_xp(item.get("end"))
                    gain = self.format_xp(item.get("gain"))
                    hourly = self.xp_per_hour(item.get("gain"), item.get("duration"))
                    hourly_text = f"{hourly:.5f}%/h" if hourly is not None else "-"
                    self.xp_history_list.insert(
                        "end", f"{duration}   {start} -> {end}   (+{gain})   EXP {hourly_text}"
                    )

    def toggle_xp_mode(self):
        self.xp_mode_enabled = not self.xp_mode_enabled
        self.settings["clock_xp_tracking_enabled"] = self.xp_mode_enabled
        if not self.xp_mode_enabled:
            self.xp_start_value = None
            self.xp_finish_pending = False
            self.xp_discard_future = False
            self.close_xp_region_editor(save_region=True)
            self.hide_stopwatch_xp_gain()
        elif not self.settings.get("clock_xp_region"):
            self.open_xp_region_editor()
        self.save()
        self.refresh_xp_ui()

    def toggle_xp_meter(self):
        self.xp_meter_enabled = not self.xp_meter_enabled
        self.settings["clock_xp_meter_enabled"] = self.xp_meter_enabled
        if (
            self.xp_meter_enabled
            and self.xp_mode_enabled
            and self.stopwatch_state in ("running", "paused")
            and self.xp_start_value is not None
        ):
            self.show_stopwatch_xp_gain()
        else:
            self.hide_stopwatch_xp_gain()
        self.save()
        self.refresh_xp_ui()

    def clear_xp_history(self):
        self.xp_history = []
        self.settings["clock_xp_measurements"] = []
        self.save()
        self.refresh_xp_ui()

    def xp_region_bbox(self, allow_default=False):
        client = self.target_rect_provider() if self.target_rect_provider else None
        if not client:
            return None
        left, top, right, bottom = map(int, client)
        client_width, client_height = right - left, bottom - top
        region = self.settings.get("clock_xp_region")
        reference = self.settings.get("clock_xp_reference_size")
        if isinstance(region, (list, tuple)) and len(region) == 4:
            sx = client_width / max(1, int(reference[0])) if isinstance(reference, (list, tuple)) and len(reference) == 2 else 1.0
            sy = client_height / max(1, int(reference[1])) if isinstance(reference, (list, tuple)) and len(reference) == 2 else 1.0
            x1, y1, x2, y2 = region
            bbox = [left + round(x1 * sx), top + round(y1 * sy), left + round(x2 * sx), top + round(y2 * sy)]
        elif allow_default:
            width, height = min(260, max(100, client_width // 4)), 46
            bbox = [left + (client_width - width) // 2, bottom - height - 80, left + (client_width + width) // 2, bottom - 80]
        else:
            return None
        bbox[0] = max(left, min(bbox[0], right - 50))
        bbox[1] = max(top, min(bbox[1], bottom - 24))
        bbox[2] = max(bbox[0] + 50, min(bbox[2], right))
        bbox[3] = max(bbox[1] + 24, min(bbox[3], bottom))
        return tuple(bbox)

    def store_xp_region(self):
        if not self.exists(self.xp_region_window):
            return
        client = self.target_rect_provider() if self.target_rect_provider else None
        if not client:
            return
        self.xp_region_window.update_idletasks()
        left, top, right, bottom = map(int, client)
        x, y = self.xp_region_window.winfo_x(), self.xp_region_window.winfo_y()
        width, height = self.xp_region_window.winfo_width(), self.xp_region_window.winfo_height()
        self.settings["clock_xp_region"] = [x - left, y - top, x + width - left, y + height - top]
        self.settings["clock_xp_reference_size"] = [right - left, bottom - top]
        self.save()

    def ensure_xp_region_editor(self):
        if self.exists(self.xp_region_window):
            return
        window = tk.Toplevel(self.master)
        self.xp_region_window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg="#ff3b30")
        window.attributes("-alpha", 0.55)
        panel = tk.Frame(window, bg="#3a0907", cursor="fleur")
        panel.pack(fill="both", expand=True, padx=2, pady=2)
        label = tk.Label(panel, text="EXP OCR", bg="#3a0907", fg="#ffffff", font=("Consolas", 10, "bold"), cursor="fleur")
        label.place(relx=0.5, rely=0.5, anchor="center")
        grip = tk.Label(panel, text="◢", bg="#3a0907", fg="#ff746c", cursor="sizing", font=("Arial", 14, "bold"))
        grip.place(relx=1.0, rely=1.0, anchor="se")
        for widget in (window, panel, label):
            widget.bind("<Button-1>", lambda event: self.begin_xp_region_drag(event, "move"))
            widget.bind("<B1-Motion>", self.drag_xp_region)
            widget.bind("<ButtonRelease-1>", self.end_xp_region_drag)
            widget.bind("<Button-3>", lambda _event: self.close_xp_region_editor(True))
        grip.bind("<Button-1>", lambda event: self.begin_xp_region_drag(event, "resize"))
        grip.bind("<B1-Motion>", self.drag_xp_region)
        grip.bind("<ButtonRelease-1>", self.end_xp_region_drag)
        make_noactivate_toolwindow(window)
        lock = tk.Toplevel(self.master)
        self.xp_region_lock_window = lock
        lock.withdraw()
        lock.overrideredirect(True)
        lock.configure(bg=GOLD)
        tk.Button(lock, text=self.texts()["xp_done"], command=lambda: self.close_xp_region_editor(True),
                  bg="#3b3022", fg="#fff1c9", relief="flat", bd=0, padx=10, pady=5,
                  cursor="hand2", font=("Noto Sans KR", 9, "bold")).pack(padx=1, pady=1)
        make_noactivate_toolwindow(lock)

    def open_xp_region_editor(self):
        if not self.xp_mode_enabled:
            self.xp_mode_enabled = True
            self.settings["clock_xp_tracking_enabled"] = True
        bbox = self.xp_region_bbox(allow_default=True)
        if not bbox:
            return
        self.ensure_xp_region_editor()
        self.xp_region_editing = True
        left, top, right, bottom = bbox
        self.xp_region_window.geometry(f"{right-left}x{bottom-top}+{left}+{top}")
        self.position_xp_region_lock()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        for window in (self.xp_region_window, self.xp_region_lock_window):
            window.deiconify()
            if owner:
                attach_above(window, owner, window.winfo_x(), window.winfo_y())
        self.save()
        self.refresh_xp_ui()

    def position_xp_region_lock(self):
        if not self.exists(self.xp_region_window) or not self.exists(self.xp_region_lock_window):
            return
        self.xp_region_lock_window.update_idletasks()
        x = self.xp_region_window.winfo_x() + self.xp_region_window.winfo_width() + 6
        y = self.xp_region_window.winfo_y()
        client = self.target_rect_provider() if self.target_rect_provider else None
        if client and x + self.xp_region_lock_window.winfo_reqwidth() > client[2]:
            x = self.xp_region_window.winfo_x() - self.xp_region_lock_window.winfo_reqwidth() - 6
        self.xp_region_lock_window.geometry(f"+{x}+{y}")

    def begin_xp_region_drag(self, event, mode):
        if not self.exists(self.xp_region_window):
            return "break"
        self.xp_region_drag_mode = mode
        self.xp_region_drag_origin = (
            event.x_root, event.y_root, self.xp_region_window.winfo_x(), self.xp_region_window.winfo_y(),
            self.xp_region_window.winfo_width(), self.xp_region_window.winfo_height(),
        )
        return "break"

    def drag_xp_region(self, event):
        if not self.xp_region_drag_origin:
            return "break"
        sx, sy, x, y, width, height = self.xp_region_drag_origin
        dx, dy = event.x_root - sx, event.y_root - sy
        client = self.target_rect_provider() if self.target_rect_provider else None
        if not client:
            return "break"
        left, top, right, bottom = client
        if self.xp_region_drag_mode == "resize":
            width = max(50, min(width + dx, right - x))
            height = max(24, min(height + dy, bottom - y))
        else:
            x = max(left, min(x + dx, right - width))
            y = max(top, min(y + dy, bottom - height))
        self.xp_region_window.geometry(f"{width}x{height}+{x}+{y}")
        self.position_xp_region_lock()
        return "break"

    def end_xp_region_drag(self, _event=None):
        self.xp_region_drag_origin = None
        self.xp_region_drag_mode = None
        self.store_xp_region()
        return "break"

    def close_xp_region_editor(self, save_region=False):
        if save_region:
            self.store_xp_region()
        self.xp_region_editing = False
        for window in (self.xp_region_window, self.xp_region_lock_window):
            if self.exists(window):
                window.withdraw()

    @staticmethod
    def parse_xp_text(value):
        normalized = str(value or "").upper().replace(",", ".").replace("O", "0")
        matches = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d{1,5})?)\s*%?", normalized)
        for match in matches:
            try:
                number = float(match)
            except ValueError:
                continue
            if 0 <= number <= 100:
                return number
        return None

    def recognize_xp_region(self, client, bbox):
        frame = self.map_engine.capture_coordinator.capture_client(client)
        if frame is None:
            return None
        left, top, _right, _bottom = client
        x1, y1, x2, y2 = bbox
        crop = frame.crop((x1 - left, y1 - top, x2 - left, y2 - top)).convert("RGB")
        pixels = crop.load()
        mask = Image.new("L", crop.size, 0)
        output = mask.load()
        for y in range(crop.height):
            for x in range(crop.width):
                red, green, blue = pixels[x, y]
                output[x, y] = 255 if min(red, green, blue) >= 155 and max(red, green, blue) - min(red, green, blue) <= 55 else 0
        prepared = ImageOps.expand(mask, border=8, fill=0).resize(
            ((mask.width + 16) * 4, (mask.height + 16) * 4), Image.Resampling.NEAREST
        )
        # Integer percentages are much shorter OCR tokens than the usual
        # five-decimal display. Some recognizers return an empty result for the
        # white-on-black mask even though a value such as 12.34567% works. Retry
        # with reversed polarity and then the original anti-aliased pixels so
        # low-level values such as 37% are handled as well.
        original = ImageOps.expand(crop, border=8, fill="black").resize(
            ((crop.width + 16) * 4, (crop.height + 16) * 4), Image.Resampling.BICUBIC
        )
        for candidate in (prepared, ImageOps.invert(prepared), original):
            result = self.parse_xp_text(self.map_engine.ocr.recognize_coordinates(candidate))
            if result is not None:
                return result
        return None

    def update_xp_ocr(self):
        if not self.xp_mode_enabled or self.xp_region_editing or self.temporarily_hidden or not self.map_engine:
            return
        if self.xp_future is not None:
            if not self.xp_future.done():
                return
            try:
                result = self.xp_future.result()
            except Exception:
                result = None
            self.xp_future = None
            if self.xp_discard_future:
                self.xp_discard_future = False
            else:
                self.xp_current_value = result
                self.refresh_xp_ui()
                self.refresh_stopwatch_xp_gain()
                if self.xp_finish_pending:
                    self.record_finished_xp_measurement()
        now = time.monotonic()
        if now - self.xp_last_capture_at < 0.75 or self.xp_future is not None:
            return
        client = self.target_rect_provider() if self.target_rect_provider else None
        bbox = self.xp_region_bbox()
        if not client or not bbox:
            return
        self.xp_last_capture_at = now
        self.xp_future = self.xp_executor.submit(self.recognize_xp_region, tuple(client), bbox)

    def finish_xp_measurement(self):
        if not self.xp_mode_enabled or self.xp_start_value is None:
            self.xp_start_value = None
            self.xp_finish_pending = False
            return
        self.xp_finished_start_value = self.xp_start_value
        self.xp_finished_duration = int(self.stopwatch_configured_duration)
        self.xp_start_value = None
        self.xp_finish_pending = True
        self.xp_discard_future = self.xp_future is not None
        self.xp_last_capture_at = 0.0

    def record_finished_xp_measurement(self):
        self.xp_finish_pending = False
        if self.xp_finished_start_value is None or self.xp_current_value is None:
            self.xp_finished_start_value = None
            return
        gain = self.xp_current_value - self.xp_finished_start_value
        if gain < 0:
            gain += 100.0
        self.xp_history.append({
            "duration": self.xp_finished_duration,
            "start": self.xp_finished_start_value,
            "end": self.xp_current_value,
            "gain": gain,
        })
        self.xp_history = self.xp_history[-10:]
        self.settings["clock_xp_measurements"] = self.xp_history
        self.xp_finished_start_value = None
        self.save()
        self.refresh_xp_ui()
        self.refresh_stopwatch_xp_gain(final_value=True)
        self.schedule_stopwatch_xp_gain_hide()

    def requested_stopwatch_duration(self):
        if not self.stopwatch_input_vars:
            return self.stopwatch_configured_duration
        try:
            values = [max(0, int(variable.get() or 0)) for variable in self.stopwatch_input_vars]
        except (TypeError, ValueError, tk.TclError):
            return 0
        return min(values[0], 99) * 3600 + min(values[1], 59) * 60 + min(values[2], 59)

    def on_stopwatch_input_changed(self, *_args):
        if self.stopwatch_state != "idle":
            return
        self.stopwatch_configured_duration = self.requested_stopwatch_duration()
        self.settings["clock_stopwatch_last_duration"] = self.stopwatch_configured_duration
        self.stopwatch_remaining = float(self.stopwatch_configured_duration)
        self.save()
        value = self.format_duration(self.stopwatch_remaining)
        if self.stopwatch_display and self.stopwatch_display.winfo_exists():
            self.stopwatch_display.configure(text=value, font=("Consolas", 24, "bold"))
        if self.stopwatch_overlay_label and self.stopwatch_overlay_label.winfo_exists():
            self.stopwatch_overlay_label.configure(text=value)

    def start_stopwatch(self):
        self.cancel_stopwatch_completion_warning()
        self.close_countdown_sounds()
        self.cancel_stopwatch_xp_gain_hide()
        if self.stopwatch_state == "paused" and self.stopwatch_remaining > 0:
            self.stopwatch_end_at = time.monotonic() + self.stopwatch_remaining
            self.stopwatch_state = "running"
        else:
            duration = self.requested_stopwatch_duration()
            if duration <= 0:
                if self.stopwatch_display:
                    self.stopwatch_display.configure(text=self.texts()["invalid_time"], font=("Noto Sans KR", 10, "bold"))
                return
            self.settings["clock_stopwatch_last_duration"] = duration
            self.stopwatch_configured_duration = duration
            self.xp_start_value = self.xp_current_value if self.xp_mode_enabled else None
            self.stopwatch_remaining = float(duration)
            self.stopwatch_countdown_played.clear()
            self.stopwatch_end_at = time.monotonic() + duration
            self.stopwatch_state = "running"
            self.save()
        self.schedule_countdown_sounds()
        self.refresh_stopwatch_controls()
        self.show_stopwatch_overlay()
        if self.xp_meter_enabled and self.xp_mode_enabled and self.xp_start_value is not None:
            self.show_stopwatch_xp_gain()

    def start_stopwatch_and_focus(self):
        previous_state = self.stopwatch_state
        self.start_stopwatch()
        if self.stopwatch_state == "running" and previous_state != self.stopwatch_state:
            owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
            if owner:
                focus_native_window(owner)

    def pause_stopwatch(self):
        if self.stopwatch_state != "running":
            return
        self.stopwatch_remaining = max(0.0, self.stopwatch_end_at - time.monotonic())
        self.stopwatch_end_at = None
        self.stopwatch_state = "paused"
        self.cancel_countdown_sound_timers()
        self.refresh_stopwatch_controls()

    def pause_stopwatch_and_focus(self):
        self.pause_stopwatch()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            focus_native_window(owner)

    def stop_stopwatch(self):
        self.cancel_stopwatch_completion_warning()
        self.close_countdown_sounds()
        self.stopwatch_state = "idle"
        self.xp_start_value = None
        self.xp_finish_pending = False
        self.xp_discard_future = False
        self.stopwatch_remaining = float(self.stopwatch_configured_duration)
        self.stopwatch_end_at = None
        self.stopwatch_countdown_played.clear()
        self.cancel_countdown_sound_timers()
        self.hide_stopwatch_xp_gain()
        reset_value = self.format_duration(self.stopwatch_remaining)
        if self.stopwatch_display and self.stopwatch_display.winfo_exists():
            self.stopwatch_display.configure(text=reset_value, font=("Consolas", 24, "bold"))
        if self.stopwatch_overlay_label and self.stopwatch_overlay_label.winfo_exists():
            self.stopwatch_overlay_label.configure(text=reset_value)
        self.refresh_stopwatch_controls()

    def stop_stopwatch_and_focus(self):
        self.stop_stopwatch()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            focus_native_window(owner)

    def update_stopwatch(self):
        self.update_stopwatch_warning_flash()
        was_active = self.stopwatch_state in ("running", "paused")
        if self.stopwatch_state == "running":
            self.stopwatch_remaining = max(0.0, self.stopwatch_end_at - time.monotonic())
            if self.stopwatch_remaining <= 0:
                self.stopwatch_state = "idle"
                self.stopwatch_end_at = None
                self.cancel_countdown_sound_timers()
                self.finish_xp_measurement()
                self.start_stopwatch_completion_warning()
                self.stopwatch_remaining = float(self.stopwatch_configured_duration)
        value = self.format_duration(self.stopwatch_remaining)
        if self.stopwatch_display and self.stopwatch_display.winfo_exists() and (self.stopwatch_state != "idle" or was_active):
            self.stopwatch_display.configure(text=value, font=("Consolas", 24, "bold"))
        if self.stopwatch_overlay_label and self.stopwatch_overlay_label.winfo_exists():
            self.stopwatch_overlay_label.configure(text=value)
        self.refresh_stopwatch_controls()

    def refresh_stopwatch_controls(self):
        if self.stopwatch_start_button and self.stopwatch_start_button.winfo_exists():
            self.stopwatch_start_button.configure(
                text=self.texts()["resume" if self.stopwatch_state == "paused" else "start"],
                state="disabled" if self.stopwatch_state in ("running", "finished") else "normal",
            )
        if self.stopwatch_pause_button and self.stopwatch_pause_button.winfo_exists():
            self.stopwatch_pause_button.configure(state="normal" if self.stopwatch_state == "running" else "disabled")
        if self.stopwatch_overlay_toggle_button and self.stopwatch_overlay_toggle_button.winfo_exists():
            self.stopwatch_overlay_toggle_button.configure(
                text=self.texts()["overlay_on" if self.stopwatch_overlay_enabled else "overlay_off"],
                bg="#8a6a36" if self.stopwatch_overlay_enabled else "#3b3022",
            )
        if self.stopwatch_overlay_start_button and self.stopwatch_overlay_start_button.winfo_exists():
            self.stopwatch_overlay_start_button.configure(
                state="disabled" if self.stopwatch_state in ("running", "finished") else "normal"
            )
        if self.stopwatch_overlay_pause_button and self.stopwatch_overlay_pause_button.winfo_exists():
            self.stopwatch_overlay_pause_button.configure(
                state="normal" if self.stopwatch_state == "running" else "disabled"
            )
        input_state = "normal" if self.stopwatch_state == "idle" else "disabled"
        for spinbox in self.stopwatch_inputs:
            if spinbox.winfo_exists():
                spinbox.configure(state=input_state)

    def toggle_stopwatch_overlay(self):
        self.stopwatch_overlay_enabled = not self.stopwatch_overlay_enabled
        self.settings["clock_stopwatch_overlay_enabled"] = self.stopwatch_overlay_enabled
        if self.stopwatch_overlay_enabled:
            self.show_stopwatch_overlay()
        else:
            self.stopwatch_overlay_editing = False
            self.hide_stopwatch_overlay()
            self.hide_stopwatch_edit_chrome()
        self.save()
        self.refresh_stopwatch_controls()

    def set_stopwatch_sound_volume(self, value):
        try:
            self.stopwatch_sound_volume = max(0, min(100, int(float(value))))
        except (TypeError, ValueError):
            return
        self.settings["clock_stopwatch_sound_volume"] = self.stopwatch_sound_volume
        self.save()

    def toggle_five_second_alert(self):
        if self.stopwatch_five_second_alert_var is not None:
            self.stopwatch_five_second_alert = bool(self.stopwatch_five_second_alert_var.get())
        else:
            self.stopwatch_five_second_alert = not self.stopwatch_five_second_alert
        self.settings["clock_stopwatch_five_second_alert"] = self.stopwatch_five_second_alert
        if self.stopwatch_state == "running":
            if self.stopwatch_five_second_alert:
                self.schedule_countdown_sounds()
            else:
                self.cancel_countdown_sound_timers()
        self.save()

    def schedule_countdown_sounds(self):
        self.cancel_countdown_sound_timers()
        if not self.stopwatch_five_second_alert or self.stopwatch_state != "running":
            return
        remaining = max(0.0, self.stopwatch_end_at - time.monotonic()) if self.stopwatch_end_at else 0.0
        for number in range(1, 6):
            if number in self.stopwatch_countdown_played:
                continue
            delay = remaining - number
            if delay < -0.1:
                continue
            delay = max(0.0, delay)
            timer = threading.Timer(delay, self.play_countdown_number, args=(number,))
            timer.daemon = True
            self.stopwatch_countdown_timers.append(timer)
            timer.start()

    def cancel_countdown_sound_timers(self):
        for timer in self.stopwatch_countdown_timers:
            timer.cancel()
        self.stopwatch_countdown_timers = []

    def play_countdown_number(self, number):
        if number not in (1, 2, 3, 4, 5) or self.stopwatch_sound_volume <= 0:
            return
        if number in self.stopwatch_countdown_played:
            return
        self.stopwatch_countdown_played.add(number)
        sound_path = self.bundle_dir / "assets" / "sounds" / "countdown" / f"{number}.mp3"
        if not sound_path.is_file():
            return
        volume = self.stopwatch_sound_volume
        alias = f"godinavi_countdown_{number}"

        def play():
            with self.stopwatch_sound_lock:
                try:
                    send = ctypes.windll.winmm.mciSendStringW
                    send(f"close {alias}", None, 0, None)
                    send(f'open "{sound_path}" type mpegvideo alias {alias}', None, 0, None)
                    send(f"setaudio {alias} volume to {volume * 10}", None, 0, None)
                    send(f"play {alias}", None, 0, None)
                except (AttributeError, OSError):
                    return

        threading.Thread(target=play, name="godinavi-countdown-sound", daemon=True).start()

    def close_countdown_sounds(self):
        try:
            send = ctypes.windll.winmm.mciSendStringW
            for number in range(1, 6):
                send(f"close godinavi_countdown_{number}", None, 0, None)
        except (AttributeError, OSError):
            pass

    def preview_stopwatch_sound(self, _event=None):
        if self.stopwatch_volume_scale and self.stopwatch_volume_scale.winfo_exists():
            self.stopwatch_sound_volume = int(self.stopwatch_volume_scale.get())
            self.settings["clock_stopwatch_sound_volume"] = self.stopwatch_sound_volume
            self.save()
        self.play_stopwatch_warning()

    def ensure_stopwatch_overlay(self):
        if self.exists(self.stopwatch_window):
            return self.stopwatch_window
        window = tk.Toplevel(self.master)
        self.stopwatch_window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        panel = tk.Frame(window, bg="#17130f", padx=6, pady=5)
        panel.pack(padx=1, pady=1)
        self.stopwatch_overlay_panel = panel
        self.stopwatch_overlay_label = tk.Label(
            panel, text="00:00:00", bg="#17130f", fg="#ffe09a", font=("Consolas", 13, "bold"),
        )
        self.stopwatch_overlay_label.pack(side="left", padx=(2, 8))
        self.stopwatch_overlay_buttons = []
        for index, (symbol, callback) in enumerate((
            ("▶", self.start_stopwatch_and_focus),
            ("Ⅱ", self.pause_stopwatch_and_focus),
            ("■", self.stop_stopwatch_and_focus),
        )):
            button = tk.Button(
                panel, text=symbol, command=callback, bg="#3b3022", fg="#fff1c9",
                activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
                width=2, pady=1, cursor="hand2", font=("Segoe UI Symbol", 9, "bold"),
            )
            button.pack(side="left", padx=1)
            self.stopwatch_overlay_buttons.append(button)
            if index == 0:
                self.stopwatch_overlay_start_button = button
            elif index == 1:
                self.stopwatch_overlay_pause_button = button
        window.attributes("-alpha", self.stopwatch_overlay_opacity / 100.0)
        for widget in (window, panel, self.stopwatch_overlay_label, *self.stopwatch_overlay_buttons):
            widget.bind("<Button-3>", self.toggle_stopwatch_overlay_editing)
            widget.bind("<MouseWheel>", self.adjust_stopwatch_overlay_opacity)
        make_noactivate_toolwindow(window)
        self.apply_stopwatch_overlay_scale()
        self.refresh_stopwatch_controls()
        return window

    def show_stopwatch_overlay(self):
        if not self.stopwatch_overlay_enabled or not self.enabled or self.temporarily_hidden:
            return
        window = self.ensure_stopwatch_overlay()
        if not self.game_group_is_foreground(window):
            return
        self.stopwatch_overlay_label.configure(text=self.format_duration(self.stopwatch_remaining))
        window.deiconify()
        self.position_stopwatch_overlay()
        if self.stopwatch_xp_gain_visible:
            self.show_stopwatch_xp_gain()

    def hide_stopwatch_overlay(self):
        self.hide_stopwatch_edit_chrome()
        if self.exists(self.stopwatch_xp_gain_window):
            self.stopwatch_xp_gain_window.withdraw()
        if self.exists(self.stopwatch_window):
            self.stopwatch_window.withdraw()

    def position_stopwatch_overlay(self):
        if not self.exists(self.stopwatch_window) or not self.exists(self.window):
            return
        if self.stopwatch_overlay_drag_origin or self.stopwatch_overlay_resize_origin:
            return
        self.stopwatch_window.update_idletasks()
        rect = self.target_rect_provider() if self.target_rect_provider else None
        saved_x = self.settings.get("clock_stopwatch_overlay_offset_x")
        saved_y = self.settings.get("clock_stopwatch_overlay_offset_y")
        if rect and isinstance(saved_x, (int, float)) and isinstance(saved_y, (int, float)):
            x, y = rect[0] + int(saved_x), rect[1] + int(saved_y)
        else:
            x = self.window.winfo_x() + (self.window.winfo_width() - self.stopwatch_window.winfo_reqwidth()) // 2
            y = self.window.winfo_y() + self.window.winfo_height() + 4
        if rect:
            x = max(rect[0], min(x, rect[2] - self.stopwatch_window.winfo_reqwidth()))
            if y + self.stopwatch_window.winfo_reqheight() > rect[3]:
                y = self.window.winfo_y() - self.stopwatch_window.winfo_reqheight() - 4
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(self.stopwatch_window, owner, x, y)
        else:
            self.stopwatch_window.geometry(f"+{x}+{y}")
        if self.stopwatch_overlay_editing:
            # The stopwatch body is reattached on every overlay tick. Raise
            # the edit chrome afterwards so the resize grip cannot end up
            # behind the Stop button/body window.
            self.show_stopwatch_edit_chrome()
        if self.stopwatch_xp_gain_visible:
            self.position_stopwatch_xp_gain()

    def ensure_stopwatch_xp_gain(self):
        if self.exists(self.stopwatch_xp_gain_window):
            return self.stopwatch_xp_gain_window
        window = tk.Toplevel(self.master)
        self.stopwatch_xp_gain_window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg=TRANSPARENT)
        try:
            window.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        gain_label = tk.Label(
            window, text="0.00000%", bg=TRANSPARENT, fg="#ffffff",
            font=("Consolas", 11, "bold"), padx=4, pady=1,
        )
        gain_label.pack(side="left")
        rate_label = tk.Label(
            window, text=" (-)", bg=TRANSPARENT, fg="#ffd45a",
            font=("Consolas", 11, "bold"), padx=0, pady=1,
        )
        rate_label.pack(side="left", padx=(0, 4))
        self.stopwatch_xp_gain_label = gain_label
        self.stopwatch_xp_rate_label = rate_label
        make_noactivate_toolwindow(window)
        return window

    def stopwatch_xp_gain(self):
        start = self.xp_start_value
        if start is None and self.xp_finish_pending:
            start = self.xp_finished_start_value
        if start is None or self.xp_current_value is None:
            return None
        gain = self.xp_current_value - start
        if gain < 0:
            gain += 100.0
        return gain

    def stopwatch_xp_elapsed(self):
        if self.stopwatch_state == "running" and self.stopwatch_end_at is not None:
            remaining = max(0.0, self.stopwatch_end_at - time.monotonic())
        else:
            remaining = self.stopwatch_remaining
        return max(0.0, float(self.stopwatch_configured_duration) - float(remaining))

    def refresh_stopwatch_xp_gain(self, final_value=False):
        if not self.stopwatch_xp_gain_visible and not final_value:
            return
        gain = self.stopwatch_xp_gain()
        elapsed = self.stopwatch_xp_elapsed()
        if final_value and self.xp_history:
            measurement = self.xp_history[-1]
            gain = measurement.get("gain")
            elapsed = measurement.get("duration", 0)
        if gain is None:
            return
        self.ensure_stopwatch_xp_gain()
        hourly = self.xp_per_hour(gain, elapsed)
        hourly_text = f"{hourly:.5f}%/h" if hourly is not None else "-"
        self.stopwatch_xp_gain_label.configure(text=f"{float(gain):.5f}%")
        self.stopwatch_xp_rate_label.configure(text=f" ({hourly_text})")

    def show_stopwatch_xp_gain(self):
        if (
            not self.xp_meter_enabled
            or not self.xp_mode_enabled
            or not self.stopwatch_overlay_enabled
            or not self.enabled
            or self.temporarily_hidden
        ):
            self.hide_stopwatch_xp_gain()
            return
        self.stopwatch_xp_gain_visible = True
        window = self.ensure_stopwatch_xp_gain()
        if not self.game_group_is_foreground(window):
            return
        self.refresh_stopwatch_xp_gain()
        window.deiconify()
        self.position_stopwatch_xp_gain()

    def position_stopwatch_xp_gain(self):
        if not self.exists(self.stopwatch_xp_gain_window) or not self.exists(self.stopwatch_window):
            return
        window = self.stopwatch_xp_gain_window
        window.update_idletasks()
        x = self.stopwatch_window.winfo_x() + (self.stopwatch_window.winfo_width() - window.winfo_reqwidth()) // 2
        above_y = self.stopwatch_window.winfo_y() - window.winfo_reqheight() - 3
        y = above_y
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            x = max(rect[0], min(x, rect[2] - window.winfo_reqwidth()))
            y = max(rect[1], min(y, rect[3] - window.winfo_reqheight()))
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(window, owner, x, y)
        else:
            window.geometry(f"+{x}+{y}")

    def schedule_stopwatch_xp_gain_hide(self):
        self.cancel_stopwatch_xp_gain_hide()
        self.stopwatch_xp_gain_hide_after = self.master.after(5000, self.hide_stopwatch_xp_gain)

    def cancel_stopwatch_xp_gain_hide(self):
        if self.stopwatch_xp_gain_hide_after is not None:
            try:
                self.master.after_cancel(self.stopwatch_xp_gain_hide_after)
            except tk.TclError:
                pass
        self.stopwatch_xp_gain_hide_after = None

    def hide_stopwatch_xp_gain(self):
        self.cancel_stopwatch_xp_gain_hide()
        self.stopwatch_xp_gain_visible = False
        if self.exists(self.stopwatch_xp_gain_window):
            self.stopwatch_xp_gain_window.withdraw()

    def apply_stopwatch_overlay_scale(self):
        if not self.exists(self.stopwatch_window):
            return
        x, y = self.stopwatch_window.winfo_x(), self.stopwatch_window.winfo_y()
        scale = self.stopwatch_overlay_scale
        if self.stopwatch_overlay_panel:
            self.stopwatch_overlay_panel.configure(padx=max(3, round(6 * scale)), pady=max(2, round(5 * scale)))
        if self.stopwatch_overlay_label:
            self.stopwatch_overlay_label.configure(font=("Consolas", max(8, round(13 * scale)), "bold"))
            self.stopwatch_overlay_label.pack_configure(padx=(max(1, round(2 * scale)), max(4, round(8 * scale))))
        for button in self.stopwatch_overlay_buttons:
            button.configure(
                width=max(1, round(2 * scale)), pady=max(0, round(scale)),
                font=("Segoe UI Symbol", max(7, round(9 * scale)), "bold"),
            )
        self.stopwatch_window.geometry("")
        self.stopwatch_window.update_idletasks()
        self.stopwatch_window.geometry(f"+{x}+{y}")

    def toggle_stopwatch_overlay_editing(self, _event=None):
        if not self.exists(self.stopwatch_window):
            return "break"
        self.stopwatch_overlay_editing = not self.stopwatch_overlay_editing
        self.stopwatch_overlay_drag_origin = None
        self.stopwatch_overlay_resize_origin = None
        if self.stopwatch_overlay_editing:
            self.show_stopwatch_edit_chrome()
        else:
            self.hide_stopwatch_edit_chrome()
            self.save_stopwatch_overlay_position()
        return "break"

    def begin_stopwatch_overlay_drag(self, event):
        if not self.stopwatch_overlay_editing or not self.exists(self.stopwatch_window):
            return
        self.stopwatch_overlay_drag_origin = (
            event.x_root, event.y_root, self.stopwatch_window.winfo_x(), self.stopwatch_window.winfo_y(),
        )
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def drag_stopwatch_overlay(self, event):
        if not self.stopwatch_overlay_drag_origin:
            return
        start_x, start_y, origin_x, origin_y = self.stopwatch_overlay_drag_origin
        x, y = origin_x + event.x_root - start_x, origin_y + event.y_root - start_y
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            x = max(rect[0], min(x, rect[2] - self.stopwatch_window.winfo_width()))
            y = max(rect[1], min(y, rect[3] - self.stopwatch_window.winfo_height()))
        self.stopwatch_window.geometry(f"+{round(x)}+{round(y)}")
        self.position_stopwatch_edit_chrome()

    def end_stopwatch_overlay_drag(self, event):
        if not self.stopwatch_overlay_drag_origin:
            return
        self.stopwatch_overlay_drag_origin = None
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.save_stopwatch_overlay_position()

    def save_stopwatch_overlay_position(self):
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if not rect or not self.exists(self.stopwatch_window):
            return
        self.settings["clock_stopwatch_overlay_offset_x"] = self.stopwatch_window.winfo_x() - rect[0]
        self.settings["clock_stopwatch_overlay_offset_y"] = self.stopwatch_window.winfo_y() - rect[1]
        self.settings["clock_stopwatch_overlay_scale"] = self.stopwatch_overlay_scale
        self.settings["clock_stopwatch_overlay_opacity_percent"] = self.stopwatch_overlay_opacity
        self.save()

    def adjust_stopwatch_overlay_opacity(self, event):
        if not self.stopwatch_overlay_editing or not event.delta:
            return None
        self.stopwatch_overlay_opacity = max(
            50, min(100, self.stopwatch_overlay_opacity + (5 if event.delta > 0 else -5))
        )
        self.stopwatch_window.attributes("-alpha", self.stopwatch_overlay_opacity / 100.0)
        return "break"

    def begin_stopwatch_overlay_resize(self, event):
        if not self.stopwatch_overlay_editing or not self.exists(self.stopwatch_window):
            return
        self.stopwatch_overlay_resize_origin = (
            event.x_root, event.y_root, self.stopwatch_overlay_scale,
            self.stopwatch_window.winfo_width(), self.stopwatch_window.winfo_height(),
        )
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def resize_stopwatch_overlay(self, event):
        if not self.stopwatch_overlay_resize_origin:
            return
        start_x, start_y, start_scale, start_width, start_height = self.stopwatch_overlay_resize_origin
        horizontal = (start_width + event.x_root - start_x) / max(1, start_width)
        vertical = (start_height + event.y_root - start_y) / max(1, start_height)
        scale = max(0.5, min(2.0, round(start_scale * (horizontal + vertical) / 2.0, 2)))
        if abs(scale - self.stopwatch_overlay_scale) < 0.01:
            return
        self.stopwatch_overlay_scale = scale
        self.apply_stopwatch_overlay_scale()
        self.position_stopwatch_edit_chrome()

    def end_stopwatch_overlay_resize(self, event):
        if not self.stopwatch_overlay_resize_origin:
            return
        self.stopwatch_overlay_resize_origin = None
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.save_stopwatch_overlay_position()

    def ensure_stopwatch_header(self):
        if self.exists(self.stopwatch_header_window):
            self.stopwatch_header_label.configure(text=self.texts()["adjust"])
            return self.stopwatch_header_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        label = tk.Label(
            window, text=self.texts()["adjust"], bg=HEADER, fg="#fff1c9", anchor="w",
            padx=8, pady=4, cursor="fleur", font=("Noto Sans KR", 8, "bold"),
        )
        label.pack(fill="both", expand=True, padx=1, pady=1)
        label.bind("<ButtonPress-1>", self.begin_stopwatch_overlay_drag)
        label.bind("<B1-Motion>", self.drag_stopwatch_overlay)
        label.bind("<ButtonRelease-1>", self.end_stopwatch_overlay_drag)
        label.bind("<MouseWheel>", self.adjust_stopwatch_overlay_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.stopwatch_header_window, self.stopwatch_header_label = window, label
        return window

    def ensure_stopwatch_grip(self):
        if self.exists(self.stopwatch_grip_window):
            return self.stopwatch_grip_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        grip = tk.Canvas(window, width=16, height=16, bg=HEADER, highlightthickness=1, highlightbackground=GOLD, cursor="size_nw_se")
        grip.pack(fill="both", expand=True)
        grip.create_line(4, 14, 14, 4, fill="#fff1c9", width=1)
        grip.create_line(9, 14, 14, 9, fill="#fff1c9", width=1)
        grip.bind("<ButtonPress-1>", self.begin_stopwatch_overlay_resize)
        grip.bind("<B1-Motion>", self.resize_stopwatch_overlay)
        grip.bind("<ButtonRelease-1>", self.end_stopwatch_overlay_resize)
        grip.bind("<MouseWheel>", self.adjust_stopwatch_overlay_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.stopwatch_grip_window = window
        return window

    def ensure_stopwatch_lock(self):
        if self.exists(self.stopwatch_lock_window):
            return self.stopwatch_lock_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        tk.Button(
            window, text="🔓", command=self.toggle_stopwatch_overlay_editing, bg="#3b3022", fg="#fff1c9",
            activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
            highlightthickness=0, cursor="hand2", font=("Segoe UI Emoji", 12),
        ).pack(fill="both", expand=True, padx=1, pady=1)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.stopwatch_lock_window = window
        return window

    def show_stopwatch_edit_chrome(self):
        windows = (self.ensure_stopwatch_header(), self.ensure_stopwatch_grip(), self.ensure_stopwatch_lock())
        self.position_stopwatch_edit_chrome()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        for window in windows:
            window.deiconify()
            if owner:
                attach_above(window, owner, window.winfo_x(), window.winfo_y())
            window.lift()

    def hide_stopwatch_edit_chrome(self):
        for window in (self.stopwatch_header_window, self.stopwatch_grip_window, self.stopwatch_lock_window):
            if self.exists(window):
                window.withdraw()

    def position_stopwatch_edit_chrome(self):
        if not self.exists(self.stopwatch_window):
            return
        header, grip, lock = self.ensure_stopwatch_header(), self.ensure_stopwatch_grip(), self.ensure_stopwatch_lock()
        x, y = self.stopwatch_window.winfo_x(), self.stopwatch_window.winfo_y()
        width, height = self.stopwatch_window.winfo_width(), self.stopwatch_window.winfo_height()
        rect = self.target_rect_provider() if self.target_rect_provider else None
        header_height = 28
        header_y = y - header_height - 4
        if rect and header_y < rect[1]:
            header_y = y + height + 4
        header.geometry(f"{max(160, width)}x{header_height}+{x}+{header_y}")
        grip.update_idletasks()
        grip.geometry(f"+{x + width - grip.winfo_reqwidth()}+{y + height - grip.winfo_reqheight()}")
        lock.update_idletasks()
        lock_x = x + width + 6
        if rect and lock_x + lock.winfo_reqwidth() > rect[2]:
            lock_x = x - lock.winfo_reqwidth() - 6
        lock.geometry(f"+{lock_x}+{y}")

    def play_stopwatch_warning(self):
        sound_path = self.bundle_dir / "assets" / "warn.mp3"
        if not sound_path.is_file() or self.stopwatch_sound_volume <= 0:
            return
        volume = self.stopwatch_sound_volume

        def play():
            with self.stopwatch_sound_lock:
                try:
                    send = ctypes.windll.winmm.mciSendStringW
                    send("close godinavi_stopwatch", None, 0, None)
                    send(f'open "{sound_path}" type mpegvideo alias godinavi_stopwatch', None, 0, None)
                    send(f"setaudio godinavi_stopwatch volume to {volume * 10}", None, 0, None)
                    send("play godinavi_stopwatch", None, 0, None)
                except (AttributeError, OSError):
                    return

        threading.Thread(target=play, name="godinavi-stopwatch-sound", daemon=True).start()

    def start_stopwatch_completion_warning(self):
        self.cancel_stopwatch_completion_warning()
        self.stopwatch_warning_remaining = 3
        self.stopwatch_warning_flashing_until = time.monotonic() + 3.6
        self.stopwatch_warning_last_flash_at = 0.0
        self.play_next_stopwatch_completion_warning()

    def play_next_stopwatch_completion_warning(self):
        self.stopwatch_warning_after = None
        if self.stopwatch_warning_remaining <= 0:
            return
        self.play_stopwatch_warning()
        self.stopwatch_warning_remaining -= 1
        if self.stopwatch_warning_remaining > 0:
            self.stopwatch_warning_after = self.master.after(1200, self.play_next_stopwatch_completion_warning)

    def cancel_stopwatch_completion_warning(self):
        if self.stopwatch_warning_after is not None:
            try:
                self.master.after_cancel(self.stopwatch_warning_after)
            except tk.TclError:
                pass
        self.stopwatch_warning_after = None
        self.stopwatch_warning_remaining = 0
        self.stopwatch_warning_flashing_until = 0.0
        self.stopwatch_warning_flash_on = False
        if self.stopwatch_overlay_label and self.stopwatch_overlay_label.winfo_exists():
            self.stopwatch_overlay_label.configure(fg="#ffe09a")

    def update_stopwatch_warning_flash(self):
        if not self.stopwatch_warning_flashing_until:
            return
        now = time.monotonic()
        if now >= self.stopwatch_warning_flashing_until:
            self.stopwatch_warning_flashing_until = 0.0
            self.stopwatch_warning_flash_on = False
            if self.stopwatch_overlay_label and self.stopwatch_overlay_label.winfo_exists():
                self.stopwatch_overlay_label.configure(fg="#ffe09a")
            return
        if now - self.stopwatch_warning_last_flash_at >= 0.5:
            self.stopwatch_warning_last_flash_at = now
            self.stopwatch_warning_flash_on = not self.stopwatch_warning_flash_on
            if self.stopwatch_overlay_label and self.stopwatch_overlay_label.winfo_exists():
                self.stopwatch_overlay_label.configure(fg="#ffffff" if self.stopwatch_warning_flash_on else "#625d55")

    def update_alarms(self):
        now = datetime.now()
        if self.active_alarm and self.alarm_snooze_until:
            remaining = max(0, int((self.alarm_snooze_until - now).total_seconds() + 0.999))
            if self.alarm_snooze_button and self.alarm_snooze_button.winfo_exists():
                self.alarm_snooze_button.configure(text=self.format_duration(remaining)[3:])
            if remaining <= 0:
                self.alarm_snooze_until = None
                self.begin_alarm_ringing()
        if not self.active_alarm:
            minute_key = now.strftime("%Y-%m-%d %H:%M")
            for index, alarm in enumerate(self.alarms):
                if not alarm.get("enabled", True):
                    continue
                if int(alarm.get("hour", -1)) == now.hour and int(alarm.get("minute", -1)) == now.minute:
                    if self.alarm_last_trigger.get(index) == minute_key:
                        continue
                    self.alarm_last_trigger[index] = minute_key
                    self.active_alarm = dict(alarm)
                    self.active_alarm["_index"] = index
                    self.begin_alarm_ringing()
                    break
        if self.active_alarm:
            monotonic_now = time.monotonic()
            if not self.alarm_snooze_until and monotonic_now - self.alarm_last_flash_at >= 0.5:
                self.alarm_last_flash_at = monotonic_now
                self.alarm_flash_on = not self.alarm_flash_on
                self.last_time = None
                if self.exists(self.window):
                    self.render()
            self.show_alarm_controls()

    def begin_alarm_ringing(self):
        self.alarm_flash_on = True
        self.alarm_last_flash_at = 0.0
        self.play_alarm_sound()
        self.show_alarm_controls()

    def play_alarm_sound(self):
        if not self.active_alarm or self.alarm_snooze_until:
            return
        sound_path = self.bundle_dir / "assets" / "warn.mp3"
        if sound_path.is_file() and self.alarm_sound_volume > 0:
            volume = self.alarm_sound_volume

            def play():
                with self.stopwatch_sound_lock:
                    try:
                        send = ctypes.windll.winmm.mciSendStringW
                        send("close godinavi_alarm", None, 0, None)
                        send(f'open "{sound_path}" type mpegvideo alias godinavi_alarm', None, 0, None)
                        send(f"setaudio godinavi_alarm volume to {volume * 10}", None, 0, None)
                        send("play godinavi_alarm", None, 0, None)
                    except (AttributeError, OSError):
                        return

            threading.Thread(target=play, name="godinavi-alarm-sound", daemon=True).start()
        if self.alarm_repeat_after is not None:
            try:
                self.master.after_cancel(self.alarm_repeat_after)
            except tk.TclError:
                pass
        self.alarm_repeat_after = self.master.after(1200, self.play_alarm_sound)

    def silence_alarm_sound(self):
        if self.alarm_repeat_after is not None:
            try:
                self.master.after_cancel(self.alarm_repeat_after)
            except tk.TclError:
                pass
            self.alarm_repeat_after = None
        try:
            ctypes.windll.winmm.mciSendStringW("close godinavi_alarm", None, 0, None)
        except (AttributeError, OSError):
            pass

    def ensure_alarm_controls(self):
        if self.exists(self.alarm_window):
            return self.alarm_window
        window = tk.Toplevel(self.master)
        self.alarm_window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg="#ff4545")
        panel = tk.Frame(window, bg="#241b13", padx=9, pady=7)
        panel.pack(fill="both", expand=True, padx=1, pady=1)
        self.alarm_memo_label = tk.Label(panel, bg="#241b13", fg="#ffe09a", anchor="w",
                                         font=("Noto Sans KR", 9, "bold"))
        self.alarm_memo_label.pack(fill="x", pady=(0, 6))
        button_row = tk.Frame(panel, bg="#241b13")
        button_row.pack()
        self.alarm_snooze_button = tk.Button(
            button_row, text=self.texts()["alarm_snooze"], command=self.snooze_alarm,
            bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff",
            relief="flat", bd=0, padx=9, pady=4, cursor="hand2", font=("Consolas", 9, "bold"),
        )
        self.alarm_snooze_button.pack(side="left", padx=2)
        tk.Button(
            button_row, text=self.texts()["alarm_stop"], command=self.stop_alarm,
            bg="#762f2b", fg="#fff1c9", activebackground="#923b35", activeforeground="#ffffff",
            relief="flat", bd=0, padx=9, pady=4, cursor="hand2", font=("Consolas", 9, "bold"),
        ).pack(side="left", padx=2)
        make_noactivate_toolwindow(window)
        return window

    def show_alarm_controls(self):
        if not self.active_alarm or not self.enabled or self.temporarily_hidden or not self.exists(self.window):
            return
        window = self.ensure_alarm_controls()
        if not self.game_group_is_foreground(window):
            return
        memo = str(self.active_alarm.get("memo") or self.texts()["alarm_default_memo"])
        self.alarm_memo_label.configure(text=memo[:10])
        if not self.alarm_snooze_until:
            self.alarm_snooze_button.configure(text=self.texts()["alarm_snooze"])
        window.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - window.winfo_reqwidth()) // 2
        y = self.window.winfo_y() + self.window.winfo_height() + 4
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            x = max(rect[0], min(x, rect[2] - window.winfo_reqwidth()))
            if y + window.winfo_reqheight() > rect[3]:
                y = self.window.winfo_y() - window.winfo_reqheight() - 4
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(window, owner, x, y)
        else:
            window.geometry(f"+{x}+{y}")

    def snooze_alarm(self):
        if not self.active_alarm:
            return
        self.silence_alarm_sound()
        self.alarm_snooze_until = datetime.now() + timedelta(minutes=5)
        self.alarm_flash_on = False
        self.last_time = None
        if self.exists(self.window):
            self.render()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            focus_native_window(owner)

    def stop_alarm(self):
        self.silence_alarm_sound()
        alarm_index = self.active_alarm.get("_index") if self.active_alarm else None
        if isinstance(alarm_index, int) and 0 <= alarm_index < len(self.alarms):
            self.alarms[alarm_index]["enabled"] = False
            self.settings["clock_alarms"] = self.alarms
            if self.alarm_draft is not None and alarm_index < len(self.alarm_draft):
                self.alarm_draft[alarm_index]["enabled"] = False
            if alarm_index < len(self.alarm_rows):
                try:
                    self.alarm_rows[alarm_index][0].set(False)
                except tk.TclError:
                    pass
            self.save()
        self.active_alarm = None
        self.alarm_snooze_until = None
        self.alarm_flash_on = False
        self.last_time = None
        if self.exists(self.alarm_window):
            self.alarm_window.withdraw()
        if self.exists(self.window):
            self.render()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            focus_native_window(owner)

    def position(self):
        if not self.exists(self.window) or self.drag_origin or self.resize_origin:
            return
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if not rect:
            self.window.withdraw()
            return
        self.window.update_idletasks()
        left, top, right, bottom = rect
        width, height = self.window.winfo_reqwidth(), self.window.winfo_reqheight()
        saved_x = self.settings.get("clock_overlay_offset_x")
        saved_y = self.settings.get("clock_overlay_offset_y")
        x = left + int(saved_x) if isinstance(saved_x, (int, float)) else left + max(0, (right - left - width) // 2)
        y = top + int(saved_y) if isinstance(saved_y, (int, float)) else top + 8
        x = max(left, min(x, right - width))
        y = max(top, min(y, bottom - height))
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(self.window, owner, x, y)
        else:
            self.window.geometry(f"+{x}+{y}")
        if self.editing:
            self.position_edit_chrome()

    def toggle_editing(self, _event=None):
        if not self.exists(self.window):
            return "break"
        self.editing = not self.editing
        self.drag_origin = None
        self.resize_origin = None
        if self.editing:
            self.show_edit_chrome()
        else:
            self.hide_edit_chrome()
            self.save_position()
        return "break"

    def begin_drag(self, event):
        if not self.editing or not self.exists(self.window):
            return
        self.drag_origin = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def drag(self, event):
        if not self.drag_origin:
            return
        start_x, start_y, origin_x, origin_y = self.drag_origin
        x, y = origin_x + event.x_root - start_x, origin_y + event.y_root - start_y
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            x = max(rect[0], min(x, rect[2] - self.window.winfo_width()))
            y = max(rect[1], min(y, rect[3] - self.window.winfo_height()))
        self.window.geometry(f"+{round(x)}+{round(y)}")
        self.position_edit_chrome()

    def end_drag(self, event):
        if not self.drag_origin:
            return
        self.drag_origin = None
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.save_position()

    def save_position(self):
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if not rect or not self.exists(self.window):
            return
        self.settings["clock_overlay_offset_x"] = self.window.winfo_x() - rect[0]
        self.settings["clock_overlay_offset_y"] = self.window.winfo_y() - rect[1]
        self.save()

    def adjust_opacity(self, event):
        if not self.editing or not event.delta:
            return None
        self.opacity = max(50, min(100, self.opacity + (5 if event.delta > 0 else -5)))
        self.settings["clock_overlay_opacity_percent"] = self.opacity
        if self.exists(self.window):
            self.window.attributes("-alpha", self.opacity / 100.0)
        return "break"

    def begin_resize(self, event):
        if not self.editing or not self.exists(self.window):
            return
        self.resize_origin = (
            event.x_root, event.y_root, self.scale, self.window.winfo_width(), self.window.winfo_height(),
        )
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def resize(self, event):
        if not self.resize_origin:
            return
        start_x, start_y, start_scale, start_width, start_height = self.resize_origin
        horizontal = (start_width + event.x_root - start_x) / max(1, start_width)
        vertical = (start_height + event.y_root - start_y) / max(1, start_height)
        scale = max(0.5, min(3.0, round(start_scale * (horizontal + vertical) / 2.0, 2)))
        if abs(scale - self.scale) < 0.01:
            return
        self.scale = scale
        self.settings["clock_overlay_scale"] = scale
        self.render()
        self.position_edit_chrome()

    def end_resize(self, event):
        if not self.resize_origin:
            return
        self.resize_origin = None
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.save_position()

    def ensure_header(self):
        if self.exists(self.header_window):
            self.header_label.configure(text=CLOCK_TEXTS[self.language()]["adjust"])
            return self.header_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        label = tk.Label(
            window, text=CLOCK_TEXTS[self.language()]["adjust"], bg=HEADER, fg="#fff1c9",
            anchor="w", padx=8, pady=4, cursor="fleur", font=("Noto Sans KR", 8, "bold"),
        )
        label.pack(fill="both", expand=True, padx=1, pady=1)
        label.bind("<ButtonPress-1>", self.begin_drag)
        label.bind("<B1-Motion>", self.drag)
        label.bind("<ButtonRelease-1>", self.end_drag)
        label.bind("<MouseWheel>", self.adjust_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.header_window, self.header_label = window, label
        return window

    def ensure_grip(self):
        if self.exists(self.grip_window):
            return self.grip_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        grip = tk.Canvas(
            window, width=16, height=16, bg=HEADER, highlightthickness=1,
            highlightbackground=GOLD, cursor="size_nw_se",
        )
        grip.pack(fill="both", expand=True)
        grip.create_line(4, 14, 14, 4, fill="#fff1c9", width=1)
        grip.create_line(9, 14, 14, 9, fill="#fff1c9", width=1)
        grip.bind("<ButtonPress-1>", self.begin_resize)
        grip.bind("<B1-Motion>", self.resize)
        grip.bind("<ButtonRelease-1>", self.end_resize)
        grip.bind("<MouseWheel>", self.adjust_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.grip_window = window
        return window

    def ensure_lock(self):
        if self.exists(self.lock_window):
            return self.lock_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        tk.Button(
            window, text="🔓", command=self.toggle_editing, bg="#3b3022", fg="#fff1c9",
            activebackground=HEADER, activeforeground="#ffffff", relief="flat", bd=0,
            highlightthickness=0, cursor="hand2", font=("Segoe UI Emoji", 12),
        ).pack(fill="both", expand=True, padx=1, pady=1)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.lock_window = window
        return window

    def show_edit_chrome(self):
        windows = (self.ensure_header(), self.ensure_grip(), self.ensure_lock())
        self.position_edit_chrome()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        for window in windows:
            window.deiconify()
            if owner:
                attach_above(window, owner, window.winfo_x(), window.winfo_y())

    def hide_edit_chrome(self):
        for window in (self.header_window, self.grip_window, self.lock_window):
            if self.exists(window):
                window.withdraw()

    def position_edit_chrome(self):
        if not self.exists(self.window):
            return
        header, grip, lock = self.ensure_header(), self.ensure_grip(), self.ensure_lock()
        x, y, width, height = self.window.winfo_x(), self.window.winfo_y(), self.window.winfo_width(), self.window.winfo_height()
        rect = self.target_rect_provider() if self.target_rect_provider else None
        header_height = 28
        header_y = y - header_height - 4
        if rect and header_y < rect[1]:
            header_y = y + height + 4
        header.geometry(f"{max(160, width)}x{header_height}+{x}+{header_y}")
        grip.update_idletasks()
        grip.geometry(f"+{x + width - grip.winfo_reqwidth()}+{y + height - grip.winfo_reqheight()}")
        lock.update_idletasks()
        lock_x = x + width + 6
        if rect and lock_x + lock.winfo_reqwidth() > rect[2]:
            lock_x = x - lock.winfo_reqwidth() - 6
        lock.geometry(f"+{lock_x}+{y}")

    def set_temporarily_hidden(self, hidden):
        self.temporarily_hidden = bool(hidden)
        if hidden:
            if self.exists(self.control_window) and self.control_window.winfo_viewable():
                self.temporarily_hidden_control_visible = True
                try:
                    grabbed = self.master.grab_current()
                    if grabbed and grabbed.winfo_toplevel() == self.control_window:
                        self.temporarily_hidden_control_had_grab = True
                        grabbed.grab_release()
                except tk.TclError:
                    self.temporarily_hidden_control_had_grab = False
                self.control_window.withdraw()
            self.hide()
            for window in (self.xp_region_window, self.xp_region_lock_window):
                if self.exists(window):
                    window.withdraw()
        elif self.enabled:
            self.show()
        if not hidden and self.temporarily_hidden_control_visible:
            self.temporarily_hidden_control_visible = False
            if self.exists(self.control_window):
                self.control_window.deiconify()
                if self.temporarily_hidden_control_had_grab:
                    activate_modal(self.control_window)
            self.temporarily_hidden_control_had_grab = False
        if not hidden and self.xp_region_editing:
            self.open_xp_region_editor()

    def close(self):
        self.silence_alarm_sound()
        self.cancel_stopwatch_completion_warning()
        self.close_countdown_sounds()
        self.cancel_countdown_sound_timers()
        self.hide_stopwatch_xp_gain()
        try:
            ctypes.windll.winmm.mciSendStringW("close godinavi_alarm_preview", None, 0, None)
        except (AttributeError, OSError):
            pass
        self.close_xp_region_editor(save_region=True)
        self.xp_executor.shutdown(wait=False, cancel_futures=True)

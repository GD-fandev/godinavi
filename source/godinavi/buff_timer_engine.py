import ctypes
import json
import math
import os
import sys
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageTk

from .window_attachment import attach_above

try:
    import dxcam
except Exception:
    dxcam = None


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = Path(__file__).resolve().parents[2]

BUFF_ASSET_DIR = RESOURCE_DIR / "assets" / "buff_timer"
CALIBRATION_PING_PADDING = 28


def calibration_ping_expansions(now: float) -> tuple[int, int, int]:
    phase = int(now * 24) % 24
    return tuple((phase + offset) % 24 for offset in (0, 8, 16))

APP_VERSION = "1.3.0"
DEFAULT_BUFF_CONFIG_JSON = r'''{
  "process_name": "Godius.exe",
  "window_title": "Godius Client",
  "duration_seconds": 600,
  "start_adjust_seconds": 2,
  "cancel_key": "0",
  "allow_timer_visibility_toggle": false,
  "grow_key": "NUMPAD_ADD",
  "shrink_key": "NUMPAD_SUBTRACT",
  "icon_path": "icons/ice_display.png",
  "program_icon_path": "icons/Godius_104.png",
  "auto_detect": true,
  "detect_template_path": "icons/ice_crystal_template.png",
  "absent_template_path": "icons/ice_absent_template.png",
  "buffs": [
    {
      "key": "ice",
      "name": "Ice Crystal",
      "detect_template_path": "icons/ice_crystal_template.png",
      "display_icon_path": "icons/ice_display.png"
    },
    {
      "key": "fire",
      "name": "Fire Crystal",
      "detect_template_path": "icons/fire_crystal_template.png",
      "display_icon_path": "icons/fire_display.png"
    }
  ],
  "detect_coordinate_origin": "client",
  "detect_reference_size": [
    2112,
    1320
  ],
  "detect_region": [
    1638,
    1222,
    1680,
    1264
  ],
  "detect_threshold": 0.7,
  "detect_min_score_gap": 0.06,
  "detect_discriminative_diff": 35,
  "detect_min_mask_pixels": 80,
  "detect_chroma_weight": 0.65,
  "detect_center_mask_ratio": 0.42,
  "detect_color_anchor_weight": 0.45,
  "detect_full_similarity_threshold": 0.56,
  "detect_slot_frame_threshold": 0.58,
  "detect_text_obstruction_threshold": 0.55,
  "detect_icon_presence_threshold": 0.35,
  "absent_threshold": 0.93,
  "detect_required_hits": 4,
  "absent_required_hits": 6,
  "missing_required_hits": 10,
  "absent_grace_seconds": 5,
  "expire_restart_suppression_seconds": 1.5,
  "stop_when_absent_detected": true,
  "stop_when_icon_missing": true,
  "detect_interval_ms": 350,
  "hide_overlay_during_capture": false,
  "offset_x": 18,
  "offset_y": 46,
  "window_width": 150,
  "window_height": 150,
  "display_icon_size": 120,
  "display_icon_opacity": 0.65,
  "timer_visible": true,
  "timer_attach_to_client": true,
  "timer_offset_x": null,
  "timer_offset_y": null,
  "timer_window_x": 1474,
  "timer_window_y": 1217,
  "control_window_x": 87,
  "control_window_y": 675
}'''


def default_buff_config():
    config_path = BUFF_ASSET_DIR / "config.json"
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.loads(DEFAULT_BUFF_CONFIG_JSON)

APP_CONFIG_DIR = Path(os.environ.get("APPDATA", APP_DIR)) / "GodiusCrystalBuffTimer"
APP_CONFIG_PATH = APP_CONFIG_DIR / "config.json"
LEGACY_CONFIG_PATH = APP_DIR / "config.json"


def resource_path(relative_path):
    return BUFF_ASSET_DIR / Path(str(relative_path)).name

VK_CODES = {
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    "F10": 0x79,
    "+": 0xBB,
    "-": 0xBD,
    "NUMPAD_ADD": 0x6B,
    "NUMPAD_SUBTRACT": 0x6D,
}

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = wintypes.HWND(-1)
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
GA_ROOT = 2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

try:
    user32.SetProcessDPIAware()
except Exception:
    pass

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL


def root_hwnd(window):
    hwnd = window.winfo_id()
    return user32.GetAncestor(hwnd, GA_ROOT) or hwnd


def load_config():
    bundled_config = resource_path("config.json")
    with open(bundled_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    appdata_exists = APP_CONFIG_PATH.exists()
    if appdata_exists:
        with open(APP_CONFIG_PATH, "r", encoding="utf-8") as f:
            external = json.load(f)
        config.update(external)

    legacy_exists = LEGACY_CONFIG_PATH.exists() and LEGACY_CONFIG_PATH != bundled_config
    if not appdata_exists and legacy_exists:
        with open(LEGACY_CONFIG_PATH, "r", encoding="utf-8") as f:
            legacy = json.load(f)
        config.update(legacy)
        save_config_file(config)
    return config


def save_config_file(config):
    APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(APP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


def process_path_from_pid(pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def process_name_for_hwnd(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    path = process_path_from_pid(pid.value)
    return os.path.basename(path), pid.value


def window_title_for_hwnd(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def find_window_by_process_name(process_name):
    matches = []
    target = process_name.lower()

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        name, _pid = process_name_for_hwnd(hwnd)
        if name.lower() == target:
            matches.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return matches[0] if matches else None


def find_window_by_title(title):
    if not title:
        return None
    matches = []
    needle = title.lower()

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if needle in window_title_for_hwnd(hwnd).lower():
            matches.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return matches[0] if matches else None


def get_window_rect(hwnd):
    rect = wintypes.RECT()
    if not hwnd or not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def get_client_screen_rect(hwnd):
    rect = wintypes.RECT()
    origin = wintypes.POINT(0, 0)
    if not hwnd or not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    return origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom


def get_detection_base_rect(hwnd, origin):
    if origin == "screen":
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    if origin == "window":
        return get_window_rect(hwnd)
    return get_client_screen_rect(hwnd)


def ensure_icon(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    size = 96
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size // 2
    points = []
    for i in range(12):
        radius = 42 if i % 2 == 0 else 20
        angle = -math.pi / 2 + i * math.pi / 6
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=(125, 220, 255, 230), outline=(225, 250, 255, 255))
    draw.ellipse((30, 30, 66, 66), fill=(235, 255, 255, 210))
    draw.line((48, 8, 48, 88), fill=(245, 255, 255, 240), width=3)
    draw.line((8, 48, 88, 48), fill=(245, 255, 255, 220), width=3)
    draw.line((20, 20, 76, 76), fill=(245, 255, 255, 190), width=2)
    draw.line((76, 20, 20, 76), fill=(245, 255, 255, 190), width=2)
    img.save(path)


def format_time(seconds_left):
    seconds_left = max(0, int(math.ceil(seconds_left)))
    return str(seconds_left)


class BuffTimerApp:
    def __init__(self, master, config, save_callback=None, target_provider=None, on_calibration_confirmed=None):
        self.config = config
        self.save_callback = save_callback
        self.target_provider = target_provider
        self.on_calibration_confirmed = on_calibration_confirmed
        self.closed = False
        self.target_hwnd = None
        self.timer_owner_hwnd = None
        self.text_owner_hwnd = None
        self.end_time = None
        self.started_at = None
        self.active_buff = None
        self.expired_buff_lock = None
        self.expired_buff_lock_until = 0.0
        self.last_cancel_down = False
        self.last_grow_down = False
        self.last_shrink_down = False
        self.calibration_mode = False
        self.calibration_ping_until = 0.0
        self.calibration_guide_window = None
        self.calibration_guide_image = None
        self.calibration_bad_guide_images = []
        self.calibration_guide_text_label = None
        self.calibration_guide_confirm_button = None
        self.calibration_correct_title = None
        self.calibration_wrong_title = None
        self.calibration_guide_drag_origin = None
        self.timer_resize_mode = False
        self.timer_resize_drag_origin = None
        self.timer_resize_drag_position = None
        self.timer_resize_drag_widget = None
        self.timer_resize_action = None
        self.timer_scale_min = 0.5
        self.timer_scale_max = 1.0
        self.timer_scale_step = 0.1
        self.timer_visible = bool(self.config.get("timer_visible", True))
        self.detect_hits = {}
        self.absent_hits = 0
        self.missing_hits = 0
        # Party presence reporting is an observer only. It deliberately does not
        # read or change the personal timer's duration, visibility, or end time.
        self.party_presence_callback = None
        self.party_observed_buff = None
        self.party_detect_hits = {}
        self.party_absent_hits = 0
        self.last_detect_at = 0.0
        self.last_absent_score = None
        self.last_capture_bbox = None
        self.buffs = self.load_buffs()
        self.absent_template = self.load_plain_template("absent_template_path")
        self.manual_position = False
        self.last_timer_geometry = ""
        self.capture_backend = "Desktop Duplication"
        self.desktop_camera = None
        # The user-facing debug menu is gone. Keep the diagnostic viewer
        # available only through an explicit developer environment flag.
        self.debug_capture_enabled = (
            os.environ.get("GODIUS_CAPTURE_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        self.config.pop("debug_capture_preview", None)
        self.debug_capture_window = None
        self.debug_capture_label = None
        self.debug_capture_text = None
        self.debug_capture_image = None
        if dxcam is not None:
            try:
                self.desktop_camera = dxcam.create(output_color="RGB", processor_backend="numpy")
            except Exception:
                self.desktop_camera = None
        if self.desktop_camera is None:
            self.capture_backend = "ImageGrab fallback"

        self.root = tk.Toplevel(master)
        self.root.title("Godius Crystal Buff Timer")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", False)
        self.root.configure(bg="#101722")

        base_config = json.loads(DEFAULT_BUFF_CONFIG_JSON)
        self.base_width = int(base_config["window_width"])
        self.base_height = int(base_config["window_height"])
        self.base_icon_size = int(base_config.get("display_icon_size", 120))
        self.timer_scale = max(self.timer_scale_min, min(self.timer_scale_max, float(config.get("timer_scale", 1.0))))
        self.width = max(1, round(self.base_width * self.timer_scale))
        self.height = max(1, round(self.base_height * self.timer_scale))
        self.config["window_width"] = self.width
        self.config["window_height"] = self.height
        self.config["timer_scale"] = self.timer_scale
        start_x = int(config.get("timer_window_x", 120))
        start_y = int(config.get("timer_window_y", 120))
        start_x, start_y = self.clamp_timer_position(start_x, start_y)
        self.root.geometry(f"{self.width}x{self.height}+{start_x}+{start_y}")
        icon_size = max(1, round(self.base_icon_size * self.timer_scale))
        self.config["display_icon_size"] = icon_size
        self.default_buff_key = self.first_buff_key()
        self.base_icon = self.icon_for_buff(self.default_buff_key, icon_size)
        self.display_icon_opacity = max(0.0, min(1.0, float(config.get("display_icon_opacity", 0.7))))
        self.root.attributes("-alpha", self.display_icon_opacity)
        self.timer_image = None
        self.text_image = None

        self.transparent_key = "#010101"
        self.root.configure(bg=self.transparent_key)
        self.root.wm_attributes("-transparentcolor", self.transparent_key)

        self.frame = tk.Frame(self.root, bg=self.transparent_key, padx=0, pady=0)
        self.frame.pack(fill="both", expand=True)

        self.body_frame = tk.Frame(self.frame, bg=self.transparent_key)
        self.body_frame.pack(fill="both", expand=True)
        self.timer_label = tk.Label(self.body_frame, bg=self.transparent_key, bd=0)
        self.timer_label.place(relx=0.5, rely=0.5, anchor="center")
        self.text_window = self.create_text_window()
        self.text_label = tk.Label(self.text_window, bg=self.transparent_key, bd=0)
        self.text_label.pack(fill="both", expand=True)
        self.apply_timer_geometry(start_x, start_y)
        self.render_no_buff_image()
        self.control_window = None
        if self.debug_capture_enabled:
            self.debug_capture_window = self.create_debug_capture_window()

        self.drag_x = 0
        self.drag_y = 0
        self.drag_enabled = False

        self.apply_tool_window_style()
        self.region_window = self.create_region_window()
        self.region_window.winfo_children()[0].bind("<ButtonPress-1>", self.begin_region_drag)
        self.region_window.winfo_children()[0].bind("<B1-Motion>", self.region_drag)
        self.calibration_guide_window = self.create_calibration_guide_window()
        self.resize_window = self.create_resize_window()
        self.resize_lock_window = self.create_resize_lock_window()
        if not self.timer_visible:
            self.root.withdraw()
            self.text_window.withdraw()
        self.tick()

    def create_region_window(self):
        return self.create_box_window("#ff3030", 0.45)

    def calibration_guide_text(self):
        return {
            "KR": "빨간 박스 안에 버프 슬롯 전체가 들어오도록 맞춰주세요.\n위 − / + 버튼이나 넘패드 − / +로 크기를 조절할 수 있습니다.\n버프 창의 위치·크기는 좌측 하단 메인 아이콘에서 조절할 수 있습니다.",
            "JP": "赤い枠の中にバフスロット全体が入るように合わせてください。\n上の－／＋ボタンまたはテンキーの－／＋でサイズを調整できます。\nバフ画面の位置・サイズは左下のメインアイコンから調整できます。",
            "EN": "Fit the entire buff slot inside the red box.\nResize it with the − / + buttons above or Numpad − / +.\nAdjust the buff window position and size from the main icon at the bottom left.",
        }.get(self.config.get("ui_language", "KR"), "빨간 박스를 예시 이미지처럼 맞춰주세요.")

    def calibration_example_text(self, correct=True):
        texts = {
            "KR": ("✓ 올바른 예시", "✕ 잘못된 예시"),
            "JP": ("✓ 正しい例", "✕ 間違った例"),
            "EN": ("✓ Correct example", "✕ Incorrect examples"),
        }
        return texts.get(self.config.get("ui_language", "KR"), texts["KR"])[0 if correct else 1]

    def calibration_confirm_text(self):
        return {"KR": "확정 및 닫기", "JP": "確定して閉じる", "EN": "Confirm and close"}.get(
            self.config.get("ui_language", "KR"), "확정 및 닫기"
        )

    def create_calibration_guide_window(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", False)
        win.configure(bg="#d8b15a")
        panel = tk.Frame(win, bg="#2a2118")
        panel.pack(fill="both", expand=True, padx=2, pady=2)

        image_path = BUFF_ASSET_DIR / "calibration_example.png"
        image_label = None
        correct_title = tk.Label(
            panel, text=self.calibration_example_text(True), bg="#2a2118", fg="#83d68a",
            anchor="w", font=("Malgun Gothic", 9, "bold"),
        )
        correct_title.pack(fill="x", padx=12, pady=(10, 4))
        self.calibration_correct_title = correct_title
        if image_path.exists():
            with Image.open(image_path) as source:
                self.calibration_guide_image = ImageTk.PhotoImage(source.convert("RGB"))
            image_label = tk.Label(panel, image=self.calibration_guide_image, bg="#17130f", bd=0)
            image_label.pack(padx=12, pady=(0, 8))

        wrong_title = tk.Label(
            panel, text=self.calibration_example_text(False), bg="#2a2118", fg="#ff7770",
            anchor="w", font=("Malgun Gothic", 9, "bold"),
        )
        wrong_title.pack(fill="x", padx=12, pady=(0, 4))
        self.calibration_wrong_title = wrong_title
        wrong_row = tk.Frame(panel, bg="#17130f")
        wrong_row.pack(fill="x", padx=12, pady=(0, 9))
        self.calibration_bad_guide_images = []
        wrong_labels = []
        for index, name in enumerate(("calibration_bad_example_1.png", "calibration_bad_example_2.png")):
            path = BUFF_ASSET_DIR / name
            if not path.exists():
                continue
            with Image.open(path) as source:
                preview = source.convert("RGB")
                preview.thumbnail((180, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(preview)
            self.calibration_bad_guide_images.append(photo)
            label = tk.Label(wrong_row, image=photo, bg="#17130f", bd=0)
            label.pack(side="left", expand=True, padx=(0 if index == 0 else 5, 5 if index == 0 else 0), pady=6)
            wrong_labels.append(label)

        controls = tk.Frame(panel, bg="#2a2118")
        controls.pack(fill="x", padx=12, pady=(0, 7))
        for symbol, delta in (("−", -2), ("+", 2)):
            button = tk.Button(
                controls, text=symbol, command=lambda amount=delta: self.resize_detect_region(amount),
                bg="#5a4932", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff",
                relief="flat", bd=0, cursor="hand2", font=("Malgun Gothic", 12, "bold"),
            )
            button.pack(side="left", fill="x", expand=True, padx=(0, 4) if delta < 0 else (4, 0), ipady=0)

        self.calibration_guide_text_label = tk.Label(
            panel,
            text=self.calibration_guide_text(),
            bg="#2a2118",
            fg="#fff1c9",
            justify="left",
            anchor="w",
            padx=12,
            pady=9,
            font=("Malgun Gothic", 9),
        )
        self.calibration_guide_text_label.pack(fill="x", padx=2, pady=(0, 3))
        self.calibration_guide_confirm_button = tk.Button(
            panel, text=self.calibration_confirm_text(), command=self.confirm_calibration,
            bg="#5a4932", fg="#fff1c9", activebackground="#756044", activeforeground="#ffffff",
            relief="flat", bd=0, cursor="hand2", font=("Malgun Gothic", 9, "bold"),
        )
        self.calibration_guide_confirm_button.pack(fill="x", padx=10, pady=(0, 10), ipady=5)
        drag_widgets = [win, panel, correct_title, wrong_title, self.calibration_guide_text_label, *wrong_labels]
        if image_label is not None:
            drag_widgets.append(image_label)
        for widget in drag_widgets:
            widget.configure(cursor="fleur")
            widget.bind("<ButtonPress-1>", self.begin_calibration_guide_drag)
            widget.bind("<B1-Motion>", self.calibration_guide_drag)
            widget.bind("<ButtonRelease-1>", self.end_calibration_guide_drag)

        win.withdraw()
        win.update_idletasks()
        hwnd = root_hwnd(win)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW)
        return win

    def confirm_calibration(self):
        if self.calibration_mode:
            self.toggle_calibration_mode()
            callback = getattr(self, "on_calibration_confirmed", None)
            if callback:
                callback()

    def begin_calibration_guide_drag(self, event):
        self.calibration_guide_drag_origin = (
            event.x_root,
            event.y_root,
            self.calibration_guide_window.winfo_x(),
            self.calibration_guide_window.winfo_y(),
        )

    def calibration_guide_drag(self, event):
        if not self.calibration_guide_drag_origin:
            return
        start_x, start_y, window_x, window_y = self.calibration_guide_drag_origin
        self.calibration_guide_window.geometry(
            f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}"
        )

    def end_calibration_guide_drag(self, _event):
        if not self.calibration_guide_drag_origin:
            return
        self.calibration_guide_drag_origin = None
        client = get_client_screen_rect(self.target_hwnd) if self.target_hwnd else None
        if client:
            self.config["calibration_guide_offset_x"] = self.calibration_guide_window.winfo_x() - client[0]
            self.config["calibration_guide_offset_y"] = self.calibration_guide_window.winfo_y() - client[1]
        self.save_config()

    def show_calibration_guide(self):
        win = self.calibration_guide_window
        if not win:
            return
        win.update_idletasks()
        client = get_client_screen_rect(self.target_hwnd) if self.target_hwnd else None
        if not client or not self.target_hwnd:
            win.withdraw()
            return
        left, top, right, bottom = client
        offset_x = self.config.get("calibration_guide_offset_x")
        offset_y = self.config.get("calibration_guide_offset_y")
        if offset_x is None or offset_y is None:
            offset_x = max(0, (right - left - win.winfo_reqwidth()) // 2)
            offset_y = max(0, (bottom - top - win.winfo_reqheight()) // 3)
        x, y = left + int(offset_x), top + int(offset_y)
        win.geometry(f"+{int(x)}+{int(y)}")
        attach_above(win, self.target_hwnd, x, y)

    def resize_instruction(self):
        return {
            "KR": "마우스 휠 : 크기조절\n드래그 : 이동",
            "JP": "マウスホイール：サイズ調整\nドラッグ：移動",
            "EN": "Mouse wheel: Resize\nDrag: Move",
        }.get(self.config.get("ui_language", "KR"), "마우스 휠 : 크기조절\n드래그 : 이동")

    def resize_edit_text(self):
        return {
            "KR": "이동 : 드래그\n크기 : 휠",
            "JP": "移動：ドラッグ\nサイズ：ホイール",
            "EN": "Move: Drag\nSize: Wheel",
        }.get(self.config.get("ui_language", "KR"), "이동 : 드래그\n크기 : 휠")

    def create_resize_window(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", False)
        win.configure(bg=self.transparent_key)
        win.wm_attributes("-transparentcolor", self.transparent_key)
        panel = tk.Frame(win, bg=self.transparent_key, highlightthickness=2, highlightbackground="#d8b15a")
        panel.pack(fill="both", expand=True)
        self.resize_spacer = tk.Frame(panel, bg=self.transparent_key)
        self.resize_spacer.place(x=4, y=4, relwidth=1.0, relheight=1.0, width=-8, height=-8)
        self.resize_drag_handle = tk.Label(
            panel, text="⠿", bg="#5a4932", fg="#fff1c9",
            padx=24, pady=0, anchor="w", cursor="fleur",
            font=("Segoe UI Symbol", 10, "bold"),
        )
        # Keep the edit bar inside the buff icon, like the minimap chrome.
        # The drag glyph sits slightly left of centre so the otherwise empty bar
        # still reads as a movable surface without covering the timer text.
        self.resize_drag_handle.place(x=4, y=4, relwidth=1.0, width=-8, height=30)
        self.resize_grip = tk.Canvas(
            self.resize_spacer, width=12, height=12, bg="#5a4932", highlightthickness=2,
            highlightbackground="#d8b15a", cursor="size_nw_se",
        )
        self.resize_grip.place(relx=1.0, rely=1.0, x=-4, y=-4, anchor="se")
        self.resize_drag_handle.lift()
        for widget in (self.resize_drag_handle, self.resize_spacer, self.timer_label, self.text_label):
            widget.bind("<ButtonPress-1>", self.begin_timer_resize_drag)
            widget.bind("<B1-Motion>", self.timer_resize_drag)
            widget.bind("<ButtonRelease-1>", self.end_timer_resize_drag)
        self.resize_grip.bind("<ButtonPress-1>", self.begin_timer_resize_drag)
        self.resize_grip.bind("<B1-Motion>", self.timer_resize_drag)
        self.resize_grip.bind("<ButtonRelease-1>", self.end_timer_resize_drag)
        self.resize_tooltip = tk.Toplevel(self.root)
        self.resize_tooltip.overrideredirect(True)
        self.resize_tooltip.attributes("-topmost", True)
        self.resize_tooltip.configure(bg="#d8b15a")
        self.resize_tooltip_label = tk.Label(
            self.resize_tooltip, text=self.resize_instruction(), bg="#2a2118", fg="#fff1c9",
            padx=10, pady=7, justify="left", font=("Malgun Gothic", 9),
        )
        self.resize_tooltip_label.pack(padx=1, pady=1)
        self.resize_tooltip.withdraw()
        self.resize_tooltip.update_idletasks()
        tooltip_hwnd = root_hwnd(self.resize_tooltip)
        tooltip_style = user32.GetWindowLongW(tooltip_hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(tooltip_hwnd, GWL_EXSTYLE, tooltip_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        win.withdraw()
        win.update_idletasks()
        hwnd = root_hwnd(win)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        return win

    def create_resize_lock_window(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#d8b15a")
        button = tk.Button(
            win, text="🔓", command=self.confirm_timer_resize,
            bg="#3b3022", fg="#fff1c9", activebackground="#5a4932", activeforeground="#ffffff",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=("Segoe UI Emoji", 12),
        )
        button.pack(fill="both", expand=True, padx=1, pady=1)
        win.withdraw()
        win.update_idletasks()
        hwnd = root_hwnd(win)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW)
        return win

    def confirm_timer_resize(self):
        if self.timer_resize_mode:
            self.toggle_timer_resize_mode()

    def show_resize_tooltip(self, event):
        if not self.timer_resize_mode:
            return
        self.resize_tooltip.geometry(f"+{event.x_root + 14}+{event.y_root + 14}")
        self.resize_tooltip.deiconify()
        self.resize_tooltip.lift()
        user32.SetWindowPos(
            root_hwnd(self.resize_tooltip), HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def hide_resize_tooltip(self, _event=None):
        if hasattr(self, "resize_tooltip"):
            self.resize_tooltip.withdraw()

    def begin_timer_resize_drag(self, event):
        if not self.timer_resize_mode:
            return
        self.timer_resize_drag_origin = (
            event.x_root,
            event.y_root,
            self.root.winfo_x(),
            self.root.winfo_y(),
        )
        self.timer_resize_drag_position = (self.root.winfo_x(), self.root.winfo_y())
        self.timer_resize_drag_widget = getattr(event, "widget", None)
        resize_grip = getattr(self, "resize_grip", None)
        self.timer_resize_action = "resize" if resize_grip is not None and self.timer_resize_drag_widget is resize_grip else "move"
        if self.timer_resize_drag_widget is not None:
            try:
                self.timer_resize_drag_widget.grab_set_global()
            except tk.TclError:
                try:
                    self.timer_resize_drag_widget.grab_set()
                except tk.TclError:
                    self.timer_resize_drag_widget = None

    def timer_resize_drag(self, event):
        if not self.timer_resize_mode or not self.timer_resize_drag_origin:
            return
        start_x, start_y, window_x, window_y = self.timer_resize_drag_origin
        if self.timer_resize_action == "resize":
            desired_size = max(event.x_root - window_x, event.y_root - window_y)
            scale = desired_size / max(1, self.base_width)
            self.set_timer_scale(scale, keep_origin=True, save=False)
            return
        x = window_x + event.x_root - start_x
        y = window_y + event.y_root - start_y
        x, y = self.clamp_timer_position(x, y)
        self.manual_position = True
        self.timer_resize_drag_position = (x, y)
        self.move_timer_windows_immediately(x, y)

    def move_timer_windows_immediately(self, x, y):
        flags = SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        frame_width = self.width + 12
        frame_x = int(x) - 6
        frame_y = int(y) - 6
        user32.SetWindowPos(root_hwnd(self.resize_window), HWND_TOPMOST, frame_x, frame_y, 0, 0, flags)
        move_flags = flags | SWP_NOZORDER
        user32.SetWindowPos(root_hwnd(self.root), 0, int(x), int(y), 0, 0, move_flags)
        user32.SetWindowPos(root_hwnd(self.text_window), 0, int(x), int(y), 0, 0, move_flags)
        if self.resize_tooltip.winfo_viewable():
            user32.SetWindowPos(root_hwnd(self.resize_tooltip), HWND_TOPMOST, 0, 0, 0, 0, flags | SWP_NOMOVE)

    def end_timer_resize_drag(self, _event):
        if not self.timer_resize_drag_origin:
            return
        position = self.timer_resize_drag_position or (self.root.winfo_x(), self.root.winfo_y())
        if self.timer_resize_drag_widget is not None:
            try:
                self.timer_resize_drag_widget.grab_release()
            except tk.TclError:
                pass
        action = self.timer_resize_action
        self.timer_resize_drag_origin = None
        self.timer_resize_drag_position = None
        self.timer_resize_drag_widget = None
        if action == "resize":
            self.set_timer_position(self.root.winfo_x(), self.root.winfo_y())
            self.save_config()
        else:
            self.set_timer_position(*position)
        self.timer_resize_action = None

    def set_ui_language(self, language):
        self.config["ui_language"] = language
        if self.calibration_guide_text_label:
            self.calibration_guide_text_label.configure(text=self.calibration_guide_text())
        if self.calibration_correct_title:
            self.calibration_correct_title.configure(text=self.calibration_example_text(True))
        if self.calibration_wrong_title:
            self.calibration_wrong_title.configure(text=self.calibration_example_text(False))
        if self.calibration_guide_confirm_button:
            self.calibration_guide_confirm_button.configure(text=self.calibration_confirm_text())
        if hasattr(self, "resize_tooltip_label"):
            self.resize_tooltip_label.configure(text=self.resize_instruction())
    def update_resize_window(self):
        if not getattr(self, "timer_resize_mode", False) or not hasattr(self, "resize_window"):
            return
        timer_x = self.root.winfo_x()
        timer_y = self.root.winfo_y()
        frame_width = self.width + 12
        frame_x = timer_x - 6
        self.resize_spacer.configure(width=self.width, height=self.height)
        frame_geometry = f"{frame_width}x{self.height + 12}+{frame_x}+{timer_y - 6}"
        if self.resize_window.geometry() != frame_geometry:
            self.resize_window.geometry(frame_geometry)
        if not self.resize_window.winfo_viewable():
            self.resize_window.deiconify()
        user32.SetWindowPos(
            root_hwnd(self.resize_window), HWND_TOPMOST,
            frame_x, timer_y - 6, 0, 0,
            SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        self.resize_lock_window.withdraw()

    def create_text_window(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", False)
        win.configure(bg=self.transparent_key)
        win.wm_attributes("-transparentcolor", self.transparent_key)
        win.geometry(f"{self.width}x{self.height}+120+120")
        hwnd = root_hwnd(win)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        return win

    def create_debug_capture_window(self):
        win = tk.Toplevel(self.root)
        win.title("Capture Debug")
        win.attributes("-topmost", True)
        win.configure(bg="#111111")
        self.debug_capture_label = tk.Label(win, bg="#111111", bd=0)
        self.debug_capture_label.pack(padx=8, pady=(8, 4))
        self.debug_capture_text = tk.Label(
            win,
            text="Waiting for capture...",
            bg="#111111",
            fg="#ffe066",
            justify="left",
            anchor="w",
            font=("Consolas", 9),
        )
        self.debug_capture_text.pack(fill="x", padx=8, pady=(0, 8))
        win.geometry("560x430+80+80")
        return win

    def update_debug_status(self, status):
        if not self.debug_capture_enabled or not self.debug_capture_window or not self.debug_capture_text:
            return
        try:
            self.debug_capture_text.configure(text=status)
            self.debug_capture_window.update_idletasks()
        except Exception:
            pass

    def create_control_window(self):
        win = tk.Toplevel(self.root)
        win.title("Crystal Buff Timer")
        win.resizable(False, False)
        win.configure(bg="#eff8fb")
        control_width = 300
        control_height = 170
        x = int(self.config.get("control_window_x", 40))
        y = int(self.config.get("control_window_y", 40))
        x, y = self.clamp_window_position(x, y, control_width, control_height)
        win.geometry(f"{control_width}x{control_height}+{x}+{y}")
        try:
            self.control_icon_image = ImageTk.PhotoImage(self.load_program_icon(32))
            win.iconphoto(True, self.control_icon_image)
        except Exception:
            self.control_icon_image = None

        shell = tk.Frame(win, bg="#eff8fb", padx=16, pady=12)
        shell.pack(fill="both", expand=True)
        header = tk.Frame(shell, bg="#eff8fb")
        header.pack(fill="x")
        if self.control_icon_image:
            tk.Label(header, image=self.control_icon_image, bg="#eff8fb", bd=0).pack(side="left", padx=(0, 8))
        title_area = tk.Frame(header, bg="#eff8fb")
        title_area.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_area,
            text="Crystal Buff Timer",
            fg="#214252",
            bg="#eff8fb",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x")
        quit_button = tk.Button(
            shell,
            text="QUIT",
            command=self.quit_app,
            fg="#ffffff",
            bg="#4d9bb8",
            activeforeground="#ffffff",
            activebackground="#367e98",
            relief="flat",
            bd=0,
            padx=18,
            pady=7,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        quit_button.pack(fill="x", pady=(14, 0))
        tk.Label(
            shell,
            text=f"Version {APP_VERSION}",
            fg="#5d7680",
            bg="#eff8fb",
            font=("Segoe UI", 8),
            anchor="center",
        ).pack(fill="x", pady=(8, 0))
        win.protocol("WM_DELETE_WINDOW", self.quit_app)
        return win

    def create_box_window(self, color, alpha):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", False)
        win.attributes("-alpha", alpha)
        win.configure(bg="#ff00ff")
        win.wm_attributes("-transparentcolor", "#ff00ff")
        canvas = tk.Canvas(win, width=40, height=40, bg="#ff00ff", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_rectangle(1, 1, 39, 39, outline=color, fill=color, width=3)
        win.withdraw()
        win.update_idletasks()
        hwnd = root_hwnd(win)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        return win

    def begin_region_drag(self, event):
        self.drag_enabled = self.calibration_mode

    def region_drag(self, event):
        if not self.drag_enabled or not self.calibration_mode:
            return
        self.calibrate_region_at_screen_point(event.x_root, event.y_root)

    def apply_tool_window_style(self):
        hwnd = root_hwnd(self.root)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)

    def quit_app(self):
        if self.closed:
            return
        self.closed = True
        if self.desktop_camera is not None:
            try:
                self.desktop_camera.release()
            except Exception:
                pass
        self.save_control_window_position()
        self.save_config()
        for window in (self.debug_capture_window, self.region_window, self.calibration_guide_window, self.resize_tooltip, self.resize_lock_window, self.resize_window, self.text_window, self.root):
            if window is not None:
                try:
                    window.destroy()
                except tk.TclError:
                    pass

    def save_control_window_position(self):
        if not getattr(self, "control_window", None):
            return
        self.control_window.update_idletasks()
        x = self.control_window.winfo_x()
        y = self.control_window.winfo_y()
        width = max(1, self.control_window.winfo_width())
        height = max(1, self.control_window.winfo_height())
        x, y = self.clamp_window_position(x, y, width, height)
        self.config["control_window_x"] = x
        self.config["control_window_y"] = y

    def begin_drag(self, event):
        self.drag_enabled = bool(event.state & 0x0004)
        self.drag_x = event.x
        self.drag_y = event.y

    def drag(self, event):
        if not self.drag_enabled:
            return
        self.manual_position = True
        x = event.x_root - self.drag_x
        y = event.y_root - self.drag_y
        self.set_timer_position(x, y)
        self.apply_timer_geometry(x, y)

    def render_timer_image(self, text, color, buff_key=None):
        canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        icon = self.icon_for_buff(buff_key or self.active_buff).copy()
        x = (self.width - icon.width) // 2
        y = (self.height - icon.height) // 2
        canvas.alpha_composite(icon, (x, y))
        self.timer_image = ImageTk.PhotoImage(canvas)
        self.timer_label.configure(image=self.timer_image)

        text_canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_canvas)
        max_text_width = max(1, int(icon.width * 0.8))
        max_text_height = max(1, int(icon.height * 0.45))
        font = ImageFont.load_default()
        for size in range(max(12, int(icon.height * 0.72)), 9, -1):
            try:
                candidate = ImageFont.truetype("segoeuib.ttf", size)
            except OSError:
                break
            bbox = draw.textbbox((0, 0), text, font=candidate)
            if (bbox[2] - bbox[0]) <= max_text_width and (bbox[3] - bbox[1]) <= max_text_height:
                font = candidate
                break
        bbox = draw.textbbox((0, 0), text, font=font)
        tx = (self.width - (bbox[2] - bbox[0])) / 2 - bbox[0]
        ty = (self.height - (bbox[3] - bbox[1])) / 2 - bbox[1]
        draw.text((tx + 1, ty + 1), text, font=font, fill=(0, 0, 0, 190))
        draw.text((tx, ty), text, font=font, fill=color)
        self.text_image = ImageTk.PhotoImage(text_canvas)
        self.text_label.configure(image=self.text_image)

    def render_no_buff_image(self):
        canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 230))
        self.timer_image = ImageTk.PhotoImage(canvas)
        self.timer_label.configure(image=self.timer_image)

        text_canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_canvas)
        text = "No buff"
        font = ImageFont.load_default()
        for size in range(max(14, int(self.height * 0.22)), 9, -1):
            try:
                candidate = ImageFont.truetype("segoeuib.ttf", size)
            except OSError:
                break
            bbox = draw.textbbox((0, 0), text, font=candidate)
            if (bbox[2] - bbox[0]) <= int(self.width * 0.85):
                font = candidate
                break
        bbox = draw.textbbox((0, 0), text, font=font)
        tx = (self.width - (bbox[2] - bbox[0])) / 2 - bbox[0]
        ty = (self.height - (bbox[3] - bbox[1])) / 2 - bbox[1]
        draw.text((tx + 1, ty + 1), text, font=font, fill=(0, 0, 0, 220))
        draw.text((tx, ty), text, font=font, fill=(255, 220, 70, 255))
        self.text_image = ImageTk.PhotoImage(text_canvas)
        self.text_label.configure(image=self.text_image)

    def keep_timer_visible(self):
        if not self.timer_visible:
            return
        if not self.root.winfo_viewable():
            self.root.deiconify()
        if not self.text_window.winfo_viewable():
            self.text_window.deiconify()
        self.root.attributes("-alpha", self.display_icon_opacity)
        if self.target_hwnd:
            if self.timer_owner_hwnd != self.target_hwnd:
                attach_above(self.root, self.target_hwnd)
                self.timer_owner_hwnd = self.target_hwnd
            icon_hwnd = root_hwnd(self.root)
            if self.text_owner_hwnd != icon_hwnd:
                # Make the number layer an owned child of the icon layer. This
                # permanently fixes their relative order without repeatedly
                # churning the Windows Z-order on every timer tick.
                attach_above(self.text_window, icon_hwnd)
                self.text_owner_hwnd = icon_hwnd
        if self.timer_resize_mode:
            self.update_resize_window()
            if self.resize_tooltip.winfo_viewable():
                flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
                user32.SetWindowPos(root_hwnd(self.resize_tooltip), HWND_TOPMOST, 0, 0, 0, 0, flags)

    def is_target_foreground(self):
        fg = user32.GetForegroundWindow()
        if not fg:
            return False
        name, _pid = process_name_for_hwnd(fg)
        return name.lower() == self.config["process_name"].lower()

    def position_near_target(self):
        if not self.target_hwnd:
            self.target_hwnd = find_window_by_title(self.config.get("window_title", ""))
        if not self.target_hwnd:
            self.target_hwnd = find_window_by_process_name(self.config["process_name"])
        if self.manual_position:
            if not self.timer_resize_drag_origin:
                self.update_timer_attached_position()
            return bool(get_client_screen_rect(self.target_hwnd))
        rect = get_window_rect(self.target_hwnd)
        if not rect:
            self.target_hwnd = None
            return False
        left, top, right, bottom = rect
        client = get_client_screen_rect(self.target_hwnd)
        if client and self.config.get("timer_attach_to_client", True):
            offset_x = self.config.get("timer_offset_x")
            offset_y = self.config.get("timer_offset_y")
            if offset_x is None or offset_y is None:
                offset_x = max(0, ((client[2] - client[0]) - self.width) // 2)
                offset_y = max(0, ((client[3] - client[1]) - self.height) // 2)
            x = client[0] + int(offset_x)
            y = client[1] + int(offset_y)
        else:
            x = right - self.width - int(self.config["offset_x"])
            y = bottom - self.height - int(self.config["offset_y"])
        x, y = self.clamp_timer_position(x, y)
        self.set_timer_position(x, y)
        self.apply_timer_geometry(x, y)
        return True

    def clamp_timer_position(self, x, y):
        return self.clamp_window_position(x, y, self.width, self.height)

    def clamp_window_position(self, x, y, width, height):
        screen_w = max(1, user32.GetSystemMetrics(0))
        screen_h = max(1, user32.GetSystemMetrics(1))
        max_x = max(0, screen_w - int(width))
        max_y = max(0, screen_h - int(height))
        return max(0, min(int(x), max_x)), max(0, min(int(y), max_y))

    def set_timer_position(self, x, y):
        x, y = self.clamp_timer_position(x, y)
        previous = (
            self.config.get("timer_window_x"), self.config.get("timer_window_y"),
            self.config.get("timer_offset_x"), self.config.get("timer_offset_y"),
        )
        self.config["timer_window_x"] = x
        self.config["timer_window_y"] = y
        client = get_client_screen_rect(self.target_hwnd)
        if client:
            self.config["timer_attach_to_client"] = True
            self.config["timer_offset_x"] = x - client[0]
            self.config["timer_offset_y"] = y - client[1]
        current = (
            self.config.get("timer_window_x"), self.config.get("timer_window_y"),
            self.config.get("timer_offset_x"), self.config.get("timer_offset_y"),
        )
        if current != previous:
            self.save_config()

    def update_timer_attached_position(self):
        if not self.config.get("timer_attach_to_client", True):
            return
        client = get_client_screen_rect(self.target_hwnd)
        if not client:
            return
        x = client[0] + int(self.config.get("timer_offset_x", 18))
        y = client[1] + int(self.config.get("timer_offset_y", 46))
        x, y = self.clamp_timer_position(x, y)
        self.apply_timer_geometry(x, y)

    def apply_timer_geometry(self, x, y):
        x, y = self.clamp_timer_position(x, y)
        geometry = f"{self.width}x{self.height}+{x}+{y}"
        self.root.geometry(geometry)
        self.text_window.geometry(geometry)
        self.last_timer_geometry = geometry

    def handle_hotkey(self):
        cancel_vk = VK_CODES.get(str(self.config.get("cancel_key", "0")).upper())
        grow_vks = self.key_codes_for(self.config.get("grow_key", "+"), "+", "NUMPAD_ADD")
        shrink_vks = self.key_codes_for(self.config.get("shrink_key", "-"), "-", "NUMPAD_SUBTRACT")

        if cancel_vk and bool(self.config.get("allow_timer_visibility_toggle", False)):
            cancel_down = bool(user32.GetAsyncKeyState(cancel_vk) & 0x8000)
            if cancel_down and not self.last_cancel_down:
                self.toggle_timer_visibility()
            self.last_cancel_down = cancel_down
        else:
            self.last_cancel_down = False

        if self.calibration_mode and grow_vks:
            grow_down = any(bool(user32.GetAsyncKeyState(vk) & 0x8000) for vk in grow_vks)
            if grow_down and not self.last_grow_down:
                self.resize_detect_region(2)
            self.last_grow_down = grow_down

        if self.calibration_mode and shrink_vks:
            shrink_down = any(bool(user32.GetAsyncKeyState(vk) & 0x8000) for vk in shrink_vks)
            if shrink_down and not self.last_shrink_down:
                self.resize_detect_region(-2)
            self.last_shrink_down = shrink_down

    def key_codes_for(self, *names):
        codes = []
        for name in names:
            code = VK_CODES.get(str(name).upper())
            if code is not None and code not in codes:
                codes.append(code)
        return codes

    def start_timer(self, buff_key):
        now = time.monotonic()
        seconds = float(self.config["duration_seconds"]) - float(self.config.get("start_adjust_seconds", 0))
        self.active_buff = buff_key
        self.base_icon = self.icon_for_buff(buff_key)
        self.started_at = now
        self.end_time = now + max(1.0, seconds)
        self.root.attributes("-alpha", self.display_icon_opacity)
        user32.ShowWindow(root_hwnd(self.root), SW_SHOWNOACTIVATE)
        user32.ShowWindow(root_hwnd(self.text_window), SW_SHOWNOACTIVATE)

    def toggle_timer_visibility(self):
        if not bool(self.config.get("allow_timer_visibility_toggle", False)):
            self.timer_visible = True
            self.config["timer_visible"] = True
            self.root.deiconify()
            self.text_window.deiconify()
            self.render_no_buff_image()
            self.save_config()
            return
        self.timer_visible = not self.timer_visible
        self.config["timer_visible"] = self.timer_visible
        self.save_config()
        if self.timer_visible:
            self.timer_owner_hwnd = None
            self.text_owner_hwnd = None
            self.root.deiconify()
            self.text_window.deiconify()
        else:
            self.root.withdraw()
            self.text_window.withdraw()

    def toggle_calibration_mode(self):
        self.calibration_mode = not self.calibration_mode
        if not self.calibration_mode:
            self.save_config()
            if self.region_window:
                self.region_window.withdraw()
            if self.calibration_guide_window:
                self.calibration_guide_window.withdraw()
        else:
            self.calibration_ping_until = time.monotonic() + 2.0
            self.show_calibration_guide()
            self.update_region_window()

    def toggle_timer_resize_mode(self):
        self.timer_resize_mode = not self.timer_resize_mode
        cursor = "fleur" if self.timer_resize_mode else "arrow"
        for widget in (self.timer_label, self.text_label, self.resize_spacer):
            widget.configure(cursor=cursor)
        if self.timer_resize_mode and not self.timer_visible:
            self.toggle_timer_visibility()
        if not self.timer_resize_mode:
            self.timer_resize_drag_origin = None
            self.timer_resize_drag_position = None
            if self.timer_resize_drag_widget is not None:
                try:
                    self.timer_resize_drag_widget.grab_release()
                except tk.TclError:
                    pass
            self.timer_resize_drag_widget = None
            self.hide_resize_tooltip()
            self.resize_window.withdraw()
            self.resize_lock_window.withdraw()
            self.save_config()
        else:
            self.update_resize_window()
        return self.timer_resize_mode

    def timer_resize_wheel(self, event):
        return "break" if self.timer_resize_mode else None

    def set_timer_scale(self, scale, keep_origin=False, save=True):
        scale = max(self.timer_scale_min, min(self.timer_scale_max, round(float(scale), 2)))
        if abs(scale - self.timer_scale) < 0.001:
            return
        old_width, old_height = self.width, self.height
        origin_x, origin_y = self.root.winfo_x(), self.root.winfo_y()
        center_x = origin_x + old_width / 2
        center_y = origin_y + old_height / 2
        self.timer_scale = scale
        self.width = max(1, round(self.base_width * scale))
        self.height = max(1, round(self.base_height * scale))
        icon_size = max(1, round(self.base_icon_size * scale))
        self.config["timer_scale"] = scale
        self.config["window_width"] = self.width
        self.config["window_height"] = self.height
        self.config["display_icon_size"] = icon_size
        self.base_icon = self.icon_for_buff(self.active_buff or self.default_buff_key, icon_size)
        x = origin_x if keep_origin else round(center_x - self.width / 2)
        y = origin_y if keep_origin else round(center_y - self.height / 2)
        if save:
            self.set_timer_position(x, y)
        self.apply_timer_geometry(x, y)
        if self.end_time is None:
            self.render_no_buff_image()
        else:
            remaining = max(0, self.end_time - time.monotonic())
            color = "#ff5555" if remaining <= 10 else "#ffdf7d" if remaining <= 30 else "#ffffff"
            self.render_timer_image(format_time(remaining), color, self.active_buff)
        self.update_resize_window()
        if save:
            self.save_config()

    def save_config(self):
        if self.save_callback:
            self.save_callback(self.config)
        else:
            save_config_file(self.config)

    def calibrate_region_at_screen_point(self, screen_x, screen_y):

        box_w = 40
        box_h = 40
        current = self.config.get("detect_region", [0, 0, 40, 40])
        if len(current) == 4:
            box_w = max(8, int(current[2]) - int(current[0]))
            box_h = max(8, int(current[3]) - int(current[1]))

        if not self.target_hwnd:
            self.target_hwnd = find_window_by_title(self.config.get("window_title", ""))
        if not self.target_hwnd:
            self.target_hwnd = find_window_by_process_name(self.config["process_name"])
        if not self.target_hwnd:
            return

        client = get_client_screen_rect(self.target_hwnd)
        if not client:
            return

        client_left, client_top, client_right, client_bottom = client
        client_w = max(1, client_right - client_left)
        client_h = max(1, client_bottom - client_top)

        # Store the calibrated area in current client coordinates. Because the
        # origin stays tied to the Godius client area, moving the window later
        # keeps the detection box on the same in-game UI position.
        self.config["detect_coordinate_origin"] = "client"
        self.config["detect_reference_size"] = [client_w, client_h]
        left = round((screen_x - client_left) - box_w / 2)
        top = round((screen_y - client_top) - box_h / 2)
        self.config["detect_region"] = [left, top, left + box_w, top + box_h]
        self.save_config()
        self.last_capture_bbox = self.current_detection_bbox()

    def resize_detect_region(self, delta):
        region = self.config.get("detect_region", [0, 0, 40, 40])
        left, top, right, bottom = [int(v) for v in region]
        width = max(8, (right - left) + delta)
        height = max(8, (bottom - top) + delta)
        self.config["detect_region"] = [left, top, left + width, top + height]
        self.save_config()
        self.last_capture_bbox = self.current_detection_bbox()

    def current_detection_bbox(self):
        if not self.target_hwnd:
            self.target_hwnd = find_window_by_title(self.config.get("window_title", ""))
        if not self.target_hwnd:
            self.target_hwnd = find_window_by_process_name(self.config["process_name"])
        if not self.target_hwnd:
            return None
        region = self.config.get("detect_region")
        if not region or len(region) != 4:
            return None
        origin = str(self.config.get("detect_coordinate_origin", "client")).lower()
        base_rect = get_detection_base_rect(self.target_hwnd, origin)
        if not base_rect:
            return None
        base_left, base_top, base_right, base_bottom = base_rect
        base_width = max(1, base_right - base_left)
        base_height = max(1, base_bottom - base_top)
        left, top, right, bottom = [int(v) for v in region]
        reference = self.config.get("detect_reference_size", [base_width, base_height])
        if reference and len(reference) == 2:
            ref_width = max(1, float(reference[0]))
            ref_height = max(1, float(reference[1]))
            scale_x = base_width / ref_width
            scale_y = base_height / ref_height
            left = round(left * scale_x)
            right = round(right * scale_x)
            top = round(top * scale_y)
            bottom = round(bottom * scale_y)
        return base_left + left, base_top + top, base_left + right, base_top + bottom

    def configured_buffs(self):
        buffs = self.config.get("buffs")
        if isinstance(buffs, list) and buffs:
            return buffs
        return [
            {
                "key": "ice",
                "name": "Ice Crystal",
                "detect_template_path": self.config.get("detect_template_path", "icons/ice_crystal_template.png"),
                "display_icon_path": self.config.get("icon_path", "icons/ice_display.png"),
            }
        ]

    def first_buff_key(self):
        for buff in self.buffs:
            return buff["key"]
        return None

    def load_buffs(self):
        if not self.config.get("auto_detect", False):
            return []
        loaded = []
        for buff_config in self.configured_buffs():
            key = str(buff_config.get("key", "")).strip()
            if not key:
                continue
            template_path = resource_path(buff_config.get("detect_template_path", ""))
            icon_path = resource_path(buff_config.get("display_icon_path", self.config.get("icon_path", "")))
            try:
                template = Image.open(template_path).convert("RGB")
                # Validate the matching display asset now as well, so a bad
                # embedded bundle cannot fail later while rendering a timer.
                with Image.open(icon_path) as icon:
                    icon.load()
            except (FileNotFoundError, OSError, ValueError):
                continue
            loaded.append({
                "key": key,
                "name": str(buff_config.get("name", key)),
                "template": template,
                "mask": self.create_detect_mask(template),
                "icon_path": icon_path,
                "icon_cache": {},
            })
        self.apply_discriminative_masks(loaded)
        return loaded

    def create_detect_mask(self, template):
        arr = np.asarray(template, dtype=np.uint8)
        # Compare mostly bright and saturated crystal pixels so similar empty UI
        # slots do not trigger.
        luma = (0.299 * arr[:, :, 0]) + (0.587 * arr[:, :, 1]) + (0.114 * arr[:, :, 2])
        channel_spread = np.max(arr, axis=2).astype(np.int16) - np.min(arr, axis=2).astype(np.int16)
        mask = (luma > 105) | ((luma > 65) & (channel_spread > 35))
        if np.count_nonzero(mask) < 20:
            mask = luma > np.percentile(luma, 70)
        return Image.fromarray((mask.astype(np.uint8) * 255), mode="L")

    def create_center_mask(self, size):
        width, height = size
        ratio = max(0.1, min(0.5, float(self.config.get("detect_center_mask_ratio", 0.42))))
        radius = min(width, height) * ratio
        center_x = (width - 1) / 2.0
        center_y = (height - 1) / 2.0
        y, x = np.ogrid[:height, :width]
        mask = ((x - center_x) ** 2) + ((y - center_y) ** 2) <= radius ** 2
        return mask

    def apply_discriminative_masks(self, buffs):
        if len(buffs) < 2:
            return
        diff_threshold = max(0.0, float(self.config.get("detect_discriminative_diff", 35)))
        min_pixels = max(1, int(self.config.get("detect_min_mask_pixels", 80)))
        for buff in buffs:
            template = buff["template"]
            template_arr = np.asarray(template, dtype=np.float32)
            max_diff = np.zeros(template_arr.shape[:2], dtype=np.float32)
            for other in buffs:
                if other is buff:
                    continue
                other_template = other["template"]
                if other_template.size != template.size:
                    other_template = other_template.resize(template.size, Image.Resampling.LANCZOS)
                other_arr = np.asarray(other_template, dtype=np.float32)
                diff = np.mean(np.abs(template_arr - other_arr), axis=2)
                max_diff = np.maximum(max_diff, diff)
            base_mask = np.asarray(buff["mask"], dtype=bool)
            center_mask = self.create_center_mask(template.size)
            discriminative_mask = base_mask & center_mask & (max_diff >= diff_threshold)
            if np.count_nonzero(discriminative_mask) >= min_pixels:
                buff["mask"] = Image.fromarray((discriminative_mask.astype(np.uint8) * 255), mode="L")

    def buff_by_key(self, buff_key):
        for buff in self.buffs:
            if buff["key"] == buff_key:
                return buff
        return self.buffs[0] if self.buffs else None

    def icon_for_buff(self, buff_key, size=None):
        buff = self.buff_by_key(buff_key)
        icon_size = int(size or self.config.get("display_icon_size", 80))
        if not buff:
            icon_path = resource_path(self.config.get("icon_path", "icons/ice_display.png"))
            return Image.open(icon_path).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.NEAREST)
        cache = buff["icon_cache"]
        if icon_size not in cache:
            cache[icon_size] = Image.open(buff["icon_path"]).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.NEAREST)
        return cache[icon_size]

    def load_program_icon(self, size):
        path = resource_path(self.config.get("program_icon_path", "icons/Godius_104.png"))
        return Image.open(path).convert("RGBA").resize((int(size), int(size)), Image.Resampling.LANCZOS)

    def load_plain_template(self, config_key):
        path = resource_path(self.config.get(config_key, ""))
        try:
            return Image.open(path).convert("RGB")
        except (FileNotFoundError, OSError, ValueError):
            return None

    def capture_client_frame(self, client_rect):
        if self.desktop_camera is not None:
            array = self.desktop_camera.grab(
                region=tuple(int(value) for value in client_rect),
                new_frame_only=False,
            )
            if array is None:
                return None
            return Image.fromarray(array, mode="RGB")
        return ImageGrab.grab(bbox=client_rect).convert("RGB")

    def crop_bbox_from_client_frame(self, client_frame, client_rect, bbox):
        client_left, client_top, _client_right, _client_bottom = client_rect
        left = max(0, round(bbox[0] - client_left))
        top = max(0, round(bbox[1] - client_top))
        right = min(client_frame.width, round(bbox[2] - client_left))
        bottom = min(client_frame.height, round(bbox[3] - client_top))
        if right <= left or bottom <= top:
            return None
        return client_frame.crop((left, top, right, bottom))

    def capture_detection_bbox(self, bbox):
        client_rect = get_client_screen_rect(self.target_hwnd)
        if client_rect:
            client_left, client_top, client_right, client_bottom = client_rect
            bbox_inside_client = (
                bbox[0] >= client_left
                and bbox[1] >= client_top
                and bbox[2] <= client_right
                and bbox[3] <= client_bottom
            )
            if bbox_inside_client:
                client_frame = self.capture_client_frame(client_rect)
                if client_frame is None:
                    return None
                return self.crop_bbox_from_client_frame(client_frame, client_rect, bbox)
        return ImageGrab.grab(bbox=bbox).convert("RGB")

    def update_debug_capture_preview(self, capture, bbox, status):
        if not self.debug_capture_enabled or not self.debug_capture_window:
            return
        try:
            scale = max(1, int(self.config.get("debug_capture_scale", 4)))
            preview = capture.resize((capture.width * scale, capture.height * scale), Image.Resampling.NEAREST)
            self.debug_capture_image = ImageTk.PhotoImage(preview)
            self.debug_capture_label.configure(image=self.debug_capture_image)
            bbox_text = f"bbox: {bbox[0]},{bbox[1]} - {bbox[2]},{bbox[3]}"
            self.debug_capture_text.configure(text=f"{self.capture_backend}\n{bbox_text}\n{status}")
            self.debug_capture_window.update_idletasks()
        except Exception:
            pass

    def detect_buff_present(self):
        if not self.buffs or not self.target_hwnd:
            self.update_debug_status("No buffs loaded or target window missing")
            return None
        region = self.config.get("detect_region")
        if not region or len(region) != 4:
            self.update_debug_status("detect_region is missing")
            return None
        origin = str(self.config.get("detect_coordinate_origin", "client")).lower()
        base_rect = get_detection_base_rect(self.target_hwnd, origin)
        if not base_rect:
            self.target_hwnd = None
            self.update_debug_status(f"Cannot get target rect\norigin: {origin}")
            return None

        base_left, base_top, base_right, base_bottom = base_rect
        base_width = max(1, base_right - base_left)
        base_height = max(1, base_bottom - base_top)
        left, top, right, bottom = [int(v) for v in region]
        reference = self.config.get("detect_reference_size", [base_width, base_height])
        if reference and len(reference) == 2:
            ref_width = max(1, float(reference[0]))
            ref_height = max(1, float(reference[1]))
            scale_x = base_width / ref_width
            scale_y = base_height / ref_height
            left = round(left * scale_x)
            right = round(right * scale_x)
            top = round(top * scale_y)
            bottom = round(bottom * scale_y)
        bbox = (base_left + left, base_top + top, base_left + right, base_top + bottom)
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            self.update_debug_status(f"Invalid bbox: {bbox}")
            return None
        self.last_capture_bbox = bbox

        hide_overlay = self.config.get("hide_overlay_during_capture", False)
        try:
            if self.region_window:
                self.region_window.withdraw()
                self.region_window.update_idletasks()
            if hide_overlay:
                self.root.withdraw()
                self.text_window.withdraw()
                self.root.update_idletasks()
                time.sleep(0.03)
            capture = self.capture_detection_bbox(bbox)
        except Exception as exc:
            self.update_debug_status(f"Capture exception\n{type(exc).__name__}: {exc}")
            return None
        finally:
            if hide_overlay:
                self.root.deiconify()
                self.text_window.deiconify()
        if capture is None:
            self.update_debug_status(f"Capture returned None\nbbox: {bbox}")
            return None
        self.update_debug_capture_preview(capture, bbox, "captured")

        if self.absent_template:
            self.last_absent_score = self.score_by_pixel_difference(capture, self.absent_template)
            absent_threshold = float(self.config.get("absent_threshold", 0.82))
            if self.last_absent_score >= absent_threshold:
                self.update_debug_capture_preview(
                    capture,
                    bbox,
                    f"absent: {self.last_absent_score:.3f} >= {absent_threshold:.3f}",
                )
                return None

        threshold = float(self.config.get("detect_threshold", 0.62))
        min_score_gap = max(0.0, float(self.config.get("detect_min_score_gap", 0.0)))
        color_anchor_weight = max(0.0, min(1.0, float(self.config.get("detect_color_anchor_weight", 0.0))))
        best_key = None
        best_score = 0.0
        scores = []
        score_lines = []
        full_scores = {}
        frame_scores = {}
        obstruction_scores = {}
        presence_scores = {}
        for buff in self.buffs:
            template = buff["template"]
            mask = buff["mask"]
            template_score = self.score_template(capture, template, mask)
            color_score = self.score_color_anchor(capture, buff["key"])
            detect_score = (template_score * (1.0 - color_anchor_weight)) + (color_score * color_anchor_weight)
            full_score = self.score_full_template(capture, template)
            frame_score = self.score_slot_frame(capture, template)
            obstruction_score = self.score_text_obstruction(capture, template)
            presence_score = self.score_icon_presence(capture, template)
            full_scores[buff["key"]] = full_score
            frame_scores[buff["key"]] = frame_score
            obstruction_scores[buff["key"]] = obstruction_score
            presence_scores[buff["key"]] = presence_score
            scores.append((buff["key"], detect_score))
            score_lines.append(
                f"{buff['key']}: old {detect_score:.3f} / full {full_score:.3f} / frame {frame_score:.3f} / icon {presence_score:.3f} / text {obstruction_score:.3f} / color {color_score:.2f}"
            )
            if detect_score > best_score:
                best_key = buff["key"]
                best_score = detect_score
        ranked_scores = sorted((score for _key, score in scores), reverse=True)
        second_score = ranked_scores[1] if len(ranked_scores) > 1 else 0.0
        score_gap = best_score - second_score
        rejection = ""
        if best_score < threshold or (len(self.buffs) > 1 and score_gap < min_score_gap):
            rejection = "legacy score/gap"
            best_key = None
        full_threshold = float(self.config.get("detect_full_similarity_threshold", 0.56))
        frame_threshold = float(self.config.get("detect_slot_frame_threshold", 0.58))
        obstruction_threshold = float(self.config.get("detect_text_obstruction_threshold", 0.55))
        presence_threshold = float(self.config.get("detect_icon_presence_threshold", 0.35))
        if best_key and full_scores.get(best_key, 0.0) < full_threshold:
            rejection = f"full {full_scores[best_key]:.3f} < {full_threshold:.3f}"
            best_key = None
        if best_key and frame_scores.get(best_key, 0.0) < frame_threshold:
            rejection = f"frame {frame_scores[best_key]:.3f} < {frame_threshold:.3f}"
            best_key = None
        if best_key and obstruction_scores.get(best_key, 0.0) >= obstruction_threshold:
            rejection = f"tooltip/text {obstruction_scores[best_key]:.3f} >= {obstruction_threshold:.3f}"
            best_key = None
        if best_key and presence_scores.get(best_key, 0.0) < presence_threshold:
            rejection = f"icon missing {presence_scores[best_key]:.3f} < {presence_threshold:.3f}"
            best_key = None
        absent_text = "absent: n/a"
        if self.last_absent_score is not None:
            absent_text = f"absent: {self.last_absent_score:.3f}"
        result_text = best_key if best_key else "none"
        self.update_debug_capture_preview(
            capture,
            bbox,
            f"{absent_text}\n" + "\n".join(score_lines)
            + f"\ngap: {score_gap:.3f} (min {min_score_gap:.3f})"
            + f"\nlimits: old {threshold:.3f} / full {full_threshold:.3f} / frame {frame_threshold:.3f} / icon>{presence_threshold:.3f} / text<{obstruction_threshold:.3f}"
            + f"\nresult: {result_text}" + (f"\nrejected: {rejection}" if rejection else ""),
        )
        return best_key

    def score_template(self, capture, template, mask):
        if template.size != capture.size:
            template = template.resize(capture.size, Image.Resampling.LANCZOS)
            if mask:
                mask = mask.resize(capture.size, Image.Resampling.NEAREST)

        cap_rgb = np.asarray(capture, dtype=np.float32)
        tmpl_rgb = np.asarray(template, dtype=np.float32)
        if mask:
            mask_arr = np.asarray(mask, dtype=bool)
            if np.count_nonzero(mask_arr) > 0:
                cap_rgb = cap_rgb[mask_arr]
                tmpl_rgb = tmpl_rgb[mask_arr]

        pixel_similarity = float(1.0 - (np.mean(np.abs(cap_rgb - tmpl_rgb)) / 255.0))

        cap = cap_rgb.reshape(-1)
        tmpl = tmpl_rgb.reshape(-1)
        cap_std = float(np.std(cap))
        tmpl_std = float(np.std(tmpl))
        if cap_std < 0.001 or tmpl_std < 0.001:
            correlation = 0.0
        else:
            correlation = float(np.mean(((cap - np.mean(cap)) / cap_std) * ((tmpl - np.mean(tmpl)) / tmpl_std)))
            correlation = (correlation + 1.0) / 2.0
        rgb_score = (correlation * 0.45) + (pixel_similarity * 0.55)

        chroma_weight = max(0.0, min(1.0, float(self.config.get("detect_chroma_weight", 0.0))))
        if chroma_weight <= 0.0:
            return rgb_score
        cap_chroma = cap_rgb / (np.sum(cap_rgb, axis=1, keepdims=True) + 1e-6)
        tmpl_chroma = tmpl_rgb / (np.sum(tmpl_rgb, axis=1, keepdims=True) + 1e-6)
        chroma_score = float(1.0 - (np.mean(np.abs(cap_chroma - tmpl_chroma)) / (2.0 / 3.0)))
        chroma_score = max(0.0, min(1.0, chroma_score))
        return (rgb_score * (1.0 - chroma_weight)) + (chroma_score * chroma_weight)

    def score_color_anchor(self, capture, buff_key):
        arr = np.asarray(capture, dtype=np.float32)
        center_mask = self.create_center_mask(capture.size)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        max_channel = np.max(arr, axis=2)
        min_channel = np.min(arr, axis=2)
        saturation = (max_channel - min_channel) / (max_channel + 1e-6)
        luma = (0.299 * r) + (0.587 * g) + (0.114 * b)
        lit_center = center_mask & (luma > 55)
        lit_pixels = int(np.count_nonzero(lit_center))
        if lit_pixels < 20:
            return 0.5

        warm_pixels = lit_center & (saturation > 0.12) & (r > g + 8) & (g > b + 5) & (r > b + 30)
        red_pixels = lit_center & (saturation > 0.12) & (r > g + 5) & (r > b + 35)
        cool_pixels = lit_center & (saturation > 0.08) & (g > r + 5) & (b > r + 5)

        warm_ratio = np.count_nonzero(warm_pixels) / lit_pixels
        red_ratio = np.count_nonzero(red_pixels) / lit_pixels
        cool_ratio = np.count_nonzero(cool_pixels) / lit_pixels

        def ramp(value, low, high):
            if high <= low:
                return 0.0
            return max(0.0, min(1.0, (value - low) / (high - low)))

        key = str(buff_key).lower()
        if "fire" in key:
            return max(ramp(warm_ratio, 0.45, 0.80), ramp(red_ratio, 0.35, 0.75))
        if "ice" in key:
            cool_score = ramp(cool_ratio, 0.12, 0.30)
            red_penalty = 1.0 - ramp(red_ratio, 0.25, 0.55)
            warm_penalty = 1.0 - ramp(warm_ratio, 0.35, 0.70)
            return max(0.0, min(1.0, (cool_score * 0.70) + (red_penalty * 0.20) + (warm_penalty * 0.10)))
        return 0.5

    def score_by_pixel_difference(self, capture, template):
        if template.size != capture.size:
            template = template.resize(capture.size, Image.Resampling.NEAREST)
        cap = np.asarray(capture, dtype=np.float32)
        tmpl = np.asarray(template, dtype=np.float32)
        return float(1.0 - (np.mean(np.abs(cap - tmpl)) / 255.0))

    def score_full_template(self, capture, template):
        return self.score_template(capture, template, None)

    def score_slot_frame(self, capture, template):
        if template.size != capture.size:
            template = template.resize(capture.size, Image.Resampling.LANCZOS)
        width, height = capture.size
        band = max(2, round(min(width, height) * 0.18))
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[:band, :] = 255
        mask[-band:, :] = 255
        mask[:, :band] = 255
        mask[:, -band:] = 255
        return self.score_template(capture, template, Image.fromarray(mask, mode="L"))

    def score_text_obstruction(self, capture, template):
        if template.size != capture.size:
            template = template.resize(capture.size, Image.Resampling.LANCZOS)
        cap = np.asarray(capture, dtype=np.float32)
        tmpl = np.asarray(template, dtype=np.float32)
        cap_luma = (0.299 * cap[:, :, 0]) + (0.587 * cap[:, :, 1]) + (0.114 * cap[:, :, 2])
        tmpl_luma = (0.299 * tmpl[:, :, 0]) + (0.587 * tmpl[:, :, 1]) + (0.114 * tmpl[:, :, 2])
        cap_spread = np.max(cap, axis=2) - np.min(cap, axis=2)
        color_delta = np.mean(np.abs(cap - tmpl), axis=2)
        # Tooltip glyphs are bright, saturated pixels appearing where the
        # selected buff template expects dark slot/background pixels.
        unexpected = (
            (cap_luma >= 145)
            & (cap_spread >= 35)
            & ((tmpl_luma <= 105) | (color_delta >= 75))
        )
        # The crystal itself occupies the center of the slot. At small client
        # sizes, resampling shifts its bright fire pixels by one or two pixels;
        # treating those pixels as tooltip glyphs can saturate this score at
        # 1.0. Tooltip panels and labels still leave unexpected pixels around
        # the outer part of the slot, so score only that area here.
        unexpected &= ~self.create_center_mask(capture.size)
        height, width = unexpected.shape
        unexpected_ratio = float(np.count_nonzero(unexpected)) / max(1, width * height)
        row_span = 0.0
        for row in unexpected:
            indices = np.flatnonzero(row)
            if indices.size >= 2:
                row_span = max(row_span, float(indices[-1] - indices[0] + 1) / max(1, width))
        edge_width = max(1, round(width * 0.18))
        edge_pixels = np.concatenate((unexpected[:, :edge_width].ravel(), unexpected[:, -edge_width:].ravel()))
        edge_ratio = float(np.count_nonzero(edge_pixels)) / max(1, edge_pixels.size)
        return max(
            0.0,
            min(1.0, max(unexpected_ratio / 0.16, row_span / 0.72, edge_ratio / 0.30)),
        )

    def score_icon_presence(self, capture, template):
        if template.size != capture.size:
            template = template.resize(capture.size, Image.Resampling.LANCZOS)
        cap = np.asarray(capture, dtype=np.float32)
        tmpl = np.asarray(template, dtype=np.float32)
        cap_luma = (0.299 * cap[:, :, 0]) + (0.587 * cap[:, :, 1]) + (0.114 * cap[:, :, 2])
        tmpl_luma = (0.299 * tmpl[:, :, 0]) + (0.587 * tmpl[:, :, 1]) + (0.114 * tmpl[:, :, 2])
        cap_spread = np.max(cap, axis=2) - np.min(cap, axis=2)
        tmpl_spread = np.max(tmpl, axis=2) - np.min(tmpl, axis=2)
        expected_icon = (tmpl_luma > 105) | ((tmpl_luma > 65) & (tmpl_spread > 35))
        visible_icon = expected_icon & ((cap_luma > 105) | ((cap_luma > 65) & (cap_spread > 35)))
        return float(np.count_nonzero(visible_icon)) / max(1, int(np.count_nonzero(expected_icon)))

    def update_region_window(self):
        if not self.region_window:
            return
        if self.calibration_mode:
            if self.calibration_guide_window and not self.calibration_guide_drag_origin:
                self.show_calibration_guide()
            self.last_capture_bbox = self.current_detection_bbox()
        if not self.calibration_mode or not self.last_capture_bbox:
            self.region_window.withdraw()
            return
        left, top, right, bottom = self.last_capture_bbox
        width = max(1, right - left)
        height = max(1, bottom - top)
        padding = CALIBRATION_PING_PADDING
        canvas_width = width + padding * 2
        canvas_height = height + padding * 2
        self.region_window.geometry(
            f"{canvas_width}x{canvas_height}+{left - padding}+{top - padding}"
        )
        canvas = self.region_window.winfo_children()[0]
        canvas.configure(width=canvas_width, height=canvas_height)
        canvas.delete("all")
        if time.monotonic() < self.calibration_ping_until:
            for expansion in sorted(calibration_ping_expansions(time.monotonic()), reverse=True):
                color = "#ff3030" if expansion >= 16 else "#ff8a45" if expansion >= 8 else "#fff0a0"
                canvas.create_rectangle(
                    padding - expansion,
                    padding - expansion,
                    padding + width + expansion,
                    padding + height + expansion,
                    outline=color,
                    width=2 if expansion >= 8 else 3,
                )
        canvas.create_rectangle(
            padding + 1,
            padding + 1,
            padding + width - 2,
            padding + height - 2,
            outline="#ff3030",
            fill="#ff3030",
            width=3,
        )
        attach_above(self.region_window, self.target_hwnd, left - padding, top - padding)

    def handle_auto_detect(self):
        if not self.config.get("auto_detect", False):
            self.update_debug_status("auto_detect is disabled")
            return
        if self.calibration_mode:
            self.update_debug_status("calibration mode is active")
            return
        if not self.is_target_foreground():
            fg = user32.GetForegroundWindow()
            name, _pid = process_name_for_hwnd(fg) if fg else ("", 0)
            self.update_debug_status(f"Waiting for foreground\nforeground: {name or 'unknown'}")
            return
        now = time.monotonic()
        interval = max(0.1, float(self.config.get("detect_interval_ms", 350)) / 1000.0)
        if now - self.last_detect_at < interval:
            return
        self.last_detect_at = now

        detected_buff = self.detect_buff_present()
        absent_detected = False
        if self.last_absent_score is not None:
            absent_detected = self.last_absent_score >= float(self.config.get("absent_threshold", 0.82))
        self._observe_party_buff_presence(detected_buff, absent_detected)
        if not detected_buff:
            self.detect_hits = {}
            self.expired_buff_lock = None
            self.expired_buff_lock_until = 0.0
            if self.end_time is not None:
                absent_grace_seconds = max(0.0, float(self.config.get("absent_grace_seconds", 5)))
                started_at = self.started_at if self.started_at is not None else now
                can_stop_on_absent = now - started_at >= absent_grace_seconds
                if can_stop_on_absent:
                    if absent_detected:
                        self.absent_hits += 1
                    else:
                        self.absent_hits = 0
                else:
                    self.absent_hits = 0
                required_absent = max(1, int(self.config.get("absent_required_hits", 2)))
                stop_on_absent = bool(self.config.get("stop_when_absent_detected", True))
                absent_long_enough = stop_on_absent and absent_detected and self.absent_hits >= required_absent
                # A rejected/covered capture is not proof that the buff ended.
                # Only the explicit absent template may cancel a running timer.
                if absent_long_enough:
                    self.end_time = None
                    self.started_at = None
                    self.active_buff = None
                    self.expired_buff_lock = None
                    self.expired_buff_lock_until = 0.0
                    self.absent_hits = 0
            else:
                self.absent_hits = 0
            self.missing_hits = 0
            return

        for buff_key in list(self.detect_hits):
            if buff_key != detected_buff:
                self.detect_hits[buff_key] = 0

        if self.expired_buff_lock and now >= self.expired_buff_lock_until:
            self.expired_buff_lock = None
            self.expired_buff_lock_until = 0.0

        if self.expired_buff_lock == detected_buff:
            self.detect_hits[detected_buff] = 0
            self.absent_hits = 0
            self.missing_hits = 0
            return

        self.detect_hits[detected_buff] = self.detect_hits.get(detected_buff, 0) + 1
        self.absent_hits = 0
        self.missing_hits = 0

        required_hits = max(1, int(self.config.get("detect_required_hits", 2)))
        if self.detect_hits[detected_buff] >= required_hits:
            if self.end_time is None or self.active_buff != detected_buff:
                self.start_timer(detected_buff)

    def _observe_party_buff_presence(self, detected_buff, absent_detected):
        required_hits = max(1, int(self.config.get("detect_required_hits", 2)))
        required_absent = max(1, int(self.config.get("absent_required_hits", 2)))
        if detected_buff:
            self.party_absent_hits = 0
            for key in list(self.party_detect_hits):
                if key != detected_buff:
                    self.party_detect_hits[key] = 0
            self.party_detect_hits[detected_buff] = self.party_detect_hits.get(detected_buff, 0) + 1
            if self.party_detect_hits[detected_buff] >= required_hits:
                self._emit_party_buff_presence(detected_buff)
            return
        self.party_detect_hits = {}
        if not absent_detected:
            self.party_absent_hits = 0
            return
        self.party_absent_hits += 1
        if self.party_absent_hits >= required_absent:
            self._emit_party_buff_presence(None)

    def _emit_party_buff_presence(self, buff_key):
        if buff_key == self.party_observed_buff:
            return
        self.party_observed_buff = buff_key
        callback = self.party_presence_callback
        if callback:
            callback(buff_key)

    def update_display(self):
        if self.end_time is None:
            self.render_no_buff_image()
            self.root.attributes("-alpha", self.display_icon_opacity)
            return
        remaining = self.end_time - time.monotonic()
        if remaining <= 0:
            expired_buff = self.active_buff
            self.active_buff = None
            self.started_at = None
            self.end_time = None
            self.expired_buff_lock = expired_buff
            self.expired_buff_lock_until = time.monotonic() + max(
                0.0,
                float(self.config.get("expire_restart_suppression_seconds", 1.5)),
            )
            self.detect_hits = {}
            self.absent_hits = 0
            self.missing_hits = 0
            self.render_no_buff_image()
            self.root.attributes("-alpha", self.display_icon_opacity)
            return
        color = "#ff5555" if remaining <= 10 else "#ffdf7d" if remaining <= 30 else "#ffffff"
        label = format_time(remaining)
        self.render_timer_image(label, color, self.active_buff)
        self.root.attributes("-alpha", self.display_icon_opacity)

    def tick(self):
        if self.closed:
            return
        attached = self.position_near_target()
        if not attached or (self.target_hwnd and user32.IsIconic(self.target_hwnd)):
            self.root.withdraw()
            self.text_window.withdraw()
            self.region_window.withdraw()
            if self.calibration_guide_window:
                self.calibration_guide_window.withdraw()
            self.resize_tooltip.withdraw()
            self.resize_lock_window.withdraw()
            self.resize_window.withdraw()
            try:
                self.root.after(100, self.tick)
            except tk.TclError:
                self.closed = True
            return
        self.handle_hotkey()
        self.handle_auto_detect()
        self.update_region_window()
        self.update_display()
        self.keep_timer_visible()
        try:
            self.root.after(100, self.tick)
        except tk.TclError:
            self.closed = True

    def run(self):
        self.root.mainloop()


def main():
    if sys.platform != "win32":
        raise SystemExit("This overlay is Windows-only.")
    config = load_config()
    BuffTimerApp(config).run()


if __name__ == "__main__":
    main()

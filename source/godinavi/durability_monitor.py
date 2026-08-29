import concurrent.futures
from collections import Counter
import ctypes
import re
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageTk

from paddle_ocr_backend import PaddleOcrBackend
from modal_window import activate_modal, bind_modal_escape
from v2_runtime_assets import materialize_runtime_assets

from .window_attachment import attach_above, client_screen_rect, user32


BG = "#17130f"
PANEL = "#2a2118"
PANEL_HOVER = "#5a4932"
GOLD = "#d8b15a"
TEXT = "#fff1c9"
MUTED = "#c9b98f"
PARTS = ("weapon", "armor", "shield")
PART_COLORS = {"weapon": "#ff5252", "armor": "#ffd740", "shield": "#40c4ff"}
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TRANSPARENT = 0x00000020
GW_OWNER = 4
GA_ROOT = 2
OCR_VALUE_HOLD_SECONDS = 5.0
OCR_VALUE_CONFIRMATIONS = 3
MAX_DURABILITY_CHANGE_PER_READING = 10
EDITOR_BORDER_WIDTH = 4
EDITOR_RESIZE_GRIP_SIZE = 16
WARNING_FLASH_INTERVAL_SECONDS = 0.5
STARTUP_WARNING_GRACE_SECONDS = 2.0

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND


TEXTS = {
    "KR": {
        "title": "내구도 감시 설정", "weapon": "무기", "armor": "갑옷", "shield": "방패",
        "enabled": "사용", "threshold": "경고 기준", "preview": "현재 인식",
        "unknown": "XX", "save": "확정 및 닫기", "move": "이동",
        "check_equipment": "Check your\nequipment!",
        "help_show": "설명 보기", "help_hide": "설명 닫기",
        "help_text": "위 예시처럼 색상별 박스를 장비 내구도 숫자에 맞춰주세요.\n빨간색은 무기, 노란색은 갑옷, 파란색은 방패입니다.\n\n경고 기준은 장비 최대 내구도의 10%보다 높은 숫자로 설정해주세요.\n내구도가 10% 미만이 되면 게임 화면의 내구도 표시 모양이 바뀌면서 숫자가 사라집니다. 숫자가 사라진 뒤에는 가디맵도 현재 내구도를 읽을 수 없으므로, 숫자가 사라지기 전에 경고가 나오도록 설정해야 합니다.\n\n예시: 최대 내구도가 1,000인 장비라면 경고 기준을 100보다 높게 설정해주세요.\n\n이 기능은 화면에 표시된 숫자를 읽어 경고하는 보조 기능입니다. 장비 상태를 직접 확인하는 것도 잊지 마세요.",
        "warning1": "장비 최대 내구도의 10% 이상의 숫자로 지정해야 올바르게 작동합니다.",
        "warning2": "이 툴에 완전히 의지하지는 마세요!",
        "hint": "색상 박스와 경고 아이콘 영역을 드래그해 이동하고 우측 하단을 드래그해 크기를 조절하세요.",
        "preset_save": "저장", "preset_names": "이름설정", "preset_name_title": "프리셋 이름 설정",
        "preset_name_save": "저장", "preset_name_close": "닫기", "preset_name_limit": "한글 4자 · 영어 6자까지 입력할 수 있습니다.",
        "warning_sound": "효과음",
    },
    "JP": {
        "title": "耐久度監視設定", "weapon": "武器", "armor": "鎧", "shield": "盾",
        "enabled": "使用", "threshold": "警告基準", "preview": "認識値",
        "unknown": "XX", "save": "確定して閉じる", "move": "移動",
        "check_equipment": "Check your\nequipment!",
        "help_show": "説明を見る", "help_hide": "説明を閉じる",
        "help_text": "上の例のように、色付きの枠を装備耐久度の数字に合わせてください。\n赤は武器、黄は鎧、青は盾です。\n\n警告基準は、装備の最大耐久度の10%より高い数値に設定してください。\n耐久度が10%未満になるとゲーム内の表示が変わり、数字が見えなくなります。数字が消えた後はGodiNaviも耐久度を読み取れないため、数字が消える前に警告が出るように設定してください。\n\n例：最大耐久度が1,000なら、警告基準は100より高く設定します。\n\nこの機能は画面上の数字を読み取る補助機能です。装備の状態も直接確認してください。",
        "warning1": "装備の最大耐久度の10%以上の数値を指定してください。",
        "warning2": "このツールだけに完全に頼らないでください！",
        "preset_save": "保存", "preset_names": "名前設定", "preset_name_title": "プリセット名設定",
        "preset_name_save": "保存", "preset_name_close": "閉じる", "preset_name_limit": "日本語は4文字、英字のみは6文字まで入力できます。",
        "warning_sound": "効果音",
        "hint": "色付き枠と警告アイコンをドラッグで移動し、右下をドラッグしてサイズを調整します。",
    },
    "EN": {
        "title": "Durability Monitor", "weapon": "Weapon", "armor": "Armor", "shield": "Shield",
        "enabled": "Use", "threshold": "Warn below", "preview": "Detected",
        "unknown": "XX", "save": "Save and close", "move": "Move",
        "check_equipment": "Check your\nequipment!",
        "help_show": "Show instructions", "help_hide": "Hide instructions",
        "help_text": "Align each colored box with an equipment durability number as shown above.\nRed is weapon, yellow is armor, and blue is shield.\n\nSet the warning threshold higher than 10% of the equipment's maximum durability.\nBelow 10%, the game's durability display changes and the number disappears. Once the number is gone, GodiNavi cannot read it, so set the warning to appear before that happens.\n\nExample: If the maximum durability is 1,000, set the warning threshold above 100.\n\nThis is an assistive warning based on numbers visible on screen. Please check your equipment directly as well.",
        "warning1": "Set the threshold to at least 10% of the equipment's maximum durability.",
        "warning2": "Do not rely entirely on this tool!",
        "preset_save": "Save", "preset_names": "Names", "preset_name_title": "Preset names",
        "preset_name_save": "Save", "preset_name_close": "Close", "preset_name_limit": "Up to 6 English characters or 4 other characters.",
        "warning_sound": "Sound",
        "hint": "Drag colored boxes and the warning icon to move them. Drag the bottom-right corner to resize.",
    },
}


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False):
        root = materialize_runtime_assets()
    elif str(relative).replace("\\", "/") == "ocr_models":
        return Path(__file__).resolve().parents[2] / "content-source" / "ocr_models"
    else:
        root = Path(__file__).resolve().parents[2] / "private" / "content-source" / "runtime"
    return root / relative


def default_durability_config() -> dict:
    return {
        "monitoring_enabled": False,
        "warning_region": None,
        "warning_reference_size": None,
        "warning_orientation": "horizontal",
        "warning_sound_enabled": False,
        "warning_sound_volume": 60,
        "parts": {
            "weapon": {"enabled": False, "threshold": 0, "region": None, "reference_size": None, "warning_region": None, "warning_reference_size": None},
            "armor": {"enabled": False, "threshold": 0, "region": None, "reference_size": None, "warning_region": None, "warning_reference_size": None},
            "shield": {"enabled": False, "threshold": 0, "region": None, "reference_size": None, "warning_region": None, "warning_reference_size": None},
        },
        "presets": [empty_durability_preset(index) for index in range(4)],
        "active_preset": 0,
    }


def empty_durability_preset(index: int) -> dict:
    return {
        "name": f"Pre{index + 1}",
        "parts": {part: {"enabled": False, "threshold": 0} for part in PARTS},
    }


def durability_preset_snapshot(parts: dict) -> dict:
    return {
        part: {
            "enabled": bool(parts.get(part, {}).get("enabled", False)),
            "threshold": max(0, int(parts.get(part, {}).get("threshold", 0))),
        }
        for part in PARTS
    }


def valid_preset_name(value: str) -> str:
    value = str(value).strip()
    limit = 6 if value.isascii() else 4
    return value[:limit]


def check_equipment_text_color(phase: int) -> tuple[int, int, int, int]:
    return (255, 78, 68, 255) if phase % 2 else (255, 223, 125, 255)


def warning_asset_path(part: str = "weapon") -> Path:
    return resource_path(f"assets/icons/godinavi/warning_{part}.jpg")


def warning_source_image(part: str = "weapon") -> Image.Image:
    image = Image.open(warning_asset_path(part)).convert("RGBA")
    return binary_alpha(image)


def binary_alpha(image: Image.Image, cutoff: int = 224) -> Image.Image:
    image = image.convert("RGBA")
    alpha = image.getchannel("A").point(lambda value: 255 if value >= cutoff else 0)
    image.putalpha(alpha)
    return image


def recognized_integer(text: str) -> int | None:
    digits = re.findall(r"\d+", str(text or ""))
    if not digits:
        return None
    try:
        return int(digits[0])
    except ValueError:
        return None


def ui_font(size: int):
    for name in ("malgun.ttf", "malgunbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    max_width, max_height = max(1, int(max_width)), max(1, int(max_height))
    scale = min(max_width / max(1, image.width), max_height / max(1, image.height))
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return binary_alpha(image.resize(size, Image.Resampling.LANCZOS))


class EditableRegion:
    HEADER_HEIGHT = 22

    def __init__(self, master, color, on_changed, content_drawer=None, label=None, action=None, action_label="↻"):
        self.color = color
        self.on_changed = on_changed
        self.content_drawer = content_drawer
        self.label = label or (lambda: "이동")
        self.action = action
        self.action_label = action_label
        self.last_draw_size = None
        self.drag = None
        self.mode = None
        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", False)
        self.transparent_key = "#010101"
        self.window.configure(bg=self.transparent_key)
        self.window.wm_attributes("-transparentcolor", self.transparent_key)
        self.canvas = tk.Canvas(self.window, bg=self.transparent_key, highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Motion>", self._pointer)
        self.canvas.bind("<Configure>", self._redraw)
        self.window.update_idletasks()
        # Keep calibration boxes visible to Windows Snipping Tool.  The boxes
        # use a transparent body, so only their thin guide chrome is captured.
        self.window.withdraw()

    def _redraw(self, _event=None):
        width, height = self.window.winfo_width(), self.window.winfo_height()
        size = (width, height)
        if size == self.last_draw_size:
            return
        self.last_draw_size = size
        self.canvas.delete("guide")
        self.canvas.create_rectangle(0, 0, width, self.HEADER_HEIGHT, fill=self.color, outline=self.color, tags="guide")
        self.canvas.create_text(8, self.HEADER_HEIGHT // 2, text=f"⠿  {self.label()}", fill="#fff1c9", anchor="w", font=("Noto Sans KR", 9, "bold"), tags="guide")
        if self.action:
            self.canvas.create_rectangle(width - 28, 2, width - 2, self.HEADER_HEIGHT - 2, fill="#2a2118", outline="#fff1c9", tags="guide")
            self.canvas.create_text(width - 15, self.HEADER_HEIGHT // 2, text=self.action_label, fill="#fff1c9", font=("Segoe UI Symbol", 11, "bold"), tags="guide")
        self.canvas.create_rectangle(1, self.HEADER_HEIGHT, width - 2, height - 2, outline=self.color, width=3, tags="guide")
        self.canvas.create_polygon(width-15, height-2, width-2, height-15, width-2, height-2, fill=self.color, tags="guide")
        if self.content_drawer:
            self.content_drawer(self.canvas, width, height, self.HEADER_HEIGHT)

    def _pointer(self, event):
        resize = event.x >= self.window.winfo_width() - 16 and event.y >= self.window.winfo_height() - 16
        self.canvas.configure(cursor="size_nw_se" if resize else "fleur" if event.y <= self.HEADER_HEIGHT else "arrow")

    def _press(self, event):
        if self.action and event.y <= self.HEADER_HEIGHT and event.x >= self.window.winfo_width() - 30:
            self.action()
            self.drag = None
            self.mode = None
            return
        self.mode = "resize" if event.x >= self.window.winfo_width() - 16 and event.y >= self.window.winfo_height() - 16 else "move"
        self.drag = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y(), self.window.winfo_width(), self.window.winfo_height())

    def _motion(self, event):
        if not self.drag:
            return
        sx, sy, x, y, width, height = self.drag
        if self.mode == "resize":
            width = max(28, width + event.x_root - sx)
            height = max(self.HEADER_HEIGHT + 20, height + event.y_root - sy)
        else:
            x += event.x_root - sx
            y += event.y_root - sy
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _release(self, _event):
        self.drag = None
        self.mode = None
        self.on_changed(self.geometry())

    def geometry(self):
        self.window.update_idletasks()
        x, y = self.window.winfo_x(), self.window.winfo_y()
        return x, y + self.HEADER_HEIGHT, x + self.window.winfo_width(), y + self.window.winfo_height()

    def show(self, bbox, owner):
        left, top, right, bottom = bbox
        outer_top = top - self.HEADER_HEIGHT
        self.window.geometry(f"{max(28, right-left)}x{max(20, bottom-top)+self.HEADER_HEIGHT}+{left}+{outer_top}")
        attach_above(self.window, owner, left, outer_top)

    def hide(self):
        self.window.withdraw()

    def destroy(self):
        self.window.destroy()


class DurabilityMonitor:
    def __init__(self, master, config, save_callback, target_provider, capture_provider, language="KR"):
        had_group_orientation = isinstance(config, dict) and "warning_orientation" in config
        migrate_legacy_preset = bool(isinstance(config, dict) and config.get("_migrate_legacy_preset"))
        defaults = default_durability_config()
        self.config = defaults
        if isinstance(config, dict):
            self.config.update({k: v for k, v in config.items() if k not in {"parts", "_migrate_legacy_preset"}})
            for part, values in config.get("parts", {}).items():
                if part in self.config["parts"] and isinstance(values, dict):
                    self.config["parts"][part].update(values)
        self._normalize_presets(migrate_legacy_preset)
        if not had_group_orientation and self.config.get("warning_region"):
            region = list(self.config["warning_region"])
            center_x = (region[0] + region[2]) // 2
            width = max(24, region[2] - region[0])
            region[0] = center_x - (width * 3) // 2
            region[2] = region[0] + width * 3
            self.config["warning_region"] = region
        self.master = master
        self.save_callback = save_callback
        self.target_provider = target_provider
        self.capture_provider = capture_provider
        self.language = language if language in TEXTS else "KR"
        self.closed = False
        self.editing = False
        self.dialog = None
        self.dialog_offset = None
        self.dialog_dragging = False
        self.enabled_vars = {}
        self.threshold_vars = {}
        self.preview_labels = {}
        self.preset_buttons = []
        self.preset_name_dialog = None
        self.last_values = {part: None for part in PARTS}
        self.last_valid_at = {part: None for part in PARTS}
        self.preview_values = {part: None for part in PARTS}
        self.preview_valid_at = {part: None for part in PARTS}
        self.candidate_values = {part: None for part in PARTS}
        self.candidate_hits = {part: 0 for part in PARTS}
        self.ocr_future = None
        self.warning_sound_enabled = bool(self.config.get("warning_sound_enabled", False))
        self.warning_sound_volume = max(0, min(100, int(self.config.get("warning_sound_volume", 60))))
        self.warning_sound_lock = threading.Lock()
        self.warning_sound_low_parts = set()
        self.warning_sound_var = None
        self.warning_volume_scale = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="durability-ocr")
        self.ocr = PaddleOcrBackend(resource_path("ocr_models"))
        self.last_ocr_at = 0.0
        self.region_windows = {
            part: EditableRegion(master, PART_COLORS[part], lambda bbox, p=part: self._store_region(p, bbox), label=lambda: TEXTS[self.language]["move"])
            for part in PARTS
        }
        if not self.config.get("warning_region"):
            saved_regions = [
                values.get("warning_region") for values in self.config["parts"].values()
                if values.get("warning_region")
            ]
            if saved_regions:
                self.config["warning_region"] = [
                    min(region[0] for region in saved_regions), min(region[1] for region in saved_regions),
                    max(region[2] for region in saved_regions), max(region[3] for region in saved_regions),
                ]
                self.config["warning_reference_size"] = next(
                    (values.get("warning_reference_size") for values in self.config["parts"].values() if values.get("warning_reference_size")),
                    None,
                )
        self.warning_preview_image = None
        self.warning_sources = {
            part: warning_source_image(part) if warning_asset_path(part).exists() else None
            for part in PARTS
        }
        self.warning_editor = EditableRegion(
            master, GOLD, self._store_warning_region,
            label=lambda: TEXTS[self.language]["move"], action=self.toggle_warning_orientation,
        )
        self.warning_editor.content_drawer = self._draw_warning_editor
        self.warning_window = self._create_warning_window()
        self.warning_label = tk.Label(self.warning_window, bg="#ffffff", bd=0, highlightthickness=0)
        self.warning_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.warning_image = None
        self.warning_image_key = None
        self.warning_flash_phase = 0
        self.warning_suppressed_until = time.monotonic() + STARTUP_WARNING_GRACE_SECONDS
        self.warning_visible = False
        self.warning_last_bbox = None
        self.tick()

    def _normalize_presets(self, migrate_legacy=False):
        raw = self.config.get("presets")
        presets = []
        for index in range(4):
            fallback = empty_durability_preset(index)
            value = raw[index] if isinstance(raw, list) and index < len(raw) and isinstance(raw[index], dict) else {}
            name = valid_preset_name(value.get("name", fallback["name"])) or fallback["name"]
            parts = durability_preset_snapshot(value.get("parts", {}))
            presets.append({"name": name, "parts": parts})
        if migrate_legacy:
            presets[0]["parts"] = durability_preset_snapshot(self.config["parts"])
        self.config["presets"] = presets
        self.config["active_preset"] = max(0, min(3, int(self.config.get("active_preset", 0))))
        self._apply_preset_to_config(self.config["active_preset"])

    def _apply_preset_to_config(self, index):
        index = max(0, min(3, int(index)))
        self.config["active_preset"] = index
        for part, values in self.config["presets"][index]["parts"].items():
            self.config["parts"][part]["enabled"] = bool(values["enabled"])
            self.config["parts"][part]["threshold"] = max(0, int(values["threshold"]))

    def _form_snapshot(self):
        result = {}
        for part in PARTS:
            try:
                threshold = max(0, int(self.threshold_vars[part].get()))
            except (KeyError, ValueError):
                threshold = 0
            result[part] = {"enabled": bool(self.enabled_vars[part].get()), "threshold": threshold}
        return result

    def _refresh_preset_buttons(self):
        active = int(self.config.get("active_preset", 0))
        for index, button in enumerate(self.preset_buttons):
            button.configure(
                text=self.config["presets"][index]["name"],
                bg=GOLD if index == active else PANEL,
                fg=BG if index == active else TEXT,
                relief="sunken" if index == active else "flat",
            )

    def select_preset(self, index):
        self._apply_preset_to_config(index)
        for part in PARTS:
            values = self.config["parts"][part]
            self.enabled_vars[part].set(bool(values["enabled"]))
            self.threshold_vars[part].set(str(values["threshold"]))
        self._refresh_preset_buttons()
        self.save()

    def save_active_preset(self):
        index = int(self.config.get("active_preset", 0))
        snapshot = self._form_snapshot()
        self.config["presets"][index]["parts"] = snapshot
        for part, values in snapshot.items():
            self.config["parts"][part].update(values)
        self._refresh_preset_buttons()
        self.save()

    @property
    def monitoring_enabled(self):
        return bool(self.config.get("monitoring_enabled", True))

    def set_language(self, language):
        self.language = language if language in TEXTS else "KR"
        for editor in (*self.region_windows.values(), self.warning_editor):
            editor.last_draw_size = None
            editor._redraw()
        if self.dialog and self.dialog.winfo_exists():
            self.close_settings(save=False)
            self.open_settings()

    def _create_warning_window(self):
        win = tk.Toplevel(self.master)
        win.overrideredirect(True)
        win.attributes("-topmost", False)
        win.configure(bg="#ffffff")
        win.wm_attributes("-transparentcolor", "#ffffff")
        win.withdraw()
        win.update_idletasks()
        hwnd = user32.GetAncestor(win.winfo_id(), 2) or win.winfo_id()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT)
        return win

    def _draw_warning_editor(self, canvas, width, height, header_height):
        inner_width = max(1, width - 8)
        inner_height = max(1, height - header_height - 8)
        source = self._warning_group_composite(inner_width, inner_height, set(PARTS), preview=True)
        self.warning_preview_image = ImageTk.PhotoImage(source)
        canvas.delete("preview")
        image_center_y = header_height + (height - header_height) // 2
        canvas.create_image(width//2, image_center_y, image=self.warning_preview_image, anchor="center", tags="preview")

    def _client_rect(self):
        hwnd = self.target_provider()
        return hwnd, client_screen_rect(hwnd)

    def _target_or_owned_overlay_is_foreground(self, target_hwnd):
        """Allow capture only while Godius or one of its owned overlays is active."""
        foreground = user32.GetForegroundWindow()
        if not foreground or not target_hwnd:
            return False
        target_root = user32.GetAncestor(target_hwnd, GA_ROOT) or target_hwnd
        current = foreground
        visited = set()
        while current and current not in visited:
            visited.add(current)
            current_root = user32.GetAncestor(current, GA_ROOT) or current
            if current_root == target_root:
                return True
            current = user32.GetWindow(current_root, GW_OWNER)
        return False

    def _default_regions(self, rect):
        left, top, right, bottom = rect
        cx, cy = (left + right) // 2, (top + bottom) // 2
        return {
            "weapon": (cx - 150, cy - 55, cx - 80, cy - 25),
            "armor": (cx - 35, cy - 55, cx + 35, cy - 25),
            "shield": (cx + 80, cy - 55, cx + 150, cy - 25),
        }

    def _screen_bbox(self, values, reference, rect, fallback):
        if not values or len(values) != 4 or not reference or len(reference) != 2:
            return fallback
        left, top, right, bottom = rect
        sx = (right - left) / max(1, reference[0])
        sy = (bottom - top) / max(1, reference[1])
        return tuple(round(value * (sx if index % 2 == 0 else sy)) + (left if index % 2 == 0 else top) for index, value in enumerate(values))

    def _part_bbox(self, part, rect):
        part_config = self.config["parts"][part]
        return self._screen_bbox(part_config.get("region"), part_config.get("reference_size"), rect, self._default_regions(rect)[part])

    def _warning_bbox(self, rect):
        left, top, right, bottom = rect
        cx, cy = (left + right) // 2, (top + bottom) // 2
        horizontal = self.config.get("warning_orientation", "horizontal") == "horizontal"
        fallback = (cx - (150 if horizontal else 50), cy - (50 if horizontal else 150), cx + (150 if horizontal else 50), cy + (50 if horizontal else 150))
        return self._screen_bbox(self.config.get("warning_region"), self.config.get("warning_reference_size"), rect, fallback)

    def _relative_region(self, bbox, rect):
        left, top, right, bottom = rect
        return [bbox[0] - left, bbox[1] - top, bbox[2] - left, bbox[3] - top], [right - left, bottom - top]

    def _store_region(self, part, bbox):
        _hwnd, rect = self._client_rect()
        if not rect:
            return
        region, reference = self._relative_region(bbox, rect)
        self.config["parts"][part]["region"] = region
        self.config["parts"][part]["reference_size"] = reference

    def _store_warning_region(self, bbox):
        _hwnd, rect = self._client_rect()
        if not rect:
            return
        self.config["warning_region"], self.config["warning_reference_size"] = self._relative_region(bbox, rect)

    def toggle_warning_orientation(self):
        old = self.warning_editor.geometry()
        left, top, right, bottom = old
        cx, cy = (left + right) // 2, (top + bottom) // 2
        width, height = right - left, bottom - top
        orientation = self.config.get("warning_orientation", "horizontal")
        self.config["warning_orientation"] = "vertical" if orientation == "horizontal" else "horizontal"
        bbox = (cx - height // 2, cy - width // 2, cx + height // 2, cy + width // 2)
        self.warning_editor.show(bbox, self.target_provider())
        self._store_warning_region(bbox)

    def open_settings(self):
        if self.dialog and self.dialog.winfo_exists():
            hwnd, rect = self._client_rect()
            if hwnd and rect:
                self._sync_edit_windows(hwnd, rect)
            activate_modal(self.dialog)
            return
        hwnd, rect = self._client_rect()
        if not hwnd or not rect:
            return
        self.editing = True
        texts = TEXTS[self.language]
        win = tk.Toplevel(self.master)
        self.dialog = win
        win.overrideredirect(True)
        win.configure(bg=GOLD)
        panel = tk.Frame(win, bg=BG, padx=14, pady=12)
        panel.pack(fill="both", expand=True, padx=2, pady=2)
        header = tk.Frame(panel, bg=PANEL)
        header.pack(fill="x", pady=(0, 8))
        title_label = tk.Label(header, text=texts["title"], bg=PANEL, fg=GOLD, font=("Noto Sans KR", 12, "bold"), anchor="w", padx=12, pady=8)
        title_label.pack(side="left", fill="x", expand=True)
        sound_controls = tk.Frame(header, bg=PANEL)
        sound_controls.pack(side="right", padx=(4, 8))
        self.warning_sound_var = tk.BooleanVar(value=self.warning_sound_enabled)
        sound_check = tk.Checkbutton(
            sound_controls, text=texts["warning_sound"], variable=self.warning_sound_var,
            command=self._toggle_warning_sound, bg=PANEL, fg=TEXT,
            activebackground=PANEL, activeforeground=TEXT, selectcolor=BG,
            highlightthickness=0, bd=0,
        )
        sound_check.pack(side="left")
        self.warning_volume_scale = tk.Scale(
            sound_controls, from_=0, to=100, orient="horizontal", showvalue=False,
            length=90, bg=PANEL, fg=TEXT, troughcolor=BG, activebackground=GOLD,
            highlightthickness=0, bd=0, sliderlength=12,
        )
        self.warning_volume_scale.set(self.warning_sound_volume)
        self.warning_volume_scale.bind("<ButtonRelease-1>", self._save_warning_volume)
        if self.warning_sound_enabled:
            self.warning_volume_scale.pack(side="left", padx=(4, 0))
        drag_origin = {"value": None}
        def begin_dialog_drag(event):
            self.dialog_dragging = True
            drag_origin["value"] = (event.x_root, event.y_root, win.winfo_x(), win.winfo_y())
        def dialog_drag(event):
            if not drag_origin["value"]:
                return
            sx, sy, wx, wy = drag_origin["value"]
            win.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")
        def end_dialog_drag(_event):
            drag_origin["value"] = None
            self.dialog_dragging = False
            current = self._client_rect()[1]
            if current:
                self.dialog_offset = (win.winfo_x() - current[0], win.winfo_y() - current[1])
        for drag_widget in (header, title_label):
            drag_widget.configure(cursor="fleur")
            drag_widget.bind("<ButtonPress-1>", begin_dialog_drag)
            drag_widget.bind("<B1-Motion>", dialog_drag)
            drag_widget.bind("<ButtonRelease-1>", end_dialog_drag)
        grid = tk.Frame(panel, bg=BG)
        grid.pack(fill="x")
        for column, label in enumerate((texts["enabled"], "", texts["threshold"], texts["preview"])):
            tk.Label(grid, text=label, bg=BG, fg=MUTED, font=("Noto Sans KR", 9)).grid(row=0, column=column, padx=6, pady=3)
        for row, part in enumerate(PARTS, 1):
            values = self.config["parts"][part]
            enabled = tk.BooleanVar(value=bool(values.get("enabled", False)))
            threshold = tk.StringVar(value=str(max(0, int(values.get("threshold", 20)))))
            self.enabled_vars[part], self.threshold_vars[part] = enabled, threshold
            tk.Checkbutton(grid, variable=enabled, bg=BG, activebackground=BG, selectcolor=PANEL, fg=TEXT).grid(row=row, column=0, padx=6)
            tk.Label(grid, text=texts[part], bg=BG, fg=PART_COLORS[part], font=("Noto Sans KR", 10, "bold"), width=8, anchor="w").grid(row=row, column=1, padx=6, pady=5)
            tk.Entry(grid, textvariable=threshold, width=8, justify="center", bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="solid", bd=1).grid(row=row, column=2, padx=6)
            preview = tk.Label(grid, text=texts["unknown"], bg=PANEL, fg=TEXT, width=10, pady=4)
            preview.grid(row=row, column=3, padx=6)
            self.preview_labels[part] = preview
        tk.Label(panel, text=texts["hint"], bg=BG, fg=MUTED, wraplength=520, justify="left", anchor="w").pack(fill="x", pady=(10, 4))
        preset_row = tk.Frame(panel, bg=BG)
        preset_row.pack(fill="x", pady=(2, 8))
        preset_left = tk.Frame(preset_row, bg=BG)
        preset_left.pack(side="left")
        self.preset_buttons = []
        for index in range(4):
            button = tk.Button(
                preset_left, command=lambda current=index: self.select_preset(current),
                activebackground=GOLD, activeforeground=BG, relief="flat", bd=0,
                padx=10, pady=6, cursor="hand2", font=("Noto Sans KR", 9, "bold"),
            )
            button.pack(side="left", padx=(0, 4))
            self.preset_buttons.append(button)
        preset_right = tk.Frame(preset_row, bg=BG)
        preset_right.pack(side="right")
        tk.Button(
            preset_right, text=texts["preset_save"], command=self.save_active_preset,
            bg=PANEL_HOVER, fg=TEXT, activebackground=GOLD, activeforeground=BG,
            relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
        ).pack(side="left", padx=(0, 4))
        tk.Button(
            preset_right, text=texts["preset_names"], command=self.open_preset_name_dialog,
            bg=PANEL_HOVER, fg=TEXT, activebackground=GOLD, activeforeground=BG,
            relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
        ).pack(side="left")
        self._refresh_preset_buttons()
        help_ping_outer = tk.Frame(panel, bg=BG, padx=2, pady=2)
        help_ping_middle = tk.Frame(help_ping_outer, bg=BG, padx=2, pady=2)
        help_ping_inner = tk.Frame(help_ping_middle, bg=BG, padx=2, pady=2)
        help_ping_inner.pack(fill="x")
        help_ping_middle.pack(fill="x")
        help_button = tk.Button(
            help_ping_inner, text=texts["help_show"], bg=PANEL, fg=TEXT,
            activebackground=PANEL_HOVER, activeforeground="#ffffff",
            relief="flat", bd=0, pady=6, cursor="hand2",
        )
        help_button.pack(fill="x")
        help_ping_outer.pack(fill="x", pady=(4, 2))
        help_slot = tk.Frame(panel, bg=BG)
        help_content = tk.Frame(help_slot, bg=PANEL, padx=12, pady=10)
        example_path = resource_path("assets/durability/setup_example.png")
        if example_path.exists():
            try:
                with Image.open(example_path) as example_source:
                    example = example_source.convert("RGB")
                    example.thumbnail((500, 180), Image.Resampling.LANCZOS)
                help_image = ImageTk.PhotoImage(example)
                help_content._example_image = help_image
                tk.Label(help_content, image=help_image, bg=PANEL, bd=0).pack(pady=(0, 10))
            except OSError:
                pass
        tk.Label(
            help_content, text=texts["help_text"], bg=PANEL, fg=TEXT,
            wraplength=500, justify="left", anchor="w", font=("Noto Sans KR", 9),
        ).pack(fill="x")
        help_open = {"value": False}
        collapsed_size = {"width": None, "height": None}

        def resize_dialog_to_content():
            win.update_idletasks()
            desired_width = max(560, win.winfo_reqwidth())
            desired_height = win.winfo_reqheight()
            client_left, client_top, client_right, client_bottom = rect
            desired_height = min(desired_height, max(320, client_bottom - client_top - 16))
            current_x, current_y = win.winfo_x(), win.winfo_y()
            current_x = max(client_left, min(current_x, client_right - desired_width))
            current_y = max(client_top, min(current_y, client_bottom - desired_height))
            win.geometry(f"{desired_width}x{desired_height}+{current_x}+{current_y}")

        def toggle_help():
            help_open["value"] = not help_open["value"]
            if help_open["value"]:
                help_slot.pack(fill="x", after=help_ping_outer)
                help_content.pack(fill="x", pady=(4, 6))
                help_button.configure(text=texts["help_hide"])
            else:
                help_content.pack_forget()
                help_slot.pack_forget()
                help_button.configure(text=texts["help_show"])
            if help_open["value"]:
                resize_dialog_to_content()
            else:
                win.update_idletasks()
                width = collapsed_size["width"] or max(560, win.winfo_reqwidth())
                height = collapsed_size["height"] or win.winfo_reqheight()
                win.geometry(f"{width}x{height}+{win.winfo_x()}+{win.winfo_y()}")

        help_button.configure(command=toggle_help)

        ping_started = time.monotonic()
        ping_rings = (help_ping_inner, help_ping_middle, help_ping_outer)

        def animate_help_ping():
            if not self.dialog or not self.dialog.winfo_exists():
                return
            elapsed = time.monotonic() - ping_started
            if elapsed >= 3.0:
                for ring in ping_rings:
                    ring.configure(bg=BG)
                return
            phase = int(elapsed / 0.16)
            for index, ring in enumerate(ping_rings):
                distance = (phase - index) % 6
                ring.configure(
                    bg="#ff3030" if distance == 0 else "#b51f1f" if distance in (1, 2) else BG
                )
            win.after(80, animate_help_ping)

        win.after(120, animate_help_ping)
        tk.Label(panel, text=texts["warning1"], bg=BG, fg="#ffcf66", wraplength=520, justify="left", anchor="w").pack(fill="x", pady=2)
        tk.Label(panel, text=texts["warning2"], bg=BG, fg="#ff7777", font=("Noto Sans KR", 10, "bold"), anchor="w").pack(fill="x", pady=(2, 10))
        tk.Button(panel, text=texts["save"], command=self.close_settings, bg=PANEL_HOVER, fg=TEXT, activebackground=GOLD, relief="flat", bd=0, pady=7).pack(fill="x")
        win.update_idletasks()
        width, height = max(560, win.winfo_reqwidth()), win.winfo_reqheight()
        left, top, right, bottom = rect
        x, y = left + (right-left-width)//2, top + (bottom-top-height)//2
        win.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog_offset = (x - left, y - top)
        collapsed_size["width"], collapsed_size["height"] = width, height
        attach_above(win, hwnd, x, y)
        defaults = self._default_regions(rect)
        for part, region_window in self.region_windows.items():
            region_window.show(self._part_bbox(part, rect), hwnd)
        self.warning_editor.show(self._warning_bbox(rect), hwnd)

    def _sync_edit_windows(self, hwnd, rect):
        if self.dialog and self.dialog.winfo_exists() and not self.dialog_dragging:
            offset_x, offset_y = self.dialog_offset or (16, 16)
            attach_above(self.dialog, hwnd, rect[0] + offset_x, rect[1] + offset_y)
        for part, region_window in self.region_windows.items():
            if not region_window.drag:
                region_window.show(self._part_bbox(part, rect), hwnd)
        if not self.warning_editor.drag:
            self.warning_editor.show(self._warning_bbox(rect), hwnd)

    def open_preset_name_dialog(self):
        if self.preset_name_dialog and self.preset_name_dialog.winfo_exists():
            self.preset_name_dialog.lift()
            return
        hwnd, rect = self._client_rect()
        if not hwnd or not rect:
            return
        texts = TEXTS[self.language]
        win = tk.Toplevel(self.master)
        self.preset_name_dialog = win
        win.overrideredirect(True)
        win.configure(bg=GOLD)
        panel = tk.Frame(win, bg=BG, padx=14, pady=12)
        panel.pack(fill="both", expand=True, padx=2, pady=2)
        tk.Label(
            panel, text=texts["preset_name_title"], bg=PANEL, fg=GOLD,
            font=("Noto Sans KR", 11, "bold"), anchor="w", padx=12, pady=8,
        ).pack(fill="x", pady=(0, 10))
        variables = []
        form = tk.Frame(panel, bg=BG)
        form.pack(fill="x")

        def valid_name(proposed):
            if not proposed:
                return True
            return len(proposed) <= (6 if proposed.isascii() else 4)

        validation = (win.register(valid_name), "%P")
        for index, preset in enumerate(self.config["presets"]):
            tk.Label(form, text=f"Pre{index + 1}", bg=BG, fg=MUTED, width=7, anchor="w").grid(
                row=index, column=0, padx=(0, 8), pady=4,
            )
            variable = tk.StringVar(value=preset["name"])
            variables.append(variable)
            tk.Entry(
                form, textvariable=variable, width=18, bg=PANEL, fg=TEXT,
                insertbackground=TEXT, relief="solid", bd=1,
                validate="key", validatecommand=validation,
            ).grid(row=index, column=1, sticky="ew", pady=4)
        form.grid_columnconfigure(1, weight=1)
        tk.Label(
            panel, text=texts["preset_name_limit"], bg=BG, fg=MUTED,
            anchor="w", justify="left",
        ).pack(fill="x", pady=(8, 10))
        footer = tk.Frame(panel, bg=BG)
        footer.pack(fill="x")

        def close():
            if win.winfo_exists():
                try:
                    win.grab_release()
                except tk.TclError:
                    pass
                win.destroy()
            self.preset_name_dialog = None

        def save_names():
            for index, variable in enumerate(variables):
                fallback = f"Pre{index + 1}"
                self.config["presets"][index]["name"] = valid_preset_name(variable.get()) or fallback
            self._refresh_preset_buttons()
            self.save()
            close()

        tk.Button(
            footer, text=texts["preset_name_close"], command=close, bg=PANEL,
            fg=TEXT, activebackground=PANEL_HOVER, relief="flat", bd=0, padx=18, pady=7,
        ).pack(side="right")
        tk.Button(
            footer, text=texts["preset_name_save"], command=save_names, bg=PANEL_HOVER,
            fg=TEXT, activebackground=GOLD, relief="flat", bd=0, padx=18, pady=7,
        ).pack(side="right", padx=(0, 6))
        bind_modal_escape(win, close)
        win.update_idletasks()
        width, height = max(360, win.winfo_reqwidth()), win.winfo_reqheight()
        left, top, right, bottom = rect
        x, y = left + (right - left - width) // 2, top + (bottom - top - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
        attach_above(win, hwnd, x, y)
        win.grab_set()

    def close_settings(self, save=True):
        if not self.dialog:
            return
        if save:
            snapshot = self._form_snapshot()
            self.config["presets"][int(self.config.get("active_preset", 0))]["parts"] = snapshot
            for part, values in snapshot.items():
                self.config["parts"][part].update(values)
            self.save()
        self.editing = False
        for window in self.region_windows.values():
            window.hide()
        self.warning_editor.hide()
        self.dialog.destroy()
        self.dialog = None
        self.dialog_offset = None
        self.dialog_dragging = False
        self.enabled_vars.clear()
        self.threshold_vars.clear()
        self.preview_labels.clear()
        self.preset_buttons.clear()
        self.warning_sound_var = None
        self.warning_volume_scale = None
        if self.preset_name_dialog and self.preset_name_dialog.winfo_exists():
            self.preset_name_dialog.destroy()
        self.preset_name_dialog = None
        self.warning_window.withdraw()

    def toggle_monitoring(self):
        self.config["monitoring_enabled"] = not self.monitoring_enabled
        if not self.monitoring_enabled:
            self.warning_window.withdraw()
            self.warning_sound_low_parts.clear()
        self.save()

    def _toggle_warning_sound(self):
        self.warning_sound_enabled = bool(self.warning_sound_var and self.warning_sound_var.get())
        self.config["warning_sound_enabled"] = self.warning_sound_enabled
        if self.warning_volume_scale and self.warning_volume_scale.winfo_exists():
            if self.warning_sound_enabled:
                self.warning_volume_scale.pack(side="left", padx=(4, 0))
            else:
                self.warning_volume_scale.pack_forget()
        self.save()

    def _save_warning_volume(self, _event=None):
        if not self.warning_volume_scale:
            return
        self.warning_sound_volume = max(0, min(100, int(self.warning_volume_scale.get())))
        self.config["warning_sound_volume"] = self.warning_sound_volume
        self.save()
        self._play_warning_sound()

    def _play_warning_sound(self):
        if not self.warning_sound_enabled:
            return
        sound_path = resource_path("assets/warn.mp3")
        if not sound_path.is_file():
            return
        volume = self.warning_sound_volume

        def play():
            with self.warning_sound_lock:
                try:
                    send = ctypes.windll.winmm.mciSendStringW
                    send("close godinavi_durability", None, 0, None)
                    send(f'open "{sound_path}" type mpegvideo alias godinavi_durability', None, 0, None)
                    send(f"setaudio godinavi_durability volume to {volume * 10}", None, 0, None)
                    send("play godinavi_durability from 0", None, 0, None)
                except (AttributeError, OSError):
                    return

        threading.Thread(target=play, name="godinavi-durability-sound", daemon=True).start()

    def _update_warning_sound(self):
        reached = self._numeric_threshold_parts()
        if reached - self.warning_sound_low_parts:
            self._play_warning_sound()
        self.warning_sound_low_parts = reached

    def _numeric_threshold_parts(self):
        return {
            part for part in PARTS
            if self.config["parts"][part].get("enabled", False)
            and self.last_values[part] is not None
            and self.last_values[part] <= int(self.config["parts"][part].get("threshold", 0))
        }

    def save(self):
        if self.save_callback:
            self.save_callback(self.config)

    def _prepare_capture_variants(self, image):
        def white_digit_mask(core_min, candidate_min, core_chroma, candidate_chroma):
            rgb = image.convert("RGB")
            red, green, blue = rgb.split()
            minimum = ImageChops.darker(ImageChops.darker(red, green), blue)
            maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
            chroma = ImageChops.subtract(maximum, minimum)
            core = ImageChops.multiply(
                minimum.point(lambda value: 255 if value >= core_min else 0),
                chroma.point(lambda value: 255 if value <= core_chroma else 0),
            )
            candidates = ImageChops.multiply(
                minimum.point(lambda value: 255 if value >= candidate_min else 0),
                chroma.point(lambda value: 255 if value <= candidate_chroma else 0),
            )
            connected = core
            # Preserve only anti-aliased gray pixels immediately connected to
            # a genuinely white digit core. Colored scenery behind the game's
            # translucent black panel therefore never grows into the glyph.
            for _ in range(3):
                connected = ImageChops.multiply(candidates, connected.filter(ImageFilter.MaxFilter(3)))
            enlarged = connected.resize(
                (connected.width * max(4, min(7, 210 // max(1, connected.height))),
                 connected.height * max(4, min(7, 210 // max(1, connected.height)))),
                Image.Resampling.NEAREST,
            )
            return enlarged.convert("RGB")

        gray = ImageOps.grayscale(image)
        scale = max(3, min(6, 180 // max(1, gray.height)))
        enlarged = ImageOps.autocontrast(
            gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.NEAREST)
        )
        threshold = enlarged.point(lambda value: 255 if value >= 145 else 0)
        return (
            white_digit_mask(215, 145, 35, 55),
            white_digit_mask(235, 175, 22, 42),
            enlarged.convert("RGB"),
            threshold.convert("RGB"),
            ImageOps.invert(threshold).convert("RGB"),
        )

    @staticmethod
    def _needs_digit_validation(value, baseline, part=None):
        digits = str(value)
        baseline_digits = "" if baseline is None else str(baseline)
        ambiguous = "1" in digits or "7" in digits or "1" in baseline_digits or "7" in baseline_digits
        if baseline is None:
            return ambiguous
        allowed_change = (
            11 if part in {"armor", "shield"} and value < baseline
            else MAX_DURABILITY_CHANGE_PER_READING
        )
        return value != baseline and (ambiguous or abs(value - baseline) > allowed_change)

    @staticmethod
    def _consensus_value(values):
        values = [value for value in values if value is not None]
        if not values:
            return None
        value, hits = Counter(values).most_common(1)[0]
        return value if hits >= 2 else None

    def _recognize_images(self, images):
        results = {}
        for part, image in images.items():
            try:
                variants = self._prepare_capture_variants(image)
                primary = recognized_integer(self.ocr.recognize(variants[0], "en"))
                baseline = getattr(self, "last_values", {}).get(part)
                needs_validation = primary is None or self._needs_digit_validation(primary, baseline, part)
                if primary is not None and not needs_validation:
                    results[part] = primary
                    continue
                readings = [primary]
                for prepared in variants[1:]:
                    readings.append(recognized_integer(self.ocr.recognize(prepared, "en")))
                if needs_validation:
                    final = self._consensus_value(readings)
                else:
                    final = primary
                if final is None and primary is None:
                    final = next(
                        (
                            value for value in readings[1:]
                            if value is not None and not self._needs_digit_validation(value, baseline)
                        ),
                        None,
                    )
                # An ambiguous disagreement is safer as a temporary miss; the
                # existing five-second hold keeps the last valid durability on
                # screen instead of accepting scenery-dependent garbage.
                results[part] = final
            except Exception:
                results[part] = None
        return results

    def _begin_ocr(self, rect):
        images = {}
        client_left, client_top, client_right, client_bottom = rect
        try:
            client_capture = self.capture_provider(rect)
        except Exception:
            return
        if client_capture is None:
            return
        client_capture = client_capture.convert("RGB")
        for part in PARTS:
            enabled = self.config["parts"][part].get("enabled", False) or self.editing
            if not enabled:
                continue
            bbox = self._part_bbox(part, rect)
            try:
                left, top, right, bottom = bbox
                crop_box = (
                    max(0, left - client_left),
                    max(0, top - client_top),
                    min(client_capture.width, right - client_left),
                    min(client_capture.height, bottom - client_top),
                )
                if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                    image = client_capture.crop(crop_box)
                    # During calibration Desktop Duplication also captures our
                    # own colored guide border and bottom-right resize grip.
                    # Remove only that known editor chrome so the debug input
                    # matches the unobstructed image used during normal play.
                    if self.editing:
                        image = self._without_editor_chrome(image)
                    images[part] = image
            except Exception:
                images[part] = None
        images = {part: image for part, image in images.items() if image is not None}
        if images:
            self.ocr_future = self.executor.submit(self._recognize_images, images)

    @staticmethod
    def _without_editor_chrome(image):
        image = image.convert("RGB")
        width, height = image.size
        if width <= EDITOR_BORDER_WIDTH * 2 or height <= EDITOR_BORDER_WIDTH * 2:
            return image

        cleaned = image.copy()
        draw = ImageDraw.Draw(cleaned)
        border = EDITOR_BORDER_WIDTH
        draw.rectangle((0, 0, width - 1, border - 1), fill="black")
        draw.rectangle((0, height - border, width - 1, height - 1), fill="black")
        draw.rectangle((0, 0, border - 1, height - 1), fill="black")
        draw.rectangle((width - border, 0, width - 1, height - 1), fill="black")

        grip = min(EDITOR_RESIZE_GRIP_SIZE, width, height)
        draw.polygon(
            ((width - grip, height - 1), (width - 1, height - grip), (width - 1, height - 1)),
            fill="black",
        )
        return cleaned

    def _accept_results(self, results, now):
        texts = TEXTS[self.language]
        for part in PARTS:
            value = results.get(part)
            if value is not None:
                self.preview_values[part] = value
                self.preview_valid_at[part] = now
                current = self.last_values[part]
                if current is not None:
                    allowed_change = (
                        11 if part in {"armor", "shield"} and value < current
                        else MAX_DURABILITY_CHANGE_PER_READING
                    )
                    if abs(value - current) <= allowed_change:
                        self.last_values[part] = value
                        self.last_valid_at[part] = now
                        self.candidate_values[part] = None
                        self.candidate_hits[part] = 0
                    else:
                        if self.candidate_values[part] == value:
                            self.candidate_hits[part] += 1
                        else:
                            self.candidate_values[part] = value
                            self.candidate_hits[part] = 1
                        if self.candidate_hits[part] >= OCR_VALUE_CONFIRMATIONS:
                            self.last_values[part] = value
                            self.last_valid_at[part] = now
                            self.candidate_values[part] = None
                            self.candidate_hits[part] = 0
                else:
                    if self.candidate_values[part] == value:
                        self.candidate_hits[part] += 1
                    else:
                        self.candidate_values[part] = value
                        self.candidate_hits[part] = 1
                    if self.candidate_hits[part] >= OCR_VALUE_CONFIRMATIONS:
                        self.last_values[part] = value
                        self.last_valid_at[part] = now
            else:
                self.candidate_values[part] = None
                self.candidate_hits[part] = 0
                if self.last_valid_at[part] is None or now - self.last_valid_at[part] >= OCR_VALUE_HOLD_SECONDS:
                    self.last_values[part] = None
            if part in self.preview_labels:
                preview_value = self.preview_values[part]
                if (
                    preview_value is not None
                    and self.preview_valid_at[part] is not None
                    and now - self.preview_valid_at[part] >= OCR_VALUE_HOLD_SECONDS
                ):
                    preview_value = None
                self.preview_labels[part].configure(
                    text=str(preview_value) if preview_value is not None else texts["unknown"]
                )

    def _low_parts(self):
        threshold_parts = self._numeric_threshold_parts()
        return [
            part for part in PARTS
            if (
            self.config["parts"][part].get("enabled", False)
            and (
                self.last_values[part] is None
                or self.last_values[part] <= 10
                or part in threshold_parts
            )
            )
        ]

    def _low_durability(self):
        return bool(self._low_parts())

    def _status_panel(self, canvas, icon_box, low_parts, preview=False):
        icon_x, icon_y, icon_right, icon_bottom = icon_box
        display_parts = list(PARTS) if preview else [
            part for part in PARTS if self.config["parts"][part].get("enabled", False)
        ]
        if not display_parts:
            return
        font_size = max(8, min(26, round(min(icon_right-icon_x, icon_bottom-icon_y) * 0.09)))
        max_panel_width = max(1, icon_right - icon_x - 8)
        while font_size > 7:
            font = ui_font(font_size)
            texts = [
                f"{TEXTS[self.language][part]} : {'XX' if preview else self.last_values[part] if self.last_values[part] is not None else 'XX'}"
                for part in display_parts
            ]
            widths = [ImageDraw.Draw(canvas).textbbox((0, 0), text, font=font, stroke_width=1)[2] for text in texts]
            padding = max(4, font_size // 2)
            if max(widths, default=0) + padding * 2 <= max_panel_width:
                break
            font_size -= 1
        font = ui_font(font_size)
        padding = max(4, font_size // 2)
        line_gap = max(2, font_size // 5)
        draw = ImageDraw.Draw(canvas)
        boxes = [draw.textbbox((0, 0), text, font=font, stroke_width=1) for text in texts]
        text_width = max((box[2] - box[0] for box in boxes), default=1)
        line_height = max((box[3] - box[1] for box in boxes), default=font_size)
        panel_width = min(max_panel_width, text_width + padding * 2)
        panel_height = line_height * len(texts) + line_gap * max(0, len(texts)-1) + padding * 2
        x = icon_x + max(4, round((icon_right-icon_x) * 0.04))
        y = icon_y + max(4, round((icon_bottom-icon_y) * 0.04))
        panel_height = min(panel_height, max(1, icon_bottom - y - 3))
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle(
            (x, y, x + panel_width, y + panel_height),
            radius=max(4, font_size // 2), fill=(0, 0, 0, 165),
        )
        canvas.alpha_composite(overlay)
        draw = ImageDraw.Draw(canvas)
        text_y = y + padding
        for part, text in zip(display_parts, texts):
            color = (255, 90, 80, 255) if preview or part in low_parts else (255, 241, 201, 255)
            draw.text(
                (x + padding, text_y), text, font=font, fill=color,
                stroke_width=1, stroke_fill=(0, 0, 0, 220), anchor="la",
            )
            text_y += line_height + line_gap

    def _warning_composite(self, part, width, height, value):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        source = self.warning_sources.get(part)
        if source is None:
            return canvas
        icon = fit_image(source, max(1, width - 4), max(1, height - 4))
        icon_x, icon_y = (width - icon.width) // 2, (height - icon.height) // 2
        canvas.alpha_composite(icon, (icon_x, icon_y))
        text = str(value)
        draw = ImageDraw.Draw(canvas)
        max_text_width = max(1, int(icon.width * 0.8))
        max_text_height = max(1, int(icon.height * 0.55))
        font = ImageFont.load_default()
        for size in range(max(12, int(icon.height * 0.38)), 5, -1):
            try:
                candidate = ImageFont.truetype("segoeuib.ttf", size)
            except OSError:
                break
            box = draw.multiline_textbbox((0, 0), text, font=candidate, spacing=0, align="center")
            if box[2] - box[0] <= max_text_width and box[3] - box[1] <= max_text_height:
                font = candidate
                break
        box = draw.multiline_textbbox((0, 0), text, font=font, spacing=0, align="center")
        x = (width - (box[2] - box[0])) / 2 - box[0]
        y = (height - (box[3] - box[1])) / 2 - box[1]
        draw.multiline_text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 210), spacing=0, align="center")
        text_color = (
            (255, 223, 125, 255)
            if value == "XX"
            else check_equipment_text_color(getattr(self, "warning_flash_phase", 0))
        )
        draw.multiline_text((x, y), text, font=font, fill=text_color, spacing=0, align="center")
        return canvas

    def _warning_group_composite(self, width, height, low_parts, preview=False):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        horizontal = self.config.get("warning_orientation", "horizontal") == "horizontal"
        slot_width = width // 3 if horizontal else width
        slot_height = height if horizontal else height // 3
        for index, part in enumerate(PARTS):
            if not preview and part not in low_parts:
                continue
            if preview:
                value = "XX"
            elif self.last_values[part] is None or self.last_values[part] <= 10:
                value = TEXTS[self.language]["check_equipment"]
            else:
                value = self.last_values[part]
            icon = self._warning_composite(part, slot_width, slot_height, value)
            x = index * slot_width if horizontal else 0
            y = 0 if horizontal else index * slot_height
            canvas.alpha_composite(icon, (x, y))
        return canvas

    def _render_warning(self, rect, now):
        if self.editing:
            self.warning_window.withdraw()
            self.warning_visible = False
            return
        if now < getattr(self, "warning_suppressed_until", 0):
            self.warning_window.withdraw()
            self.warning_visible = False
            return
        hwnd = self.target_provider()
        low_parts = set(self._low_parts())
        self._update_warning_sound()
        if not low_parts:
            self.warning_window.withdraw()
            self.warning_visible = False
            return
        bbox = self._warning_bbox(rect)
        left, top, right, bottom = bbox
        width, height = max(24, right-left), max(24, bottom-top)
        self.warning_window.geometry(f"{width}x{height}+{left}+{top}")
        self.warning_flash_phase = int(now / WARNING_FLASH_INTERVAL_SECONDS) % 2
        image_key = (
            width, height, self.config.get("warning_orientation"), tuple(sorted(low_parts)),
            tuple((part, self.last_values[part]) for part in PARTS),
            self.warning_flash_phase,
        )
        if self.warning_image is None or self.warning_image_key != image_key:
            self.warning_image = ImageTk.PhotoImage(self._warning_group_composite(width, height, low_parts))
            self.warning_image_key = image_key
        self.warning_label.configure(image=self.warning_image, text="")
        if hwnd and (not self.warning_visible or self.warning_last_bbox != bbox):
            attach_above(self.warning_window, hwnd, left, top)
            self.warning_visible = True
            self.warning_last_bbox = bbox

    def tick(self):
        if self.closed:
            return
        hwnd, rect = self._client_rect()
        now = time.monotonic()
        if not hwnd or not rect or user32.IsIconic(hwnd):
            self.warning_window.withdraw()
            self.warning_visible = False
        else:
            if self.editing:
                self._sync_edit_windows(hwnd, rect)
            if self.ocr_future and self.ocr_future.done():
                try:
                    self._accept_results(self.ocr_future.result(), now)
                except Exception:
                    pass
                self.ocr_future = None
            capture_allowed = self._target_or_owned_overlay_is_foreground(hwnd)
            if (
                (self.monitoring_enabled or self.editing)
                and capture_allowed
                and not self.ocr_future
                and now - self.last_ocr_at >= 0.7
            ):
                self.last_ocr_at = now
                self._begin_ocr(rect)
            if self.monitoring_enabled or self.editing:
                self._render_warning(rect, now)
            else:
                self.warning_window.withdraw()
        try:
            self.master.after(100, self.tick)
        except tk.TclError:
            self.closed = True

    def quit(self):
        if self.closed:
            return
        self.closed = True
        if self.dialog:
            self.close_settings()
        self.executor.shutdown(wait=False, cancel_futures=True)
        for window in self.region_windows.values():
            window.destroy()
        self.warning_editor.destroy()
        self.warning_window.destroy()

import ctypes
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

from PIL import Image

try:
    import pystray
except ImportError:
    pystray = None

from map_engine import BUNDLE_DIR, CONFIG_PATH, RESOURCE_DIR, MapEngine, save_config

from .actions import DockItem, QuickAction
from .app_update_ui import AppUpdateUI
from .buff_timer_engine import BuffTimerApp, default_buff_config
from .dock import OverlayDock
from .durability_monitor import DurabilityMonitor, default_durability_config
from .map_update_ui import MapUpdateUI
from .window_attachment import attach_above, client_screen_rect, find_godius_window, is_minimized


ICON_DIR = BUNDLE_DIR / "assets" / "icons" / "godinavi"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GD-fandev.GodiNavi")
except Exception:
    pass


def onboarding_required(config_exists: bool, config: dict) -> bool:
    return not config_exists or bool(config.get("onboarding_pending", False))


def default_dock_offset(client_width: int, client_height: int, bar_width: int, bar_height: int) -> tuple[int, int]:
    margin = 24
    return (
        max(0, min(margin, client_width - bar_width)),
        max(0, client_height - bar_height - margin),
    )

DOCK_TEXTS = {
    "KR": {
        "map": "지도", "map_adjust": "지도 위치·크기 조절", "ocr_edit": "OCR 영역 편집", "world_map": "월드맵 열기 (F10)",
        "portal": "포탈", "portal_edit": "포탈 장소 편집", "preset": "프리셋 전환", "portal_bar": "포탈 바 표시/숨김",
        "buff": "버프 타이머", "buff_region": "버프 인식 영역 편집", "buff_toggle": "타이머 표시/숨김", "buff_size": "버프 창 조정",
        "durability": "내구도 감시", "durability_settings": "내구도 감시 설정", "durability_toggle": "내구도 감시 On/Off",
        "settings": "기타 설정", "button_ui": "버튼 UI 설정", "orientation": "가로/세로 전환", "quit": "종료",
        "map_update": "지도 데이터 업데이트", "map_update_available": "지도 업데이트 가능 ↓",
        "app_update": "GodiNavi 업데이트", "app_update_available": "GodiNavi 업데이트 가능 ↓",
    },
    "JP": {
        "map": "地図", "map_adjust": "地図の位置・サイズ調整", "ocr_edit": "OCR領域を編集", "world_map": "ワールドマップを開く (F10)",
        "portal": "ポータル", "portal_edit": "ポータル地点を編集", "preset": "プリセット切替", "portal_bar": "ポータルバー 表示/非表示",
        "buff": "バフタイマー", "buff_region": "バフ認識領域を編集", "buff_toggle": "タイマー 表示/非表示", "buff_size": "バフ画面調整",
        "durability": "耐久度監視", "durability_settings": "耐久度監視設定", "durability_toggle": "耐久度監視 On/Off",
        "settings": "設定", "button_ui": "ボタンUI設定", "orientation": "横/縦を切替", "quit": "終了",
        "map_update": "マップデータ更新", "map_update_available": "マップ更新あり ↓",
        "app_update": "GodiNaviアップデート", "app_update_available": "GodiNavi更新あり ↓",
    },
    "EN": {
        "map": "Map", "map_adjust": "Adjust map position/size", "ocr_edit": "Edit OCR region", "world_map": "Open world map (F10)",
        "portal": "Portal", "portal_edit": "Edit portal locations", "preset": "Switch preset", "portal_bar": "Show/hide portal bar",
        "buff": "Buff Timer", "buff_region": "Edit buff detection region", "buff_toggle": "Show/hide timer", "buff_size": "Adjust buff window",
        "durability": "Durability Monitor", "durability_settings": "Durability settings", "durability_toggle": "Durability monitor On/Off",
        "settings": "Settings", "button_ui": "Button UI settings", "orientation": "Switch horizontal/vertical", "quit": "Quit",
        "map_update": "Map data update", "map_update_available": "Map update available ↓",
        "app_update": "GodiNavi update", "app_update_available": "GodiNavi update available ↓",
    },
}


class PrototypeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.tray_icon = None
        self.dock: OverlayDock | None = None
        self.map_update_ui: MapUpdateUI | None = None
        self.app_update_ui: AppUpdateUI | None = None
        new_install = not CONFIG_PATH.exists()
        self.map_engine: MapEngine | None = MapEngine(
            master=self.root,
            shell_mode=True,
            on_calibration_confirmed=self._complete_onboarding,
        )
        self.onboarding_pending = onboarding_required(not new_install, self.map_engine.config)
        self.onboarding_started = False
        if self.onboarding_pending:
            self.map_engine.config["onboarding_pending"] = True
            self.map_engine.config["onboarding_complete"] = False
            self.map_engine.config["minimap_enabled"] = False
            self.map_engine.config["favorite_overlay_visible"] = False
            self.map_engine.minimap_enabled = False
            save_config(self.map_engine.config)
        buff_config = default_buff_config()
        saved_buff_config = self.map_engine.config.get("buff_timer", {})
        if isinstance(saved_buff_config, dict):
            buff_config.update(saved_buff_config)
        buff_config["process_name"] = self.map_engine.config.get("process_name", "Godius.exe")
        buff_config["window_title"] = self.map_engine.config.get("window_title", "Godius Client")
        buff_config["ui_language"] = self.map_engine.ui_language
        buff_config["allow_timer_visibility_toggle"] = True
        if self.onboarding_pending:
            buff_config["timer_visible"] = False
        self.buff_timer = BuffTimerApp(
            self.root,
            buff_config,
            self._save_buff_config,
            on_calibration_confirmed=self._start_map_onboarding,
        )
        self.target_hwnd = None
        self.client_rect = None
        durability_config = default_durability_config()
        saved_durability_config = self.map_engine.config.get("durability_monitor", {})
        if isinstance(saved_durability_config, dict):
            durability_config.update(saved_durability_config)
        self.durability_monitor = DurabilityMonitor(
            self.root,
            durability_config,
            self._save_durability_config,
            lambda: self.target_hwnd,
            self.buff_timer.capture_client_frame,
            self.map_engine.ui_language,
        )
        saved_x = self.map_engine.config.get("dock_offset_x")
        saved_y = self.map_engine.config.get("dock_offset_y")
        self.dock_offset: tuple[int, int] | None = (
            (int(saved_x), int(saved_y)) if saved_x is not None and saved_y is not None else None
        )
        self.items = self._create_items()
        self.dock = OverlayDock(
            self.root,
            self.items,
            on_orientation_changed=self._orientation_changed,
            on_moved=self._remember_position,
            on_scale_changed=self._scale_changed,
            on_collapsed_changed=self._collapsed_changed,
            initial_orientation=self.map_engine.config.get("dock_orientation", "horizontal"),
            initial_icon_scale=self.map_engine.config.get("dock_icon_scale", 1.0),
            initial_collapsed=self.map_engine.config.get("dock_collapsed", False),
            initial_ui_language=self.map_engine.ui_language,
        )
        self.map_update_ui = MapUpdateUI(
            self.root,
            RESOURCE_DIR,
            lambda: self.map_engine.ui_language if self.map_engine else "EN",
            self._map_update_state_changed,
            self._map_update_installed,
        )
        self.app_update_ui = AppUpdateUI(
            self.root,
            RESOURCE_DIR,
            lambda: self.map_engine.ui_language if self.map_engine else "EN",
            self._app_update_state_changed,
            self.shutdown,
        )
        self._start_tray_icon()
        self.root.after(100, self._follow_godius)
        self.root.after(3000, lambda: self.map_update_ui.check(False) if self.map_update_ui else None)
        self.root.after(4500, lambda: self.app_update_ui.check(False) if self.app_update_ui else None)

    def _start_tray_icon(self):
        if pystray is None:
            return
        icon_path = ICON_DIR.parent / "Godius_104.png"
        try:
            image = Image.open(icon_path).convert("RGBA")
        except OSError:
            return
        language = self.map_engine.ui_language if self.map_engine else "KR"
        exit_label = {"KR": "종료", "JP": "終了", "EN": "Exit"}.get(language, "Exit")

        def request_exit(_icon=None, _item=None):
            try:
                self.root.after(0, self.shutdown)
            except (tk.TclError, RuntimeError):
                pass

        self.tray_icon = pystray.Icon(
            "GodiNavi", image, "GodiNavi",
            menu=pystray.Menu(pystray.MenuItem(exit_label, request_exit)),
        )
        self.tray_icon.run_detached()

    def message(self, text: str, duration: int = 1600):
        if self.dock:
            self.dock.set_message(text, duration)

    def open_map_update(self):
        if self.map_update_ui:
            self.map_update_ui.open()
            if self.map_update_ui.state in ("idle", "latest", "installed", "error"):
                self.map_update_ui.check(False)

    def _map_update_state_changed(self):
        if self.dock:
            self.items = self._create_items()
            self.dock.set_items(self.items)

    def _map_update_installed(self):
        if self.map_engine:
            self.map_engine.reload_map_database_if_changed()

    def open_app_update(self):
        if self.app_update_ui:
            self.app_update_ui.open()
            if self.app_update_ui.state in ("idle", "latest", "error", "missing"):
                self.app_update_ui.check(False)

    def _app_update_state_changed(self):
        if self.dock:
            self.items = self._create_items()
            self.dock.set_items(self.items)

    def placeholder(self, feature: str):
        return lambda: self.message(f"{feature} · 기존 엔진 연결 예정")

    def toggle_minimap(self):
        if not self.map_engine:
            return
        visible = self.map_engine.toggle_minimap()
        detecting = visible and not self.map_engine.active_map
        if detecting:
            text = {
                "KR": "미니맵 ON · 지도 인식 중…",
                "JP": "ミニマップ ON・マップ認識中…",
                "EN": "Minimap ON · Detecting map…",
            }[self.map_engine.ui_language]
        else:
            text = {
                "KR": "미니맵 ON" if visible else "미니맵 OFF",
                "JP": "ミニマップ ON" if visible else "ミニマップ OFF",
                "EN": "Minimap ON" if visible else "Minimap OFF",
            }[self.map_engine.ui_language]
        self.message(text, 2400 if detecting else 1600)

    def toggle_world_map(self):
        if self.map_engine:
            self.map_engine.toggle_world_map()

    def toggle_map_adjustment(self):
        if self.map_engine:
            self.map_engine.toggle_map_resize_mode()

    def toggle_map_calibration(self):
        if self.map_engine:
            self.map_engine.toggle_calibration()

    def open_portal_editor(self):
        if self.map_engine:
            self.map_engine.open_favorite_dialog()

    def toggle_portal_bar(self):
        if self.map_engine:
            self.map_engine.toggle_favorite_overlay()

    def portal_bar_visible(self):
        return bool(
            self.map_engine
            and self.map_engine.config.get("favorite_overlay_visible")
        )

    def cycle_portal_preset(self):
        if self.map_engine:
            index = self.map_engine.cycle_favorite_preset()
            numeral = ("I", "II", "III", "IV")[index]
            self.message(f"포탈 프리셋 {numeral}")

    def cycle_language(self):
        if not self.map_engine:
            return
        self.map_engine.cycle_locale()
        if self.buff_timer:
            self.buff_timer.set_ui_language(self.map_engine.ui_language)
        self.durability_monitor.set_language(self.map_engine.ui_language)
        if self.dock:
            self.dock.set_ui_language(self.map_engine.ui_language)
            self.items = self._create_items()
            self.dock.set_items(self.items)
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
            self._start_tray_icon()
        language_name = {"KR": "한국어", "JP": "日本語", "EN": "English"}[self.map_engine.ui_language]
        self.message(f"언어: {language_name}")

    def current_language_name(self):
        return "🌐 LANGUAGE"

    def shutdown(self):
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.durability_monitor.quit()
        if self.buff_timer and not self.buff_timer.closed:
            self.buff_timer.quit_app()
        if self.map_engine and not self.map_engine.closed:
            self.map_engine.quit()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _start_onboarding(self):
        if not self.onboarding_pending or self.buff_timer.calibration_mode:
            return
        self.buff_timer.config["detect_coordinate_origin"] = "client"
        self.buff_timer.config["detect_region"] = [0, 0, 40, 40]
        self.buff_timer.toggle_calibration_mode()
        self.root.after(60, self._position_initial_buff_region)

    def _position_initial_buff_region(self):
        if not self.buff_timer.calibration_mode or not self.client_rect:
            return
        guide = self.buff_timer.calibration_guide_window
        guide.update_idletasks()
        left, top, right, bottom = self.client_rect
        screen_x = max(left + 24, min(guide.winfo_x() + 24, right - 24))
        screen_y = max(top + 24, min(guide.winfo_y() + 24, bottom - 24))
        self.buff_timer.calibrate_region_at_screen_point(screen_x, screen_y)
        self.buff_timer.update_region_window()

    def _start_map_onboarding(self):
        if self.buff_timer and not self.buff_timer.timer_visible:
            self.buff_timer.toggle_timer_visibility()
        if not self.onboarding_pending or not self.map_engine:
            return
        if not self.map_engine.calibration_mode:
            self.map_engine.toggle_calibration()
        self.root.after(60, self._position_initial_map_regions)

    def _position_initial_map_regions(self):
        engine = self.map_engine
        if not engine or not engine.calibration_mode:
            return
        client = engine.get_stable_client_rect()
        if not client:
            self.root.after(100, self._position_initial_map_regions)
            return
        guide = engine.ocr_guide_window
        guide.update_idletasks()
        cl, ct, cr, cb = client
        name_width, coordinate_width, region_height = 280, 140, 42
        x = max(cl, min(guide.winfo_x() + 18, cr - name_width))
        name_y = max(ct, min(guide.winfo_y() - 98, cb - region_height * 2 - 8))
        coordinate_y = max(ct, min(name_y + region_height + 8, cb - region_height))
        engine.capture_bboxes["name"] = (x, name_y, x + name_width, name_y + region_height)
        engine.capture_bboxes["coordinates"] = (
            x,
            coordinate_y,
            x + coordinate_width,
            coordinate_y + region_height,
        )
        for kind in ("name", "coordinates"):
            engine.store_bbox(engine.capture_bboxes[kind], kind)
        engine.update_region_windows()

    def _complete_onboarding(self):
        if not self.map_engine:
            return
        if not self.map_engine.minimap_enabled:
            self.map_engine.toggle_minimap()
        if not self.onboarding_pending:
            return
        self.onboarding_pending = False
        self.map_engine.config["onboarding_pending"] = False
        self.map_engine.config["onboarding_complete"] = True
        save_config(self.map_engine.config)
        self.message({"KR": "초기 설정 완료", "JP": "初期設定完了", "EN": "Initial setup complete"}[self.map_engine.ui_language])

    def _save_buff_config(self, config):
        if not self.map_engine:
            return
        self.map_engine.config["buff_timer"] = dict(config)
        save_config(self.map_engine.config)

    def _save_durability_config(self, config):
        if not self.map_engine:
            return
        self.map_engine.config["durability_monitor"] = dict(config)
        save_config(self.map_engine.config)

    def toggle_durability_monitor(self):
        self.durability_monitor.toggle_monitoring()

    def open_durability_settings(self):
        self.durability_monitor.open_settings()

    def toggle_buff_timer(self):
        if self.buff_timer:
            self.buff_timer.toggle_timer_visibility()

    def toggle_buff_region(self):
        if self.buff_timer:
            self.buff_timer.toggle_calibration_mode()

    def toggle_buff_size(self):
        if not self.buff_timer:
            return
        editing = self.buff_timer.toggle_timer_resize_mode()
        language = self.map_engine.ui_language if self.map_engine else "KR"
        message = {
            "KR": "휠로 크기 조절 · 드래그로 이동 · 다시 누르면 저장" if editing else "버프 창 위치·크기 저장 완료",
            "JP": "ホイールでサイズ調整・ドラッグで移動・再クリックで保存" if editing else "バフ画面の位置・サイズを保存しました",
            "EN": "Wheel to resize · Drag to move · Click again to save" if editing else "Buff window position and size saved",
        }[language]
        self.message(message, 3000)

    def _create_items(self) -> list[DockItem]:
        texts = DOCK_TEXTS[self.map_engine.ui_language if self.map_engine else "KR"]
        update_available = bool(self.map_update_ui and self.map_update_ui.update_available)
        map_actions = [
            QuickAction(texts["map_adjust"], self.toggle_map_adjustment),
            QuickAction(texts["ocr_edit"], self.toggle_map_calibration),
            QuickAction(texts["world_map"], self.toggle_world_map),
        ]
        if update_available:
            map_actions.append(QuickAction(texts["map_update_available"], self.open_map_update))
        return [
            DockItem(
                "map", "🗺", texts["map"], self.toggle_minimap,
                tuple(map_actions),
                str(ICON_DIR / "map.jpg"),
                state=lambda: bool(self.map_engine and self.map_engine.minimap_enabled),
                alert=lambda: "↓" if self.map_update_ui and self.map_update_ui.update_available else "",
            ),
            DockItem(
                "portal", "◈", texts["portal"], self.toggle_portal_bar,
                (QuickAction(texts["portal_edit"], self.open_portal_editor), QuickAction(texts["preset"], self.cycle_portal_preset), QuickAction(texts["portal_bar"], self.toggle_portal_bar)),
                str(ICON_DIR / "portal.jpg"),
                state=self.portal_bar_visible,
                secondary=self.open_portal_editor,
            ),
            DockItem(
                "buff", "⏱", texts["buff"], self.toggle_buff_timer,
                (QuickAction(texts["buff_region"], self.toggle_buff_region), QuickAction(texts["buff_size"], self.toggle_buff_size)),
                str(ICON_DIR / "buff_timer.jpg"),
                state=lambda: bool(self.buff_timer and self.buff_timer.timer_visible),
                secondary=self.toggle_buff_size,
            ),
            DockItem(
                "durability", "◆", texts["durability"], self.toggle_durability_monitor,
                (
                    QuickAction(texts["durability_settings"], self.open_durability_settings),
                    QuickAction(texts["durability_toggle"], self.toggle_durability_monitor),
                ),
                str(ICON_DIR / "dura.jpg"),
                state=lambda: self.durability_monitor.monitoring_enabled,
            ),
            DockItem(
                "settings", "⚙", texts["settings"], lambda: self.dock.toggle_lock() if self.dock else None,
                (
                    QuickAction(self.current_language_name, self.cycle_language),
                    QuickAction(texts["button_ui"], lambda: self.dock.toggle_lock() if self.dock else None),
                    QuickAction(texts["orientation"], lambda: self.dock.toggle_orientation() if self.dock else None),
                    QuickAction(texts["map_update"], self.open_map_update),
                    QuickAction(
                        texts["app_update_available"] if self.app_update_ui and self.app_update_ui.update_available else texts["app_update"],
                        self.open_app_update,
                    ),
                ),
                str(ICON_DIR / "settings.jpg"),
                badge=lambda: self.map_engine.ui_language if self.map_engine else "KR",
                alert=lambda: "↓" if self.app_update_ui and self.app_update_ui.update_available else "",
            ),
            DockItem(
                "quit", "🚪", texts["quit"], self.shutdown,
                (),
                str(ICON_DIR / "quit.jpg"),
                False,
            ),
        ]

    def run(self):
        self.root.mainloop()

    def _remember_position(self, _window_x: int, _window_y: int):
        if not self.client_rect or not self.dock:
            return
        left, top, right, bottom = self.client_rect
        bar_left, bar_top, bar_right, bar_bottom = self.dock.button_bar_screen_rect()
        bar_width = bar_right - bar_left
        bar_height = bar_bottom - bar_top
        client_width = right - left
        client_height = bottom - top
        offset_x = max(0, min(bar_left - left, client_width - bar_width))
        offset_y = max(0, min(bar_top - top, client_height - bar_height))
        self.dock_offset = offset_x, offset_y
        self.map_engine.config["dock_offset_x"] = offset_x
        self.map_engine.config["dock_offset_y"] = offset_y
        save_config(self.map_engine.config)

    def _orientation_changed(self, orientation: str):
        if not self.map_engine:
            return
        self.map_engine.config["dock_orientation"] = orientation
        save_config(self.map_engine.config)

    def _scale_changed(self, scale: float):
        if not self.map_engine:
            return
        self.map_engine.config["dock_icon_scale"] = scale
        save_config(self.map_engine.config)

    def _collapsed_changed(self, collapsed: bool):
        if not self.map_engine:
            return
        self.map_engine.config["dock_collapsed"] = bool(collapsed)
        save_config(self.map_engine.config)

    def _follow_godius(self):
        if self.target_hwnd is None or client_screen_rect(self.target_hwnd) is None:
            self.target_hwnd = find_godius_window()
            self.client_rect = None

        rect = client_screen_rect(self.target_hwnd)
        if not rect or is_minimized(self.target_hwnd):
            if self.root.winfo_viewable():
                self.root.withdraw()
        else:
            self.client_rect = rect
            self.root.update_idletasks()
            left, top, right, bottom = rect
            if not self.dock:
                self.root.after(100, self._follow_godius)
                return
            bar_left, bar_top, bar_right, bar_bottom = self.dock.button_bar_screen_rect()
            bar_width = max(1, bar_right - bar_left)
            bar_height = max(1, bar_bottom - bar_top)
            client_width = right - left
            client_height = bottom - top
            if self.dock_offset is None:
                self.dock_offset = default_dock_offset(client_width, client_height, bar_width, bar_height)
            desired_bar_x = left + max(0, min(self.dock_offset[0], client_width - bar_width))
            desired_bar_y = top + max(0, min(self.dock_offset[1], client_height - bar_height))
            bar_x_inside_root = bar_left - self.root.winfo_x()
            bar_y_inside_root = bar_top - self.root.winfo_y()
            x = desired_bar_x - bar_x_inside_root
            y = desired_bar_y - bar_y_inside_root
            if self.dock.drag_origin:
                attach_above(self.root, self.target_hwnd)
            else:
                attach_above(self.root, self.target_hwnd, x, y)
            if self.onboarding_pending and not self.onboarding_started:
                self.onboarding_started = True
                self.root.after(250, self._start_onboarding)

        self.root.after(100, self._follow_godius)


def main():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    mutex = kernel32.CreateMutexW(None, False, "Local\\GodiNavi.SingleInstance")
    if not mutex or ctypes.get_last_error() == 183:
        ctypes.windll.user32.MessageBoxW(None, "GodiNavi is already running.", "GodiNavi", 0x40)
        return
    try:
        PrototypeApp().run()
    finally:
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()

import ctypes
import json
import secrets
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

from PIL import Image

try:
    import pystray
except ImportError:
    pystray = None

from app_update_checker import APP_VERSION
from map_engine import BUNDLE_DIR, CONFIG_PATH, RESOURCE_DIR, V2_MANAGED_INSTALL, MapEngine, load_config, save_config
from map_updater import load_local_version
from modal_window import activate_modal, bind_modal_escape, modal_font_family, place_modal

from .actions import DockItem, QuickAction
from .alchemy_ui import AlchemyUI
from .app_update_ui import AppUpdateUI
from .armor_catalog_ui import ArmorCatalogUI
from .buff_timer_engine import BuffTimerApp, default_buff_config
from .dock import OverlayDock
from .durability_monitor import DurabilityMonitor, default_durability_config
from .feature_notice_ui import FeatureNoticeUI
from .map_update_ui import MapUpdateUI, map_update_prompt_is_snoozed
from .app_update_ui import update_prompt_is_snoozed
from .monster_dictionary_ui import MonsterDictionaryUI
from .party_ui import PartyUI
from .party_client import PartyClient
from .toolbar_customize_ui import ToolbarCustomizeUI
from .ui_fonts import apply_tk_default_fonts, register_bundled_fonts
from .window_attachment import (
    attach_above, client_screen_rect, find_godius_window, is_minimized,
    focus_native_window, move_attached, native_window_handle,
)


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
        "map": "지도", "map_adjust": "지도 위치·크기 조절", "ocr_edit": "OCR 영역 편집", "world_map": "월드맵 열기 (F10)", "map_boundary_on": "영역제한 ON", "map_boundary_off": "영역제한 OFF", "maze_mode_on": "미궁 지도 모드 ON", "maze_mode_off": "미궁 지도 모드 OFF",
        "portal": "포탈", "portal_edit": "포탈 장소 편집", "preset": "프리셋 전환", "portal_bar": "포탈 바 표시/숨김",
        "buff": "버프 타이머", "buff_region": "버프 인식 영역 편집", "buff_toggle": "타이머 표시/숨김", "buff_size": "버프 창 조정",
        "durability": "내구도 감시", "durability_settings": "내구도 감시 설정", "durability_toggle": "내구도 감시 On/Off",
        "alchemy": "모험수첩", "alchemy_open": "연금술 계산기", "monster_dictionary": "몬스터 사전", "armor_catalog": "장비 도감",
        "party": "파티룸", "party_create": "파티룸 생성", "party_join": "파티룸 입실", "party_leave": "파티룸 퇴실", "party_settings": "파티룸 확인", "party_buff_adjust": "버프 확인창 조정", "party_personal_timer": "개인 버프 타이머",
        "settings": "기타 설정", "button_ui": "버튼 UI 설정", "toolbar_customize": "툴바 커스터마이즈", "orientation": "가로/세로 전환", "quit": "종료",
        "map_update": "지도 데이터 업데이트", "map_update_available": "지도 업데이트 가능 ↓",
        "app_update": "GodiNavi 업데이트", "app_update_available": "GodiNavi 업데이트 가능 ↓",
        "version_check": "버전 확인", "version_title": "버전 정보", "close": "닫기",
    },
    "JP": {
        "map": "地図", "map_adjust": "地図の位置・サイズ調整", "ocr_edit": "OCR領域を編集", "world_map": "ワールドマップを開く (F10)", "map_boundary_on": "領域制限 ON", "map_boundary_off": "領域制限 OFF", "maze_mode_on": "迷宮マップモード ON", "maze_mode_off": "迷宮マップモード OFF",
        "portal": "ポータル", "portal_edit": "ポータル地点を編集", "preset": "プリセット切替", "portal_bar": "ポータルバー 表示/非表示",
        "buff": "バフタイマー", "buff_region": "バフ認識領域を編集", "buff_toggle": "タイマー 表示/非表示", "buff_size": "バフ画面調整",
        "durability": "耐久度監視", "durability_settings": "耐久度監視設定", "durability_toggle": "耐久度監視 On/Off",
        "alchemy": "冒険手帳", "alchemy_open": "錬金術計算機", "monster_dictionary": "モンスター図鑑", "armor_catalog": "装備図鑑",
        "party": "パーティールーム", "party_create": "パーティールーム作成", "party_join": "パーティールーム入室", "party_leave": "パーティールーム退出", "party_settings": "パーティールーム確認", "party_buff_adjust": "バフ確認画面の調整", "party_personal_timer": "個人バフタイマー",
        "settings": "設定", "button_ui": "ボタンUI設定", "toolbar_customize": "ツールバーカスタマイズ", "orientation": "横/縦を切替", "quit": "終了",
        "map_update": "マップデータ更新", "map_update_available": "マップ更新あり ↓",
        "app_update": "GodiNaviアップデート", "app_update_available": "GodiNavi更新あり ↓",
        "version_check": "バージョン確認", "version_title": "バージョン情報", "close": "閉じる",
    },
    "EN": {
        "map": "Map", "map_adjust": "Adjust map position/size", "ocr_edit": "Edit OCR region", "world_map": "Open world map (F10)", "map_boundary_on": "Boundary lock ON", "map_boundary_off": "Boundary lock OFF", "maze_mode_on": "Labyrinth Map Mode ON", "maze_mode_off": "Labyrinth Map Mode OFF",
        "portal": "Portal", "portal_edit": "Edit portal locations", "preset": "Switch preset", "portal_bar": "Show/hide portal bar",
        "buff": "Buff Timer", "buff_region": "Edit buff detection region", "buff_toggle": "Show/hide timer", "buff_size": "Adjust buff window",
        "durability": "Durability Monitor", "durability_settings": "Durability settings", "durability_toggle": "Durability monitor On/Off",
        "alchemy": "Adventure Journal", "alchemy_open": "Alchemy calculator", "monster_dictionary": "Monster compendium", "armor_catalog": "Equipment catalog",
        "party": "Party Room", "party_create": "Create party room", "party_join": "Join party room", "party_leave": "Leave party room", "party_settings": "Party room overview", "party_buff_adjust": "Adjust party buff window", "party_personal_timer": "Personal buff timer",
        "settings": "Settings", "button_ui": "Button UI settings", "toolbar_customize": "Customize toolbar", "orientation": "Switch horizontal/vertical", "quit": "Quit",
        "map_update": "Map data update", "map_update_available": "Map update available ↓",
        "app_update": "GodiNavi update", "app_update_available": "GodiNavi update available ↓",
        "version_check": "Check version", "version_title": "Version information", "close": "Close",
    },
}

SYSTEM_TEXTS = {
    "KR": {
        "exit": "종료",
        "map_version": "지도 버전: {version}",
        "client_version": "클라이언트 버전: {version}",
        "missing_title": "가디우스 연결 안내",
        "missing_message": "가디우스 윈도우를 찾을 수 없습니다.",
        "already_running": "이미 가디내비가 실행 중입니다.",
    },
    "JP": {
        "exit": "終了",
        "map_version": "マップバージョン: {version}",
        "client_version": "クライアントバージョン: {version}",
        "missing_title": "ガディウス接続案内",
        "missing_message": "ガディウスのウィンドウが見つかりません。",
        "already_running": "ガディナビはすでに実行中です。",
    },
    "EN": {
        "exit": "Exit",
        "map_version": "Map version: {version}",
        "client_version": "Client version: {version}",
        "missing_title": "Godius connection",
        "missing_message": "The Godius window could not be found.",
        "already_running": "GodiNavi is already running.",
    },
}

VERSION_COMPONENT_LABELS = {
    "KR": {"client": "클라이언트", "snapshot": "구성 스냅샷", "maps": "지도", "monsters": "몬스터", "equipment": "장비 도감", "ocr_models": "OCR 모델", "ui_assets": "UI 리소스", "audio_assets": "오디오"},
    "JP": {"client": "クライアント", "snapshot": "構成スナップショット", "maps": "マップ", "monsters": "モンスター", "equipment": "装備図鑑", "ocr_models": "OCRモデル", "ui_assets": "UIリソース", "audio_assets": "オーディオ"},
    "EN": {"client": "Client", "snapshot": "Snapshot", "maps": "Maps", "monsters": "Monsters", "equipment": "Equipment", "ocr_models": "OCR models", "ui_assets": "UI assets", "audio_assets": "Audio"},
}


def system_texts(language: str) -> dict:
    return SYSTEM_TEXTS.get(language, SYSTEM_TEXTS["EN"])


def installed_map_version(resource_dir=RESOURCE_DIR, v2_managed=V2_MANAGED_INSTALL):
    if v2_managed:
        try:
            state = json.loads((Path(resource_dir) / "installation.json").read_text(encoding="utf-8-sig"))
            version = str(state.get("snapshotVersion", "")).strip()
            return version or "-"
        except (OSError, UnicodeError, json.JSONDecodeError):
            return "-"
    return load_local_version(resource_dir)


def source_manifest_version_info(resource_dir):
    """Read component versions when running directly from the source tree."""
    path = Path(resource_dir) / "update" / "v2" / "stable" / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        components = manifest.get("components", {})
        return {
            "snapshot": str(manifest.get("snapshotVersion") or "-"),
            **{
                name: str(components.get(name, {}).get("version") or "-")
                for name in ("maps", "monsters", "equipment", "ocr_models", "ui_assets", "audio_assets")
            },
        }
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return None


def v2_runtime_enabled(resource_dir=RESOURCE_DIR, v2_managed=V2_MANAGED_INSTALL):
    return v2_managed or source_manifest_version_info(resource_dir) is not None


def legacy_map_updater_enabled(resource_dir=RESOURCE_DIR, v2_managed=V2_MANAGED_INSTALL):
    """Keep the standalone map updater only for legacy, non-V2 runtimes."""
    return not v2_runtime_enabled(resource_dir, v2_managed)


def installed_version_info(resource_dir=RESOURCE_DIR, v2_managed=V2_MANAGED_INSTALL):
    if v2_managed:
        try:
            state = json.loads((Path(resource_dir) / "installation.json").read_text(encoding="utf-8-sig"))
            components = state.get("components", {})
            return {
                "client": str(state.get("clientVersion") or APP_VERSION),
                "snapshot": str(state.get("snapshotVersion") or "-"),
                **{name: str(components.get(name) or "-") for name in ("maps", "monsters", "equipment", "ocr_models", "ui_assets", "audio_assets")},
            }
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            pass
    source_info = source_manifest_version_info(resource_dir)
    if source_info:
        return {"client": APP_VERSION, **source_info}
    return {"client": APP_VERSION, "snapshot": installed_map_version(resource_dir, v2_managed), "maps": installed_map_version(resource_dir, v2_managed)}


def version_lines(language, resource_dir=RESOURCE_DIR, v2_managed=V2_MANAGED_INSTALL, compact=False):
    labels = VERSION_COMPONENT_LABELS.get(language, VERSION_COMPONENT_LABELS["EN"])
    info = installed_version_info(resource_dir, v2_managed)
    keys = ("client", "snapshot", "maps", "monsters", "equipment", "ocr_models") if compact else tuple(key for key in labels if key in info)
    return [f"{labels[key]}: {info[key]}" for key in keys if key in info]


class PrototypeApp:
    def __init__(self):
        register_bundled_fonts(BUNDLE_DIR / "assets" / "fonts")
        self.root = tk.Tk()
        initial_language = str(load_config().get("ui_language", "KR")).upper()
        apply_tk_default_fonts(self.root, initial_language)
        self.root.withdraw()
        self.tray_icon = None
        self.missing_client_window = None
        self.missing_client_labels = {}
        self.missing_client_drag_origin = None
        self.version_window = None
        self.dock: OverlayDock | None = None
        self.map_update_ui: MapUpdateUI | None = None
        self.app_update_ui: AppUpdateUI | None = None
        self.update_prompt_phase = "waiting"
        self.pending_party_entry_action = None
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
            performance=self.map_engine.performance,
            capture_coordinator=self.map_engine.capture_coordinator,
        )
        self.target_hwnd = None
        self.dock_owner_hwnd = None
        self.client_rect = None
        self.overlays_temporarily_hidden = False
        self.temporarily_hidden_windows = set()
        self.temporarily_released_grab = None
        durability_config = default_durability_config()
        saved_durability_config = self.map_engine.config.get("durability_monitor", {})
        if isinstance(saved_durability_config, dict):
            durability_config.update(saved_durability_config)
            if saved_durability_config and "presets" not in saved_durability_config:
                durability_config["_migrate_legacy_preset"] = True
        self.durability_monitor = DurabilityMonitor(
            self.root,
            durability_config,
            self._save_durability_config,
            lambda: self.target_hwnd,
            self.buff_timer.capture_client_frame,
            self.map_engine.ui_language,
        )
        self.alchemy_ui = AlchemyUI(
            self.root,
            lambda: self.client_rect,
            lambda: self.target_hwnd,
            lambda: self.map_engine.ui_language if self.map_engine else "KR",
        )
        self.monster_dictionary_ui = MonsterDictionaryUI(
            self.root,
            RESOURCE_DIR,
            lambda: self.map_engine.ui_language if self.map_engine else "KR",
            lambda: self.map_engine.active_map if self.map_engine else None,
            lambda: self.map_engine.maps if self.map_engine else [],
            lambda: self.client_rect,
            lambda: self.target_hwnd,
            BUNDLE_DIR,
        )
        self.armor_catalog_ui = ArmorCatalogUI(
            self.root,
            RESOURCE_DIR,
            lambda: self.map_engine.ui_language if self.map_engine else "KR",
        )
        installation_id = str(self.map_engine.config.get("party_installation_id", ""))
        if len(installation_id) < 16:
            installation_id = secrets.token_urlsafe(24)
            self.map_engine.config["party_installation_id"] = installation_id
            save_config(self.map_engine.config)
        self.party_client = PartyClient(
            installation_id,
            lambda callback: self.root.after(0, callback),
        )
        self.party_ui = PartyUI(
            self.root,
            self.map_engine.config,
            lambda: save_config(self.map_engine.config),
            lambda: self.map_engine.ui_language if self.map_engine else "KR",
            lambda: self.client_rect,
            lambda: self.target_hwnd,
            self.party_client,
            self.message,
            self.map_engine,
            center_message_callback=self.center_message,
        )
        self.buff_timer.party_presence_callback = self.party_ui.update_local_buff_presence
        self.toolbar_customize_ui = ToolbarCustomizeUI(
            self.root,
            lambda: self.map_engine.ui_language if self.map_engine else "KR",
            lambda: self.client_rect,
            lambda: self.target_hwnd,
            self.map_engine.config,
            lambda: save_config(self.map_engine.config),
            self._apply_toolbar_customization,
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
            on_opacity_changed=self._dock_opacity_changed,
            on_collapsed_changed=self._collapsed_changed,
            focus_callback=lambda: focus_native_window(self.target_hwnd),
            client_rect_provider=lambda: self.client_rect,
            initial_orientation=self.map_engine.config.get("dock_orientation", "horizontal"),
            initial_icon_scale=self.map_engine.config.get("dock_icon_scale", 1.0),
            initial_opacity_percent=self.map_engine.config.get("dock_opacity_percent", 94),
            initial_collapsed=self.map_engine.config.get("dock_collapsed", False),
            initial_collapse_edge=self.map_engine.config.get("dock_collapse_edge"),
            initial_ui_language=self.map_engine.ui_language,
        )
        if legacy_map_updater_enabled():
            self.map_update_ui = MapUpdateUI(
                self.root,
                RESOURCE_DIR,
                lambda: self.map_engine.ui_language if self.map_engine else "EN",
                self._map_update_state_changed,
                self._map_update_installed,
                lambda: self.client_rect,
                lambda: self.target_hwnd,
                self._map_update_prompt_decision,
                self._before_map_update,
            )
        self.app_update_ui = AppUpdateUI(
            self.root,
            RESOURCE_DIR,
            lambda: self.map_engine.ui_language if self.map_engine else "EN",
            self._app_update_state_changed,
            self.shutdown,
            lambda: self.client_rect,
            lambda: self.target_hwnd,
            self._app_update_prompt_decision,
        )
        self.feature_notice_ui = FeatureNoticeUI(
            self.root,
            lambda: self.map_engine.ui_language if self.map_engine else "EN",
            self._complete_monster_notice,
        )
        self._start_tray_icon()
        self.root.after(100, self._follow_godius)
        self.root.after(1500, self._start_140_notice_flow)

    def _start_tray_icon(self):
        if pystray is None:
            return
        icon_path = ICON_DIR.parent / "Godius_104.png"
        try:
            image = Image.open(icon_path).convert("RGBA")
        except OSError:
            return
        language = self.map_engine.ui_language if self.map_engine else "KR"
        texts = system_texts(language)

        def request_exit(_icon=None, _item=None):
            try:
                self.root.after(0, self.shutdown)
            except (tk.TclError, RuntimeError):
                pass

        self.tray_icon = pystray.Icon(
            "GodiNavi", image, "GodiNavi",
            menu=pystray.Menu(
                *(pystray.MenuItem(line, None, enabled=False) for line in version_lines(language, compact=True)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(texts["exit"], request_exit),
            ),
        )
        self.tray_icon.run_detached()

    def _restart_tray_icon(self):
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self._start_tray_icon()

    def _show_missing_client(self):
        language = self.map_engine.ui_language if self.map_engine else "EN"
        texts = system_texts(language)
        if self.missing_client_window and self.missing_client_window.winfo_exists():
            self.missing_client_labels["title"].configure(text=texts["missing_title"])
            self.missing_client_labels["message"].configure(text=texts["missing_message"])
            self.missing_client_labels["exit"].configure(text=texts["exit"])
            if not self.missing_client_window.winfo_viewable():
                self.missing_client_window.deiconify()
            return

        win = tk.Toplevel(self.root)
        self.missing_client_window = win
        win.overrideredirect(True)
        win.configure(bg="#17130f")
        win.attributes("-topmost", True)
        frame = tk.Frame(
            win,
            bg="#17130f",
            padx=12,
            pady=12,
            highlightbackground="#d8b15a",
            highlightthickness=1,
        )
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg="#5a4932")
        header.pack(fill="x", pady=(0, 12))
        title = tk.Label(
            header, text=texts["missing_title"], bg="#5a4932", fg="#ffe09a",
            anchor="w", padx=12, pady=9, font=("Noto Sans KR", 13, "bold"),
        )
        title.pack(fill="x")
        message = tk.Label(
            frame, text=texts["missing_message"], bg="#17130f", fg="#f1e5c7",
            anchor="center", justify="center", padx=24, pady=22,
            font=("Noto Sans KR", 11),
        )
        message.pack(fill="both", expand=True)
        exit_button = tk.Button(
            frame, text=texts["exit"], command=self.shutdown, relief="flat",
            bg="#6b5537", fg="#fff1c9", activebackground="#806846",
            activeforeground="#ffffff", pady=8, font=("Noto Sans KR", 10, "bold"),
        )
        exit_button.pack(fill="x")
        self.missing_client_labels = {"title": title, "message": message, "exit": exit_button}

        def start_drag(event):
            self.missing_client_drag_origin = (
                event.x_root, event.y_root, win.winfo_x(), win.winfo_y()
            )

        def drag(event):
            if not self.missing_client_drag_origin:
                return
            sx, sy, wx, wy = self.missing_client_drag_origin
            win.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")

        for widget in (header, title):
            widget.bind("<ButtonPress-1>", start_drag)
            widget.bind("<B1-Motion>", drag)
        win.update_idletasks()
        width = max(420, win.winfo_reqwidth())
        height = max(210, win.winfo_reqheight())
        x = max(0, (win.winfo_screenwidth() - width) // 2)
        y = max(0, (win.winfo_screenheight() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.lift()
        win.after(250, lambda: win.attributes("-topmost", False) if win.winfo_exists() else None)

    def _hide_missing_client(self):
        if self.missing_client_window and self.missing_client_window.winfo_exists():
            self.missing_client_window.withdraw()

    def message(self, text: str, duration: int = 1600):
        if self.dock:
            self.dock.set_message(text, duration)

    def center_message(self, text: str, duration: int = 1600, _attempt: int = 0):
        # Session restoration starts before the first Godius-follow pass. Wait
        # until the client rectangle exists so the notice is neither misplaced
        # nor hidden behind the game during startup.
        if self.dock and self.client_rect:
            self.dock.set_center_message(text, duration)
            return
        if _attempt < 40:
            self.root.after(150, lambda: self.center_message(text, duration, _attempt + 1))

    def _start_140_notice_flow(self):
        if APP_VERSION != "1.4.0":
            self._check_startup_updates()
            return
        if self.map_engine.config.get("monster_dictionary_140_notice_seen"):
            self._check_startup_updates()
            return
        self.feature_notice_ui.show()

    def _complete_monster_notice(self):
        self.map_engine.config["monster_dictionary_140_notice_seen"] = True
        save_config(self.map_engine.config)
        self._check_startup_updates()

    def _check_startup_updates(self):
        self.update_prompt_phase = "waiting"
        self.app_update_ui.check(False)
        if self.map_update_ui:
            self.map_update_ui.check(False)

    def _maybe_show_startup_update_prompt(self):
        if self.update_prompt_phase != "waiting":
            return
        if self.app_update_ui.state in ("idle", "checking"):
            return
        if self.map_update_ui and self.map_update_ui.state in ("idle", "checking"):
            return
        if self.app_update_ui.state == "available" and not update_prompt_is_snoozed():
            self.update_prompt_phase = "app"
            self.app_update_ui.show_update_prompt()
            return
        self._offer_startup_map_update()

    def _offer_startup_map_update(self):
        if self.map_update_ui and self.map_update_ui.state == "available" and not map_update_prompt_is_snoozed():
            self.update_prompt_phase = "map"
            self.map_update_ui.show_update_prompt()
        else:
            self.update_prompt_phase = "done"

    def _app_update_prompt_decision(self, decision):
        if decision == "accepted":
            self.update_prompt_phase = "done"
            return
        self._offer_startup_map_update()

    def _map_update_prompt_decision(self, _decision):
        self.update_prompt_phase = "done"

    def _before_map_update(self):
        self.monster_dictionary_ui.store.close()

    def open_map_update(self):
        if self.map_update_ui:
            self.map_update_ui.open()
            if self.map_update_ui.state in ("idle", "latest", "installed", "error"):
                self.map_update_ui.check(False)

    def _map_update_state_changed(self):
        if self.dock:
            self.items = self._create_items()
            self.dock.set_items(self.items)
        self._maybe_show_startup_update_prompt()

    def _map_update_installed(self):
        if self.map_engine:
            self.map_engine.reload_map_database_if_changed()
        self.monster_dictionary_ui.store.close()
        self.monster_dictionary_ui.reload_data(clear_image_cache=True)
        self._restart_tray_icon()

    def open_app_update(self):
        if self.app_update_ui:
            self.app_update_ui.open()
            if self.app_update_ui.state in ("idle", "latest", "error", "missing"):
                self.app_update_ui.check(False)

    def _app_update_state_changed(self):
        if self.dock:
            self.items = self._create_items()
            self.dock.set_items(self.items)
        self._maybe_show_startup_update_prompt()
        if (
            self.pending_party_entry_action is not None
            and self.app_update_ui
            and not self.app_update_ui.busy
            and self.app_update_ui.state != "checking"
        ):
            action = self.pending_party_entry_action
            self.pending_party_entry_action = None
            self.root.after_idle(lambda: self._continue_party_entry_action(action))

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

    def toggle_labyrinth_map_mode(self):
        if not self.map_engine:
            return
        enabled = self.map_engine.toggle_labyrinth_map_mode()
        text = {
            "KR": f"미궁 지도 모드 {'ON' if enabled else 'OFF'}",
            "JP": f"迷宮マップモード {'ON' if enabled else 'OFF'}",
            "EN": f"Labyrinth Map Mode {'ON' if enabled else 'OFF'}",
        }[self.map_engine.ui_language]
        self.message(text, 1800)

    def toggle_map_adjustment(self):
        if self.map_engine:
            self.map_engine.toggle_map_resize_mode()

    def toggle_map_boundary_restriction(self):
        if self.map_engine:
            self.map_engine.toggle_minimap_boundary_restriction()

    def toggle_map_calibration(self):
        if self.map_engine:
            self.map_engine.toggle_calibration()

    def _run_party_entry_action(self, action):
        self.party_ui.show_experimental_notice()
        if self.app_update_ui and self.app_update_ui.state in {"idle", "checking"}:
            self.pending_party_entry_action = action
            if self.app_update_ui.state == "idle":
                self.app_update_ui.check(False)
            return
        self._continue_party_entry_action(action)

    def _continue_party_entry_action(self, action):
        latest_version = None
        if self.app_update_ui and self.app_update_ui.update_available and self.app_update_ui.release:
            latest_version = self.app_update_ui.release.get("version")
        self.party_ui.show_outdated_notice(latest_version)
        action()

    def toggle_party_overview(self):
        if self.party_ui.overview_open:
            self.party_ui.toggle_settings()
            return
        self._run_party_entry_action(self.party_ui.toggle_settings)

    def create_party_room(self):
        self._run_party_entry_action(self.party_ui.create_room)

    def join_or_leave_party_room(self):
        if self.party_ui.joined:
            self.party_ui.join_or_leave()
            return
        self._run_party_entry_action(self.party_ui.join_or_leave)

    def open_party_overview(self):
        self._run_party_entry_action(self.party_ui.open_settings)

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
        self.party_ui.refresh_language()
        self._restart_tray_icon()
        language_name = {"KR": "한국어", "JP": "日本語", "EN": "English"}[self.map_engine.ui_language]
        self.message(f"언어: {language_name}")

    def current_language_name(self):
        return "🌐 LANGUAGE"

    def shutdown(self):
        if hasattr(self, "party_client"):
            self.party_client.close()
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
        if hasattr(self, "armor_catalog_ui"):
            self.armor_catalog_ui.store.close()
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
        self.buff_timer.toggle_timer_resize_mode()

    def open_version_dialog(self):
        if self.version_window and self.version_window.winfo_exists():
            self.version_window.deiconify()
            self.version_window.lift()
            activate_modal(self.version_window)
            return
        language = self.map_engine.ui_language if self.map_engine else "KR"
        texts = DOCK_TEXTS.get(language, DOCK_TEXTS["EN"])
        win = tk.Toplevel(self.root)
        self.version_window = win
        win.overrideredirect(True)
        win.configure(bg="#d8b15a")
        win.transient(self.root)
        outer = tk.Frame(win, bg="#17130f", padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        family = modal_font_family(win, language)
        tk.Label(
            outer, text=texts["version_title"], bg="#5a4932", fg="#ffe09a",
            anchor="w", padx=14, pady=10, font=(family, 11, "bold"),
        ).pack(fill="x")
        version_text = "\n".join(version_lines(language))
        tk.Label(
            outer, text=version_text, justify="left",
            bg="#17130f", fg="#f1e5c7", padx=28, pady=24,
            font=(family, 11, "bold"),
        ).pack(fill="both", expand=True)

        def close():
            if self.version_window and self.version_window.winfo_exists():
                self.version_window.destroy()
            self.version_window = None

        tk.Button(
            outer, text=texts["close"], command=close, relief="flat",
            bg="#6b5537", fg="#fff1c9", activebackground="#806846",
            activeforeground="#ffffff", padx=20, pady=7,
            font=(family, 9, "bold"),
        ).pack(side="bottom", anchor="e", padx=12, pady=(0, 12))
        place_modal(win, minimum_width=390, minimum_height=330 if v2_runtime_enabled() else 210, position_key="version_dialog")
        bind_modal_escape(win, close)

    def _create_items(self, configured=True) -> list[DockItem]:
        texts = DOCK_TEXTS[self.map_engine.ui_language if self.map_engine else "KR"]
        update_available = bool(self.map_update_ui and self.map_update_ui.update_available)
        map_actions = [
            QuickAction(texts["map_adjust"], self.toggle_map_adjustment),
            QuickAction(
                lambda: texts["map_boundary_off"] if self.map_engine.minimap_boundary_restricted else texts["map_boundary_on"],
                self.toggle_map_boundary_restriction,
            ),
            QuickAction(texts["ocr_edit"], self.toggle_map_calibration),
            QuickAction(texts["world_map"], self.toggle_world_map),
            QuickAction(
                lambda: texts["maze_mode_off"] if self.map_engine.labyrinth_map_mode else texts["maze_mode_on"],
                self.toggle_labyrinth_map_mode,
            ),
        ]
        if update_available:
            map_actions.append(QuickAction(texts["map_update_available"], self.open_map_update))
        settings_actions = [
            QuickAction(self.current_language_name, self.cycle_language),
            QuickAction(texts["button_ui"], lambda: self.dock.toggle_lock() if self.dock else None),
            QuickAction(texts["toolbar_customize"], self.open_toolbar_customize),
            QuickAction(texts["orientation"], lambda: self.dock.toggle_orientation() if self.dock else None),
        ]
        if self.map_update_ui:
            settings_actions.append(QuickAction(texts["map_update"], self.open_map_update))
        settings_actions.append(QuickAction(
            texts["app_update_available"] if self.app_update_ui and self.app_update_ui.update_available else texts["app_update"],
            self.open_app_update,
        ))
        settings_actions.append(QuickAction(texts["version_check"], self.open_version_dialog))
        items = [
            DockItem(
                "map", "🗺", texts["map"], self.toggle_minimap,
                tuple(map_actions),
                str(ICON_DIR / "map.jpg"),
                state=lambda: bool(self.map_engine and self.map_engine.minimap_enabled),
                alert=lambda: "NEW" if self.map_update_ui and self.map_update_ui.update_available else "",
                focus_after_primary=True,
                focus_after_secondary=True,
            ),
            DockItem(
                "portal", "◈", texts["portal"], self.toggle_portal_bar,
                (QuickAction(texts["portal_edit"], self.open_portal_editor), QuickAction(texts["preset"], self.cycle_portal_preset), QuickAction(texts["portal_bar"], self.toggle_portal_bar)),
                str(ICON_DIR / "portal.jpg"),
                state=self.portal_bar_visible,
                secondary=self.open_portal_editor,
                focus_after_primary=True,
            ),
            DockItem(
                "buff", "⏱", texts["buff"], self.toggle_buff_timer,
                (QuickAction(texts["buff_region"], self.toggle_buff_region), QuickAction(texts["buff_size"], self.toggle_buff_size)),
                str(ICON_DIR / "buff_timer.jpg"),
                state=lambda: bool(self.buff_timer and self.buff_timer.timer_visible),
                secondary=self.toggle_buff_size,
                focus_after_primary=True,
                focus_after_secondary=True,
            ),
            DockItem(
                "durability", "◆", texts["durability"], self.toggle_durability_monitor,
                (
                    QuickAction(texts["durability_settings"], self.open_durability_settings),
                    QuickAction(texts["durability_toggle"], self.toggle_durability_monitor),
                ),
                str(ICON_DIR / "dura.jpg"),
                state=lambda: self.durability_monitor.monitoring_enabled,
                focus_after_primary=True,
            ),
            DockItem(
                "alchemy", "", texts["alchemy"], self.monster_dictionary_ui.open,
                (
                    QuickAction(texts["alchemy_open"], self.alchemy_ui.open),
                    QuickAction(texts["monster_dictionary"], self.monster_dictionary_ui.open),
                    QuickAction(texts["armor_catalog"], self.armor_catalog_ui.open),
                ),
                str(ICON_DIR / "encyclopedia.jpg"),
                secondary=self.alchemy_ui.open,
            ),
            DockItem(
                "party", "", texts["party"], self.toggle_party_overview,
                (
                    QuickAction(self.party_ui.server_status_text, lambda: None, enabled=lambda: False),
                    QuickAction(texts["party_create"], self.create_party_room,
                                enabled=lambda: self.party_ui.server_available and self.party_ui.party_client.service_accepting_rooms and not self.party_ui.joined),
                    QuickAction(
                        lambda: texts["party_leave"] if self.party_ui.joined else texts["party_join"],
                        self.join_or_leave_party_room,
                        enabled=lambda: self.party_ui.server_available,
                    ),
                    QuickAction(texts["party_settings"], self.open_party_overview,
                                enabled=lambda: self.party_ui.server_available),
                    QuickAction(texts["party_buff_adjust"], self.party_ui.toggle_buff_bar_adjustment),
                    QuickAction(texts["party_personal_timer"], self.party_ui.open_personal_buff_timer),
                    QuickAction(
                        lambda: self.party_ui.texts()["disband"],
                        self.party_ui.disband_room,
                        enabled=self.party_ui.can_disband,
                    ),
                ),
                str(ICON_DIR / "party.jpg"),
                secondary=self.party_ui.toggle_buff_bar_adjustment,
                icon_bottom_text="BETA",
                focus_after_secondary=True,
            ),
            DockItem(
                "settings", "⚙", texts["settings"], lambda: self.dock.toggle_lock() if self.dock else None,
                tuple(settings_actions),
                str(ICON_DIR / "settings.jpg"),
                badge=lambda: self.map_engine.ui_language if self.map_engine else "KR",
                alert=lambda: "NEW" if self.app_update_ui and self.app_update_ui.update_available else "",
                focus_after_primary=True,
                focus_after_secondary=True,
            ),
            DockItem(
                "quit", "🚪", texts["quit"], self.shutdown,
                (),
                str(ICON_DIR / "quit.jpg"),
                False,
                secondary=self.toggle_temporary_overlay_visibility,
            ),
        ]
        return self._configured_toolbar_items(items) if configured else items

    def _configured_toolbar_items(self, items):
        fixed = [item for item in items if item.key in {"settings", "quit"}]
        movable = {item.key: item for item in items if item.key not in {"settings", "quit"}}
        saved_order = self.map_engine.config.get("toolbar_item_order", [])
        if not isinstance(saved_order, list):
            saved_order = []
        order = [key for key in saved_order if key in movable]
        order.extend(key for key in movable if key not in order)
        disabled_value = self.map_engine.config.get("toolbar_disabled_items", [])
        disabled = set(disabled_value if isinstance(disabled_value, list) else [])
        return [movable[key] for key in order if key not in disabled] + fixed

    def open_toolbar_customize(self):
        raw_items = self._create_items(configured=False)
        ordered_items = self._configured_toolbar_items_without_filter(raw_items)
        self.toolbar_customize_ui.open(ordered_items)

    def _configured_toolbar_items_without_filter(self, items):
        fixed = [item for item in items if item.key in {"settings", "quit"}]
        movable = {item.key: item for item in items if item.key not in {"settings", "quit"}}
        saved_order = self.map_engine.config.get("toolbar_item_order", [])
        if not isinstance(saved_order, list):
            saved_order = []
        order = [key for key in saved_order if key in movable]
        order.extend(key for key in movable if key not in order)
        return [movable[key] for key in order] + fixed

    def _apply_toolbar_customization(self, order, enabled, previous_disabled):
        disabled = set(order) - set(enabled)
        for key in disabled - previous_disabled:
            self._suspend_toolbar_feature(key)
        for key in previous_disabled - disabled:
            self._restore_toolbar_feature(key)
        self.items = self._create_items()
        self.dock.set_items(self.items)

    @staticmethod
    def _window_visible(window):
        try:
            return bool(window and window.winfo_exists() and window.winfo_viewable())
        except tk.TclError:
            return False

    def _suspended_toolbar_states(self):
        value = self.map_engine.config.get("toolbar_suspended_states", {})
        if not isinstance(value, dict):
            value = {}
            self.map_engine.config["toolbar_suspended_states"] = value
        return value

    def _suspend_toolbar_feature(self, key):
        states = self._suspended_toolbar_states()
        if key == "map":
            states[key] = {"visible": bool(self.map_engine.minimap_enabled)}
        elif key == "portal":
            states[key] = {"visible": bool(self.map_engine.config.get("favorite_overlay_visible"))}
        elif key == "buff":
            states[key] = {"visible": bool(self.buff_timer.timer_visible)}
        elif key == "durability":
            states[key] = {"enabled": bool(self.durability_monitor.monitoring_enabled)}
        elif key == "alchemy":
            states[key] = {
                "alchemy_visible": self._window_visible(self.alchemy_ui.window),
                "dictionary_visible": self._window_visible(self.monster_dictionary_ui.window),
                "armor_catalog_visible": self._window_visible(self.armor_catalog_ui.window),
            }
        elif key == "party":
            states[key] = {
                "chat_overlay_enabled": bool(self.party_ui.chat_overlay_enabled),
                "settings_visible": self._window_visible(self.party_ui.settings_window),
            }

        if key == "map" and self.map_engine.minimap_enabled:
            self.map_engine.toggle_minimap()
        elif key == "portal" and self.map_engine.config.get("favorite_overlay_visible"):
            self.map_engine.toggle_favorite_overlay()
        elif key == "buff" and self.buff_timer.timer_visible:
            self.buff_timer.toggle_timer_visibility()
        elif key == "durability" and self.durability_monitor.monitoring_enabled:
            self.durability_monitor.toggle_monitoring()
        elif key == "alchemy":
            self.alchemy_ui.close()
            window = self.monster_dictionary_ui.window
            if window and window.winfo_exists():
                window.withdraw()
            self.armor_catalog_ui.close()
        elif key == "party":
            self.party_ui.chat_overlay_enabled = False
            self.map_engine.config["party_chat_overlay_enabled"] = False
            self.party_ui.set_owner_overlays_available(False)
            for name in ("settings_window", "overview_window", "chat_overlay_window", "buff_bar_window"):
                window = getattr(self.party_ui, name, None)
                if window and window.winfo_exists():
                    window.withdraw()
            save_config(self.map_engine.config)

        self.map_engine.config["toolbar_suspended_states"] = states
        save_config(self.map_engine.config)

    def _restore_toolbar_feature(self, key):
        states = self._suspended_toolbar_states()
        state = states.pop(key, {})
        if not isinstance(state, dict):
            state = {}
        if key == "map" and state.get("visible") and not self.map_engine.minimap_enabled:
            self.map_engine.toggle_minimap()
        elif key == "portal" and state.get("visible") and not self.map_engine.config.get("favorite_overlay_visible"):
            self.map_engine.toggle_favorite_overlay()
        elif key == "buff" and state.get("visible") and not self.buff_timer.timer_visible:
            self.buff_timer.toggle_timer_visibility()
        elif key == "durability" and state.get("enabled") and not self.durability_monitor.monitoring_enabled:
            self.durability_monitor.toggle_monitoring()
        elif key == "alchemy":
            if state.get("alchemy_visible"):
                self.alchemy_ui.open()
            if state.get("dictionary_visible"):
                self.monster_dictionary_ui.open()
            if state.get("armor_catalog_visible"):
                self.armor_catalog_ui.open()
        elif key == "party":
            restore_chat = bool(state.get("chat_overlay_enabled"))
            self.party_ui.chat_overlay_enabled = restore_chat
            self.map_engine.config["party_chat_overlay_enabled"] = restore_chat
            self.party_ui.set_owner_overlays_available(bool(self.client_rect))
            if state.get("settings_visible"):
                self.party_ui.open_settings()
        self.map_engine.config["toolbar_suspended_states"] = states
        save_config(self.map_engine.config)

    def _overlay_windows(self):
        windows = []
        pending = list(self.root.winfo_children())
        while pending:
            widget = pending.pop()
            try:
                pending.extend(widget.winfo_children())
                if isinstance(widget, tk.Toplevel) and widget.winfo_exists():
                    windows.append(widget)
            except tk.TclError:
                continue
        return windows

    def _temporary_overlay_exclusions(self):
        if not self.dock:
            return set()
        return {
            window for window in (self.dock.edit_header_window, self.dock.edit_grip_window)
            if window is not None
        }

    def _hide_non_toolbar_overlays(self, remember=True):
        excluded = self._temporary_overlay_exclusions()
        ephemeral = {
            window for window in (
                getattr(self.dock, "status_window", None) if self.dock else None,
                getattr(self.dock, "flyout", None) if self.dock else None,
            ) if window is not None
        }
        for window in self._overlay_windows():
            if window in excluded:
                continue
            try:
                if window.winfo_viewable():
                    if remember and window not in ephemeral:
                        self.temporarily_hidden_windows.add(window)
                    window.withdraw()
            except tk.TclError:
                continue

    def toggle_temporary_overlay_visibility(self):
        self.overlays_temporarily_hidden = not self.overlays_temporarily_hidden
        if self.overlays_temporarily_hidden:
            self.temporarily_hidden_windows.clear()
            try:
                grabbed = self.root.grab_current()
                if grabbed:
                    grabbed.grab_release()
                    self.temporarily_released_grab = grabbed
            except tk.TclError:
                self.temporarily_released_grab = None
            self.party_ui.set_owner_overlays_available(False)
            self.map_engine.set_overlays_temporarily_hidden(True)
            self.buff_timer.set_overlays_temporarily_hidden(True)
            self._hide_non_toolbar_overlays(remember=True)
            if self.dock:
                self.dock.set_temporarily_disabled(True)
            return

        if self.dock:
            self.dock.set_temporarily_disabled(False)
        self.map_engine.set_overlays_temporarily_hidden(False)
        self.buff_timer.set_overlays_temporarily_hidden(False)
        self.party_ui.set_owner_overlays_available(bool(self.client_rect) and self._toolbar_feature_enabled("party"))
        for window in tuple(self.temporarily_hidden_windows):
            try:
                if window.winfo_exists():
                    window.deiconify()
            except tk.TclError:
                pass
        self.temporarily_hidden_windows.clear()
        grabbed = self.temporarily_released_grab
        self.temporarily_released_grab = None
        try:
            if grabbed and grabbed.winfo_exists():
                grabbed.grab_set()
        except tk.TclError:
            pass

    def _toolbar_feature_enabled(self, key):
        disabled = self.map_engine.config.get("toolbar_disabled_items", [])
        return key not in set(disabled if isinstance(disabled, list) else [])

    def run(self):
        self.root.mainloop()

    def _remember_position(self, _window_x: int, _window_y: int):
        if not self.client_rect or not self.dock:
            return
        if self.dock.restoring_anchor:
            return
        self.dock.update_collapse_edge(self.client_rect)
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
        self.map_engine.config["dock_collapse_edge"] = self.dock.collapse_edge
        save_config(self.map_engine.config)

    def _orientation_changed(self, orientation: str):
        if not self.map_engine:
            return
        self.map_engine.config["dock_orientation"] = orientation
        if self.dock:
            self.map_engine.config["dock_collapse_edge"] = self.dock.collapse_edge
        save_config(self.map_engine.config)
        if self.dock and self.client_rect:
            self.root.after_idle(lambda: self.dock.update_collapse_edge(self.client_rect))

    def _scale_changed(self, scale: float):
        if not self.map_engine:
            return
        self.map_engine.config["dock_icon_scale"] = scale
        save_config(self.map_engine.config)

    def _dock_opacity_changed(self, opacity_percent: int):
        if not self.map_engine:
            return
        self.map_engine.config["dock_opacity_percent"] = int(opacity_percent)
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
        if self.target_hwnd is None or not rect:
            self._show_missing_client()
            self.party_ui.set_owner_overlays_available(False)
            if self.root.winfo_viewable():
                self.root.withdraw()
        elif is_minimized(self.target_hwnd):
            self._hide_missing_client()
            self.party_ui.set_owner_overlays_available(False)
            if self.root.winfo_viewable():
                self.root.withdraw()
        else:
            self._hide_missing_client()
            self.client_rect = rect
            self.party_ui.set_owner_overlays_available(
                self._toolbar_feature_enabled("party") and not self.overlays_temporarily_hidden
            )
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
            self.map_engine.minimap_avoid_rect = (
                desired_bar_x,
                desired_bar_y,
                desired_bar_x + bar_width,
                desired_bar_y + bar_height,
            )
            if self.map_engine.map_window.winfo_viewable():
                self.map_engine.position_map()
            bar_x_inside_root = bar_left - self.root.winfo_x()
            bar_y_inside_root = bar_top - self.root.winfo_y()
            x = desired_bar_x - bar_x_inside_root
            y = desired_bar_y - bar_y_inside_root
            map_visible = self.map_engine.map_window.winfo_viewable()
            desired_dock_owner = (
                native_window_handle(self.map_engine.map_window)
                if map_visible else self.target_hwnd
            )
            if self.dock_owner_hwnd != desired_dock_owner:
                attach_above(self.root, desired_dock_owner)
                self.dock_owner_hwnd = desired_dock_owner
            if not self.dock.drag_origin:
                move_attached(self.root, x, y)
            if self.onboarding_pending and not self.onboarding_started:
                self.onboarding_started = True
                self.root.after(250, self._start_onboarding)
            self.party_ui.follow_owner(rect, self.target_hwnd)
            self.party_ui.sync_position()

        if self.overlays_temporarily_hidden:
            self._hide_non_toolbar_overlays(remember=True)

        self.root.after(100, self._follow_godius)


def main():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    mutex = kernel32.CreateMutexW(None, False, "Local\\GodiNavi.SingleInstance")
    if not mutex or ctypes.get_last_error() == 183:
        language = load_config().get("ui_language", "EN")
        ctypes.windll.user32.MessageBoxW(
            None, system_texts(language)["already_running"], "GodiNavi", 0x40
        )
        return
    try:
        PrototypeApp().run()
    finally:
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()

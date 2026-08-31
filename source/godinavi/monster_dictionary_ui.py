import tkinter as tk
from modal_window import activate_modal, bind_modal_escape
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

from monster_store import MonsterStore
from v2_assets import V2AssetStore
from .window_attachment import (
    attach_above, make_noactivate_toolwindow, mouse_buttons_down, native_window_handle,
    owner_group_is_foreground,
)


BG = "#17130f"
PANEL = "#2a2118"
PANEL_HOVER = "#443422"
HEADER = "#5a4932"
GOLD = "#d8b15a"
PK_RED = "#ff4658"
TEXT = "#f1e5c7"
MUTED = "#bda982"
ATTRIBUTE_COLORS = {
    "ice": "#67C7FF",
    "fire": "#FF6655",
    "divine": "#F2C94C",
    "neutral": "#F2F2F2",
    "poison": "#B777E8",
    "disease": "#67C96F",
    "petrify": "#8B929A",
}
DROP_ICON_FILES = {
    "dragonscale": "dragonscale.jpg",
    "demonhorn": "demonhorn.jpg",
    "mithrill": "mithril.jpg",
}
ATTRIBUTE_ICON_FILES = {
    "neutral": "neutral.png",
    "fire": "fire.png",
    "ice": "ice.png",
    "poison": "poison.png",
    "divine": "divine.png",
    "petrify": "petrification.png",
    "all_non_neutral": "all.png",
    "disease": "disease.png",
}
CARD_COLUMNS = 2
CARD_WIDTH = 520
CARD_HEIGHT = 158
CARD_IMAGE_SIZE = 124
CARD_IMAGE_X = 14
CARD_IMAGE_Y = 17
CARD_TEXT_X = 154


TEXTS = {
    "KR": {
        "title": "몬스터 사전", "search": "이름 검색", "all_maps": "전체 지역",
        "current_only": "현재 지역 몬스터", "attack": "공격 속성", "weakness": "약점",
        "all": "전체", "monster": "몬스터", "map": "등장 지역", "status": "검증 상태",
        "no_map": "현재 지역을 인식하지 못했습니다.", "no_results": "조건에 맞는 몬스터가 없습니다.",
        "names": "이름", "aliases": "별칭", "magic": "마법 공격", "drops": "드롭 아이템",
        "contributors": "기여자", "notes": "메모", "draft": "검토 필요", "reviewed": "검토됨",
        "verified": "검증 완료", "yes": "사용", "no": "미사용", "unknown": "미확인",
        "other_maps": "그 외 서식지", "no_other_maps": "다른 서식지가 없습니다.",
        "no_image": "이미지\n없음", "count": "{count}종", "close": "닫기",
        "sort_name": "이름순", "sort_level": "레벨순",
        "minimum_region_level": "Lv {level} ~",
        "minimum_level_notice": "※카드에 표기된 레벨은 해당 몬스터의 레벨이 아닌, 등장지역 중 가장 낮은 레벨을 표시한 것입니다.",
        "monster_overlay_on": "몬스터 일람 오버레이 ON", "monster_overlay_off": "몬스터 일람 오버레이 OFF",
        "monster_overlay_adjust": "드래그 이동 · 휠로 투명도 조절",
    },
    "JP": {
        "title": "モンスター図鑑", "search": "名前検索", "all_maps": "全地域",
        "current_only": "現在地域のモンスター", "attack": "攻撃属性", "weakness": "弱点属性",
        "all": "すべて", "monster": "モンスター", "map": "出現地域", "status": "検証状態",
        "no_map": "現在地域を認識できません。", "no_results": "条件に一致するモンスターがありません。",
        "names": "名前", "aliases": "別名", "magic": "魔法攻撃", "drops": "ドロップアイテム",
        "contributors": "協力者", "notes": "メモ", "draft": "要確認", "reviewed": "確認済み",
        "verified": "検証完了", "yes": "使用", "no": "未使用", "unknown": "未確認",
        "other_maps": "その他の生息地", "no_other_maps": "他の生息地はありません。",
        "no_image": "画像\nなし", "count": "{count}種", "close": "閉じる",
        "sort_name": "名前順", "sort_level": "レベル順",
        "minimum_region_level": "Lv {level} ~",
        "minimum_level_notice": "※カードのレベルはモンスター自身ではなく、出現地域のうち最も低いレベルを示します。",
        "monster_overlay_on": "モンスター一覧オーバーレイ ON", "monster_overlay_off": "モンスター一覧オーバーレイ OFF",
        "monster_overlay_adjust": "ドラッグで移動・ホイールで透明度調整",
    },
    "EN": {
        "title": "Monster Compendium", "search": "Search names", "all_maps": "All regions",
        "current_only": "Monsters in current region", "attack": "Attack attribute", "weakness": "Weakness",
        "all": "All", "monster": "Monster", "map": "Regions", "status": "Verification",
        "no_map": "The current region is not recognized.", "no_results": "No monsters match these filters.",
        "names": "Names", "aliases": "Aliases", "magic": "Magic attacks", "drops": "Drop items",
        "contributors": "Contributors", "notes": "Notes", "draft": "Needs review", "reviewed": "Reviewed",
        "verified": "Verified", "yes": "Yes", "no": "No", "unknown": "Unknown",
        "other_maps": "Other habitats", "no_other_maps": "There are no other habitats.",
        "no_image": "No\nimage", "count": "{count} monsters", "close": "Close",
        "sort_name": "Name", "sort_level": "Level",
        "minimum_region_level": "Lv {level} ~",
        "minimum_level_notice": "※The card level is the lowest level among its habitats, not the monster's own level.",
        "monster_overlay_on": "Monster list overlay ON", "monster_overlay_off": "Monster list overlay OFF",
        "monster_overlay_adjust": "Drag to move · Wheel adjusts opacity",
    },
}


class MonsterDictionaryUI:
    def __init__(
        self, master, project_dir, language_provider, active_map_provider, maps_provider,
        target_rect_provider=None, owner_hwnd_provider=None, bundle_dir=None,
        settings=None, save_settings=None,
    ):
        self.master = master
        # The user-facing compendium always exercises the same PAK path used
        # by packaged releases. Source JSON remains exclusive to editor tools.
        self.store = MonsterStore(project_dir, prefer_pak=True)
        self.project_dir = Path(project_dir)
        self.assets = V2AssetStore(project_dir)
        self.bundle_dir = Path(bundle_dir) if bundle_dir else self.project_dir
        self.language_provider = language_provider
        self.active_map_provider = active_map_provider
        self.maps_provider = maps_provider
        self.target_rect_provider = target_rect_provider
        self.owner_hwnd_provider = owner_hwnd_provider
        self.settings = settings if isinstance(settings, dict) else {}
        self.save_settings = save_settings
        self.window = None
        self.built_language = None
        self.monsters = []
        self.catalogs = {}
        self.map_records = {}
        self.visible_ids = []
        self.card_images = []
        self.image_cache = {}
        self.card_font_cache = {}
        self.search_refresh_job = None
        self.magic_tooltip = None
        self.drag_origin = None
        self.habitat_window = None
        self.habitat_outside_binding = None
        self.habitat_focus_misses = 0
        self.habitat_mouse_was_down = False
        self.monster_overlay_window = None
        self.monster_overlay_tooltip = None
        self.monster_overlay_images = []
        self.monster_overlay_badge_fonts = {}
        self.monster_overlay_map_id = None
        self.monster_overlay_adjusting = False
        self.monster_overlay_drag_origin = None
        self.monster_overlay_resize_origin = None
        self.monster_overlay_header_window = None
        self.monster_overlay_header_label = None
        self.monster_overlay_grip_window = None
        self.monster_overlay_lock_window = None
        self.monster_overlay_scale = max(0.5, min(2.0, float(self.settings.get("monster_list_overlay_scale", 1.0))))
        self.monster_overlay_opacity = max(50, min(100, int(self.settings.get("monster_list_overlay_opacity_percent", 100))))
        self.master.after(500, self.refresh_monster_overlay)

    def language(self):
        value = self.language_provider() if self.language_provider else "KR"
        return value if value in TEXTS else "EN"

    def locale(self):
        return {"KR": "ko", "JP": "ja", "EN": "en"}[self.language()]

    def texts(self):
        return TEXTS[self.language()]

    def open(self):
        self.reload_data()
        if self.window and self.window.winfo_exists() and self.built_language != self.language():
            self.window.destroy()
            self.window = None
        if self.window and self.window.winfo_exists():
            self.populate_filters()
            self.window.deiconify()
            self.window.lift()
            activate_modal(self.window)
            self.place_window()
            self.apply_initial_scope()
            return
        self.build_window()
        self.place_window()
        self.apply_initial_scope()

    def reload_data(self, clear_image_cache=False):
        if clear_image_cache:
            self.image_cache.clear()
        try:
            self.monsters = self.store.load_monsters()
        except Exception:
            self.monsters = []
        self.catalogs = {}
        for filename in ("attributes.json", "items.json", "magic_attacks.json"):
            try:
                self.catalogs[filename] = {item["id"]: item for item in self.store.load_catalog(filename)}
            except Exception:
                self.catalogs[filename] = {}
        self.map_records = {str(record.get("id")): record for record in (self.maps_provider() or []) if record.get("id")}

    def build_window(self):
        text = self.texts()
        window = tk.Toplevel(self.master)
        self.window = window
        self.built_language = self.language()
        window.title(text["title"])
        window.geometry("1120x720")
        window.resizable(False, False)
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        bind_modal_escape(window, self._escape_close)

        style = ttk.Style(window)
        style.theme_use("clam")
        style.configure(
            "Dictionary.TEntry", fieldbackground="#3b3022", foreground="#fff0c9",
            insertcolor="#fff0c9", bordercolor="#8f7a52", lightcolor="#8f7a52", darkcolor="#8f7a52",
        )
        style.configure(
            "Dictionary.TCombobox", fieldbackground="#3b3022", background="#5a4932",
            foreground="#fff0c9", arrowcolor="#f1d28c", bordercolor="#8f7a52",
            lightcolor="#8f7a52", darkcolor="#8f7a52",
        )
        style.map(
            "Dictionary.TCombobox",
            fieldbackground=[("readonly", "#3b3022")], foreground=[("readonly", "#fff0c9")],
            selectbackground=[("readonly", "#3b3022")], selectforeground=[("readonly", "#fff0c9")],
        )
        style.configure(
            "Dictionary.TCheckbutton", background=PANEL, foreground=TEXT,
            indicatorbackground="#3b3022", indicatorforeground=GOLD,
        )
        style.map(
            "Dictionary.TCheckbutton", background=[("active", PANEL)], foreground=[("active", "#fff1c9")],
            indicatorbackground=[("selected", "#8a6a36")],
        )
        style.configure(
            "Dictionary.Vertical.TScrollbar", background=HEADER, troughcolor=BG,
            arrowcolor="#f1d28c", bordercolor=BG,
        )
        window.option_add("*TCombobox*Listbox.background", "#34291d")
        window.option_add("*TCombobox*Listbox.foreground", TEXT)
        window.option_add("*TCombobox*Listbox.selectBackground", HEADER)
        window.option_add("*TCombobox*Listbox.selectForeground", "#fff1c9")

        content = tk.Frame(window, bg=BG)
        content.pack(fill="both", expand=True, padx=1, pady=1)

        header = tk.Frame(content, bg=HEADER, height=42, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title_label = tk.Label(header, text=text["title"], bg=HEADER, fg="#ffe09a", font=("Noto Sans KR", 13, "bold"), padx=14)
        title_label.pack(side="left", fill="y")
        self.location_label = tk.Label(header, text="", bg=HEADER, fg=TEXT, font=("Noto Sans KR", 10))
        self.location_label.pack(side="right", fill="y", padx=14)
        self.monster_overlay_button = tk.Button(
            header, command=self.toggle_monster_overlay,
            relief="flat", bd=0, padx=10, pady=2,
            bg="#3b3022", fg="#f3d68f", activebackground="#6b5537",
            activeforeground="#fff4d2", font=("Noto Sans KR", 8, "bold"), cursor="hand2",
        )
        self.monster_overlay_button.pack(side="right", fill="y", pady=7)
        self.update_monster_overlay_button()
        for widget in (header, title_label, self.location_label):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag_window)

        filters = tk.Frame(content, bg=PANEL, padx=12, pady=8)
        filters.pack(fill="x", padx=10)
        self.search_var = tk.StringVar()
        self.map_var = tk.StringVar(value=text["all_maps"])
        self.map_sort_var = tk.StringVar(value="name")
        self.attack_var = tk.StringVar(value=text["all"])
        self.weakness_var = tk.StringVar(value=text["all"])
        self.drop_var = tk.StringVar(value=text["all"])
        self.current_only_var = tk.BooleanVar(value=False)
        tk.Label(filters, text=text["search"], bg=PANEL, fg=MUTED).grid(row=0, column=0, sticky="w")
        search = ttk.Entry(filters, textvariable=self.search_var, width=24, style="Dictionary.TEntry")
        self.search_entry = search
        search.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        map_label_row = tk.Frame(filters, bg=PANEL)
        map_label_row.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        tk.Label(map_label_row, text=text["map"], bg=PANEL, fg=MUTED).pack(side="left")
        for value, label in (("name", text["sort_name"]), ("level", text["sort_level"])):
            tk.Radiobutton(
                map_label_row, text=label, variable=self.map_sort_var, value=value,
                command=self.map_sort_changed, bg=PANEL, fg=TEXT,
                activebackground=PANEL, activeforeground="#fff1c9",
                selectcolor="#3b3022", highlightthickness=0, bd=0,
                font=("Noto Sans KR", 8), padx=2, pady=0,
            ).pack(side="right")
        self.map_combo = ttk.Combobox(filters, textvariable=self.map_var, state="readonly", width=28, style="Dictionary.TCombobox")
        self.map_combo.grid(row=1, column=1, sticky="ew", padx=(0, 10))
        self.map_combo.bind("<<ComboboxSelected>>", self.map_filter_selected)
        tk.Label(filters, text=text["attack"], bg=PANEL, fg=MUTED).grid(row=0, column=2, sticky="w")
        self.attack_combo = ttk.Combobox(filters, textvariable=self.attack_var, state="readonly", width=17, style="Dictionary.TCombobox")
        self.attack_combo.grid(row=1, column=2, sticky="ew", padx=(0, 10))
        tk.Label(filters, text=text["weakness"], bg=PANEL, fg=MUTED).grid(row=0, column=3, sticky="w")
        self.weakness_combo = ttk.Combobox(filters, textvariable=self.weakness_var, state="readonly", width=17, style="Dictionary.TCombobox")
        self.weakness_combo.grid(row=1, column=3, sticky="ew", padx=(0, 10))
        tk.Label(filters, text=text["drops"], bg=PANEL, fg=MUTED).grid(row=0, column=4, sticky="w")
        self.drop_combo = ttk.Combobox(
            filters, textvariable=self.drop_var, state="readonly", width=17,
            style="Dictionary.TCombobox",
        )
        self.drop_combo.grid(row=1, column=4, sticky="ew")
        filters.columnconfigure(0, weight=1)
        self.search_var.trace_add("write", lambda *_: self.schedule_search_refresh())
        for variable in (self.attack_var, self.weakness_var, self.drop_var):
            variable.trace_add("write", lambda *_: self.refresh_list())

        card_header = tk.Frame(content, bg=BG, padx=12, pady=4)
        card_header.pack(fill="x", padx=10)
        self.minimum_level_notice = tk.Label(
            card_header, text=text["minimum_level_notice"],
            bg=BG, fg=MUTED, anchor="w", font=("Noto Sans KR", 8),
        )
        self.result_label = tk.Label(card_header, text="", bg=BG, fg=GOLD, font=("Noto Sans KR", 9, "bold"))
        self.result_label.pack(side="right")
        footer = tk.Frame(content, bg=PANEL, height=44, padx=10, pady=7)
        footer.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        footer.pack_propagate(False)
        close_button = tk.Button(
            footer, text=text["close"], command=window.withdraw,
            bg="#3b3022", fg="#f3d68f", activebackground=HEADER, activeforeground="#fff4d2",
            relief="flat", bd=0, padx=18, pady=5, font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        )
        close_button.pack(side="right", fill="y")
        self.current_toggle_button = tk.Button(
            footer, command=self.toggle_current_only,
            relief="flat", bd=0, padx=15, pady=5,
            font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        )
        self.current_toggle_button.pack(side="right", fill="y", padx=(0, 7))
        self.update_current_toggle()
        if self.language_provider() == "JP":
            tk.Label(
                footer,
                text="※日本語版 調査協力：セリシア さん",
                bg=PANEL,
                fg=MUTED,
                anchor="w",
                font=("Noto Sans KR", 9),
            ).pack(side="left", fill="y", padx=(4, 0))
        body = tk.Frame(content, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.card_canvas = tk.Canvas(body, bg=BG, bd=0, highlightthickness=0)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.card_canvas.yview, style="Dictionary.Vertical.TScrollbar")
        self.card_canvas.configure(yscrollcommand=scroll.set)
        self.card_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.cards_frame = tk.Frame(self.card_canvas, bg=BG, padx=7, pady=7)
        self.cards_window = self.card_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", self.sync_card_scrollregion)
        self.card_canvas.bind("<Configure>", self.resize_cards_frame)
        self.card_canvas.bind("<Enter>", lambda _event: self.card_canvas.bind_all("<MouseWheel>", self.scroll_cards))
        self.card_canvas.bind("<Leave>", lambda _event: self.card_canvas.unbind_all("<MouseWheel>"))
        self.populate_filters()

    def sync_card_scrollregion(self, _event=None):
        self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all"))

    def resize_cards_frame(self, event):
        self.card_canvas.itemconfigure(self.cards_window, width=event.width)

    def scroll_cards(self, event):
        bounds = self.card_canvas.bbox("all")
        content_height = bounds[3] - bounds[1] if bounds else 0
        if content_height <= self.card_canvas.winfo_height():
            self.card_canvas.yview_moveto(0)
            return "break"
        self.card_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def start_drag(self, event):
        if self.window:
            self.drag_origin = event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y()

    def drag_window(self, event):
        if self.window and self.drag_origin:
            sx, sy, wx, wy = self.drag_origin
            self.window.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")

    def place_window(self):
        if not self.window:
            return
        self.window.update_idletasks()
        width, height = 1120, 720
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            left, top, right, bottom = rect
            x = left + (right - left - width) // 2
            y = top + (bottom - top - height) // 2
        else:
            x = max(0, (self.window.winfo_screenwidth() - width) // 2)
            y = max(0, (self.window.winfo_screenheight() - height) // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(self.window, owner, x, y)
        else:
            self.window.lift()

    def monster_overlay_enabled(self):
        return bool(self.settings.get("monster_list_overlay_enabled", False))

    def update_monster_overlay_button(self):
        button = getattr(self, "monster_overlay_button", None)
        if not button:
            return
        enabled = self.monster_overlay_enabled()
        key = "monster_overlay_on" if enabled else "monster_overlay_off"
        button.configure(bg="#8a6a36" if enabled else "#3b3022", text=self.texts()[key])

    def toggle_monster_overlay(self):
        enabled = not self.monster_overlay_enabled()
        self.settings["monster_list_overlay_enabled"] = enabled
        if not enabled:
            self.monster_overlay_adjusting = False
            self.monster_overlay_drag_origin = None
            self.monster_overlay_resize_origin = None
        if self.save_settings:
            self.save_settings()
        self.update_monster_overlay_button()
        self.monster_overlay_map_id = None
        self.refresh_monster_overlay(schedule_next=False)

    def refresh_monster_overlay(self, schedule_next=True):
        try:
            if not self.monster_overlay_enabled():
                self.hide_monster_overlay()
                return
            active = self.active_map_provider() if self.active_map_provider else None
            map_id = str(active.get("id", "")) if active else ""
            if not map_id:
                self.hide_monster_overlay()
                return
            if not self.monsters:
                self.reload_data()
            if map_id != self.monster_overlay_map_id or not self.monster_overlay_window:
                self.build_monster_overlay(active)
            elif self.monster_overlay_drag_origin or self.monster_overlay_resize_origin:
                return
            else:
                self.position_monster_overlay()
        finally:
            if schedule_next:
                self.master.after(500, self.refresh_monster_overlay)

    def hide_monster_overlay(self):
        self.hide_monster_overlay_tooltip()
        self.hide_monster_overlay_edit_chrome()
        window, self.monster_overlay_window = self.monster_overlay_window, None
        self.monster_overlay_map_id = None
        self.monster_overlay_images.clear()
        if window:
            try:
                if window.winfo_exists():
                    window.destroy()
            except tk.TclError:
                pass

    def monsters_for_map(self, map_record):
        map_id = str(map_record.get("id", ""))
        records = {str(record.get("id")): record for record in self.monsters}
        ordered_ids = [str(value) for value in map_record.get("monsterIds", [])]
        if ordered_ids:
            return [records[value] for value in ordered_ids if value in records]
        return [record for record in self.monsters if map_id in record.get("mapIds", [])]

    def monster_overlay_border_color(self, map_record=None):
        record = map_record or (self.active_map_provider() if self.active_map_provider else None) or {}
        map_id = str(record.get("id", ""))
        is_pk_area = bool(record.get("isPKArea"))
        if not is_pk_area and map_id:
            is_pk_area = bool(self.map_records.get(map_id, {}).get("isPKArea"))
        return PK_RED if is_pk_area else GOLD

    def build_monster_overlay(self, map_record):
        records = self.monsters_for_map(map_record)
        if not records:
            self.hide_monster_overlay()
            return
        self.hide_monster_overlay_tooltip()
        old_window = self.monster_overlay_window
        self.monster_overlay_window = None
        self.monster_overlay_images.clear()
        if self.overlay_window_exists(old_window):
            old_window.destroy()
        window = tk.Toplevel(self.master)
        self.monster_overlay_window = window
        self.monster_overlay_map_id = str(map_record.get("id", ""))
        window.overrideredirect(True)
        window.configure(bg=self.monster_overlay_border_color(map_record))
        window.attributes("-alpha", self.monster_overlay_opacity / 100.0)
        window.bind("<Button-3>", self.toggle_monster_overlay_adjustment)
        window.bind("<MouseWheel>", self.adjust_monster_overlay_opacity)
        row = tk.Frame(window, bg="#17130f", padx=3, pady=3)
        row.pack(padx=1, pady=1)
        row.bind("<Button-3>", self.toggle_monster_overlay_adjustment)
        row.bind("<MouseWheel>", self.adjust_monster_overlay_opacity)
        level_range = map_record.get("levelRange", {})
        minimum_level = level_range.get("min") if isinstance(level_range, dict) else None
        for record in records:
            photo = self.monster_overlay_photo(record)
            if not photo:
                continue
            self.monster_overlay_images.append(photo)
            label = tk.Label(row, image=photo, bg="#17130f", bd=0, padx=1, pady=1, cursor="hand2")
            label.pack(side="left", padx=2)
            label.bind("<Button-3>", self.toggle_monster_overlay_adjustment)
            label.bind("<MouseWheel>", self.adjust_monster_overlay_opacity)
            label.bind(
                "<Enter>",
                lambda event, current=record, level=minimum_level: self.show_monster_overlay_tooltip(event, current, level),
            )
            label.bind("<Leave>", self.hide_monster_overlay_tooltip)
        window.update_idletasks()
        make_noactivate_toolwindow(window)
        self.position_monster_overlay()
        if self.monster_overlay_adjusting:
            self.show_monster_overlay_edit_chrome()

    def monster_overlay_photo(self, record):
        value = str(record.get("image", "")).strip()
        if not value:
            return None
        try:
            image_size = max(32, round(64 * self.monster_overlay_scale))
            card_width = max(48, round(80 * self.monster_overlay_scale))
            panel_height = max(18, round(36 * self.monster_overlay_scale))
            row_height = panel_height // 2
            icon_size = max(8, round(14 * self.monster_overlay_scale))
            with self.assets.open(value) as stream, Image.open(stream) as source:
                sprite = ImageOps.fit(
                    ImageOps.exif_transpose(source).convert("RGBA"),
                    (image_size, image_size), method=Image.Resampling.LANCZOS,
                )
            canvas = Image.new("RGBA", (card_width, image_size + panel_height), (21, 19, 16, 235))
            sprite_left = (card_width - image_size) // 2
            canvas.alpha_composite(sprite, (sprite_left, 0))
            magic_icon_size = max(8, round(16 * self.monster_overlay_scale))
            magic_gap = max(1, round(self.monster_overlay_scale))
            magic_x = sprite_left + image_size - magic_icon_size - 1
            magic_y = 1
            for magic_id in record.get("magicAttackIds", []):
                try:
                    with self.assets.open(f"assets/icons/godinavi/{magic_id}.png") as stream, Image.open(stream) as magic_source:
                        magic_icon = magic_source.convert("RGBA").resize(
                            (magic_icon_size, magic_icon_size), Image.Resampling.NEAREST,
                        )
                    canvas.alpha_composite(magic_icon, (magic_x, magic_y))
                    magic_y += magic_icon_size + magic_gap
                except (OSError, ValueError, KeyError):
                    continue
            draw = ImageDraw.Draw(canvas)
            font_size = max(6, round(8 * self.monster_overlay_scale))
            font = self.monster_overlay_badge_fonts.get(font_size)
            if font is None:
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
                except OSError:
                    font = ImageFont.load_default()
                self.monster_overlay_badge_fonts[font_size] = font
            panel_top = image_size
            draw.rectangle(
                (0, panel_top, card_width - 1, image_size + panel_height - 1),
                fill="#2a2118", outline="#6b5537", width=1,
            )
            draw.line(
                (1, panel_top + row_height, card_width - 2, panel_top + row_height),
                fill="#493b2b", width=1,
            )
            weakness_ids = record.get("weaknessAttributeIds", []) or ["none"]
            icon_specs = (
                ("ATK", record.get("attackAttributeIds", []), panel_top),
                (
                    "WEAK",
                    weakness_ids,
                    panel_top + row_height,
                ),
            )
            caption_width = max(draw.textlength("ATK", font=font), draw.textlength("WEAK", font=font))
            caption_right = 4 + caption_width
            for caption, attribute_ids, row_top in icon_specs:
                caption_y = row_top + row_height // 2
                draw.text(
                    (4, caption_y), caption, font=font, anchor="lm",
                    fill="#f1e5c7", stroke_width=1, stroke_fill="#17130f",
                )
                colon_x = caption_right + max(1, round(2 * self.monster_overlay_scale))
                draw.text(
                    (colon_x, caption_y), ":", font=font, anchor="lm",
                    fill="#f1e5c7", stroke_width=1, stroke_fill="#17130f",
                )
                colon_box = draw.textbbox((colon_x, caption_y), ":", font=font, anchor="lm", stroke_width=1)
                start_x = round(colon_box[2] + max(1, round(2 * self.monster_overlay_scale)))
                y = row_top + max(1, (row_height - icon_size) // 2)
                gap = max(1, round(2 * self.monster_overlay_scale))
                cursor_x = start_x
                for attribute_id in attribute_ids:
                    if str(attribute_id) == "none":
                        cross_width = max(1, round(2 * self.monster_overlay_scale))
                        inset = max(1, round(self.monster_overlay_scale))
                        draw.line(
                            (cursor_x + inset, y + inset, cursor_x + icon_size - inset - 1, y + icon_size - inset - 1),
                            fill="#ff3448", width=cross_width,
                        )
                        draw.line(
                            (cursor_x + icon_size - inset - 1, y + inset, cursor_x + inset, y + icon_size - inset - 1),
                            fill="#ff3448", width=cross_width,
                        )
                        cursor_x += icon_size + gap
                        continue
                    if str(attribute_id) == "all_non_neutral":
                        all_y = y + icon_size // 2
                        draw.text(
                            (cursor_x, all_y), "ALL", font=font, anchor="lm",
                            fill="#ffd65a", stroke_width=1, stroke_fill="#17130f",
                        )
                        all_box = draw.textbbox(
                            (cursor_x, all_y), "ALL", font=font, anchor="lm", stroke_width=1,
                        )
                        cursor_x = round(all_box[2] + gap)
                        with self.assets.open("assets/icons/monster_attributes/neutral.png") as stream, Image.open(stream) as icon_source:
                            icon = icon_source.convert("RGBA").resize((icon_size, icon_size), Image.Resampling.NEAREST)
                        canvas.alpha_composite(icon, (cursor_x, y))
                        cross_width = max(1, round(2 * self.monster_overlay_scale))
                        inset = max(1, round(self.monster_overlay_scale))
                        draw.line(
                            (cursor_x + inset, y + inset, cursor_x + icon_size - inset - 1, y + icon_size - inset - 1),
                            fill="#ff3448", width=cross_width,
                        )
                        draw.line(
                            (cursor_x + icon_size - inset - 1, y + inset, cursor_x + inset, y + icon_size - inset - 1),
                            fill="#ff3448", width=cross_width,
                        )
                        cursor_x += icon_size + gap
                        continue
                    filename = ATTRIBUTE_ICON_FILES.get(str(attribute_id))
                    if not filename:
                        continue
                    with self.assets.open(f"assets/icons/monster_attributes/{filename}") as stream, Image.open(stream) as icon_source:
                        icon = icon_source.convert("RGBA").resize((icon_size, icon_size), Image.Resampling.NEAREST)
                    canvas.alpha_composite(icon, (cursor_x, y))
                    cursor_x += icon_size + gap
            return ImageTk.PhotoImage(canvas, master=self.master)
        except Exception:
            return None

    def position_monster_overlay(self):
        window = self.monster_overlay_window
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if not window or not rect:
            return
        window.update_idletasks()
        left, top, right, bottom = rect
        width, height = window.winfo_reqwidth(), window.winfo_reqheight()
        saved_x = self.settings.get("monster_list_overlay_offset_x")
        saved_y = self.settings.get("monster_list_overlay_offset_y")
        x = left + int(saved_x) if isinstance(saved_x, (int, float)) else left + max(0, (right - left - width) // 2)
        y = top + int(saved_y) if isinstance(saved_y, (int, float)) else top + 8
        x = max(left, min(x, right - width))
        y = max(top, min(y, bottom - height))
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(window, owner, x, y)
        else:
            window.geometry(f"+{x}+{y}")
        if self.monster_overlay_adjusting:
            self.position_monster_overlay_edit_chrome()

    def show_monster_overlay_tooltip(self, event, record, minimum_level):
        if self.monster_overlay_adjusting:
            return
        self.hide_monster_overlay_tooltip()
        tooltip = tk.Toplevel(self.monster_overlay_window)
        self.monster_overlay_tooltip = tooltip
        tooltip.overrideredirect(True)
        tooltip.configure(bg=GOLD)
        name = self.localized_name(record.get("names", {}), record.get("id", ""))
        level = minimum_level if isinstance(minimum_level, int) and not isinstance(minimum_level, bool) else "?"
        attacks = ", ".join(self.catalog_name("attributes.json", value) for value in record.get("attackAttributeIds", [])) or "-"
        weaknesses = ", ".join(self.catalog_name("attributes.json", value) for value in record.get("weaknessAttributeIds", [])) or "-"
        text = f"{name} (Lv.{level}~)\n{self.texts()['attack']} : {attacks}\n{self.texts()['weakness']} : {weaknesses}"
        tk.Label(
            tooltip, text=text, justify="left", bg="#2a2118", fg="#fff1c9",
            padx=10, pady=7, font=("Noto Sans KR", 9),
        ).pack(padx=1, pady=1)
        tooltip.update_idletasks()
        x, y = event.x_root + 12, event.y_root + 12
        tooltip.geometry(f"+{x}+{y}")
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(tooltip, owner, x, y)

    def hide_monster_overlay_tooltip(self, _event=None):
        tooltip, self.monster_overlay_tooltip = self.monster_overlay_tooltip, None
        if tooltip:
            try:
                if tooltip.winfo_exists():
                    tooltip.destroy()
            except tk.TclError:
                pass

    @staticmethod
    def overlay_window_exists(window):
        try:
            return bool(window and window.winfo_exists())
        except tk.TclError:
            return False

    def save_monster_overlay_settings(self):
        self.settings["monster_list_overlay_scale"] = self.monster_overlay_scale
        self.settings["monster_list_overlay_opacity_percent"] = self.monster_overlay_opacity
        if self.save_settings:
            self.save_settings()

    def toggle_monster_overlay_adjustment(self, _event=None):
        if not self.overlay_window_exists(self.monster_overlay_window):
            return "break"
        self.monster_overlay_adjusting = not self.monster_overlay_adjusting
        self.monster_overlay_drag_origin = None
        self.monster_overlay_resize_origin = None
        self.hide_monster_overlay_tooltip()
        if self.monster_overlay_adjusting:
            self.show_monster_overlay_edit_chrome()
        else:
            self.hide_monster_overlay_edit_chrome()
            self.save_monster_overlay_settings()
        return "break"

    def begin_monster_overlay_drag(self, event):
        if not self.monster_overlay_adjusting or not self.overlay_window_exists(self.monster_overlay_window):
            return
        self.monster_overlay_drag_origin = (
            event.x_root, event.y_root,
            self.monster_overlay_window.winfo_x(), self.monster_overlay_window.winfo_y(),
        )
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def drag_monster_overlay(self, event):
        if not self.monster_overlay_drag_origin:
            return
        start_x, start_y, origin_x, origin_y = self.monster_overlay_drag_origin
        x = origin_x + event.x_root - start_x
        y = origin_y + event.y_root - start_y
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            left, top, right, bottom = rect
            x = max(left, min(x, right - self.monster_overlay_window.winfo_width()))
            y = max(top, min(y, bottom - self.monster_overlay_window.winfo_height()))
        self.monster_overlay_window.geometry(f"+{round(x)}+{round(y)}")
        self.position_monster_overlay_edit_chrome()

    def end_monster_overlay_drag(self, event):
        if not self.monster_overlay_drag_origin:
            return
        self.monster_overlay_drag_origin = None
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.save_monster_overlay_position()

    def save_monster_overlay_position(self):
        window = self.monster_overlay_window
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if not self.overlay_window_exists(window) or not rect:
            return
        self.settings["monster_list_overlay_offset_x"] = window.winfo_x() - rect[0]
        self.settings["monster_list_overlay_offset_y"] = window.winfo_y() - rect[1]
        self.save_monster_overlay_settings()

    def adjust_monster_overlay_opacity(self, event):
        if not self.monster_overlay_adjusting or not event.delta:
            return None
        self.monster_overlay_opacity = max(
            50, min(100, self.monster_overlay_opacity + (5 if event.delta > 0 else -5)),
        )
        self.settings["monster_list_overlay_opacity_percent"] = self.monster_overlay_opacity
        if self.overlay_window_exists(self.monster_overlay_window):
            self.monster_overlay_window.attributes("-alpha", self.monster_overlay_opacity / 100.0)
        return "break"

    def begin_monster_overlay_resize(self, event):
        if not self.monster_overlay_adjusting or not self.overlay_window_exists(self.monster_overlay_window):
            return
        self.monster_overlay_resize_origin = (
            event.x_root, event.y_root, self.monster_overlay_scale,
            self.monster_overlay_window.winfo_width(), self.monster_overlay_window.winfo_height(),
        )
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            self.settings["monster_list_overlay_offset_x"] = self.monster_overlay_window.winfo_x() - rect[0]
            self.settings["monster_list_overlay_offset_y"] = self.monster_overlay_window.winfo_y() - rect[1]
        try:
            event.widget.grab_set()
        except tk.TclError:
            pass

    def drag_monster_overlay_resize(self, event):
        if not self.monster_overlay_resize_origin:
            return
        start_x, start_y, start_scale, start_width, start_height = self.monster_overlay_resize_origin
        horizontal_ratio = (start_width + event.x_root - start_x) / max(1, start_width)
        vertical_ratio = (start_height + event.y_root - start_y) / max(1, start_height)
        pending_scale = max(0.5, min(2.0, round(start_scale * (horizontal_ratio + vertical_ratio) / 2.0, 2)))
        if abs(pending_scale - self.monster_overlay_scale) < 0.01:
            return
        self.monster_overlay_scale = pending_scale
        self.settings["monster_list_overlay_scale"] = self.monster_overlay_scale
        active = self.active_map_provider() if self.active_map_provider else None
        if active:
            self.build_monster_overlay(active)

    def end_monster_overlay_resize(self, event):
        if not self.monster_overlay_resize_origin:
            return
        try:
            event.widget.grab_release()
        except tk.TclError:
            pass
        self.monster_overlay_resize_origin = None
        self.save_monster_overlay_position()
        self.save_monster_overlay_settings()

    def ensure_monster_overlay_header(self):
        if self.overlay_window_exists(self.monster_overlay_header_window):
            self.monster_overlay_header_window.configure(bg=self.monster_overlay_border_color())
            if self.monster_overlay_header_label is not None:
                self.monster_overlay_header_label.configure(text=self.texts()["monster_overlay_adjust"])
            return self.monster_overlay_header_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        window.configure(bg=self.monster_overlay_border_color())
        label = tk.Label(
            window, text=self.texts()["monster_overlay_adjust"], bg=HEADER, fg="#fff1c9",
            anchor="w", padx=8, pady=4, cursor="fleur", font=("Noto Sans KR", 8, "bold"),
        )
        label.pack(fill="both", expand=True, padx=1, pady=1)
        label.bind("<ButtonPress-1>", self.begin_monster_overlay_drag)
        label.bind("<B1-Motion>", self.drag_monster_overlay)
        label.bind("<ButtonRelease-1>", self.end_monster_overlay_drag)
        label.bind("<MouseWheel>", self.adjust_monster_overlay_opacity)
        self.monster_overlay_header_label = label
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.monster_overlay_header_window = window
        return window

    def ensure_monster_overlay_grip(self):
        if self.overlay_window_exists(self.monster_overlay_grip_window):
            for child in self.monster_overlay_grip_window.winfo_children():
                child.configure(highlightbackground=self.monster_overlay_border_color())
            return self.monster_overlay_grip_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        grip = tk.Canvas(
            window, width=16, height=16, bg=HEADER, highlightthickness=1,
            highlightbackground=self.monster_overlay_border_color(), cursor="size_nw_se",
        )
        grip.pack(fill="both", expand=True)
        grip.create_line(4, 14, 14, 4, fill="#fff1c9", width=1)
        grip.create_line(9, 14, 14, 9, fill="#fff1c9", width=1)
        grip.bind("<ButtonPress-1>", self.begin_monster_overlay_resize)
        grip.bind("<B1-Motion>", self.drag_monster_overlay_resize)
        grip.bind("<ButtonRelease-1>", self.end_monster_overlay_resize)
        grip.bind("<MouseWheel>", self.adjust_monster_overlay_opacity)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.monster_overlay_grip_window = window
        return window

    def ensure_monster_overlay_lock(self):
        if self.overlay_window_exists(self.monster_overlay_lock_window):
            self.monster_overlay_lock_window.configure(bg=self.monster_overlay_border_color())
            return self.monster_overlay_lock_window
        window = tk.Toplevel(self.master)
        window.overrideredirect(True)
        window.configure(bg=self.monster_overlay_border_color())
        tk.Button(
            window, text="🔓", command=self.toggle_monster_overlay_adjustment,
            bg="#3b3022", fg="#fff1c9", activebackground=HEADER, activeforeground="#ffffff",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=("Segoe UI Emoji", 12),
        ).pack(fill="both", expand=True, padx=1, pady=1)
        window.withdraw()
        make_noactivate_toolwindow(window)
        self.monster_overlay_lock_window = window
        return window

    def show_monster_overlay_edit_chrome(self):
        windows = (
            self.ensure_monster_overlay_header(),
            self.ensure_monster_overlay_grip(),
            self.ensure_monster_overlay_lock(),
        )
        self.position_monster_overlay_edit_chrome()
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        for window in windows:
            window.deiconify()
            if owner:
                attach_above(window, owner, window.winfo_x(), window.winfo_y())

    def hide_monster_overlay_edit_chrome(self):
        for window in (
            self.monster_overlay_header_window,
            self.monster_overlay_grip_window,
            self.monster_overlay_lock_window,
        ):
            if self.overlay_window_exists(window):
                window.withdraw()

    def position_monster_overlay_edit_chrome(self):
        bar = self.monster_overlay_window
        if not self.overlay_window_exists(bar):
            return
        header = self.ensure_monster_overlay_header()
        grip = self.ensure_monster_overlay_grip()
        lock = self.ensure_monster_overlay_lock()
        x, y, width, height = bar.winfo_x(), bar.winfo_y(), bar.winfo_width(), bar.winfo_height()
        header_height = 28
        rect = self.target_rect_provider() if self.target_rect_provider else None
        header_y = y - header_height - 4
        if rect and header_y < rect[1]:
            header_y = y + height + 4
        header.geometry(f"{max(160, width)}x{header_height}+{x}+{header_y}")
        grip.update_idletasks()
        grip_width, grip_height = grip.winfo_reqwidth(), grip.winfo_reqheight()
        grip.geometry(f"+{x + width - grip_width}+{y + height - grip_height}")
        lock.update_idletasks()
        lock_width, lock_height = lock.winfo_reqwidth(), lock.winfo_reqheight()
        lock_x, lock_y = x + width + 6, y
        if rect and lock_x + lock_width > rect[2]:
            lock_x = x - lock_width - 6
        lock.geometry(f"+{lock_x}+{lock_y}")

    def localized_name(self, names, fallback=""):
        if not isinstance(names, dict):
            return fallback
        locale = self.locale()
        return names.get(locale) or names.get("en") or names.get("ko") or names.get("ja") or fallback

    def _escape_close(self):
        if getattr(self, "habitat_window", None) and self.habitat_window.winfo_exists():
            self.dismiss_habitats()
        elif self.window and self.window.winfo_exists():
            self.window.withdraw()

    def map_name(self, map_id):
        record = self.map_records.get(str(map_id), {})
        values = record.get("names", {}).get(self.locale(), [])
        if isinstance(values, list):
            return str(values[0]) if values else str(map_id)
        return str(values or map_id)

    def map_name_with_pk(self, map_id):
        prefix = "[PK] " if self.map_records.get(str(map_id), {}).get("isPKArea") else ""
        return f"{prefix}{self.map_name(map_id)}"

    def map_level_text(self, map_id):
        record = self.map_records.get(str(map_id), {})
        level_range = record.get("levelRange", {})
        if not isinstance(level_range, dict):
            level_range = {}
        minimum = level_range.get("min")
        maximum = level_range.get("max")
        minimum_text = str(minimum) if isinstance(minimum, int) and not isinstance(minimum, bool) else "?"
        maximum_text = str(maximum) if isinstance(maximum, int) and not isinstance(maximum, bool) else "?"
        return f"{minimum_text}-{maximum_text}"

    def map_display_name(self, map_id):
        return f"{self.map_name_with_pk(map_id)} ({self.map_level_text(map_id)})"

    def monster_minimum_level(self, record):
        levels = []
        for map_id in record.get("mapIds", []):
            level_range = self.map_records.get(str(map_id), {}).get("levelRange", {})
            minimum = level_range.get("min") if isinstance(level_range, dict) else None
            if isinstance(minimum, int) and not isinstance(minimum, bool):
                levels.append(minimum)
        return min(levels) if levels else None

    def card_font(self, size, weight="normal"):
        key = (int(size), str(weight))
        font = self.card_font_cache.get(key)
        if font is None:
            font = tkfont.Font(
                root=self.master, family="Noto Sans KR", size=int(size), weight=weight,
            )
            self.card_font_cache[key] = font
        return font

    def fitted_card_name_font(self, value, maximum_width):
        # Measure with the actual Tk font renderer. Most names retain 13px;
        # only text that would enter the reserved level-label area is reduced.
        for size in range(13, 7, -1):
            font = self.card_font(size, "bold")
            if font.measure(str(value)) <= maximum_width:
                return font
        return self.card_font(8, "bold")

    def sorted_map_ids(self):
        def has_known_level(map_id):
            level_range = self.map_records.get(str(map_id), {}).get("levelRange", {})
            if not isinstance(level_range, dict):
                return False
            minimum = level_range.get("min")
            maximum = level_range.get("max")
            return all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in (minimum, maximum)
            )

        # Regions without a complete level range are not useful in the
        # compendium's region picker. Keep them in map_records so current-map
        # and habitat information can still identify them elsewhere.
        map_ids = [map_id for map_id in self.map_records if has_known_level(map_id)]
        if self.map_sort_var.get() == "level":
            def level_key(map_id):
                level_range = self.map_records.get(str(map_id), {}).get("levelRange", {})
                minimum = level_range.get("min") if isinstance(level_range, dict) else None
                return (minimum, self.map_name(map_id).casefold())
            return sorted(map_ids, key=level_key)
        return sorted(map_ids, key=lambda value: self.map_name(value).casefold())

    def catalog_name(self, filename, item_id):
        item = self.catalogs.get(filename, {}).get(item_id, {})
        return self.localized_name(item.get("names", {}), item_id)

    def populate_filters(self):
        text = self.texts()
        previous_map_id = getattr(self, "map_choices", {}).get(self.map_var.get())
        self.map_choices = {text["all_maps"]: None}
        for map_id in self.sorted_map_ids():
            self.map_choices[self.map_display_name(map_id)] = map_id
        self.map_combo.configure(values=tuple(self.map_choices))
        if previous_map_id is not None:
            selected_label = next(
                (label for label, map_id in self.map_choices.items() if str(map_id) == str(previous_map_id)),
                text["all_maps"],
            )
            if self.map_var.get() != selected_label:
                self.map_var.set(selected_label)
        elif self.map_var.get() not in self.map_choices:
            self.map_var.set(text["all_maps"])
        attributes = self.catalogs.get("attributes.json", {})
        self.attribute_choices = {text["all"]: None}
        for item_id, item in sorted(attributes.items(), key=lambda pair: self.localized_name(pair[1].get("names", {}), pair[0])):
            self.attribute_choices[self.localized_name(item.get("names", {}), item_id)] = item_id
        choices = tuple(self.attribute_choices)
        self.attack_combo.configure(values=choices)
        self.weakness_combo.configure(values=choices)
        items = self.catalogs.get("items.json", {})
        self.drop_choices = {text["all"]: None}
        for item_id, item in sorted(
            items.items(),
            key=lambda pair: self.localized_name(pair[1].get("names", {}), pair[0]),
        ):
            self.drop_choices[self.localized_name(item.get("names", {}), item_id)] = item_id
        self.drop_combo.configure(values=tuple(self.drop_choices))

    def map_sort_changed(self):
        self.populate_filters()
        self.refresh_list()

    def apply_initial_scope(self):
        if not self.window or not self.window.winfo_exists():
            return
        active = self.active_map_provider() if self.active_map_provider else None
        map_id = str(active.get("id")) if active else ""
        name = self.map_display_name(map_id) if map_id else self.texts()["no_map"]
        self.location_label.configure(text=name)
        has_monsters = bool(map_id and any(map_id in record.get("mapIds", []) for record in self.monsters))
        self.current_only_var.set(has_monsters)
        self.update_current_toggle()
        self.map_var.set(self.texts()["all_maps"])
        self.refresh_list()

    def toggle_current_only(self):
        self.current_only_var.set(not self.current_only_var.get())
        self.update_current_toggle()
        self.refresh_list()

    def map_filter_selected(self, _event=None):
        if self.current_only_var.get():
            self.current_only_var.set(False)
            self.update_current_toggle()
        self.refresh_list()

    def update_current_toggle(self):
        button = getattr(self, "current_toggle_button", None)
        if not button:
            return
        enabled = self.current_only_var.get()
        button.configure(
            text=f"{self.texts()['current_only']}  {'ON' if enabled else 'OFF'}",
            bg="#8a6a36" if enabled else "#3b3732",
            fg="#fff1c9" if enabled else "#aaa092",
            activebackground="#a27d42" if enabled else "#4a4540",
            activeforeground="#fff8e6",
        )

    def schedule_search_refresh(self):
        if not self.window or not self.window.winfo_exists():
            return
        if self.search_refresh_job is not None:
            try:
                self.window.after_cancel(self.search_refresh_job)
            except tk.TclError:
                pass
        # A short debounce still feels immediate, but prevents every key event
        # in a fast IME/keyboard sequence from rebuilding all card widgets.
        self.search_refresh_job = self.window.after(90, self.run_search_refresh)

    def run_search_refresh(self):
        self.search_refresh_job = None
        self.refresh_list()

    def refresh_list(self):
        if not self.window or not hasattr(self, "cards_frame"):
            return
        query = self.search_var.get().strip().casefold()
        selected_map = self.map_choices.get(self.map_var.get())
        attack_id = self.attribute_choices.get(self.attack_var.get())
        weakness_id = self.attribute_choices.get(self.weakness_var.get())
        drop_id = self.drop_choices.get(self.drop_var.get())
        active = self.active_map_provider() if self.active_map_provider else None
        active_id = str(active.get("id")) if active else None
        records = []
        for record in self.monsters:
            map_ids = record.get("mapIds", [])
            names = list(record.get("names", {}).values())
            aliases = [alias for values in record.get("aliases", {}).values() for alias in values]
            if query and query not in " ".join([record.get("id", ""), *names, *aliases]).casefold():
                continue
            if selected_map and selected_map not in map_ids:
                continue
            if self.current_only_var.get() and active_id not in map_ids:
                continue
            if attack_id and attack_id not in record.get("attackAttributeIds", []):
                continue
            if weakness_id and weakness_id not in record.get("weaknessAttributeIds", []):
                continue
            if drop_id and drop_id not in record.get("dropItemIds", []):
                continue
            records.append(record)
        feature_filter_active = bool(attack_id or weakness_id or drop_id)
        feature_sort = feature_filter_active and not selected_map and not self.current_only_var.get()
        if feature_sort:
            if not self.minimum_level_notice.winfo_manager():
                self.minimum_level_notice.pack(side="left", fill="x", expand=True)
        elif self.minimum_level_notice.winfo_manager():
            self.minimum_level_notice.pack_forget()
        if feature_sort:
            def feature_sort_key(record):
                minimum_level = self.monster_minimum_level(record)
                return (
                    minimum_level is None,
                    minimum_level if minimum_level is not None else 0,
                    self.localized_name(record.get("names", {}), record.get("id", "")).casefold(),
                )
            records.sort(key=feature_sort_key)
        else:
            records.sort(key=lambda record: self.localized_name(record.get("names", {}), record.get("id", "")).casefold())
        context_map_id = selected_map or (active_id if self.current_only_var.get() else None)
        self.render_cards(records, context_map_id, show_minimum_level=feature_sort)

    def render_cards(self, records, context_map_id=None, show_minimum_level=False):
        self.hide_magic_tooltip()
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.card_images.clear()
        self.visible_ids = [record["id"] for record in records]
        self.result_label.configure(text=self.texts()["count"].format(count=len(records)))
        for column in range(CARD_COLUMNS):
            self.cards_frame.columnconfigure(column, weight=1, uniform="monster_cards")
        if not records:
            tk.Label(
                self.cards_frame,
                text=self.texts()["no_results"],
                bg=BG, fg=MUTED, font=("Noto Sans KR", 12), pady=40,
            ).grid(row=0, column=0, columnspan=CARD_COLUMNS, sticky="ew")
        for index, record in enumerate(records):
            self.build_card(
                record,
                index // CARD_COLUMNS,
                index % CARD_COLUMNS,
                context_map_id,
                show_minimum_level,
            )
        self.cards_frame.update_idletasks()
        self.sync_card_scrollregion()
        self.card_canvas.yview_moveto(0)

    def build_card(self, record, row, column, context_map_id, show_minimum_level=False):
        text = self.texts()
        card = tk.Canvas(
            self.cards_frame,
            bg=BG, width=CARD_WIDTH, height=CARD_HEIGHT,
            bd=0, highlightthickness=0, cursor="hand2",
        )
        # Do not stretch cards with their grid column; a one-pixel remainder
        # between columns would otherwise make card widths differ.
        card.grid(row=row, column=column, sticky="n", padx=4, pady=4)
        shape = self.rounded_rectangle(
            card, 2, 2, CARD_WIDTH - 2, CARD_HEIGHT - 2, radius=14,
            fill="#211c18", outline="#5c5044", width=1,
        )
        image_box = tk.Frame(
            card, bg="#151310", width=CARD_IMAGE_SIZE, height=CARD_IMAGE_SIZE,
        )
        image_box.pack_propagate(False)
        image_label = tk.Label(
            image_box, text=text["no_image"], bg="#151310", fg="#8e8170",
            anchor="center", justify="center", font=("Noto Sans KR", 10, "bold"),
            bd=0, highlightthickness=0, padx=0, pady=0,
        )
        image_label.pack(fill="both", expand=True)
        card.create_window(
            CARD_IMAGE_X, CARD_IMAGE_Y, window=image_box, anchor="nw",
            width=CARD_IMAGE_SIZE, height=CARD_IMAGE_SIZE,
        )
        self.load_card_image(record, image_label)
        drop_icon_widgets = self.load_drop_icons(record, image_box)
        name = self.localized_name(record.get("names", {}), record.get("id", ""))
        minimum_level = self.monster_minimum_level(record) if show_minimum_level else None
        level_text = (
            text["minimum_region_level"].format(level=minimum_level)
            if minimum_level is not None else ""
        )
        level_font = self.card_font(9, "bold")
        available_right = CARD_WIDTH - 16
        if level_text:
            available_right -= level_font.measure(level_text) + 12
        name_width = max(80, available_right - CARD_TEXT_X)
        name_font = self.fitted_card_name_font(name, name_width)
        card.create_text(
            CARD_TEXT_X, 14, text=name, fill="#f2d995", anchor="nw",
            width=name_width, font=name_font,
        )
        if level_text:
            card.create_text(
                CARD_WIDTH - 16, 17, text=level_text,
                fill=GOLD, anchor="ne", font=level_font,
            )
        attack_ids = record.get("attackAttributeIds", [])
        weakness_ids = record.get("weaknessAttributeIds", [])
        magic = record.get("magicAttack")
        self.draw_attribute_row(card, text["attack"], attack_ids, 48)
        self.draw_attribute_row(card, text["weakness"], weakness_ids, 76)
        magic_icon_widgets = []
        if magic:
            magic_icon_widgets = self.draw_magic_icons(card, record.get("magicAttackIds", []), 104)
        elif magic is None:
            card.create_text(
                CARD_TEXT_X, 104, text=f"{text['magic']}: {text['unknown']}",
                fill="#ddd4c6", anchor="nw", width=348,
                font=("Noto Sans KR", 10),
            )

        def click(_event, current=record, context=context_map_id):
            self.hide_magic_tooltip()
            self.show_habitats(current, context)

        hover = lambda _event: card.after_idle(lambda: self.sync_card_highlight(card, shape))
        for widget in (card, image_box, image_label, *drop_icon_widgets, *magic_icon_widgets):
            widget.bind("<Button-1>", click)
            widget.bind("<Enter>", hover, add="+")
            widget.bind("<Leave>", hover, add="+")

    def draw_attribute_row(self, card, label, attribute_ids, y):
        font = ("Noto Sans KR", 10)
        x = CARD_TEXT_X

        def append(value, color="#ddd4c6"):
            nonlocal x
            item = card.create_text(x, y, text=value, fill=color, anchor="nw", font=font)
            bounds = card.bbox(item)
            if bounds:
                x = bounds[2]

        append(f"{label}: ")
        if not attribute_ids:
            append("-")
            return
        for index, attribute_id in enumerate(attribute_ids):
            if index:
                append(", ")
            append(
                self.catalog_name("attributes.json", attribute_id),
                ATTRIBUTE_COLORS.get(attribute_id, "#ddd4c6"),
            )

    def draw_magic_icons(self, card, magic_ids, y):
        font = ("Noto Sans KR", 10)
        label_item = card.create_text(
            CARD_TEXT_X, y, text=f"{self.texts()['magic']}: ",
            fill="#ddd4c6", anchor="nw", font=font,
        )
        bounds = card.bbox(label_item)
        x = (bounds[2] + 2) if bounds else 178
        widgets = []
        if not magic_ids:
            card.create_text(
                x, y, text=self.texts()["unknown"], fill="#ddd4c6",
                anchor="nw", font=font,
            )
            return widgets

        for magic_id in magic_ids:
            magic_id = str(magic_id)
            filename = f"{magic_id}.png"
            photo = self.cached_photo(
                self.bundle_dir / "assets" / "icons" / "godinavi" / filename,
                (24, 24), Image.Resampling.NEAREST,
            )
            if photo:
                self.card_images.append(photo)
            widget = tk.Label(
                card,
                image=photo if photo else "",
                text="" if photo else "?",
                bg="#211c18", fg="#f2d995",
                bd=0, highlightthickness=0, padx=0, pady=0,
                font=("Noto Sans KR", 10, "bold"), cursor="hand2",
            )
            card.create_window(x, y + 4, window=widget, anchor="nw", width=24, height=24)
            full_name = self.catalog_name("magic_attacks.json", magic_id)
            widget.bind(
                "<Enter>",
                lambda event, name=full_name: self.show_magic_tooltip(event, name),
                add="+",
            )
            widget.bind("<Leave>", lambda _event: self.hide_magic_tooltip(), add="+")
            widgets.append(widget)
            x += 28
        return widgets

    def show_magic_tooltip(self, event, name):
        self.hide_magic_tooltip()
        if not self.window or not self.window.winfo_exists():
            return
        tooltip = tk.Toplevel(self.window)
        self.magic_tooltip = tooltip
        tooltip.overrideredirect(True)
        tooltip.transient(self.window)
        tooltip.configure(bg=GOLD)
        tk.Label(
            tooltip, text=name, bg="#2a2118", fg="#fff1c9",
            padx=9, pady=5, bd=0, font=("Noto Sans KR", 9),
        ).pack(padx=1, pady=1)
        tooltip.update_idletasks()
        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty() - tooltip.winfo_reqheight() - 4
        tooltip.geometry(f"+{max(0, x)}+{max(0, y)}")
        attach_above(
            tooltip,
            native_window_handle(self.window),
            max(0, x), max(0, y),
        )

    def hide_magic_tooltip(self):
        tooltip = self.magic_tooltip
        self.magic_tooltip = None
        if tooltip:
            try:
                if tooltip.winfo_exists():
                    tooltip.destroy()
            except tk.TclError:
                pass

    @staticmethod
    def rounded_rectangle(canvas, x1, y1, x2, y2, radius=12, **kwargs):
        points = (
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2,
            x1 + radius, y2, x1, y2, x1, y2 - radius,
            x1, y1 + radius, x1, y1,
        )
        return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    @staticmethod
    def sync_card_highlight(card, shape):
        x, y = card.winfo_pointerx(), card.winfo_pointery()
        try:
            hovered = card.winfo_containing(x, y)
        except tk.TclError:
            hovered = None
        active = False
        while hovered is not None:
            if hovered == card:
                active = True
                break
            hovered = getattr(hovered, "master", None)
        card.itemconfigure(
            shape,
            fill="#302820" if active else "#211c18",
            outline="#d0a757" if active else "#5c5044",
            width=2 if active else 1,
        )

    def show_habitats(self, record, context_map_id):
        self.dismiss_habitats()
        text = self.texts()
        other_ids = [value for value in record.get("mapIds", []) if str(value) != str(context_map_id)]
        habitats = [self.map_display_name(value) for value in other_ids]
        modal = tk.Toplevel(self.window)
        self.habitat_window = modal
        modal.withdraw()
        modal.title(text["other_maps"])
        modal.transient(self.window)
        modal.resizable(False, False)
        modal.overrideredirect(True)
        modal.configure(bg=GOLD)
        modal.geometry("440x320")
        modal.attributes("-topmost", True)
        outer = tk.Frame(modal, bg=BG, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(outer, bg=HEADER, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        name = self.localized_name(record.get("names", {}), record.get("id", ""))
        name_label = tk.Label(header, text=name, bg=HEADER, fg="#ffe09a", font=("Noto Sans KR", 13, "bold"), padx=14)
        name_label.pack(side="left", fill="y")
        habitat_title = tk.Label(header, text=text["other_maps"], bg=HEADER, fg=TEXT, font=("Noto Sans KR", 9), padx=14)
        habitat_title.pack(side="right", fill="y")
        modal_drag = {"value": None}

        def start_modal_drag(event):
            modal_drag["value"] = event.x_root, event.y_root, modal.winfo_x(), modal.winfo_y()

        def drag_modal(event):
            if modal_drag["value"]:
                sx, sy, wx, wy = modal_drag["value"]
                modal.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")

        for widget in (header, name_label, habitat_title):
            widget.bind("<ButtonPress-1>", start_modal_drag)
            widget.bind("<B1-Motion>", drag_modal)
        content = tk.Frame(outer, bg=PANEL, padx=14, pady=12)
        content.pack(fill="both", expand=True)
        close_button = tk.Button(
            content, text=text["close"], command=self.dismiss_habitats,
            bg="#3b3022", fg="#f3d68f", activebackground=HEADER, activeforeground="#fff4d2",
            relief="flat", bd=0, padx=14, pady=6, font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        )
        close_button.pack(side="bottom", fill="x", pady=(10, 0))
        list_frame = tk.Frame(content, bg=BG, highlightbackground=HEADER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True)
        habitat_list = tk.Listbox(
            list_frame, bg=BG, fg=TEXT, selectbackground=HEADER, selectforeground="#fff1c9",
            relief="flat", bd=0, highlightthickness=0, activestyle="none",
            font=("Noto Sans KR", 10), cursor="hand2",
        )
        habitat_scroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=habitat_list.yview,
            style="Dictionary.Vertical.TScrollbar",
        )
        habitat_list.configure(yscrollcommand=habitat_scroll.set)
        habitat_list.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        habitat_scroll.pack(side="right", fill="y")
        for habitat in habitats:
            habitat_list.insert("end", habitat)
        habitat_list.bind(
            "<Double-1>",
            lambda _event, widget=habitat_list, map_ids=tuple(other_ids):
                self.open_habitat_filter(widget, map_ids),
        )
        if not habitats:
            habitat_list.insert("end", text["no_other_maps"])
            habitat_list.configure(state="disabled", disabledforeground=MUTED)
        modal.update_idletasks()
        x = self.window.winfo_rootx() + (self.window.winfo_width() - 440) // 2
        y = self.window.winfo_rooty() + (self.window.winfo_height() - 320) // 2
        modal.geometry(f"440x320+{max(0, x)}+{max(0, y)}")
        modal.deiconify()
        modal.lift()
        self.habitat_focus_misses = 0
        self.habitat_mouse_was_down = mouse_buttons_down()
        modal.bind("<Escape>", lambda _event: self.dismiss_habitats())
        modal.bind("<Destroy>", self.on_habitat_destroy, add="+")
        # Installing this during the card click would make the opening click
        # itself count as an outside click. Activate it on the next event loop.
        modal.after_idle(self.bind_habitat_outside_click)
        # Keep keyboard focus on the dictionary. This lets the very first
        # click on its search entry work normally. Clicking outside the Tk
        # application is detected separately because bind_all cannot see it.
        modal.after(150, self.monitor_habitat_application_focus)

    def open_habitat_filter(self, habitat_list, map_ids):
        selected = habitat_list.curselection()
        if not selected or selected[0] >= len(map_ids):
            return "break"
        map_id = str(map_ids[selected[0]])
        label = next(
            (name for name, value in self.map_choices.items() if str(value) == map_id),
            self.map_display_name(map_id),
        )
        self.dismiss_habitats()
        self.current_only_var.set(False)
        self.update_current_toggle()
        self.map_var.set(label)
        # Setting the same filter value does not trigger the variable trace.
        self.refresh_list()
        # The selected Listbox is destroyed above. Explicitly return keyboard
        # focus to the dictionary so its next popup is not mistaken for an
        # unfocused application until Windows performs another focus change.
        self.window.after_idle(self.restore_dictionary_focus)
        return "break"

    def restore_dictionary_focus(self):
        if not self.window or not self.window.winfo_exists() or not self.window.winfo_viewable():
            return
        try:
            self.window.focus_set()
        except tk.TclError:
            pass

    def bind_habitat_outside_click(self):
        modal = self.habitat_window
        if not modal or not modal.winfo_exists() or self.habitat_outside_binding:
            return
        self.habitat_outside_binding = self.master.bind_all(
            "<ButtonPress-1>", self.on_habitat_global_click, add="+",
        )

    def on_habitat_global_click(self, event):
        modal = self.habitat_window
        if not modal or not modal.winfo_exists():
            return
        try:
            clicked_window = event.widget.winfo_toplevel()
        except (AttributeError, tk.TclError):
            clicked_window = None
        if clicked_window != modal:
            self.dismiss_habitats()

    def monitor_habitat_application_focus(self):
        modal = self.habitat_window
        if not modal or not modal.winfo_exists():
            return
        try:
            mouse_is_down = mouse_buttons_down()
            if mouse_is_down and not self.habitat_mouse_was_down:
                pointer_x, pointer_y = self.master.winfo_pointerxy()
                inside_modal = (
                    modal.winfo_rootx() <= pointer_x < modal.winfo_rootx() + modal.winfo_width()
                    and modal.winfo_rooty() <= pointer_y < modal.winfo_rooty() + modal.winfo_height()
                )
                if not inside_modal:
                    self.dismiss_habitats()
                    return
            self.habitat_mouse_was_down = mouse_is_down
            owner_hwnd = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
            modal_hwnd = native_window_handle(modal)
            dictionary_hwnd = native_window_handle(self.window)
            group_owner = owner_hwnd or dictionary_hwnd
            if not (
                owner_group_is_foreground(group_owner, modal_hwnd)
                or owner_group_is_foreground(group_owner, dictionary_hwnd)
            ):
                self.dismiss_habitats()
                return
            modal.after(100, self.monitor_habitat_application_focus)
        except tk.TclError:
            self.dismiss_habitats()

    def on_habitat_destroy(self, event):
        if event.widget == self.habitat_window:
            self.clear_habitat_binding()
            self.habitat_window = None

    def clear_habitat_binding(self):
        if not self.habitat_outside_binding:
            return
        try:
            self.master._unbind(
                ("bind", "all", "<ButtonPress-1>"),
                self.habitat_outside_binding,
            )
        except tk.TclError:
            pass
        self.habitat_outside_binding = None

    def dismiss_habitats(self):
        modal = self.habitat_window
        self.clear_habitat_binding()
        self.habitat_window = None
        self.habitat_focus_misses = 0
        self.habitat_mouse_was_down = False
        if modal and modal.winfo_exists():
            modal.destroy()

    def load_card_image(self, record, label):
        value = str(record.get("image", "")).strip()
        if not value:
            return
        photo = self.cached_asset_photo(
            value, (CARD_IMAGE_SIZE, CARD_IMAGE_SIZE), Image.Resampling.LANCZOS,
        )
        if not photo:
            return
        self.card_images.append(photo)
        label.configure(image=photo, text="")

    def cached_asset_photo(self, value, size, method):
        path = Path(value)
        key = ("asset", str(value).replace("\\", "/"), tuple(size), int(method))
        cached = self.image_cache.get(key)
        if cached is not None:
            return cached
        try:
            stream = path.open("rb") if path.is_absolute() else self.assets.open(path.as_posix())
            with stream, Image.open(stream) as source:
                source = ImageOps.exif_transpose(source)
                image = ImageOps.fit(source.convert("RGBA"), tuple(size), method=method)
            photo = ImageTk.PhotoImage(image)
        except Exception:
            return None
        self.image_cache[key] = photo
        return photo

    def cached_photo(self, path, size, method):
        path = Path(path)
        key = (str(path.resolve()), tuple(size), int(method))
        cached = self.image_cache.get(key)
        if cached is not None:
            return cached
        try:
            with path.open("rb") as stream, Image.open(stream) as source:
                source = ImageOps.exif_transpose(source)
                image = ImageOps.fit(source.convert("RGBA"), tuple(size), method=method)
            photo = ImageTk.PhotoImage(image)
        except Exception:
            return None
        self.image_cache[key] = photo
        return photo

    def load_drop_icons(self, record, image_box):
        widgets = []
        for item_id in record.get("dropItemIds", []):
            filename = DROP_ICON_FILES.get(str(item_id))
            if not filename:
                continue
            photo = self.cached_photo(
                self.bundle_dir / "assets" / "icons" / "godinavi" / filename,
                (28, 28), Image.Resampling.LANCZOS,
            )
            if not photo:
                continue
            self.card_images.append(photo)
            widget = tk.Label(
                image_box, image=photo, bg="#151310",
                bd=0, highlightthickness=0, padx=0, pady=0,
                cursor="hand2",
            )
            widget.place(
                x=len(widgets) * 28,
                y=CARD_IMAGE_SIZE - 28,
                width=28,
                height=28,
            )
            full_name = self.catalog_name("items.json", str(item_id))
            widget.bind(
                "<Enter>",
                lambda event, name=full_name: self.show_magic_tooltip(event, name),
                add="+",
            )
            widget.bind(
                "<Leave>", lambda _event: self.hide_magic_tooltip(), add="+",
            )
            widgets.append(widget)
        return widgets

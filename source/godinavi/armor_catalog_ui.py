import json
import math
import os
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from armor_catalog_store import ArmorCatalogStore, enhanced_stats, filtered_items, localized_name
from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, modal_font_family, place_modal
from config_store import load_section, save_section


BG, PANEL, HEADER = "#17130f", "#2a2118", "#5a4932"
GOLD, TEXT, MUTED, CARD_BG = "#d8b15a", "#f1e5c7", "#bda982", "#211c18"
CARD_WIDTH, CARD_HEIGHT, CARD_COLUMNS = 500, 216, 2
SEARCH_DEBOUNCE_MS = 180
WHEEL_STEP_PIXELS = 48
SCROLL_FRAME_MS = 8
SCROLL_EASING_SECONDS = 0.035
PREFERENCES_PATH = Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi" / "armor-catalog-preferences.json"

TEXTS = {
    "KR": {"title": "장비 도감", "search": "이름 검색", "all": "전체", "male": "남자", "female": "여자",
           "armor": "갑옷", "clothes": "옷", "shoes": "신발", "outfit": "코스튬", "level": "착용 레벨",
           "base": "기본", "enhanced": "강화", "weight": "무게", "color": "색상", "sort": "정렬",
           "sort_name": "이름순", "sort_level_asc": "레벨 낮은순", "sort_level_desc": "레벨 높은순",
           "sort_category": "종류순", "count": "{count}개", "no_results": "조건에 맞는 장비가 없습니다.",
           "variants": "염색 색상표", "move_speed": "이동속도", "poison_resistance": "독 저항",
           "disease_resistance": "질병 저항", "portal_feature": "포탈기능", "experience_5": "경험치 5%",
           "max_resources_5": "최대 HP/MP/SP +5%", "magic_physical_damage_10": "마법/물리 데미지 +10", "set": "세트",
           "dye_credit": "염색정보 제공 : {names} 님",
           "unknown_color": "정보제공\n잘 부탁\n드립니다!", "close": "닫기"},
    "JP": {"title": "装備図鑑", "search": "名前検索", "all": "すべて", "male": "男性", "female": "女性",
           "armor": "鎧", "clothes": "服", "shoes": "靴", "outfit": "コスチューム", "level": "装備レベル",
           "base": "基本", "enhanced": "強化", "weight": "重量", "color": "カラー", "sort": "並び順",
           "sort_name": "名前順", "sort_level_asc": "レベル昇順", "sort_level_desc": "レベル降順",
           "sort_category": "種類順", "count": "{count}件", "no_results": "条件に一致する装備がありません。",
           "variants": "染色カラーチャート", "move_speed": "移動速度", "poison_resistance": "毒耐性",
           "disease_resistance": "病気耐性", "portal_feature": "ポータル機能", "experience_5": "経験値 5%",
           "max_resources_5": "最大 HP/MP/SP +5%", "magic_physical_damage_10": "魔法・物理ダメージ +10", "set": "セット",
           "dye_credit": "染色情報提供：{names} 様",
           "unknown_color": "情報提供を\nお待ちして\nおります！", "close": "閉じる"},
    "EN": {"title": "Equipment Catalog", "search": "Search names", "all": "All", "male": "Male", "female": "Female",
           "armor": "Armor", "clothes": "Clothes", "shoes": "Shoes", "outfit": "Costume", "level": "Required level",
           "base": "Base", "enhanced": "Enhanced", "weight": "Weight", "color": "Color", "sort": "Sort",
           "sort_name": "Name", "sort_level_asc": "Level: low to high", "sort_level_desc": "Level: high to low",
           "sort_category": "Category", "count": "{count} items", "no_results": "No equipment matches these filters.",
           "variants": "Dye color chart", "move_speed": "Move speed", "poison_resistance": "Poison resist",
           "disease_resistance": "Disease resist", "portal_feature": "Portal feature", "experience_5": "EXP 5%",
           "max_resources_5": "Max HP/MP/SP +5%", "magic_physical_damage_10": "Magic/Physical damage +10", "set": "SET",
           "dye_credit": "Dye information courtesy of {names}",
           "unknown_color": "No\nInformation", "close": "Close"},
}

OUTFIT_BASIC_EFFECT_ITEM_IDS = {55, 58, 59}


def outfit_effect_keys(item):
    """Return the display effects granted by a costume item."""
    if item.get("category") != "outfit":
        return []
    effects = ["portal_feature", "experience_5"]
    if item.get("item_id") == 60:
        effects.append("magic_physical_damage_10")
    elif item.get("item_id") not in OUTFIT_BASIC_EFFECT_ITEM_IDS:
        effects.append("max_resources_5")
    return effects


def load_preferences(path=PREFERENCES_PATH):
    defaults = {"gender": "male", "category": "armor", "sort": "level_asc", "color": "0", "shoe_dye_mode": "clothing"}
    if Path(path) == PREFERENCES_PATH:
        value = load_section("armor_catalog_preferences", defaults, (PREFERENCES_PATH,))
    else:
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return defaults
    if not isinstance(value, dict):
        return defaults
    if value.get("gender") in {"all", "male", "female"}:
        defaults["gender"] = value["gender"]
    if value.get("category") in {"all", "armor", "clothes", "shoes", "outfit"}:
        defaults["category"] = value["category"]
    if value.get("sort") in {"level_asc", "level_desc", "name", "category"}:
        defaults["sort"] = value["sort"]
    if str(value.get("color", "")).isdigit():
        defaults["color"] = str(value["color"])
    if value.get("shoe_dye_mode") in {"clothing", "shoe"}:
        defaults["shoe_dye_mode"] = value["shoe_dye_mode"]
    return defaults


def save_preferences(value, path=PREFERENCES_PATH):
    path = Path(path)
    if path == PREFERENCES_PATH:
        save_section("armor_catalog_preferences", value)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def zoom_transparent_sprite(image, size=(170, 150), scale=2.5):
    source = image.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    if not bbox:
        return canvas
    sprite = source.crop(bbox)
    target_width = max(1, round(sprite.width * scale))
    target_height = max(1, round(sprite.height * scale))
    fit = min(1.0, size[0] / target_width, size[1] / target_height)
    target = (max(1, round(target_width * fit)), max(1, round(target_height * fit)))
    sprite = sprite.resize(target, Image.Resampling.NEAREST)
    canvas.alpha_composite(sprite, ((size[0] - target[0]) // 2, (size[1] - target[1]) // 2))
    return canvas


def color_index_for_selection(item, selected):
    colors = item.get("colors") or []
    selected = str(selected)
    return next(
        (index for index, color in enumerate(colors) if str(color.get("id")) == selected),
        next((index for index, color in enumerate(colors) if str(color.get("id")) == "0"), 0),
    )


def catalog_color_selection(category, selected):
    """Use every item's base color while the category filter shows all items."""
    return "0" if category == "all" else str(selected)


def variant_slots(item):
    """Return real color records followed by explicit unknown color slots."""
    colors = list(item.get("colors") or [])
    known_ids = {color.get("id") for color in colors}
    slots = [(color, False) for color in colors]
    for color_id in item.get("unknown_color_ids") or []:
        if color_id not in known_ids:
            slots.append(({"id": color_id}, True))
    return slots


def ellipsize(text, font, max_width):
    """Shorten text to a pixel width while preserving a useful tooltip value."""
    text = str(text)
    if font.measure(text) <= max_width:
        return text
    suffix = "..."
    while text and font.measure(text + suffix) > max_width:
        text = text[:-1]
    return text + suffix


def virtual_screen_bounds(widget):
    if sys.platform == "win32":
        import ctypes
        user32 = ctypes.windll.user32
        return tuple(user32.GetSystemMetrics(index) for index in (76, 77, 78, 79))
    return 0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()


def move_window_absolute(window, x, y):
    """Place a Tk window at virtual-desktop coordinates, including negatives."""
    if sys.platform != "win32":
        window.geometry(f"{x:+d}{y:+d}")
        return
    import ctypes
    window.update_idletasks()
    user32 = ctypes.windll.user32
    hwnd = user32.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
    user32.SetWindowPos(hwnd, 0, int(x), int(y), 0, 0, 0x0001 | 0x0010 | 0x0040)


class CardDrawing:
    """A tagged group of primitives on the single catalog canvas, not a widget."""

    def __init__(self, canvas, tag):
        self.canvas, self.tag = canvas, tag
        self.x = self.y = 0

    def _create(self, kind, *coords, **options):
        tags = options.pop("tags", ())
        if isinstance(tags, str):
            tags = (tags,)
        options["tags"] = (self.tag, *tags)
        return getattr(self.canvas, f"create_{kind}")(*coords, **options)

    def create_polygon(self, *coords, **options):
        return self._create("polygon", *coords, **options)

    def create_text(self, *coords, **options):
        return self._create("text", *coords, **options)

    def create_rectangle(self, *coords, **options):
        return self._create("rectangle", *coords, **options)

    def create_image(self, *coords, **options):
        return self._create("image", *coords, **options)

    def itemconfigure(self, item, **options):
        self.canvas.itemconfigure(item, **options)

    def place(self, *, x, y):
        if (x, y) != (self.x, self.y):
            self.canvas.move(self.tag, x - self.x, y - self.y)
            self.x, self.y = x, y
        self.canvas.itemconfigure(self.tag, state="normal")

    def place_forget(self):
        self.canvas.itemconfigure(self.tag, state="hidden")


class ArmorCatalogUI:
    def __init__(self, master, project_dir, language_provider, store=None, preferences_path=None):
        self.master, self.language_provider = master, language_provider
        self.store = store or ArmorCatalogStore(project_dir)
        self.window = self.built_language = None
        self.items, self.visible_items, self.items_by_id = [], [], {}
        self.bounds = (0, 0, 1, 1)
        self.card_states, self.image_cache = {}, {}
        self.refresh_job = None
        self.viewport_job = None
        self.viewport_layout = None
        self.wheel_job = None
        self.wheel_target = None
        self.wheel_last_at = 0.0
        self.displayed_ids = set()
        self.card_row_count = 0
        self.no_results_label = None
        self.variant_window = None
        self.variant_photos = []
        self.name_tooltip = None
        self.preferences_path = Path(preferences_path) if preferences_path else PREFERENCES_PATH
        self.preferences = load_preferences(self.preferences_path)

    def language(self):
        value = self.language_provider() if self.language_provider else "KR"
        return value if value in TEXTS else "EN"

    def locale(self):
        return {"KR": "ko", "JP": "ja", "EN": "en"}[self.language()]

    def texts(self):
        return TEXTS[self.language()]

    def open(self):
        try:
            self.store.reload()
            self.items = self.store.items()
            self.items_by_id = {item.get("id"): item for item in self.items}
        except Exception:
            self.items = []
        if self.window and self.window.winfo_exists() and self.built_language != self.language():
            self.cancel_pending_jobs()
            self.window.destroy()
            self.window = None
            self.card_states.clear()
            self.no_results_label = None
            self.image_cache.clear()
        if not self.window or not self.window.winfo_exists():
            self.build_window()
        self.refresh_list()
        _owner, self.bounds = place_modal(self.window, 1060, 700, "armor_catalog")
        self.window.deiconify()
        self.window.lift()
        activate_modal(self.window)

    def build_window(self):
        text, family = self.texts(), modal_font_family(self.master, self.language())
        self.font_family = family
        self.title_font = tkfont.Font(root=self.master, family="Noto Sans KR", size=13, weight="bold")
        self.displayed_ids.clear()
        self.card_row_count = 0
        win = tk.Toplevel(self.master)
        self.window, self.built_language = win, self.language()
        win.withdraw()
        win.title(text["title"])
        win.overrideredirect(True)
        win.resizable(False, False)
        win.configure(bg=GOLD)
        win.protocol("WM_DELETE_WINDOW", self.close)
        bind_modal_escape(win, self.close)
        style = ttk.Style(win)
        style.theme_use("clam")
        style.configure("Armor.TEntry", fieldbackground="#3b3022", foreground="#fff0c9", insertcolor="#fff0c9")
        style.configure("Armor.TCombobox", fieldbackground="#3b3022", background=HEADER, foreground="#fff0c9", arrowcolor=GOLD)
        style.map("Armor.TCombobox", fieldbackground=[("readonly", "#3b3022")], foreground=[("readonly", "#fff0c9")])
        style.configure("Armor.Vertical.TScrollbar", background=HEADER, troughcolor=BG, arrowcolor="#f1d28c")

        content = tk.Frame(win, bg=BG)
        content.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(content, bg=HEADER, height=44, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(header, text=text["title"], bg=HEADER, fg="#ffe09a", font=(family, 13, "bold"), padx=14)
        title.pack(side="left", fill="y")
        self.count_label = tk.Label(header, bg=HEADER, fg=TEXT, font=(family, 9), padx=14)
        self.count_label.pack(side="right", fill="y")
        bind_modal_drag(win, (header, title, self.count_label), lambda: self.bounds, "armor_catalog")

        filters = tk.Frame(content, bg=PANEL, padx=12, pady=8)
        filters.pack(fill="x", padx=10)
        row1, row2 = tk.Frame(filters, bg=PANEL), tk.Frame(filters, bg=PANEL)
        row1.pack(fill="x")
        row2.pack(fill="x", pady=(7, 0))
        self.search_var = tk.StringVar()
        self.gender_var = tk.StringVar(value=self.preferences["gender"])
        self.category_var = tk.StringVar(value=self.preferences["category"])
        self.color_var = tk.StringVar(value=self.preferences["color"])
        self.shoe_dye_mode_var = tk.StringVar(value=self.preferences.get("shoe_dye_mode", "clothing"))
        self.color_choice_var = tk.StringVar()
        tk.Label(row1, text=text["search"], bg=PANEL, fg=MUTED, font=(family, 9)).pack(side="left")
        ttk.Entry(row1, textvariable=self.search_var, width=28, style="Armor.TEntry").pack(side="left", padx=(7, 18))
        tk.Label(row1, text=text["sort"], bg=PANEL, fg=MUTED, font=(family, 9)).pack(side="left")
        self.sort_choices = {text["sort_level_asc"]: "level_asc", text["sort_level_desc"]: "level_desc",
                             text["sort_name"]: "name", text["sort_category"]: "category"}
        selected_sort = next((label for label, key in self.sort_choices.items() if key == self.preferences["sort"]), text["sort_level_asc"])
        self.sort_var = tk.StringVar(value=selected_sort)
        combo = ttk.Combobox(row1, textvariable=self.sort_var, values=tuple(self.sort_choices), state="readonly", width=20, style="Armor.TCombobox")
        combo.pack(side="left", padx=(7, 0))
        combo.bind("<<ComboboxSelected>>", lambda _event: self.filter_changed())
        self.global_color_frame = tk.Frame(row1, bg=PANEL)
        self.global_color_frame.pack(side="right")
        for value, label in (("all", text["all"]), ("male", text["male"]), ("female", text["female"])):
            self.radio(row2, label, self.gender_var, value, family).pack(side="left")
        tk.Frame(row2, width=22, bg=PANEL).pack(side="left")
        for value in ("all", "armor", "clothes", "shoes", "outfit"):
            self.radio(row2, text[value], self.category_var, value, family).pack(side="left")
        self.search_var.trace_add("write", lambda *_: self.schedule_refresh())

        footer = tk.Frame(content, bg=PANEL, height=44, padx=10, pady=7)
        footer.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        footer.pack_propagate(False)
        tk.Button(footer, text=text["close"], command=self.close, bg="#3b3022", fg="#f3d68f",
                  activebackground=HEADER, activeforeground="#fff4d2", relief="flat", bd=0,
                  padx=18, font=(family, 9, "bold"), cursor="hand2").pack(side="right", fill="y")
        body = tk.Frame(content, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        self.card_canvas = tk.Canvas(body, bg=BG, bd=0, highlightthickness=0)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.scrollbar_scroll, style="Armor.Vertical.TScrollbar")
        def viewport_changed(first, last):
            scroll.set(first, last)
            self.schedule_viewport()
        self.card_canvas.configure(yscrollcommand=viewport_changed)
        self.card_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.card_canvas.bind("<Configure>", self.resize_viewport)
        self.card_canvas.bind("<MouseWheel>", self.scroll_cards)
        self.card_canvas.configure(takefocus=True)
        self.canvas_controls = {}
        self.focused_control = None
        self.card_canvas.bind("<KeyPress-Tab>", self.focus_next_control)
        self.card_canvas.bind("<Shift-KeyPress-Tab>", lambda event: self.focus_next_control(event, -1))
        self.card_canvas.bind("<Return>", self.activate_focused_control)
        self.card_canvas.bind("<space>", self.activate_focused_control)
        self.card_canvas.bind("<FocusOut>", lambda _event: self.clear_control_focus())

    def radio(self, parent, label, variable, value, family):
        return tk.Radiobutton(parent, text=label, value=value, variable=variable, command=self.filter_changed,
                              bg=PANEL, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                              selectcolor="#3b3022", highlightthickness=0, font=(family, 9))

    def filter_changed(self):
        self.save_filter_preferences()
        self.refresh_list()

    def save_filter_preferences(self):
        self.preferences = {
            "gender": self.gender_var.get(), "category": self.category_var.get(),
            "sort": self.sort_choices.get(self.sort_var.get(), "level_asc"), "color": self.color_var.get(),
            "shoe_dye_mode": self.shoe_dye_mode_var.get(),
        }
        save_preferences(self.preferences, self.preferences_path)

    def schedule_refresh(self):
        if self.window and self.window.winfo_exists():
            if self.refresh_job:
                self.window.after_cancel(self.refresh_job)
            self.refresh_job = self.window.after(SEARCH_DEBOUNCE_MS, self.refresh_list)

    def refresh_list(self):
        if not self.window or not hasattr(self, "card_canvas"):
            return
        if self.refresh_job is not None:
            self.window.after_cancel(self.refresh_job)
        self.refresh_job = None
        self.visible_items = filtered_items(self.items, self.search_var.get(), self.gender_var.get(),
                                            self.category_var.get(), self.locale(),
                                            self.sort_choices.get(self.sort_var.get(), "level_asc"))
        self.update_global_color_controls()
        if self.category_var.get() == "shoes":
            for item in self.visible_items:
                self.preview_color_id(item, self.color_var.get())
        self.render_cards()

    def update_global_color_controls(self):
        for child in self.global_color_frame.winfo_children():
            child.destroy()
        if self.category_var.get() == "all":
            return
        clothing_mode = self.category_var.get() in {"armor", "clothes"} or (
            self.category_var.get() == "shoes" and self.shoe_dye_mode_var.get() == "clothing")
        if self.category_var.get() == "shoes":
            mode_labels = {"ko": ("옷 염색", "신발 염색"), "en": ("Clothing dye", "Shoe dye"),
                           "ja": ("服の染色", "靴の染色")}.get(self.locale(), ("Clothing dye", "Shoe dye"))
            for value, label in zip(("clothing", "shoe"), mode_labels):
                tk.Radiobutton(self.global_color_frame, text=label, value=value,
                               variable=self.shoe_dye_mode_var, command=self.change_shoe_dye_mode,
                               bg=PANEL, fg=TEXT, selectcolor=BG, activebackground=PANEL,
                               font=(modal_font_family(self.master, self.language()), 9)).pack(side="left")
        if clothing_mode:
            color_ids = [str(c) for c in range(5)]
            labels = self.store.color_labels("armor", self.locale())
        else:
            color_ids = sorted({str(color.get("id")) for item in self.visible_items
                                for color in (item.get("colors") or [])}, key=int)
            labels = self.store.color_labels(self.category_var.get(), self.locale())
        if not color_ids:
            return
        if self.color_var.get() not in color_ids:
            self.color_var.set(color_ids[0])
        choices = [(labels.get(color_id, f'{self.texts()["color"]} {color_id}'), color_id) for color_id in color_ids]
        self.color_choice_ids = {label: color_id for label, color_id in choices}
        selected_label = next(label for label, color_id in choices if color_id == self.color_var.get())
        self.color_choice_var.set(selected_label)
        tk.Label(self.global_color_frame, text=self.texts()["color"], bg=PANEL, fg=MUTED,
                 font=(modal_font_family(self.master, self.language()), 9)).pack(side="left", padx=(0, 7))
        combo = ttk.Combobox(
            self.global_color_frame, textvariable=self.color_choice_var,
            values=tuple(label for label, _color_id in choices), state="readonly", width=14,
            style="Armor.TCombobox",
        )
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self.global_color_selected)

    def preview_color_id(self, item, selected):
        if self.category_var.get() != "shoes":
            return self.store.display_color_id(item, selected)
        if not hasattr(self, "shoe_preview_colors"):
            self.shoe_preview_colors = {}
        applicable = self.store.uses_clothing_dyes(item) == (self.shoe_dye_mode_var.get() == "clothing")
        if applicable:
            color_id = self.store.display_color_id(item, selected)
            if any(str(color.get("id")) == color_id for color in item.get("colors", [])):
                self.shoe_preview_colors[item["id"]] = color_id
        return self.shoe_preview_colors.get(item["id"], "0")

    def change_shoe_dye_mode(self):
        self.color_var.set("0")
        self.save_filter_preferences()
        self.refresh_list()

    def global_color_selected(self, _event=None):
        color_id = getattr(self, "color_choice_ids", {}).get(self.color_choice_var.get())
        if color_id is not None:
            self.color_var.set(color_id)
            self.global_color_changed()

    def global_color_changed(self):
        self.save_filter_preferences()
        if self.category_var.get() == "shoes":
            self.refresh_list()
            return
        selected = catalog_color_selection(self.category_var.get(), self.color_var.get())
        for item_id in self.displayed_ids:
            state = self.card_states[item_id]
            state["color"] = color_index_for_selection(state["item"], self.preview_color_id(state["item"], selected))
            self.update_card(state)

    def render_cards(self):
        self.stop_wheel()
        self.viewport_layout = None
        self.clear_control_focus()
        for state in self.card_states.values():
            state["card"].place_forget()
        self.displayed_ids.clear()
        if self.no_results_label is not None:
            self.card_canvas.delete(self.no_results_label)
            self.no_results_label = None
        self.count_label.configure(text=self.texts()["count"].format(count=len(self.visible_items)))
        row_count = (len(self.visible_items) + CARD_COLUMNS - 1) // CARD_COLUMNS
        self.card_row_count = row_count
        if not self.visible_items:
            self.no_results_label = self.card_canvas.create_text(
                self.card_canvas.winfo_width() / 2, 50, text=self.texts()["no_results"], fill=MUTED,
                font=("Noto Sans KR", 12),
            )
        self.resize_viewport()
        self.card_canvas.yview_moveto(0)
        self.render_viewport()

    def resize_viewport(self, _event=None):
        width = self.card_canvas.winfo_width()
        # Only canvas primitives are scrolled; no embedded native windows.
        height = max(100, self.card_row_count * (CARD_HEIGHT + 8) + 10)
        self.card_canvas.configure(scrollregion=(0, 0, width, height))
        self.schedule_viewport()

    def schedule_viewport(self):
        if self.viewport_job is None and self.window and self.window.winfo_exists():
            self.viewport_job = self.window.after_idle(self.render_viewport)

    def render_viewport(self):
        if self.viewport_job is not None:
            self.window.after_cancel(self.viewport_job)
            self.viewport_job = None
        if not self.window or not self.window.winfo_exists():
            return
        row_height = CARD_HEIGHT + 8
        top = max(0, self.card_canvas.canvasy(0) - 5)
        height = max(1, self.card_canvas.winfo_height())
        first = max(0, int(top // row_height) - 1) * CARD_COLUMNS
        last = min(len(self.visible_items), (int((top + height) // row_height) + 2) * CARD_COLUMNS)
        layout = (first, last, self.card_canvas.winfo_width())
        if layout == self.viewport_layout:
            return
        self.viewport_layout = layout
        wanted = {item["id"] for item in self.visible_items[first:last]}
        for item_id in self.displayed_ids - wanted:
            self.card_states[item_id]["card"].place_forget()
        selected_color = catalog_color_selection(self.category_var.get(), self.color_var.get())
        for index in range(first, last):
            item = self.visible_items[index]
            state = self.card_states.get(item["id"])
            if state is None:
                self.build_card(item, index // CARD_COLUMNS, index % CARD_COLUMNS)
                state = self.card_states[item["id"]]
            elif item["id"] not in self.displayed_ids:
                state["item"] = item
                state["color"] = color_index_for_selection(item, self.preview_color_id(item, selected_color))
                self.update_card(state)
            self.place_card(state["card"], index // CARD_COLUMNS, index % CARD_COLUMNS)
        self.displayed_ids = wanted
        if self.focused_control and self.canvas_controls[self.focused_control]["item_id"] not in wanted:
            self.clear_control_focus()

    def place_card(self, card, row, column):
        column_width = self.card_canvas.winfo_width() / CARD_COLUMNS
        card.place(x=round(column_width * column + (column_width - CARD_WIDTH) / 2),
                   y=5 + row * (CARD_HEIGHT + 8) + 4)

    def build_card(self, item, row, column):
        text = self.texts()
        control_font = (self.font_family, 12, "bold")
        card = CardDrawing(self.card_canvas, f"card:{item['id']}")
        self.rounded_rectangle(card, 2, 2, CARD_WIDTH - 2, CARD_HEIGHT - 2, 13, fill=CARD_BG, outline="#5c5044", width=1)
        image_tag = f"image:{item['id']}"
        card.create_rectangle(16, 32, 186, 182, fill="#151310", outline="", tags=image_tag)
        image_label = card.create_image(16, 32, anchor="nw", tags=image_tag)
        image_fallback = card.create_text(101, 107, text="No image", fill=MUTED, tags=image_tag)
        title_label = card.create_text(206, 31, fill="#f2d995", anchor="w", font=self.title_font)
        meta = f'{text[item["gender"]]} · {text[item["category"]]}'
        if item.get("category") != "shoes":
            meta += f' · Lv.{item.get("required_level", 0)}'
        card.create_text(16, 7, text=meta, fill=MUTED, anchor="nw", width=170,
                         font=("Noto Sans KR", 8))
        stat_widgets = {}
        for row_index, (metric, label_text) in enumerate((("ac", "AC"), ("dc", "DC"), ("weight", text["weight"]))):
            row_y = 66 + row_index * 23
            card.create_text(206, row_y + 13, text=label_text, fill="#f2d995", anchor="w",
                             font=("Noto Sans KR", 10, "bold"))
            base_label = card.create_text(336, row_y + 13, fill=TEXT, anchor="e",
                                          font=("Noto Sans KR", 10, "bold"))
            bonus_label = card.create_text(396, row_y + 13, fill=GOLD, anchor="e",
                                           font=("Noto Sans KR", 10, "bold"))
            total_label = card.create_text(468, row_y + 13, fill="#e36a5d", anchor="e",
                                           font=("Noto Sans KR", 10, "bold"))
            stat_widgets[metric] = (base_label, bonus_label, total_label)
        set_effect = item.get("set_effect")
        set_var = tk.BooleanVar(value=False)
        set_check = None
        if isinstance(set_effect, dict):
            required_ref = set_effect.get("required_item", {})
            required = self.items_by_id.get(required_ref.get("id"), required_ref)
            full_set_name = f'{text["set"]}: {localized_name(required, self.locale())}'
            set_font = tkfont.Font(root=self.master, family="Noto Sans KR", size=8)
            short_set_name = ellipsize(full_set_name, set_font, 145)
            set_check = self.draw_control(
                card, item["id"], "set", (16, 182, 186, 206),
                "[ ] " + short_set_name, ("Noto Sans KR", 8),
                lambda value=item["id"]: self.toggle_set(value),
            )
            if short_set_name != full_set_name:
                self.card_canvas.tag_bind(set_check, "<Enter>",
                    lambda event, value=full_set_name: self.show_control_tooltip(event, value))
                self.card_canvas.tag_bind(set_check, "<Leave>", self.hide_name_tooltip)
        if item.get("category") != "outfit":
            for name, label, x, delta in (("minus", "−", 400, -1), ("plus", "+", 444, 1)):
                self.draw_control(card, item["id"], name, (x, 155, x + 40, 185),
                                  label, control_font,
                                  lambda value=item["id"], step=delta: self.adjust_enhancement(value, step))
        effect_width = 280 if item.get("category") == "outfit" else 195
        effect_label = card.create_text(
            206, 172, fill=MUTED, anchor="w", justify="left", width=effect_width,
            font=("Noto Sans KR", 8),
        )
        colors = item.get("colors") or []
        selected_color = catalog_color_selection(self.category_var.get(), self.color_var.get())
        initial_color = color_index_for_selection(item, self.preview_color_id(item, selected_color))
        state = {"item": item, "card": card, "color": initial_color, "enhancement": 0, "image": image_label,
                 "set_var": set_var, "set_check": set_check, "title_label": title_label,
                 "stat_widgets": stat_widgets,
                 "effect_label": effect_label, "image_fallback": image_fallback}
        self.card_states[item["id"]] = state
        self.card_canvas.tag_bind(image_tag, "<Button-1>", lambda _event, value=item: self.show_variants(value))
        self.update_card(state)
        self.place_card(card, row, column)

    def draw_control(self, card, item_id, name, box, label, font, command):
        tag = f"control:{item_id}:{name}"
        x1, y1, x2, y2 = box
        border = card.create_rectangle(*box, fill="#3b3022", outline="#3b3022", tags=tag)
        text_id = card.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                   text=label, fill=TEXT, font=font, tags=tag)
        self.canvas_controls[tag] = {"item_id": item_id, "border": border, "text": text_id,
                                     "label": label, "command": command}
        self.card_canvas.tag_bind(tag, "<Button-1>", lambda _event: self.activate_control(tag))
        return tag

    def clear_control_focus(self):
        if self.focused_control in self.canvas_controls:
            self.card_canvas.itemconfigure(self.canvas_controls[self.focused_control]["border"], outline="#3b3022")
        self.focused_control = None

    def activate_control(self, tag):
        self.clear_control_focus()
        self.focused_control = tag
        self.card_canvas.focus_set()
        control = self.canvas_controls[tag]
        self.card_canvas.itemconfigure(control["border"], outline=GOLD)
        control["command"]()

    def focus_next_control(self, _event, direction=1):
        controls = [tag for item in self.visible_items if item["id"] in self.displayed_ids
                    for tag, value in self.canvas_controls.items() if value["item_id"] == item["id"]]
        if not controls:
            return None
        index = controls.index(self.focused_control) + direction if self.focused_control in controls else (0 if direction > 0 else len(controls) - 1)
        self.clear_control_focus()
        if not 0 <= index < len(controls):
            return None  # Let Tk move focus to the next/previous widget.
        self.focused_control = controls[index]
        self.card_canvas.itemconfigure(self.canvas_controls[self.focused_control]["border"], outline=GOLD)
        return "break"

    def activate_focused_control(self, _event):
        if self.focused_control in self.canvas_controls:
            self.canvas_controls[self.focused_control]["command"]()
            return "break"

    def toggle_set(self, item_id):
        state = self.card_states[item_id]
        state["set_var"].set(not state["set_var"].get())
        control = self.canvas_controls[state["set_check"]]
        label = ("[x] " if state["set_var"].get() else "[ ] ") + control["label"][4:]
        self.card_canvas.itemconfigure(control["text"], text=label)
        self.update_card(state)

    def show_control_tooltip(self, event, text):
        self.card_canvas._armor_full_text = text
        self.show_name_tooltip(event)

    def update_card(self, state):
        item, colors = state["item"], state["item"].get("colors") or []
        if colors:
            state["color"] %= len(colors)
            color = colors[state["color"]]
            label = self.store.color_labels(item.get("category"), self.locale()).get(str(color.get("id")), str(color.get("id")))
            self.show_card_image(state, color.get("image"))
        active_set = item.get("set_effect") if state["set_var"].get() else None
        result = enhanced_stats(item, state["enhancement"], self.store.enhancement_steps(item.get("category")), active_set)
        level = state["enhancement"]
        full_title = f'{localized_name(item, self.locale())}{f" +{level}" if level else ""}'
        state["card"].itemconfigure(state["title_label"], text=ellipsize(full_title, self.title_font, 270))
        stats = item.get("stats") or {}
        for metric, widgets in state["stat_widgets"].items():
            base_label, bonus_label, total_label = widgets
            base = stats.get(metric, 0)
            total = result.get(metric, base) if result else base
            bonus = total - base
            state["card"].itemconfigure(base_label, text=str(base))
            state["card"].itemconfigure(bonus_label, text=f'{bonus:+d}')
            state["card"].itemconfigure(total_label, text=f'({total})')
        extra = []
        extra.extend(self.texts()[key] for key in outfit_effect_keys(item))
        if active_set and result:
            if result.get("move_speed_percent"):
                extra.append(f'{self.texts()["move_speed"]} +{result["move_speed_percent"]}%')
            if result.get("poison_resistance"):
                extra.append(f'{self.texts()["poison_resistance"]} +{result["poison_resistance"]}')
            if result.get("disease_resistance"):
                extra.append(f'{self.texts()["disease_resistance"]} +{result["disease_resistance"]}')
        state["card"].itemconfigure(state["effect_label"], text=" · ".join(extra))

    def show_card_image(self, state, relative):
        try:
            photo = self.image_cache.get(relative)
            if photo is None:
                photo = ImageTk.PhotoImage(zoom_transparent_sprite(self.store.image(relative), (170, 150), 2.5))
                self.image_cache[relative] = photo
            state["card"].itemconfigure(state["image"], image=photo)
            state["card"].itemconfigure(state["image_fallback"], text="")
            state["photo"] = photo
        except Exception:
            state["card"].itemconfigure(state["image"], image="")
            state["card"].itemconfigure(state["image_fallback"], text="No image")

    def adjust_enhancement(self, item_id, delta):
        state = self.card_states.get(item_id)
        if state:
            maximum = len(self.store.enhancement_steps(state["item"].get("category")))
            state["enhancement"] = max(0, min(maximum, state["enhancement"] + delta))
            self.update_card(state)

    def show_variants(self, item):
        if self.variant_window and self.variant_window.winfo_exists():
            self.variant_window.destroy()
        text, family = self.texts(), modal_font_family(self.master, self.language())
        win = tk.Toplevel(self.window)
        self.variant_window = win
        self.variant_photos = []
        win.withdraw()
        win.title(text["variants"])
        win.overrideredirect(True)
        win.resizable(False, False)
        win.configure(bg=GOLD)
        win.protocol("WM_DELETE_WINDOW", self.close_variants)
        bind_modal_escape(win, self.close_variants)
        content = tk.Frame(win, bg=BG)
        content.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(content, bg=HEADER, height=44, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(
            header, text=f'{localized_name(item, self.locale())} · {text["variants"]}',
            bg=HEADER, fg="#ffe09a", font=(family, 13, "bold"), padx=14,
        )
        title.pack(side="left", fill="y")
        variant_bounds = {"value": (0, 0, 1, 1)}
        bind_modal_drag(win, (header, title), lambda: variant_bounds["value"], "armor_catalog_variants")

        table_area = tk.Frame(content, bg=BG)
        table_area.pack(fill="both", expand=True, padx=10, pady=10)
        table = tk.Frame(table_area, bg=BG)
        table.pack(fill="both", expand=True)
        labels = self.store.item_color_labels(item, self.locale())
        slots = variant_slots(item)
        set_shoes = self.store.matching_set_shoes(item)
        columns = min(4, max(1, len(slots)))
        for index, (color, unknown) in enumerate(slots):
            color_id = str(color.get("id"))
            cell = tk.Frame(table, bg=PANEL, highlightbackground="#5c5044", highlightthickness=1, padx=5, pady=5)
            cell.grid(row=index // columns, column=index % columns, padx=3, pady=3, sticky="n")
            tk.Label(cell, text=labels.get(color_id, color_id), bg=PANEL, fg="#f2d995",
                     font=(family, 9, "bold"), width=16).pack(fill="x", pady=(0, 4))
            previews = tk.Frame(cell, bg=PANEL)
            previews.pack()
            image_box = tk.Frame(previews, bg="#151310", width=130, height=170)
            image_box.pack_propagate(False)
            image_box.pack(side="left")
            image_label = tk.Label(image_box, bg="#151310")
            image_label.pack(fill="both", expand=True)
            if unknown:
                image_label.configure(text=text["unknown_color"], fg=MUTED, justify="center",
                                      font=(family, 9, "bold"))
            else:
                try:
                    image = zoom_transparent_sprite(self.store.equipped_variant_image(item, color), (130, 170), 2.5)
                    photo = ImageTk.PhotoImage(image)
                    self.variant_photos.append(photo)
                    image_label.configure(image=photo)
                except Exception:
                    image_label.configure(text="No image", fg=MUTED)
            if not unknown and any(self.store.matching_shoe_color(shoe, color_id) is None for shoe in set_shoes):
                tk.Label(cell, text=text["unknown_color"], bg=PANEL, fg=MUTED,
                         font=(family, 9)).pack()
        footer = tk.Frame(content, bg=PANEL, height=44, padx=10, pady=7)
        footer.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        footer.pack_propagate(False)
        tk.Button(footer, text=text["close"], command=self.close_variants, bg="#3b3022", fg="#f3d68f",
                  activebackground=HEADER, activeforeground="#fff4d2", relief="flat", bd=0,
                  padx=18, font=(family, 9, "bold"), cursor="hand2").pack(side="right", fill="y")
        contributors = item.get("dye_contributors", [])
        if contributors:
            tk.Label(footer, text=text["dye_credit"].format(names=", ".join(contributors)),
                     bg=PANEL, fg=MUTED, anchor="w", font=(family, 9)).pack(side="left", fill="y")
        rows = max(1, (len(slots) + columns - 1) // columns)
        modal_width = max(350, columns * 150 + 40)
        modal_height = 118 + rows * 218
        _owner, variant_bounds["value"] = place_modal(win, modal_width, modal_height, "armor_catalog_variants")
        win.deiconify()
        win.lift()
        activate_modal(win)

    def close_variants(self):
        if self.variant_window and self.variant_window.winfo_exists():
            self.variant_window.destroy()
        self.variant_window = None
        self.variant_photos = []

    def bind_name_tooltip(self, widget, full_text):
        widget._armor_full_text = full_text
        if getattr(widget, "_armor_tooltip_bound", False):
            return
        widget._armor_tooltip_bound = True
        widget.bind("<Enter>", self.show_name_tooltip, add="+")
        widget.bind("<Leave>", self.hide_name_tooltip, add="+")

    def show_name_tooltip(self, event):
        self.hide_name_tooltip()
        text = getattr(event.widget, "_armor_full_text", "")
        if not text:
            return
        tip = tk.Toplevel(self.window)
        self.name_tooltip = tip
        tip.overrideredirect(True)
        tip.transient(self.window)
        tip.configure(bg=GOLD)
        tk.Label(tip, text=text, bg=PANEL, fg=TEXT, padx=9, pady=5,
                 font=(modal_font_family(self.master, self.language()), 9)).pack(padx=1, pady=1)
        tip.update_idletasks()
        pointer_x, pointer_y = self.master.winfo_pointerxy()
        width, height = tip.winfo_reqwidth(), tip.winfo_reqheight()
        screen_x, screen_y, screen_width, screen_height = virtual_screen_bounds(tip)
        right, bottom = screen_x + screen_width, screen_y + screen_height
        x = pointer_x - width - 14
        y = pointer_y - height - 10
        if x < screen_x:
            x = min(pointer_x + 14, right - width)
        if y < screen_y:
            y = min(pointer_y + 18, bottom - height)
        x = min(max(screen_x, x), max(screen_x, right - width))
        y = min(max(screen_y, y), max(screen_y, bottom - height))
        tip.geometry(f"{width}x{height}")
        move_window_absolute(tip, x, y)
        tip.lift()

    def hide_name_tooltip(self, _event=None):
        tip, self.name_tooltip = self.name_tooltip, None
        if tip:
            try:
                if tip.winfo_exists():
                    tip.destroy()
            except tk.TclError:
                pass

    def scroll_cards(self, event):
        if not event.delta:
            return "break"
        total, maximum = self.scroll_limits()
        current = max(0.0, self.card_canvas.canvasy(0))
        if self.wheel_target is None:
            self.wheel_target = current
            self.wheel_last_at = time.perf_counter()
        # Preserve high-resolution wheel deltas. Tk's default "units" jump by
        # a tenth of the viewport and rounding small deltas amplifies touchpads.
        self.wheel_target = min(maximum, max(0.0, self.wheel_target - event.delta / 120.0 * WHEEL_STEP_PIXELS))
        if abs(self.wheel_target - current) < 0.5:
            self.stop_wheel()
            return "break"
        if self.wheel_job is None:
            self.wheel_job = self.window.after(SCROLL_FRAME_MS, self.flush_wheel)
        return "break"

    def scroll_limits(self):
        total = max(100, self.card_row_count * (CARD_HEIGHT + 8) + 10)
        return total, max(0.0, total - self.card_canvas.winfo_height())

    def flush_wheel(self):
        self.wheel_job = None
        if self.wheel_target is None:
            return
        total, maximum = self.scroll_limits()
        self.wheel_target = min(maximum, self.wheel_target)
        now = time.perf_counter()
        elapsed = max(0.0, now - self.wheel_last_at)
        self.wheel_last_at = now
        current = max(0.0, self.card_canvas.canvasy(0))
        remaining = self.wheel_target - current
        if abs(remaining) <= 1:
            self.card_canvas.yview_moveto(self.wheel_target / total)
            self.wheel_target = None
            return
        step = remaining * (1.0 - math.exp(-elapsed / SCROLL_EASING_SECONDS))
        # Tk rounds canvas positions to whole pixels; finish the last pixels
        # instead of scheduling frames forever below that rounding threshold.
        if 0 < abs(step) < 1:
            step = math.copysign(min(1.0, abs(remaining)), step)
        self.card_canvas.yview_moveto((current + step) / total)
        self.wheel_job = self.window.after(SCROLL_FRAME_MS, self.flush_wheel)

    def stop_wheel(self):
        if self.wheel_job is not None:
            self.window.after_cancel(self.wheel_job)
            self.wheel_job = None
        self.wheel_target = None

    def scrollbar_scroll(self, *args):
        self.stop_wheel()
        self.card_canvas.yview(*args)

    @staticmethod
    def rounded_rectangle(canvas, x1, y1, x2, y2, radius=12, **kwargs):
        points = (x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2,
                  x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1)
        return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def cancel_pending_jobs(self):
        for name in ("refresh_job", "viewport_job", "wheel_job"):
            job = getattr(self, name)
            if job is not None:
                self.window.after_cancel(job)
                setattr(self, name, None)
        self.wheel_target = None

    def close(self):
        self.hide_name_tooltip()
        self.close_variants()
        if self.window and self.window.winfo_exists():
            self.cancel_pending_jobs()
            self.window.withdraw()

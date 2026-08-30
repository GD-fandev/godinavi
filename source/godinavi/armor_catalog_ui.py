import json
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from armor_catalog_store import ArmorCatalogStore, enhanced_stats, filtered_items, localized_name
from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, modal_font_family, place_modal


BG, PANEL, HEADER = "#17130f", "#2a2118", "#5a4932"
GOLD, TEXT, MUTED, CARD_BG = "#d8b15a", "#f1e5c7", "#bda982", "#211c18"
CARD_WIDTH, CARD_HEIGHT, CARD_COLUMNS = 500, 216, 2
SEARCH_DEBOUNCE_MS = 180
PREFERENCES_PATH = Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi" / "armor-catalog-preferences.json"

TEXTS = {
    "KR": {"title": "장비 도감", "search": "이름 검색", "all": "전체", "male": "남자", "female": "여자",
           "armor": "갑옷", "clothes": "옷", "shoes": "신발", "outfit": "코스튬", "level": "착용 레벨",
           "base": "기본", "enhanced": "강화", "weight": "무게", "color": "색상", "sort": "정렬",
           "sort_name": "이름순", "sort_level_asc": "레벨 낮은순", "sort_level_desc": "레벨 높은순",
           "sort_category": "종류순", "count": "{count}개", "no_results": "조건에 맞는 장비가 없습니다.",
           "variants": "염색 색상표", "move_speed": "이동속도", "poison_resistance": "독 저항",
           "disease_resistance": "질병 저항", "set": "세트", "unknown_color": "정보제공\n잘 부탁\n드립니다!", "close": "닫기"},
    "JP": {"title": "装備図鑑", "search": "名前検索", "all": "すべて", "male": "男性", "female": "女性",
           "armor": "鎧", "clothes": "服", "shoes": "靴", "outfit": "コスチューム", "level": "装備レベル",
           "base": "基本", "enhanced": "強化", "weight": "重量", "color": "カラー", "sort": "並び順",
           "sort_name": "名前順", "sort_level_asc": "レベル昇順", "sort_level_desc": "レベル降順",
           "sort_category": "種類順", "count": "{count}件", "no_results": "条件に一致する装備がありません。",
           "variants": "染色カラーチャート", "move_speed": "移動速度", "poison_resistance": "毒耐性",
           "disease_resistance": "病気耐性", "set": "セット", "unknown_color": "情報提供を\nお待ちして\nおります！", "close": "閉じる"},
    "EN": {"title": "Equipment Catalog", "search": "Search names", "all": "All", "male": "Male", "female": "Female",
           "armor": "Armor", "clothes": "Clothes", "shoes": "Shoes", "outfit": "Costume", "level": "Required level",
           "base": "Base", "enhanced": "Enhanced", "weight": "Weight", "color": "Color", "sort": "Sort",
           "sort_name": "Name", "sort_level_asc": "Level: low to high", "sort_level_desc": "Level: high to low",
           "sort_category": "Category", "count": "{count} items", "no_results": "No equipment matches these filters.",
           "variants": "Dye color chart", "move_speed": "Move speed", "poison_resistance": "Poison resist",
           "disease_resistance": "Disease resist", "set": "SET", "unknown_color": "No\nInformation", "close": "Close"},
}


def load_preferences(path=PREFERENCES_PATH):
    defaults = {"gender": "male", "category": "armor", "sort": "level_asc", "color": "0"}
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
    return defaults


def save_preferences(value, path=PREFERENCES_PATH):
    path = Path(path)
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


class ArmorCatalogUI:
    def __init__(self, master, project_dir, language_provider, store=None, preferences_path=None):
        self.master, self.language_provider = master, language_provider
        self.store = store or ArmorCatalogStore(project_dir)
        self.window = self.built_language = None
        self.items, self.visible_items, self.items_by_id = [], [], {}
        self.bounds = (0, 0, 1, 1)
        self.card_states, self.image_cache = {}, {}
        self.refresh_job = None
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
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.card_canvas.yview, style="Armor.Vertical.TScrollbar")
        self.card_canvas.configure(yscrollcommand=scroll.set)
        self.card_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.cards_frame = tk.Frame(self.card_canvas, bg=BG, padx=5, pady=5)
        self.cards_window = self.card_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda _event: self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all")))
        self.card_canvas.bind("<Configure>", lambda event: self.card_canvas.itemconfigure(self.cards_window, width=event.width))
        self.card_canvas.bind("<Enter>", lambda _event: self.card_canvas.bind_all("<MouseWheel>", self.scroll_cards))
        self.card_canvas.bind("<Leave>", lambda _event: self.card_canvas.unbind_all("<MouseWheel>"))

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
        }
        save_preferences(self.preferences, self.preferences_path)

    def schedule_refresh(self):
        if self.window and self.window.winfo_exists():
            if self.refresh_job:
                self.window.after_cancel(self.refresh_job)
            self.refresh_job = self.window.after(SEARCH_DEBOUNCE_MS, self.refresh_list)

    def refresh_list(self):
        if not self.window or not hasattr(self, "cards_frame"):
            return
        self.refresh_job = None
        self.visible_items = filtered_items(self.items, self.search_var.get(), self.gender_var.get(),
                                            self.category_var.get(), self.locale(),
                                            self.sort_choices.get(self.sort_var.get(), "level_asc"))
        self.update_global_color_controls()
        self.render_cards()

    def update_global_color_controls(self):
        for child in self.global_color_frame.winfo_children():
            child.destroy()
        if self.category_var.get() == "all":
            return
        color_ids = sorted({str(color.get("id")) for item in self.visible_items for color in (item.get("colors") or [])}, key=int)
        if not color_ids:
            return
        if self.color_var.get() not in color_ids:
            self.color_var.set(color_ids[0])
            self.preferences["color"] = color_ids[0]
            save_preferences(self.preferences, self.preferences_path)
        categories = {item.get("category") for item in self.visible_items}
        label_category = self.category_var.get() if self.category_var.get() != "all" else (next(iter(categories)) if len(categories) == 1 else None)
        labels = self.store.color_labels(label_category, self.locale()) if label_category else {}
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

    def global_color_selected(self, _event=None):
        color_id = getattr(self, "color_choice_ids", {}).get(self.color_choice_var.get())
        if color_id is not None:
            self.color_var.set(color_id)
            self.global_color_changed()

    def global_color_changed(self):
        self.save_filter_preferences()
        selected = self.color_var.get()
        for state in self.card_states.values():
            state["color"] = color_index_for_selection(state["item"], selected)
            self.update_card(state)

    def render_cards(self):
        for state in self.card_states.values():
            state["card"].grid_remove()
        if self.no_results_label is not None:
            self.no_results_label.destroy()
            self.no_results_label = None
        self.count_label.configure(text=self.texts()["count"].format(count=len(self.visible_items)))
        for column in range(CARD_COLUMNS):
            self.cards_frame.columnconfigure(column, weight=1, uniform="armor_cards")
        if not self.visible_items:
            self.no_results_label = tk.Label(
                self.cards_frame, text=self.texts()["no_results"], bg=BG, fg=MUTED,
                font=("Noto Sans KR", 12), pady=40,
            )
            self.no_results_label.grid(row=0, column=0, columnspan=2, sticky="ew")
        selected_color = catalog_color_selection(self.category_var.get(), self.color_var.get())
        for index, item in enumerate(self.visible_items):
            state = self.card_states.get(item["id"])
            if state is None:
                self.build_card(item, index // CARD_COLUMNS, index % CARD_COLUMNS)
                continue
            state["color"] = color_index_for_selection(item, selected_color)
            state["card"].grid(row=index // CARD_COLUMNS, column=index % CARD_COLUMNS,
                               sticky="n", padx=4, pady=4)
            self.update_card(state)
        self.cards_frame.update_idletasks()
        self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all"))
        self.card_canvas.yview_moveto(0)

    def build_card(self, item, row, column):
        text = self.texts()
        control_font = (modal_font_family(self.master, self.language()), 12, "bold")
        card = tk.Canvas(self.cards_frame, bg=BG, width=CARD_WIDTH, height=CARD_HEIGHT, bd=0, highlightthickness=0)
        card.grid(row=row, column=column, sticky="n", padx=4, pady=4)
        self.rounded_rectangle(card, 2, 2, CARD_WIDTH - 2, CARD_HEIGHT - 2, 13, fill=CARD_BG, outline="#5c5044", width=1)
        image_label = tk.Label(card, bg="#151310", fg=MUTED, text="No image")
        card.create_window(16, 32, window=image_label, anchor="nw", width=170, height=150)
        title_label = tk.Label(card, bg=CARD_BG, fg="#f2d995", anchor="w", font=("Noto Sans KR", 13, "bold"))
        card.create_window(204, 18, window=title_label, anchor="nw", width=275, height=27)
        meta = f'{text[item["gender"]]} · {text[item["category"]]}'
        if item.get("category") != "shoes":
            meta += f' · Lv.{item.get("required_level", 0)}'
        card.create_text(16, 7, text=meta, fill=MUTED, anchor="nw", width=170,
                         font=("Noto Sans KR", 8))
        stat_widgets = {}
        for row_index, (metric, label_text) in enumerate((("ac", "AC"), ("dc", "DC"), ("weight", text["weight"]))):
            row_y = 66 + row_index * 23
            label = tk.Label(card, text=label_text, bg=CARD_BG, fg="#f2d995", anchor="w",
                             font=("Noto Sans KR", 10, "bold"))
            base_label = tk.Label(card, bg=CARD_BG, fg=TEXT, anchor="e",
                                  font=("Noto Sans KR", 10, "bold"))
            bonus_label = tk.Label(card, bg=CARD_BG, fg=GOLD, anchor="e",
                                   font=("Noto Sans KR", 10, "bold"))
            total_label = tk.Label(card, bg=CARD_BG, fg="#e36a5d", anchor="e",
                                   font=("Noto Sans KR", 10, "bold"))
            card.create_window(204, row_y, window=label, anchor="nw", width=82, height=26)
            card.create_window(338, row_y, window=base_label, anchor="ne", width=44, height=26)
            card.create_window(398, row_y, window=bonus_label, anchor="ne", width=48, height=26)
            card.create_window(470, row_y, window=total_label, anchor="ne", width=62, height=26)
            stat_widgets[metric] = (base_label, bonus_label, total_label)
        set_effect = item.get("set_effect")
        set_var = tk.BooleanVar(value=False)
        set_check = None
        # Only render the set-effect control when this exact item has a
        # verified set pairing. This keeps ordinary armor cards uncluttered,
        # while allowing the Elice/Scoble clothing pair to expose its bonus.
        if isinstance(set_effect, dict):
            set_check = tk.Checkbutton(
                card, variable=set_var, bg="#3b3022", fg=TEXT, activebackground="#3b3022",
                activeforeground=TEXT, selectcolor="#17130f", highlightthickness=0, bd=0,
                anchor="w", padx=4, font=("Noto Sans KR", 8),
            )
            required_ref = set_effect.get("required_item", {})
            required = self.items_by_id.get(required_ref.get("id"), required_ref)
            required_name = localized_name(required, self.locale())
            full_set_name = f'{text["set"]}: {required_name}'
            set_font = tkfont.Font(font=set_check.cget("font"))
            short_set_name = ellipsize(full_set_name, set_font, 132)
            set_check.configure(text=short_set_name)
            if short_set_name != full_set_name:
                self.bind_name_tooltip(set_check, full_set_name)
            card.create_window(16, 182, window=set_check, anchor="nw", width=170, height=24)
        controls = tk.Frame(card, bg=CARD_BG)
        minus_button = tk.Button(
            controls, text="−", command=lambda value=item["id"]: self.adjust_enhancement(value, -1),
            bg="#3b3022", fg=TEXT, activebackground=HEADER, activeforeground=TEXT,
            relief="flat", bd=0, highlightthickness=0, padx=0, pady=0,
            font=control_font, cursor="hand2",
        )
        plus_button = tk.Button(
            controls, text="+", command=lambda value=item["id"]: self.adjust_enhancement(value, 1),
            bg="#3b3022", fg=TEXT, activebackground=HEADER, activeforeground=TEXT,
            relief="flat", bd=0, highlightthickness=0, padx=0, pady=0,
            font=control_font, cursor="hand2",
        )
        minus_button.place(x=0, y=1, width=40, height=30)
        plus_button.place(x=44, y=1, width=40, height=30)
        card.create_window(400, 154, window=controls, anchor="nw", width=84, height=36)
        effect_label = tk.Label(card, bg=CARD_BG, fg=MUTED, anchor="w", font=("Noto Sans KR", 8))
        card.create_window(204, 145, window=effect_label, anchor="nw", width=195, height=36)
        colors = item.get("colors") or []
        selected_color = catalog_color_selection(self.category_var.get(), self.color_var.get())
        initial_color = color_index_for_selection(item, selected_color)
        state = {"item": item, "card": card, "color": initial_color, "enhancement": 0, "image": image_label,
                 "set_var": set_var, "set_check": set_check, "title_label": title_label,
                 "stat_widgets": stat_widgets,
                 "effect_label": effect_label}
        self.card_states[item["id"]] = state
        if set_check is not None:
            set_check.configure(command=lambda value=item["id"]: self.update_card(self.card_states[value]))
        image_label.bind("<Button-1>", lambda _event, value=item: self.show_variants(value))
        if set_check is not None:
            set_check.bind("<Button-1>", lambda event: event.widget.after_idle(lambda: None), add="+")
        self.update_card(state)

    def update_card(self, state):
        item, colors = state["item"], state["item"].get("colors") or []
        if colors:
            state["color"] %= len(colors)
            color = colors[state["color"]]
            label = self.store.color_labels(item.get("category"), self.locale()).get(str(color.get("id")), str(color.get("id")))
            self.show_card_image(state["image"], color.get("image"))
        active_set = item.get("set_effect") if state["set_var"].get() else None
        result = enhanced_stats(item, state["enhancement"], self.store.enhancement_steps(item.get("category")), active_set)
        level = state["enhancement"]
        full_title = f'{localized_name(item, self.locale())}{f" +{level}" if level else ""}'
        title_font = tkfont.Font(font=state["title_label"].cget("font"))
        state["title_label"].configure(text=ellipsize(full_title, title_font, 270))
        stats = item.get("stats") or {}
        for metric, widgets in state["stat_widgets"].items():
            base_label, bonus_label, total_label = widgets
            base = stats.get(metric, 0)
            total = result.get(metric, base) if result else base
            bonus = total - base
            base_label.configure(text=str(base))
            bonus_label.configure(text=f'{bonus:+d}')
            total_label.configure(text=f'({total})')
        extra = []
        if active_set and result:
            if result.get("move_speed_percent"):
                extra.append(f'{self.texts()["move_speed"]} +{result["move_speed_percent"]}%')
            if result.get("poison_resistance"):
                extra.append(f'{self.texts()["poison_resistance"]} +{result["poison_resistance"]}')
            if result.get("disease_resistance"):
                extra.append(f'{self.texts()["disease_resistance"]} +{result["disease_resistance"]}')
        state["effect_label"].configure(text=" · ".join(extra))

    def show_card_image(self, label, relative):
        try:
            photo = self.image_cache.get(relative)
            if photo is None:
                photo = ImageTk.PhotoImage(zoom_transparent_sprite(self.store.image(relative), (170, 150), 2.5))
                self.image_cache[relative] = photo
            label.configure(image=photo, text="")
            label.image = photo
        except Exception:
            label.configure(image="", text="No image")

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
        labels = self.store.color_labels(item.get("category"), self.locale())
        slots = variant_slots(item)
        columns = min(4, max(1, len(slots)))
        for index, (color, unknown) in enumerate(slots):
            color_id = str(color.get("id"))
            cell = tk.Frame(table, bg=PANEL, highlightbackground="#5c5044", highlightthickness=1, padx=5, pady=5)
            cell.grid(row=index // columns, column=index % columns, padx=3, pady=3, sticky="n")
            tk.Label(cell, text=labels.get(color_id, color_id), bg=PANEL, fg="#f2d995",
                     font=(family, 9, "bold"), width=16).pack(fill="x", pady=(0, 4))
            image_box = tk.Frame(cell, bg="#151310", width=130, height=170)
            image_box.pack_propagate(False)
            image_box.pack()
            image_label = tk.Label(image_box, bg="#151310")
            image_label.pack(fill="both", expand=True)
            if unknown:
                image_label.configure(text=text["unknown_color"], fg=MUTED, justify="center",
                                      font=(family, 9, "bold"))
            else:
                try:
                    image = zoom_transparent_sprite(self.store.image(color.get("image")), (130, 170), 2.5)
                    photo = ImageTk.PhotoImage(image)
                    self.variant_photos.append(photo)
                    image_label.configure(image=photo)
                except Exception:
                    image_label.configure(text="No image", fg=MUTED)
        footer = tk.Frame(content, bg=PANEL, height=44, padx=10, pady=7)
        footer.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        footer.pack_propagate(False)
        tk.Button(footer, text=text["close"], command=self.close_variants, bg="#3b3022", fg="#f3d68f",
                  activebackground=HEADER, activeforeground="#fff4d2", relief="flat", bd=0,
                  padx=18, font=(family, 9, "bold"), cursor="hand2").pack(side="right", fill="y")
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
        self.card_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    @staticmethod
    def rounded_rectangle(canvas, x1, y1, x2, y2, radius=12, **kwargs):
        points = (x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2,
                  x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1)
        return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def close(self):
        self.hide_name_tooltip()
        self.close_variants()
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

from __future__ import annotations

import tkinter as tk

from modal_window import activate_modal, bind_modal_escape

from .window_attachment import attach_above


STACK_SIZE = 99
MEDICINE_STACK_SIZE = 50
TONIC_STACK_SIZE = 10
BG = "#17130f"
PANEL = "#2a2118"
PANEL_HOVER = "#443422"
HEADER = "#5a4932"
GOLD = "#d8b15a"
TEXT = "#f1e5c7"
BRIGHT = "#fff1c9"
MUTED = "#bda982"

RECIPES: dict[str, dict[str, int]] = {
    "해독약": {"인삼": 1, "푸른곰팡이": 1},
    "질병치료약": {"인삼": 1, "기름": 1},
    "독약": {"생선비늘": 1, "기름": 1, "염산": 1},
    "석화치료약": {"박쥐털": 1, "푸른곰팡이": 1, "녹슨철가루": 1},
    "칼기름": {"기름": 1, "녹슨철가루": 1},
    "강장제": {"생선비늘": 1, "효모": 1},
    "응급처치약": {"인삼": 3, "생선비늘": 2, "효모": 1},
    "갑옷기름": {"녹슨철가루": 1, "염산": 1},
    "방패기름": {"양잿물": 1, "녹슨철가루": 1},
    "힘의 약": {"인삼": 2, "염산": 1},
    "불의 결정": {"인삼": 1, "유황": 2, "기름": 1, "염산": 1},
    "얼음의 결정": {"인삼": 1, "유황": 1, "기름": 1, "녹슨철가루": 1, "염산": 1},
    "병균의 병": {"박쥐털": 1, "푸른곰팡이": 1, "기름": 1, "염산": 1},
}

MATERIAL_PRICES = {
    "인삼": 50,
    "생선비늘": 10,
    "박쥐털": 15,
    "유황": 20,
    "푸른곰팡이": 10,
    "효모": 15,
    "기름": 10,
    "양잿물": 20,
    "녹슨철가루": 30,
    "염산": 40,
}

MEDICINE_NAMES = {
    "KR": {name: name for name in RECIPES},
    "JP": {
        "해독약": "解毒薬", "질병치료약": "病気治療薬", "독약": "毒薬", "석화치료약": "石化治療薬",
        "칼기름": "武器油", "강장제": "強壮剤", "응급처치약": "応急処置薬", "방패기름": "盾油",
        "갑옷기름": "鎧油", "힘의 약": "力の薬", "불의 결정": "炎の結晶", "얼음의 결정": "氷の結晶",
        "병균의 병": "病菌の瓶",
    },
    "EN": {
        "해독약": "Antidote", "질병치료약": "Disease Cure", "독약": "Poison", "석화치료약": "Petrification Cure",
        "칼기름": "Blade Oil", "강장제": "Tonic", "응급처치약": "First Aid Medicine", "방패기름": "Shield Oil",
        "갑옷기름": "Armor Oil", "힘의 약": "Strength Medicine", "불의 결정": "Fire Crystal",
        "얼음의 결정": "Ice Crystal", "병균의 병": "Bottle of Germs",
    },
}

MATERIAL_NAMES = {
    "KR": {
        "인삼": "인삼", "생선비늘": "생선비늘", "박쥐털": "박쥐털", "유황": "유황", "푸른곰팡이": "푸른곰팡이",
        "효모": "효모", "기름": "기름", "양잿물": "양잿물", "녹슨철가루": "녹슨철가루", "염산": "염산",
    },
    "JP": {
        "인삼": "高麗人参", "생선비늘": "魚の鱗", "박쥐털": "コウモリの毛", "유황": "硫黄", "푸른곰팡이": "青カビ",
        "효모": "酵母", "기름": "油", "양잿물": "灰汁", "녹슨철가루": "錆鉄粉", "염산": "塩酸",
    },
    "EN": {
        "인삼": "Ginseng", "생선비늘": "Fish Scale", "박쥐털": "Bat fur", "유황": "Sulfur", "푸른곰팡이": "Blue Mold",
        "효모": "Yeast", "기름": "Oil", "양잿물": "Lye", "녹슨철가루": "Rusty Iron Powder",
        "염산": "Hydrochloric Acid",
    },
}

TEXTS = {
    "KR": {
        "title": "연금술 시뮬레이터", "unit": "제작 수량 단위", "count_mode": "개수 단위",
        "stack_mode": "묶음 단위", "items": "만들 물건", "materials": "필요한 총 재료",
        "selected": "선택한 물건", "calculate": "계산하기", "close": "닫기", "reset": "내용물 초기화",
        "empty_materials": "수량을 입력해 주세요", "empty_selected": "선택한 물건이 없습니다",
        "tonic_warning": "강장제는 10개가 1묶음입니다.",
        "material_cost": "재료비 {cost:,} 란스",
    },
    "JP": {
        "title": "錬金術シミュレーター", "unit": "製作数量の単位", "count_mode": "個数単位",
        "stack_mode": "束単位", "items": "作るアイテム", "materials": "必要素材の合計",
        "selected": "選択したアイテム", "calculate": "計算", "close": "閉じる", "reset": "内容をリセット",
        "empty_materials": "数量を入力してください", "empty_selected": "アイテムが選択されていません",
        "tonic_warning": "強壮剤は10個で1束です。",
        "material_cost": "材料費 {cost:,} ランス",
    },
    "EN": {
        "title": "Alchemy Simulator", "unit": "Crafting quantity unit", "count_mode": "Item count",
        "stack_mode": "Stack unit", "items": "Items to craft", "materials": "Total materials required",
        "selected": "Selected items", "calculate": "Calculate", "close": "Close", "reset": "Reset contents",
        "empty_materials": "Enter a quantity", "empty_selected": "No items selected",
        "tonic_warning": "Tonic is 10 items per stack.",
        "material_cost": "Material Cost {cost:,} Lance",
    },
}


def calculate_materials(amounts: dict[str, int]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for medicine, amount in amounts.items():
        if medicine not in RECIPES:
            raise KeyError(medicine)
        if amount < 0:
            raise ValueError("제작 수량은 0 이상이어야 합니다.")
        for material, per_item in RECIPES[medicine].items():
            totals[material] = totals.get(material, 0) + per_item * amount
    return {material: count for material, count in totals.items() if count}


def calculate_material_cost(materials: dict[str, int]) -> int:
    return sum(count * MATERIAL_PRICES[material] for material, count in materials.items())


def medicine_stack_size(medicine: str) -> int:
    return TONIC_STACK_SIZE if medicine == "강장제" else MEDICINE_STACK_SIZE


def expand_crafting_amounts(amounts: dict[str, int], mode: str) -> dict[str, int]:
    if mode == "count":
        return dict(amounts)
    if mode != "stack":
        raise ValueError(f"Unknown crafting unit mode: {mode}")
    return {medicine: count * medicine_stack_size(medicine) for medicine, count in amounts.items()}


def format_stack_count(count: int, language: str = "KR") -> str:
    stacks, remainder = divmod(count, STACK_SIZE)
    if language == "JP":
        if stacks == 0:
            return f"{count:,}個"
        if remainder == 0:
            return f"{count:,}個 ({stacks:,}束)"
        return f"{count:,}個 ({stacks:,}束+{remainder:,}個)"
    if language == "EN":
        if stacks == 0:
            return f"{count:,}"
        if remainder == 0:
            return f"{count:,} ({stacks:,}S)"
        return f"{count:,} ({stacks:,}S+{remainder:,})"
    if stacks == 0:
        return f"{count:,}개"
    if remainder == 0:
        return f"{count:,}개 ({stacks:,}묶음)"
    return f"{count:,}개 ({stacks:,}묶음+{remainder:,}개)"


def format_medicine_count(medicine: str, count: int, language: str = "KR") -> str:
    stack_size = medicine_stack_size(medicine)
    stacks, remainder = divmod(count, stack_size)
    if language == "JP":
        if stacks == 0:
            return f"{count:,}個"
        if remainder == 0:
            return f"{count:,}個 ({stacks:,}束)"
        return f"{count:,}個 ({stacks:,}束+{remainder:,}個)"
    if language == "EN":
        if stacks == 0:
            return f"{count:,}"
        if remainder == 0:
            return f"{count:,} ({stacks:,}S)"
        return f"{count:,} ({stacks:,}S+{remainder:,})"
    if stacks == 0:
        return f"{count:,}개"
    if remainder == 0:
        return f"{count:,}개 ({stacks:,}묶음)"
    return f"{count:,}개 ({stacks:,}묶음+{remainder:,}개)"


class AlchemyUI:
    def __init__(self, root, target_rect_provider=None, owner_hwnd_provider=None, language_provider=None):
        self.root = root
        self.target_rect_provider = target_rect_provider
        self.owner_hwnd_provider = owner_hwnd_provider
        self.language_provider = language_provider
        self.built_language = None
        self.window: tk.Toplevel | None = None
        self.drag_origin = None
        self.mode = "count"
        self.amount_vars = {name: tk.StringVar(master=root, value="0") for name in RECIPES}
        self.adjust_frames: dict[str, tk.Frame] = {}
        self.mode_buttons: dict[str, tk.Button] = {}
        self.material_rows: tk.Frame | None = None
        self.selected_rows: tk.Frame | None = None
        self.material_cost_label: tk.Label | None = None
        self.tooltip: tk.Toplevel | None = None

    def language(self):
        language = self.language_provider() if self.language_provider else "KR"
        return language if language in TEXTS else "EN"

    def open(self):
        language = self.language()
        if self.window and self.window.winfo_exists() and self.built_language != language:
            self._hide_tooltip()
            self.window.destroy()
            self.window = None
            self.adjust_frames.clear()
            self.mode_buttons.clear()
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self._place_window()
            activate_modal(self.window)
            return

        win = tk.Toplevel(self.root)
        self.window = win
        self.built_language = language
        text = TEXTS[language]
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)

        frame = tk.Frame(win, bg=BG, padx=10, pady=10, highlightbackground=GOLD, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        header = tk.Frame(frame, bg=HEADER)
        header.pack(fill="x", pady=(0, 10))
        title = tk.Label(
            header, text=text["title"], bg=HEADER, fg="#ffe09a",
            anchor="w", padx=12, pady=9, font=("Noto Sans KR", 14, "bold"),
        )
        title.pack(fill="x")
        for widget in (header, title):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)

        mode_bar = tk.Frame(frame, bg=BG)
        mode_bar.pack(fill="x", pady=(0, 9))
        tk.Label(mode_bar, text=text["unit"], bg=BG, fg=MUTED, font=("Noto Sans KR", 10, "bold")).pack(side="left")
        for key, label in (("count", text["count_mode"]), ("stack", text["stack_mode"])):
            button = tk.Button(
                mode_bar, text=label, command=lambda value=key: self._set_mode(value),
                relief="flat", bd=0, padx=14, pady=5, font=("Noto Sans KR", 10, "bold"),
            )
            button.pack(side="left", padx=(8, 0))
            self.mode_buttons[key] = button
        tk.Label(
            mode_bar, text=text["tonic_warning"], bg=BG, fg=GOLD,
            anchor="se", font=("Noto Sans KR", 9, "bold"),
        ).pack(side="right", anchor="s", padx=(18, 2), pady=(0, 1))
        self._refresh_mode_buttons()

        content = tk.Frame(frame, bg=BG)
        content.pack(fill="both", expand=True)
        inputs = tk.Frame(content, bg=PANEL, padx=9, pady=9, highlightbackground=HEADER, highlightthickness=1)
        inputs.pack(side="left", fill="y", padx=(0, 9))
        results = tk.Frame(content, bg=PANEL, padx=9, pady=9, highlightbackground=HEADER, highlightthickness=1)
        results.pack(side="left", fill="both", expand=True)

        tk.Label(inputs, text=text["items"], bg=PANEL, fg=BRIGHT, anchor="w", font=("Noto Sans KR", 11, "bold")).pack(fill="x", pady=(0, 5))
        info_width = 180 if language == "EN" else (165 if language == "JP" else 150)
        for medicine, recipe in RECIPES.items():
            row = tk.Frame(inputs, bg=PANEL, width=500 + info_width - 150, height=32)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            info = tk.Frame(row, bg=PANEL, width=info_width)
            info.pack(side="left", fill="y")
            info.pack_propagate(False)
            name_label = tk.Label(
                info, text=MEDICINE_NAMES[language][medicine], bg=PANEL, fg=TEXT, anchor="w",
                font=("Noto Sans KR", 10, "bold"),
            )
            name_label.pack(fill="both", expand=True)
            recipe_text = ", ".join(f"{MATERIAL_NAMES[language][name]} {count}" for name, count in recipe.items())
            name_label.bind("<Enter>", lambda event, text=recipe_text: self._show_tooltip(event, text))
            name_label.bind("<Leave>", self._hide_tooltip)
            controls = tk.Frame(row, bg=PANEL)
            controls.pack(side="left", fill="y")
            self.adjust_frames[medicine] = controls
        self._rebuild_adjusters()

        material_panel = tk.Frame(results, bg=PANEL)
        material_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        selected_panel = tk.Frame(results, bg=PANEL)
        selected_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))
        tk.Label(material_panel, text=text["materials"], bg=PANEL, fg=BRIGHT, anchor="w", font=("Noto Sans KR", 11, "bold")).pack(fill="x")
        self.material_rows = tk.Frame(material_panel, bg=PANEL)
        self.material_rows.pack(fill="x", pady=(5, 0))
        self.material_cost_label = tk.Label(
            material_panel, bg=HEADER, fg="#ffe09a", anchor="e", padx=9, pady=6,
            font=("Noto Sans KR", 10, "bold"),
        )
        self.material_cost_label.pack(fill="x", pady=(7, 0))
        tk.Label(selected_panel, text=text["selected"], bg=PANEL, fg=BRIGHT, anchor="w", font=("Noto Sans KR", 11, "bold")).pack(fill="x")
        self.selected_rows = tk.Frame(selected_panel, bg=PANEL)
        self.selected_rows.pack(fill="x", pady=(5, 0))
        self._render_results({}, {})

        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x", pady=(10, 0))
        tk.Button(
            buttons, text=text["calculate"], command=self.calculate, relief="flat", bd=0,
            bg="#6b5537", fg=BRIGHT, activebackground="#806846", activeforeground="#ffffff",
            padx=24, pady=7, font=("Noto Sans KR", 10, "bold"),
        ).pack(side="right")
        tk.Button(
            buttons, text=text["close"], command=self.close, relief="flat", bd=0,
            bg=PANEL, fg=TEXT, activebackground=PANEL_HOVER, activeforeground="#ffffff",
            padx=24, pady=7, font=("Noto Sans KR", 10),
        ).pack(side="right", padx=(0, 7))
        tk.Button(
            buttons, text=text["reset"], command=self.reset, relief="flat", bd=0,
            bg=PANEL, fg=TEXT, activebackground=PANEL_HOVER, activeforeground="#ffffff",
            padx=18, pady=7, font=("Noto Sans KR", 10),
        ).pack(side="left")

        win.bind("<Return>", lambda _event: self.calculate())
        bind_modal_escape(win, self.close)
        self._place_window()

    def _set_mode(self, mode: str):
        if mode == self.mode:
            return
        self.mode = mode
        self._refresh_mode_buttons()
        self._rebuild_adjusters()
        self.reset()

    def _refresh_mode_buttons(self):
        for key, button in self.mode_buttons.items():
            selected = key == self.mode
            button.configure(
                bg="#6b5537" if selected else PANEL,
                fg=BRIGHT if selected else MUTED,
                activebackground="#806846" if selected else PANEL_HOVER,
                activeforeground="#ffffff",
            )

    def _rebuild_adjusters(self):
        for medicine, frame in self.adjust_frames.items():
            for child in frame.winfo_children():
                child.destroy()
            deltas = (-10, -5, -1, 1, 5, 10) if self.mode == "count" else (-1, 1)
            for delta in deltas[: len(deltas) // 2]:
                self._adjust_button(frame, medicine, delta).pack(side="left", padx=1)
            entry = tk.Entry(
                frame, textvariable=self.amount_vars[medicine], width=6, justify="center",
                bg="#fff4d2", fg="#25190f", relief="flat", bd=0, font=("Noto Sans KR", 10, "bold"),
            )
            entry.pack(side="left", fill="y", padx=3)
            for delta in deltas[len(deltas) // 2:]:
                self._adjust_button(frame, medicine, delta).pack(side="left", padx=1)

    def _adjust_button(self, parent, medicine: str, delta: int):
        return tk.Button(
            parent, text=f"{delta:+d}", command=lambda: self._adjust(medicine, delta),
            width=3 if abs(delta) < 10 else 4, relief="flat", bd=0,
            bg="#3b3022", fg=TEXT, activebackground="#6b5537", activeforeground="#ffffff",
            font=("Noto Sans KR", 9, "bold"),
        )

    def _adjust(self, medicine: str, delta: int):
        current = self._safe_value(self.amount_vars[medicine])
        self.amount_vars[medicine].set(str(max(0, current + delta)))

    @staticmethod
    def _safe_value(var: tk.StringVar) -> int:
        try:
            return max(0, int(var.get().strip() or "0"))
        except ValueError:
            return 0

    def calculate(self):
        raw_amounts = {name: self._safe_value(var) for name, var in self.amount_vars.items()}
        amounts = expand_crafting_amounts(raw_amounts, self.mode)
        for name, var in self.amount_vars.items():
            if not var.get().strip().isdigit():
                var.set("0")
        self._render_results(calculate_materials(amounts), amounts)

    def reset(self):
        for var in self.amount_vars.values():
            var.set("0")
        self._render_results({}, {})

    def _show_tooltip(self, event, text: str):
        self._hide_tooltip()
        tip = tk.Toplevel(self.window)
        self.tooltip = tip
        tip.overrideredirect(True)
        tip.configure(bg=GOLD)
        label = tk.Label(
            tip, text=text, bg="#2a2118", fg=BRIGHT, padx=9, pady=6,
            font=("Noto Sans KR", 10), relief="flat", bd=0,
        )
        label.pack(padx=1, pady=1)
        tip.update_idletasks()
        x = event.x_root + 14
        y = event.y_root + 12
        x = min(x, tip.winfo_screenwidth() - tip.winfo_reqwidth() - 4)
        y = min(y, tip.winfo_screenheight() - tip.winfo_reqheight() - 4)
        tip.geometry(f"+{max(4, x)}+{max(4, y)}")

    def _hide_tooltip(self, _event=None):
        if self.tooltip and self.tooltip.winfo_exists():
            self.tooltip.destroy()
        self.tooltip = None

    def _render_results(self, materials: dict[str, int], amounts: dict[str, int]):
        language = self.language()
        text = TEXTS[language]
        self._clear_rows(self.material_rows)
        self._clear_rows(self.selected_rows)
        if materials:
            for index, (name, count) in enumerate(sorted(materials.items())):
                self._result_row(self.material_rows, MATERIAL_NAMES[language][name], format_stack_count(count, language), index)
        else:
            self._empty_row(self.material_rows, text["empty_materials"])
        if self.material_cost_label:
            self.material_cost_label.configure(
                text=text["material_cost"].format(cost=calculate_material_cost(materials))
            )
        selected = [(name, count) for name, count in amounts.items() if count]
        if selected:
            for index, (name, count) in enumerate(selected):
                self._result_row(self.selected_rows, MEDICINE_NAMES[language][name], format_medicine_count(name, count, language), index)
        else:
            self._empty_row(self.selected_rows, text["empty_selected"])

    @staticmethod
    def _clear_rows(frame):
        if frame:
            for child in frame.winfo_children():
                child.destroy()

    @staticmethod
    def _result_row(parent, name: str, value: str, index: int):
        row = tk.Frame(parent, bg="#211a14", width=400, height=27)
        row.grid(row=index, column=0, sticky="ew", pady=1)
        row.pack_propagate(False)
        parent.grid_columnconfigure(0, minsize=400, weight=1)
        tk.Label(row, text=name, width=18, bg="#211a14", fg=TEXT, anchor="w", padx=7, font=("Noto Sans KR", 10)).pack(side="left", fill="y")
        tk.Label(row, text=value, bg="#211a14", fg=BRIGHT, anchor="w", padx=2, font=("Noto Sans KR", 10, "bold")).pack(side="left", fill="y")

    @staticmethod
    def _empty_row(parent, text: str):
        parent.grid_columnconfigure(0, minsize=400, weight=1)
        tk.Label(parent, text=text, bg="#211a14", fg=MUTED, anchor="w", padx=7, pady=5, font=("Noto Sans KR", 10)).grid(row=0, column=0, sticky="ew")

    def _place_window(self):
        if not self.window:
            return
        self.window.update_idletasks()
        width = self.window.winfo_reqwidth()
        height = self.window.winfo_reqheight()
        rect = self.target_rect_provider() if self.target_rect_provider else None
        if rect:
            left, top, right, bottom = rect
            x = left + (right - left - width) // 2
            y = top + (bottom - top - height) // 2
        else:
            x = (self.window.winfo_screenwidth() - width) // 2
            y = (self.window.winfo_screenheight() - height) // 2
        x, y = max(0, x), max(0, y)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        owner = self.owner_hwnd_provider() if self.owner_hwnd_provider else None
        if owner:
            attach_above(self.window, owner, x, y)
        else:
            self.window.deiconify()
            self.window.lift()
        self.window.update_idletasks()

    def _start_drag(self, event):
        if self.window:
            self.drag_origin = event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y()

    def _drag(self, event):
        if self.window and self.drag_origin:
            sx, sy, wx, wy = self.drag_origin
            self.window.geometry(f"+{wx + event.x_root - sx}+{wy + event.y_root - sy}")

    def close(self):
        self._hide_tooltip()
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

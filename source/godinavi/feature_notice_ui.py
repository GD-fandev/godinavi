import tkinter as tk

from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, modal_font_family, place_modal


TEXTS = {
    "KR": {
        "title": "GodiNavi 1.4.0 안내",
        "message": (
            "몬스터 도감의 추가로 인해 맵 업데이트가 반드시 필요합니다.\n\n"
            "아직 업데이트하지 않으셨다면 몬스터 도감의 정상적인 이용을 위해 "
            "반드시 맵 업데이트를 진행해주세요."
        ),
        "confirm": "확인",
    },
    "JP": {
        "title": "GodiNavi 1.4.0 のご案内",
        "message": (
            "モンスター図鑑の追加に伴い、マップ更新が必要です。\n\n"
            "まだ更新していない場合は、モンスター図鑑を正常に利用するため、"
            "必ずマップ更新を行ってください。"
        ),
        "confirm": "確認",
    },
    "EN": {
        "title": "GodiNavi 1.4.0 Notice",
        "message": (
            "A map update is required for the new Monster Compendium.\n\n"
            "If you have not updated yet, please install the map update so the "
            "Monster Compendium can work correctly."
        ),
        "confirm": "OK",
    },
}


class FeatureNoticeUI:
    def __init__(self, root, language_provider, close_callback=None):
        self.root = root
        self.language_provider = language_provider
        self.close_callback = close_callback
        self.window = None
        self.preview = False

    def language(self):
        value = self.language_provider() if self.language_provider else "EN"
        return value if value in TEXTS else "EN"

    def show(self, preview=False):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            activate_modal(self.window)
            return
        self.preview = preview
        text = TEXTS[self.language()]
        win = tk.Toplevel(self.root)
        self.window = win
        win.overrideredirect(True)
        win.configure(bg="#17130f")
        win.transient(self.root)
        frame = tk.Frame(win, bg="#17130f", padx=12, pady=12, highlightbackground="#d8b15a", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        family = modal_font_family(win, self.language())
        header = tk.Frame(frame, bg="#5a4932")
        header.pack(fill="x", pady=(0, 14))
        title = tk.Label(header, text=text["title"], bg="#5a4932", fg="#ffe09a", anchor="w", padx=14, pady=10, font=(family, 12, "bold"))
        title.pack(fill="x")
        tk.Label(
            frame, text=text["message"], bg="#17130f", fg="#f1e5c7",
            anchor="w", justify="left", wraplength=520, padx=8, pady=12,
            font=(family, 10),
        ).pack(fill="both", expand=True)
        footer = tk.Frame(frame, bg="#17130f")
        footer.pack(side="bottom", fill="x", pady=(14, 0))
        tk.Button(
            footer, text=text["confirm"], command=self.close, relief="flat",
            bg="#6b5537", fg="#fff1c9", activebackground="#806846",
            activeforeground="#ffffff", padx=20, pady=7, font=(family, 9, "bold"),
        ).pack(side="right")
        _owner, bounds = place_modal(win, minimum_width=560, minimum_height=260, position_key="monster_dictionary_notice")
        bind_modal_drag(win, (header, title), lambda: bounds, position_key="monster_dictionary_notice")
        bind_modal_escape(win, self.close)

    def close(self):
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        preview = self.preview
        self.preview = False
        if not preview and self.close_callback:
            self.close_callback()

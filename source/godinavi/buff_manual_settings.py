"""Manual buff bindings and their shared-style settings dialog."""
import tkinter as tk

from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, modal_font_family, place_modal
from .window_attachment import client_screen_rect, find_godius_window, user32

MODIFIERS = {"Ctrl": (0x11,), "Alt": (0x12,), "Shift": (0x10,), "Win": (0x5B, 0x5C)}
KEY_NAMES = {**{n: chr(n) for n in range(0x30, 0x5B) if n <= 0x39 or n >= 0x41},
             **{0x70 + n: f"F{n + 1}" for n in range(24)},
             **{0x60 + n: f"Numpad {n}" for n in range(10)},
             0x04: "Mouse Middle", 0x05: "Mouse X1", 0x06: "Mouse X2",
             0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x20: "Space",
             0x21: "Page Up", 0x22: "Page Down", 0x23: "End", 0x24: "Home",
             0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
             0x2D: "Insert", 0x2E: "Delete", 0x6A: "Numpad *", 0x6B: "Numpad +",
             0x6D: "Numpad -", 0x6E: "Numpad .", 0x6F: "Numpad /",
             0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".",
             0xBF: "/", 0xC0: "`", 0xDB: "[", 0xDC: "Backslash", 0xDD: "]", 0xDE: "'"}


def defaults():
    return {"ice": {"key": ord("S"), "modifiers": ["Shift"], "seconds": 600},
            "fire": {"key": ord("D"), "modifiers": ["Shift"], "seconds": 600}}


def signature(binding):
    return binding["key"], frozenset(binding["modifiers"])


def validate_bindings(value):
    result = {}
    for buff in ("ice", "fire"):
        binding = value[buff]
        key = binding["key"]
        mods = binding["modifiers"]
        seconds = str(binding["seconds"])
        if (type(key) is not int or key not in KEY_NAMES or not isinstance(mods, list)
                or any(mod not in MODIFIERS for mod in mods) or len(set(mods)) != len(mods)
                or not seconds.isascii() or not seconds.isdigit() or not 1 <= int(seconds) <= 2147483647):
            raise ValueError("invalid")
        # These Windows combinations are reserved and cannot reliably reach the app.
        if (key == 0x73 and "Alt" in mods or key == 0x2E and {"Ctrl", "Alt"} <= set(mods)
                or key == ord("L") and "Win" in mods or key == 0x09 and ("Alt" in mods or "Win" in mods)):
            raise ValueError("reserved")
        result[buff] = {"key": key, "modifiers": [m for m in MODIFIERS if m in mods], "seconds": int(seconds)}
    if signature(result["ice"]) == signature(result["fire"]):
        raise ValueError("duplicate")
    return result


def load_bindings(config):
    try:
        return validate_bindings(config.get("manual_start_bindings", defaults()))
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
        return defaults()


def key_label(binding):
    return " + ".join([m for m in MODIFIERS if m in binding["modifiers"]] + [KEY_NAMES[binding["key"]]])


def input_state(get_state):
    keys = {key for key in KEY_NAMES if get_state(key) & 0x8000}
    mods = {mod for mod, codes in MODIFIERS.items() if any(get_state(code) & 0x8000 for code in codes)}
    return keys, mods


TEXTS = {
    "KR": {
        "title": "수동시작모드 키설정", "ice": "얼음의 결정 시작 키", "fire": "불의 결정 시작 키", "seconds": "초",
        "reset": "초기설정", "apply": "적용 및 닫기", "close": "닫기",
        "hint": "키 버튼을 클릭한 뒤 조합을 누르세요. 가운데·측면 마우스 버튼도 사용할 수 있습니다.",
        "capture": "조합을 입력하세요…", "cancel": "Esc: 입력 취소",
        "warning": "※가디내비는 가디우스와 프로그램적으로 연동되어있지 않으므로\n쉬운조합을 사용하실 경우 채팅 등의 일상적인 동작에도\n의도치 않게 카운트가 시작되거나 종료될 수 있습니다.",
        "invalid": "사용 가능한 키 조합과 1~2,147,483,647 사이의 정수 초를 입력해주세요.",
        "duplicate": "얼음과 불은 서로 다른 키 조합을 지정해주세요.",
        "reserved": "운영체제가 사용하는 예약 조합입니다. 다른 조합을 지정해주세요.",
    },
    "JP": {
        "title": "手動開始モードのキー設定", "ice": "氷の結晶 開始キー", "fire": "炎の結晶 開始キー", "seconds": "秒",
        "reset": "初期設定", "apply": "適用して閉じる", "close": "閉じる",
        "hint": "キーボタンをクリックして組み合わせを入力してください。マウスの中央・サイドボタンも使用できます。",
        "capture": "キーを入力…", "cancel": "Esc: 入力をキャンセル",
        "warning": "※ガディナビはガディウスとプログラム的に連携していないため、\n簡単な組み合わせを使うと、チャットなどの普段の操作でも\n意図せずカウントが開始・停止することがあります。",
        "invalid": "使用可能なキーと1～2,147,483,647の整数秒を入力してください。",
        "duplicate": "氷と炎には異なるキーの組み合わせを指定してください。",
        "reserved": "OSが使用する組み合わせです。別のキーを指定してください。",
    },
    "EN": {
        "title": "Manual start mode key settings", "ice": "Ice Crystal start key", "fire": "Fire Crystal start key", "seconds": "sec",
        "reset": "Defaults", "apply": "Apply and close", "close": "Close",
        "hint": "Click a key button, then press a combination. Middle and side mouse buttons are also supported.",
        "capture": "Press a combination…", "cancel": "Esc: cancel capture",
        "warning": "GodiNavi is not programmatically integrated with Godius.\nSimple combinations may unintentionally start or stop a countdown\nduring everyday actions such as chatting.",
        "invalid": "Choose a supported key combination and whole seconds from 1 to 2,147,483,647.",
        "duplicate": "Choose different key combinations for ice and fire.",
        "reserved": "This combination is reserved by the operating system. Choose another.",
    },
}


class ManualBuffSettings:
    def __init__(self, engine):
        self.engine = engine
        self.window = None
        self.job = None
        self.capturing = None

    def open(self):
        if self.window and self.window.winfo_exists():
            activate_modal(self.window)
            return
        self.draft = load_bindings(self.engine.config)
        self.text = TEXTS.get(self.engine.config.get("ui_language", "KR"), TEXTS["EN"])
        win = self.window = tk.Toplevel(self.engine.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg="#d8b15a")
        font = modal_font_family(win, self.engine.config.get("ui_language", "KR"))
        body = tk.Frame(win, bg="#17130f")
        body.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Label(body, text=self.text["title"], bg="#5a4932", fg="#ffe09a",
                          font=(font, 13, "bold"), padx=14, pady=12, anchor="w", cursor="fleur")
        header.pack(fill="x")
        content = tk.Frame(body, bg="#17130f", padx=18, pady=12)
        content.pack(fill="both", expand=True)
        self.buttons, self.seconds = {}, {}
        def label(parent, text, **kwargs):
            return tk.Label(parent, text=text, bg="#17130f", fg="#f1e5c7", font=(font, 10), **kwargs)
        def button(parent, text, command):
            return tk.Button(parent, text=text, command=command, bg="#3b3022", fg="#f3d68f",
                             activebackground="#5a4932", activeforeground="#fff4d2", relief="flat",
                             font=(font, 10), padx=14, pady=7, cursor="hand2")
        for buff in ("ice", "fire"):
            label(content, self.text[buff]).pack(anchor="w", pady=(8, 4))
            row = tk.Frame(content, bg="#17130f")
            row.pack(fill="x", pady=(0, 8))
            self.buttons[buff] = button(row, key_label(self.draft[buff]), lambda b=buff: self.capture(b))
            self.buttons[buff].configure(width=24)
            self.buttons[buff].pack(side="left", padx=(0, 12))
            self.seconds[buff] = tk.StringVar(win, str(self.draft[buff]["seconds"]))
            tk.Entry(row, textvariable=self.seconds[buff], width=11, bg="#2a2118", fg="#f1e5c7",
                     insertbackground="#f1e5c7", relief="flat", font=(font, 11)).pack(side="left", ipady=6)
            label(row, self.text["seconds"]).pack(side="left", padx=8)
        label(content, self.text["hint"], wraplength=530, justify="left").pack(anchor="w", pady=(6, 10))
        label(content, self.text["warning"], wraplength=530, justify="left").pack(anchor="w")
        self.status = label(content, "", wraplength=530, justify="left")
        self.status.configure(fg="#ffb5a0")
        self.status.pack(fill="x", pady=(8, 0))
        footer = tk.Frame(body, bg="#2a2118", padx=12, pady=10)
        footer.pack(fill="x")
        button(footer, self.text["reset"], self.reset).pack(side="left")
        button(footer, self.text["close"], self.close).pack(side="right", padx=(8, 0))
        button(footer, self.text["apply"], self.apply).pack(side="right")
        bind_modal_drag(win, (header,), lambda: client_screen_rect(find_godius_window()) or
                        (0, 0, win.winfo_screenwidth(), win.winfo_screenheight()), "buff_manual_settings")
        bind_modal_escape(win, self.escape)
        win.protocol("WM_DELETE_WINDOW", self.close)
        # Capture keys without activating focused buttons or inserting text into a field.
        self.capture_tag = "BuffCapture" + str(id(win))
        self.capture_command = win.bind_class(self.capture_tag, "<KeyPress>", self.capture_key_event)
        for widget in self.buttons.values():
            widget.bindtags((self.capture_tag,) + widget.bindtags())
        win.bind("<Button-1>", lambda event: self.cancel_capture()
                 if event.widget not in self.buttons.values() else None, add="+")
        place_modal(win, minimum_width=580, minimum_height=380, position_key="buff_manual_settings")
        win.deiconify()
        activate_modal(win)

    def capture_key_event(self, event):
        if self.capturing:
            if event.keysym == "Escape":
                self.escape()
            return "break"

    def capture(self, buff):
        self.cancel_capture()
        self.capturing = buff
        self.buttons[buff].focus_set()
        self.buttons[buff].configure(text=self.text["capture"])
        self.status.configure(text=self.text["cancel"])
        self.previous, _ = input_state(user32.GetAsyncKeyState)
        self.poll()

    def poll(self):
        self.job = None
        if not self.capturing or not self.window:
            return
        keys, mods = input_state(user32.GetAsyncKeyState)
        pressed = keys - self.previous
        self.previous = keys
        focus = self.window.focus_displayof()
        if focus is not None and focus.winfo_toplevel() == self.window and len(pressed) == 1:
            self.draft[self.capturing].update(key=pressed.pop(), modifiers=[m for m in MODIFIERS if m in mods])
            self.cancel_capture()
            self.status.configure(text="")
            return
        self.job = self.window.after(30, self.poll)

    def cancel_capture(self):
        if self.job and self.window:
            self.window.after_cancel(self.job)
        self.job = None
        self.capturing = None
        for buff, widget in getattr(self, "buttons", {}).items():
            widget.configure(text=key_label(self.draft[buff]))

    def escape(self):
        if self.capturing:
            self.cancel_capture()
            self.status.configure(text="")
        else:
            self.close()

    def reset(self):
        self.cancel_capture()
        self.draft = defaults()
        for buff in self.draft:
            self.seconds[buff].set(str(self.draft[buff]["seconds"]))
            self.buttons[buff].configure(text=key_label(self.draft[buff]))
        self.status.configure(text="")

    def apply(self):
        self.cancel_capture()
        for buff in self.draft:
            self.draft[buff]["seconds"] = self.seconds[buff].get().strip()
        try:
            value = validate_bindings(self.draft)
        except (ValueError, TypeError, KeyError) as exc:
            self.status.configure(text=self.text.get(str(exc), self.text["invalid"]))
            place_modal(self.window, minimum_width=580, minimum_height=380, position_key="buff_manual_settings")
            return
        self.engine.config["manual_start_bindings"] = value
        self.engine.save_config()
        self.close()

    def close(self):
        self.cancel_capture()
        if self.window:
            self.window.unbind_class(self.capture_tag, "<KeyPress>")
            self.window._root().deletecommand(self.capture_command)
            self.window.destroy()
        self.window = None

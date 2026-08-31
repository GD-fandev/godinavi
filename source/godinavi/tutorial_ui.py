import time
import tkinter as tk

from PIL import Image, ImageTk
from map_engine import BUNDLE_DIR
from modal_window import activate_modal, bind_modal_drag, bind_modal_escape, place_modal
from .window_attachment import client_screen_rect, find_godius_window


BG = "#17130f"
PANEL = "#2a2118"
HEADER = "#5a4932"
GOLD = "#d8b15a"
TEXT = "#f1e5c7"
MUTED = "#bda982"


TEXTS = {
    "KR": {
        "window_title": "가디내비 튜토리얼",
        "close": "닫기",
        "mark_all_read": "모두 읽음처리",
        "read": "읽음",
        "unread": "읽지 않음",
    },
    "JP": {
        "window_title": "ガディナビ チュートリアル",
        "close": "閉じる",
        "mark_all_read": "すべて既読にする",
        "read": "既読",
        "unread": "未読",
    },
    "EN": {
        "window_title": "GodiNavi Tutorial",
        "close": "Close",
        "mark_all_read": "Mark all as read",
        "read": "Read",
        "unread": "Unread",
    },
}

NOTICE_TEXTS = {
    "KR": {
        "title": "튜토리얼 안내",
        "message": "모험수첩에 튜토리얼이 추가되었습니다.\n새로운 기능에 대한 설명을 확인해주세요.",
        "never_show": "다시 보지 않음",
        "close": "닫기",
    },
    "JP": {
        "title": "チュートリアルのご案内",
        "message": "冒険手帳にチュートリアルが追加されました。\n新機能の説明をご確認ください。",
        "never_show": "今後表示しない",
        "close": "閉じる",
    },
    "EN": {
        "title": "Tutorial Notice",
        "message": "Tutorials have been added to the Adventure Journal.\nPlease review the explanations of the new features.",
        "never_show": "Don't show again",
        "close": "Close",
    },
}


TUTORIALS = (
    {
        "id": "tutorial_intro",
        "titles": {
            "KR": "튜토리얼",
            "JP": "チュートリアル",
            "EN": "Tutorial",
        },
        "contents": {
            "KR": (
                "가디내비의 사용법을 신규기능 위주로 설명하는 튜토리얼이 생겼습니다.\n"
                "여기에 조금씩 튜토리얼을 추가해갈 예정입니다.\n"
                "튜토리얼 추가만을 위한 업데이트는 하지 않을 예정입니다.\n\n"
                "모두 읽음처리를 하실 경우, 읽지 않은 모든 튜토리얼이 읽음처리 됩니다.\n"
                "이 동작은 되돌릴 수 없습니다."
            ),
            "JP": (
                "ガディナビの使い方を、新機能を中心に説明する\n"
                "チュートリアルを追加しました。\n\n"
                "今後、ここに少しずつチュートリアルを追加していく予定です。\n"
                "チュートリアル追加の実を目的としたアップデートは\n"
                "行わない予定です。\n\n"
                "「すべて既読にする」ボタンをクリックすると\n"
                "未読のチュートリアルがすべて既読になります。\n"
                "この動作は元に戻せません。"
            ),
            "EN": (
                "A tutorial focused on GodiNavi's newer features is now available.\n"
                "More tutorials will gradually be added here.\n"
                "Updates will not be released solely to add tutorial entries.\n\n"
                "Marking all as read will mark every unread tutorial as read.\n"
                "This action cannot be undone."
            ),
        },
    },
    {
        "id": "Tutorial_002_monsteroverlay",
        "titles": {
            "KR": "몬스터 오버레이",
            "JP": "モンスターオーバーレイ",
            "EN": "Monster Overlay",
        },
        "blocks": (
            {"image": "icons/godinavi/encyclopedia.jpg", "max_width": 75, "max_height": 70},
            {"text": {
                "KR": "몬스터 사전에 몬스터 오버레이 기능을 추가했습니다.",
                "JP": "モンスター図鑑にモンスターオーバーレイ機能を追加しました。",
                "EN": "A monster overlay feature has been added to the Monster Compendium.",
            }},
            {"image": "tutorials/tutorial_002_overlay_enable.png"},
            {"text": {
                "KR": (
                    "사냥터에서 오버레이를 활성화 할 경우\n"
                    "해당 사냥터의 몬스터 정보를 요약한 오버레이가\n"
                    "가디우스 화면 위에 생성됩니다."
                ),
                "JP": (
                    "狩場でオーバーレイを有効にすると、\n"
                    "その狩場に出現するモンスター情報をまとめたオーバーレイが\n"
                    "ガディウスの画面上に表示されます。"
                ),
                "EN": (
                    "When the overlay is enabled in a hunting area,\n"
                    "a summary of the monsters found there is displayed\n"
                    "over the Godius window."
                ),
            }},
            {"image": "tutorials/tutorial_002_overlay_edit.png"},
            {"text": {
                "KR": (
                    "오버레이는 오른클릭으로 수정모드로 진입하며\n"
                    "수정모드에서 이동 및 크기조절, 투명도 조절이 가능합니다.\n"
                    "수정모드를 종료하시려면 다시 한 번 오른클릭 하시거나\n"
                    "자물쇠 버튼을 눌러주세요."
                ),
                "JP": (
                    "オーバーレイを右クリックすると編集モードに切り替わり、\n"
                    "位置・サイズ・透明度を調整できます。\n"
                    "編集モードを終了するには、もう一度右クリックするか、\n"
                    "鍵ボタンを押してください。"
                ),
                "EN": (
                    "Right-click the overlay to enter edit mode.\n"
                    "In edit mode, you can move and resize it and adjust its opacity.\n"
                    "To leave edit mode, right-click again or press the lock button."
                ),
            }},
            {"image": "tutorials/tutorial_002_overlay_tooltip.png"},
            {"text": {
                "KR": "몬스터에 마우스를 올리면 요약정보를\n툴팁으로 확인 가능합니다.",
                "JP": "モンスターにマウスを合わせると、\n概要をツールチップで確認できます。",
                "EN": "Hover over a monster to view\nits summary in a tooltip.",
            }},
            {"image": "tutorials/tutorial_002_overlay_pk_border.png"},
            {"text": {
                "KR": "PK존일 경우 테두리가 빨갛게 표시됩니다.",
                "JP": "PKゾーンでは枠が赤く表示されます。",
                "EN": "In a PK zone, the border is displayed in red.",
            }},
        ),
    },
    {
        "id": "Tutorial_003_pk_minimap",
        "titles": {
            "KR": "PK존의 미니맵",
            "JP": "PKゾーンのミニマップ",
            "EN": "PK Zone Minimap",
        },
        "blocks": (
            {"image": "icons/godinavi/map.jpg", "max_width": 75, "max_height": 70},
            {"text": {
                "KR": (
                    "PK존에 진입시 미니맵의 테두리가 붉게 변하며\n"
                    "우측 상단에 PK존 알림을 표시해줍니다."
                ),
                "JP": (
                    "PKゾーンに入るとミニマップの枠が赤くなり、\n"
                    "右上にPKゾーンの警告が表示されます。"
                ),
                "EN": (
                    "When you enter a PK zone, the minimap border turns red\n"
                    "and a PK zone warning appears in the upper-right corner."
                ),
            }},
            {"image": "tutorials/tutorial_003_pk_minimap.png"},
            {"text": {
                "KR": (
                    "초보자용 설정이므로, 필요없으실 경우\n"
                    "지도아이콘에서 비활성화 할 수 있습니다."
                ),
                "JP": (
                    "初心者向けの設定です。不要な場合は、\n"
                    "地図アイコンから無効にできます。"
                ),
                "EN": (
                    "This setting is intended for beginners. If you do not need it,\n"
                    "you can disable it from the map icon."
                ),
            }},
        ),
    },
    {
        "id": "Tutorial_003_clock_alarm",
        "titles": {
            "KR": "시계와 알람설정",
            "JP": "時計とアラーム設定",
            "EN": "Clock and Alarm Settings",
        },
        "blocks": (
            {"image": "icons/godinavi/encyclopedia.jpg", "max_width": 75, "max_height": 70},
            {"text": {
                "KR": (
                    "모험수첩에서 시계 표시를 활성화할 경우\n"
                    "사용자 PC의 현재 시각에 맞춘 시계를 표시합니다."
                ),
                "JP": (
                    "冒険手帳から時計表示を有効にすると、\n"
                    "ユーザーのPCの現在時刻に合わせた時計が表示されます。"
                ),
                "EN": (
                    "Enable the clock display from the Adventure Journal to show\n"
                    "a clock synchronized with your PC's current time."
                ),
            }},
            {"image": "tutorials/tutorial_003_clock_edit.png"},
            {"text": {
                "KR": (
                    "시계를 우클릭하면 크기, 투명도, 위치 등을 조절할 수 있습니다.\n"
                    "잠그려면 자물쇠를 좌클릭하거나 시계를 다시 우클릭하세요."
                ),
                "JP": (
                    "時計を右クリックすると、サイズ・透明度・位置などを調整できます。\n"
                    "ロックするには、鍵を左クリックするか、時計をもう一度右クリックしてください。"
                ),
                "EN": (
                    "Right-click the clock to adjust its size, opacity, and position.\n"
                    "To lock it, left-click the lock or right-click the clock again."
                ),
            }},
            {"image": "tutorials/tutorial_003_alarm_settings.png"},
            {"text": {
                "KR": (
                    "알람은 최대 5개까지 설정할 수 있습니다.\n"
                    "24시간 체계로 설정합니다. (예: 오후 4시 = 16시)\n"
                    "사용에 체크한 뒤 닫기 버튼을 누르면 알람이 활성화됩니다.\n"
                    "간단한 메모도 입력할 수 있습니다."
                ),
                "JP": (
                    "アラームは最大5件まで設定できます。\n"
                    "時刻は24時間制で設定します。（例：午後4時＝16時）\n"
                    "「使用」にチェックして閉じるボタンを押すと、アラームが有効になります。\n"
                    "簡単なメモも入力できます。"
                ),
                "EN": (
                    "You can configure up to five alarms using 24-hour time\n"
                    "(for example, 4 PM is 16:00). Check On and press Close to activate an alarm.\n"
                    "You can also add a short memo."
                ),
            }},
            {"image": "tutorials/tutorial_003_alarm_ringing.png"},
            {"text": {
                "KR": (
                    "설정한 시각이 되면 알람이 울리며,\n"
                    "메모에 입력한 내용도 함께 표시됩니다."
                ),
                "JP": (
                    "設定した時刻になるとアラームが鳴り、\n"
                    "メモに入力した内容も一緒に表示されます。"
                ),
                "EN": (
                    "At the configured time, the alarm sounds and displays\n"
                    "the memo you entered."
                ),
            }},
            {"image": "tutorials/tutorial_003_alarm_snooze.png"},
            {"text": {
                "KR": (
                    "+5min 버튼을 누르면 알람이 잠시 멈추고 5분간 카운트다운합니다.\n"
                    "5분이 지나면 알람이 다시 울립니다.\n"
                    "STOP을 누르면 알람이 종료되고 사용 체크가 해제됩니다.\n"
                    "다시 사용하려면 알람 설정에서 해당 알람을 다시 활성화해야 합니다."
                ),
                "JP": (
                    "「+5min」を押すとアラームが一時停止し、5分間のカウントダウンが始まります。\n"
                    "5分後にアラームが再び鳴ります。\n"
                    "STOPを押すとアラームが終了し、「使用」のチェックが外れます。\n"
                    "再度使用するには、アラーム設定からもう一度有効にしてください。"
                ),
                "EN": (
                    "Press +5min to silence the alarm and start a five-minute countdown.\n"
                    "The alarm sounds again when the countdown ends.\n"
                    "Pressing STOP ends the alarm and clears its On checkbox.\n"
                    "To use it again, enable it again in the alarm settings."
                ),
            }},
        ),
    },
    {
        "id": "Tutorial_004_stopwatch_exp",
        "titles": {
            "KR": "스톱워치와 경험치 계산기",
            "JP": "ストップウォッチと経験値計算機",
            "EN": "Stopwatch and EXP Calculator",
        },
        "blocks": (
            {"image": "icons/godinavi/encyclopedia.jpg", "max_width": 75, "max_height": 70},
            {"text": {
                "KR": (
                    "시계를 활성화한 후 좌클릭하면 스톱워치 탭에서\n"
                    "스톱워치 기능을 사용할 수 있습니다."
                ),
                "JP": (
                    "時計を有効にして左クリックすると、ストップウォッチタブから\n"
                    "ストップウォッチ機能を使用できます。"
                ),
                "EN": (
                    "After enabling the clock, left-click it to use the stopwatch\n"
                    "from the Stopwatch tab."
                ),
            }},
            {"image": "tutorials/tutorial_004_stopwatch_settings.png"},
            {"text": {
                "KR": (
                    "이 창에서 카운트할 시간을 설정합니다.\n"
                    "오버레이를 활성화하면 오른클릭으로 이동, 크기와 투명도를 조절할 수 있는\n"
                    "간편한 별도 스톱워치 창이 활성화됩니다."
                ),
                "JP": (
                    "この画面でカウントする時間を設定します。\n"
                    "オーバーレイを有効にすると、右クリックで移動・サイズ・透明度を調整できる\n"
                    "コンパクトなストップウォッチウィンドウが表示されます。"
                ),
                "EN": (
                    "Set the countdown duration in this window. Enabling the overlay displays\n"
                    "a compact stopwatch window that can be moved and resized and have its opacity\n"
                    "adjusted after you right-click it."
                ),
            }},
            {"image": "tutorials/tutorial_004_stopwatch_overlay.png"},
            {"text": {
                "KR": (
                    "시작, 일시정지, 중단 버튼으로 메인 창에서 설정한 시간의\n"
                    "카운트다운을 조작할 수 있습니다.\n"
                    "5초 전 알림을 설정하면 종료 5초 전부터 숫자를 세는 음성이 재생됩니다."
                ),
                "JP": (
                    "開始・一時停止・中止ボタンで、メイン画面に設定した時間の\n"
                    "カウントダウンを操作できます。\n"
                    "5秒前通知を有効にすると、終了5秒前から音声でカウントダウンします。"
                ),
                "EN": (
                    "Use Start, Pause, and Stop to control the countdown configured in the main window.\n"
                    "When the 5-second warning is enabled, a voice counts down the final five seconds."
                ),
            }},
            {"image": "tutorials/tutorial_004_exp_tracking.png"},
            {"text": {
                "KR": (
                    "경험치 측정을 활성화하면 스톱워치 시작 시점의 경험치를 기억한 뒤\n"
                    "종료 시점의 경험치를 다시 읽어옵니다.\n"
                    "설정한 시간 동안 획득한 경험치를 퍼센트로 알려줍니다."
                ),
                "JP": (
                    "経験値測定を有効にすると、開始時の経験値を記録し、\n"
                    "終了時に経験値をもう一度読み取ります。\n"
                    "設定時間内に獲得した経験値をパーセントで表示します。"
                ),
                "EN": (
                    "EXP tracking remembers the recognized EXP when the stopwatch starts and reads it\n"
                    "again when the countdown ends, then reports the percentage gained during that time."
                ),
            }},
            {"image": "tutorials/tutorial_004_exp_region.png"},
            {"text": {
                "KR": (
                    "영역 설정에서 OCR 인식 범위를 지정해야 합니다.\n"
                    "위 스크린샷처럼 경험치 퍼센트 숫자 전체가 들어오도록 설정하세요.\n"
                    "설정이 끝나면 OCR 인식 영역 오른쪽의 설정 완료 버튼을 누르세요."
                ),
                "JP": (
                    "範囲設定からOCRの認識範囲を指定する必要があります。\n"
                    "上の画像のように経験値のパーセント全体が入るように設定してください。\n"
                    "設定後、OCR認識範囲の右側にある設定完了ボタンを押します。"
                ),
                "EN": (
                    "Use Set region to define the OCR area. Position it so the complete EXP percentage\n"
                    "is inside the region, as shown above, then press the completion button on its right."
                ),
            }},
            {"image": "tutorials/tutorial_004_exp_recognized.png"},
            {"text": {
                "KR": "정상적으로 인식되면 현재 캐릭터 경험치와 인식된 경험치가 동일하게 표시됩니다.",
                "JP": "正常に認識されると、現在のキャラクター経験値と認識値が同じ値で表示されます。",
                "EN": "When recognition works correctly, the recognized value matches your character's current EXP.",
            }},
            {"image": "tutorials/tutorial_004_character_info.png"},
            {"text": {
                "KR": (
                    "주의: 적어도 시작 시점과 종료 직전에는 위 스크린샷처럼\n"
                    "내 캐릭터 정보창이 열려 있어야 합니다.\n"
                    "5초 전 알림을 활성화하면 정보창을 열 타이밍을 쉽게 파악할 수 있습니다."
                ),
                "JP": (
                    "注意：少なくとも開始時と終了直前には、上の画像のように\n"
                    "自分のキャラクター情報画面を開いておく必要があります。\n"
                    "5秒前通知を有効にすると、情報画面を開くタイミングが分かりやすくなります。"
                ),
                "EN": (
                    "Important: your character information window must be open at least when the timer starts\n"
                    "and just before it ends. The 5-second warning makes the timing easier to recognize."
                ),
            }},
            {"image": "tutorials/tutorial_004_live_gain.png"},
            {"text": {
                "KR": (
                    "측정하는 동안 캐릭터 정보창을 계속 열어두면\n"
                    "위와 같이 획득한 경험치를 실시간으로 확인할 수도 있습니다."
                ),
                "JP": (
                    "測定中にキャラクター情報画面を開いたままにすると、\n"
                    "上のように獲得経験値をリアルタイムで確認できます。"
                ),
                "EN": (
                    "If you keep the character information window open during measurement,\n"
                    "you can also monitor the EXP gained in real time, as shown above."
                ),
            }},
        ),
    },
)


class TutorialUI:
    def __init__(self, master, language_provider, config, save_config):
        self.master = master
        self.language_provider = language_provider
        self.config = config
        self.save_config = save_config
        self.window = None
        self.built_language = None
        self.listbox = None
        self.title_label = None
        self.content_label = None
        self.content_text = None
        self.content_images = []
        self.content_render_job = None
        self.mark_all_button = None
        self.selected_index = 0
        self.notice_window = None
        self.notice_icon = None
        self.notice_close_callback = None
        self.notice_shown_this_session = False

    def language(self):
        value = self.language_provider() if self.language_provider else "KR"
        return value if value in TEXTS else "EN"

    def texts(self):
        return TEXTS[self.language()]

    def read_flags(self):
        value = self.config.get("tutorial_read_flags", {})
        if not isinstance(value, dict):
            value = {}
            self.config["tutorial_read_flags"] = value
        return value

    def is_read(self, tutorial):
        return bool(self.read_flags().get(tutorial["id"], False))

    def has_unread(self):
        return any(not self.is_read(tutorial) for tutorial in TUTORIALS)

    def alert_badge(self):
        if not self.has_unread():
            return ""
        phase = time.monotonic() % 1.0
        opacity = phase / 0.5 if phase < 0.5 else (1.0 - phase) / 0.5
        return "!", max(0, min(100, round(opacity * 20) * 5))

    def should_show_notice(self):
        return (
            bool(self.config.get("onboarding_complete"))
            and not bool(self.config.get("tutorial_notice_dismissed", False))
            and not self.notice_shown_this_session
        )

    def show_notice(self, close_callback=None):
        if close_callback is not None:
            self.notice_close_callback = close_callback
        if self.notice_window and self.notice_window.winfo_exists():
            self.notice_window.deiconify()
            self.notice_window.lift()
            activate_modal(self.notice_window)
            return
        self.notice_shown_this_session = True
        text = NOTICE_TEXTS[self.language()]
        window = tk.Toplevel(self.master)
        self.notice_window = window
        window.withdraw()
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        window.transient(self.master)
        outer = tk.Frame(window, bg=BG, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(outer, bg=HEADER, height=44, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        title = tk.Label(
            header, text=text["title"], bg=HEADER, fg="#ffe09a", anchor="w",
            padx=14, font=("Noto Sans KR", 11, "bold"), cursor="fleur",
        )
        title.pack(fill="both", expand=True)
        content = tk.Frame(outer, bg=BG, padx=18, pady=18)
        content.pack(fill="both", expand=True)
        try:
            with Image.open(BUNDLE_DIR / "assets" / "icons" / "godinavi" / "encyclopedia.jpg") as source:
                icon = source.convert("RGBA").resize((75, 70), Image.Resampling.LANCZOS)
            self.notice_icon = ImageTk.PhotoImage(icon, master=window)
            tk.Label(content, image=self.notice_icon, bg=BG, bd=0).pack(side="left", padx=(0, 16))
        except (OSError, ValueError, tk.TclError):
            self.notice_icon = None
        tk.Label(
            content, text=text["message"], bg=BG, fg=TEXT, justify="left", anchor="w",
            font=("Noto Sans KR", 10),
        ).pack(side="left", fill="both", expand=True)
        footer = tk.Frame(outer, bg=PANEL, padx=12, pady=10)
        footer.pack(fill="x")
        tk.Button(
            footer, text=text["close"], command=lambda: self.close_notice(False),
            bg="#3b3022", fg="#f3d68f", activebackground=HEADER, activeforeground="#fff4d2",
            relief="flat", bd=0, padx=18, pady=6, font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        ).pack(side="right")
        tk.Button(
            footer, text=text["never_show"], command=lambda: self.close_notice(True),
            bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff",
            relief="flat", bd=0, padx=16, pady=6, font=("Noto Sans KR", 9), cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        def bounds():
            owner = find_godius_window()
            return client_screen_rect(owner) if owner else (0, 0, window.winfo_screenwidth(), window.winfo_screenheight())

        bind_modal_drag(window, (header, title), bounds, "tutorial_notice")
        bind_modal_escape(window, lambda: self.close_notice(False))
        place_modal(window, minimum_width=540, minimum_height=245, position_key="tutorial_notice")
        activate_modal(window)

    def close_notice(self, never_show=False):
        if never_show:
            self.config["tutorial_notice_dismissed"] = True
            self.save_config()
        if self.notice_window and self.notice_window.winfo_exists():
            self.notice_window.destroy()
        self.notice_window = None
        self.notice_icon = None
        callback, self.notice_close_callback = self.notice_close_callback, None
        if callback:
            callback()

    def open(self):
        language = self.language()
        if self.window and self.window.winfo_exists() and self.built_language != language:
            self.window.destroy()
            self.window = None
        if not self.window or not self.window.winfo_exists():
            self.build_window()
        self.window.deiconify()
        self.window.lift()
        activate_modal(self.window)
        first_unread = next((index for index, item in enumerate(TUTORIALS) if not self.is_read(item)), None)
        self.select_tutorial(first_unread if first_unread is not None else min(self.selected_index, len(TUTORIALS) - 1))

    def build_window(self):
        text = self.texts()
        window = tk.Toplevel(self.master)
        self.window = window
        self.built_language = self.language()
        window.overrideredirect(True)
        window.configure(bg=GOLD)
        window.withdraw()
        outer = tk.Frame(window, bg=BG, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(outer, bg=HEADER, height=46, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        header_label = tk.Label(
            header, text=text["window_title"], bg=HEADER, fg="#ffe09a",
            anchor="w", padx=14, font=("Noto Sans KR", 12, "bold"), cursor="fleur",
        )
        header_label.pack(fill="both", expand=True)

        body = tk.Frame(outer, bg=BG, padx=12, pady=12)
        body.pack(fill="both", expand=True)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1, uniform="tutorial_columns")
        body.grid_columnconfigure(1, weight=3, uniform="tutorial_columns")

        left = tk.Frame(body, bg=PANEL, highlightbackground="#6b5537", highlightthickness=1)
        right = tk.Frame(body, bg=PANEL, highlightbackground="#6b5537", highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.listbox = tk.Listbox(
            left, bg=PANEL, fg=TEXT, selectbackground=HEADER, selectforeground="#fff1c9",
            relief="flat", bd=0, highlightthickness=0, activestyle="none",
            font=("Noto Sans KR", 10), exportselection=False, cursor="hand2",
        )
        self.listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.listbox.bind("<<ListboxSelect>>", self.on_list_selected)

        self.title_label = tk.Label(
            right, text="", bg=PANEL, fg="#ffe09a", anchor="w",
            padx=18, pady=14, font=("Noto Sans KR", 13, "bold"),
        )
        self.title_label.pack(fill="x")
        content_frame = tk.Frame(right, bg=PANEL)
        content_frame.pack(fill="both", expand=True, padx=(18, 6), pady=(6, 12))
        content_scrollbar = tk.Scrollbar(
            content_frame, orient="vertical", bg=HEADER, troughcolor=PANEL,
            activebackground="#806846", relief="flat", bd=0,
        )
        self.content_text = tk.Text(
            content_frame, bg=PANEL, fg=TEXT, wrap="word", relief="flat", bd=0,
            highlightthickness=0, padx=0, pady=0, cursor="arrow",
            font=("Noto Sans KR", 10), spacing1=1, spacing3=1,
            yscrollcommand=content_scrollbar.set,
        )
        self.content_label = self.content_text
        content_scrollbar.configure(command=self.content_text.yview)
        content_scrollbar.pack(side="right", fill="y")
        self.content_text.pack(side="left", fill="both", expand=True)
        self.content_text.tag_configure("body", foreground=TEXT, font=("Noto Sans KR", 10))
        self.content_text.configure(state="disabled")
        self.content_text.bind("<Configure>", self.schedule_content_render, add="+")

        footer = tk.Frame(outer, bg=PANEL, padx=12, pady=10)
        footer.pack(fill="x", padx=12, pady=(0, 12))
        close_button = tk.Button(
            footer, text=text["close"], command=self.close,
            bg="#3b3022", fg="#f3d68f", activebackground=HEADER, activeforeground="#fff4d2",
            relief="flat", bd=0, padx=18, pady=6, font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        )
        close_button.pack(side="right")
        self.mark_all_button = tk.Button(
            footer, text=text["mark_all_read"], command=self.mark_all_read,
            bg="#6b5537", fg="#fff1c9", activebackground="#806846", activeforeground="#ffffff",
            relief="flat", bd=0, padx=16, pady=6, font=("Noto Sans KR", 9, "bold"), cursor="hand2",
        )
        self.mark_all_button.pack(side="right", padx=(0, 8))

        def bounds():
            owner = find_godius_window()
            return client_screen_rect(owner) if owner else (0, 0, window.winfo_screenwidth(), window.winfo_screenheight())

        bind_modal_drag(window, (header, header_label), bounds, "tutorial_window")
        bind_modal_escape(window, self.close)
        place_modal(window, minimum_width=840, minimum_height=520, position_key="tutorial_window")
        self.refresh_list()

    def close(self):
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

    def schedule_content_render(self, _event=None):
        if self.content_render_job or not self.window or not self.window.winfo_exists():
            return
        self.content_render_job = self.window.after(80, self.render_selected_content)

    def render_selected_content(self):
        self.content_render_job = None
        if not self.content_text or not TUTORIALS:
            return
        tutorial = TUTORIALS[max(0, min(self.selected_index, len(TUTORIALS) - 1))]
        language = self.language()
        text_widget = self.content_text
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        self.content_images.clear()
        blocks = tutorial.get("blocks")
        if not blocks:
            text_widget.insert("end", tutorial["contents"][language], "body")
        else:
            available_width = max(160, text_widget.winfo_width() - 8)
            for index, block in enumerate(blocks):
                image_path = block.get("image")
                if image_path:
                    path = BUNDLE_DIR / "assets" / image_path
                    try:
                        with Image.open(path) as source:
                            rendered = source.convert("RGBA")
                        max_width = min(available_width, int(block.get("max_width", available_width)))
                        max_height = int(block.get("max_height", rendered.height))
                        scale = min(1.0, max_width / rendered.width, max_height / rendered.height)
                        if scale < 1.0:
                            rendered = rendered.resize(
                                (max(1, round(rendered.width * scale)), max(1, round(rendered.height * scale))),
                                Image.Resampling.LANCZOS,
                            )
                        photo = ImageTk.PhotoImage(rendered)
                        self.content_images.append(photo)
                        text_widget.image_create("end", image=photo)
                    except (OSError, ValueError, tk.TclError):
                        pass
                elif "text" in block:
                    text_widget.insert("end", block["text"][language], "body")
                if index < len(blocks) - 1:
                    text_widget.insert("end", "\n\n", "body")
        text_widget.configure(state="disabled")
        text_widget.yview_moveto(0.0)

    def refresh_list(self):
        if not self.listbox:
            return
        language = self.language()
        self.listbox.delete(0, "end")
        for tutorial in TUTORIALS:
            marker = "" if self.is_read(tutorial) else "⚠ "
            self.listbox.insert("end", f"{marker}{tutorial['titles'][language]}")
        if self.mark_all_button:
            self.mark_all_button.configure(state="normal" if self.has_unread() else "disabled")

    def on_list_selected(self, _event=None):
        selection = self.listbox.curselection() if self.listbox else ()
        if selection:
            index = selection[0]
            if index == self.selected_index and self.is_read(TUTORIALS[index]):
                return
            self.select_tutorial(index)

    def select_tutorial(self, index):
        if not TUTORIALS:
            return
        index = max(0, min(int(index), len(TUTORIALS) - 1))
        tutorial = TUTORIALS[index]
        self.selected_index = index
        if not self.is_read(tutorial):
            self.read_flags()[tutorial["id"]] = True
            self.save_config()
        self.refresh_list()
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        language = self.language()
        self.title_label.configure(text=tutorial["titles"][language])
        self.render_selected_content()

    def mark_all_read(self):
        flags = self.read_flags()
        for tutorial in TUTORIALS:
            flags[tutorial["id"]] = True
        self.save_config()
        self.refresh_list()

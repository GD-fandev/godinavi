"""Explain the end of 1.x migration without modifying an old installation."""
import json
import os
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox

FULL_RELEASE_URL = 'https://github.com/GD-fandev/godinavi/releases/tag/v3.0.1'


def show_legacy_install_notice():
    try:
        config = Path(os.environ.get('LOCALAPPDATA', '')) / 'GodiNavi/godinavi-config.json'
        language = json.loads(config.read_text(encoding='utf-8-sig')).get('ui_language', 'EN')
    except (OSError, ValueError):
        language = 'EN'
    texts = {
        'KR': ('가디내비 3 설치 안내', '1.x에서 자동으로 이전하는 기능은 지원이 종료되었습니다.\n3.0.1 풀버전을 새 폴더에 압축 해제해 실행해 주세요.\n기존 개인 설정은 유지됩니다.\n\n다운로드 페이지를 여시겠습니까?'),
        'JP': ('ガディナビ 3 インストールのご案内', '1.xからの自動移行のサポートは終了しました。\n3.0.1フルバージョンを新しいフォルダーに展開して起動してください。\n既存の個人設定は保持されます。\n\nダウンロードページを開きますか？'),
        'EN': ('GodiNavi 3 installation', 'Automatic migration from 1.x is no longer supported.\nExtract the full 3.0.1 package into a new folder and run it.\nYour existing personal settings are preserved.\n\nOpen the download page?'),
    }
    root = tk.Tk()
    root.withdraw()
    try:
        if messagebox.askyesno(*texts.get(language, texts['EN']), parent=root):
            webbrowser.open(FULL_RELEASE_URL)
    finally:
        root.destroy()

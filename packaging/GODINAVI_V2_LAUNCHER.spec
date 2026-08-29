# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'source')
ICON_PATH = os.path.join(PROJECT_ROOT, 'private', 'content-source', 'runtime', 'assets', 'icons', 'Godius_104.png')
CHANNEL_FILE = os.environ.get('GODINAVI_V2_CHANNEL_FILE')
if not CHANNEL_FILE or not os.path.isfile(CHANNEL_FILE):
    raise SystemExit('GODINAVI_V2_CHANNEL_FILE must point to a validated channel profile')

# PyInstaller data tuples preserve the source basename. Stage the selected
# profile under the immutable runtime filename expected by v2_launcher.py.
CHANNEL_STAGE_DIR = os.path.join(PROJECT_ROOT, 'build', 'v2-launcher-channel')
os.makedirs(CHANNEL_STAGE_DIR, exist_ok=True)
CHANNEL_STAGE_FILE = os.path.join(CHANNEL_STAGE_DIR, 'update-channel.json')
shutil.copyfile(CHANNEL_FILE, CHANNEL_STAGE_FILE)

a = Analysis([os.path.join(SOURCE_DIR, 'v2_launcher.py')], pathex=[SOURCE_DIR], datas=[(CHANNEL_STAGE_FILE, '.')])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='GodiNaviLauncher', console=False, icon=[ICON_PATH])

# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'source')
ICON_PATH = os.path.join(PROJECT_ROOT, 'private', 'content-source', 'runtime', 'assets', 'icons', 'Godius_104.png')
CHANNEL_FILE = os.environ.get('GODINAVI_V2_CHANNEL_FILE')
if not CHANNEL_FILE or not os.path.isfile(CHANNEL_FILE):
    raise FileNotFoundError('GODINAVI_V2_CHANNEL_FILE is required for a bridge build.')

a = Analysis(
    [os.path.join(SOURCE_DIR, 'v2_bridge.py')], pathex=[SOURCE_DIR],
    datas=[(CHANNEL_FILE, '.')],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='GodiNaviBridge', console=False, icon=[ICON_PATH])

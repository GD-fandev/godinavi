# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'source')
ICON_PATH = os.path.join(PROJECT_ROOT, 'private', 'content-source', 'runtime', 'assets', 'icons', 'Godius_104.png')

a = Analysis([os.path.join(SOURCE_DIR, 'v2_updater_app.py')], pathex=[SOURCE_DIR])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='GodiNaviUpdater', console=False, icon=[ICON_PATH])

# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'source')
ASSET_DIR = os.path.join(PROJECT_ROOT, 'assets', 'icons')
PARTY_ENDPOINT = os.path.join(PROJECT_ROOT, 'private', 'party-endpoint.json')

if not os.path.isfile(PARTY_ENDPOINT):
    raise FileNotFoundError('Missing private/party-endpoint.json. Copy the example and set the private endpoint before building.')

datas = [
    (os.path.join(ASSET_DIR, 'Godius_104.png'), 'assets/icons'),
    (os.path.join(ASSET_DIR, 'godinavi'), 'assets/icons/godinavi'),
    (os.path.join(PROJECT_ROOT, 'assets', 'buff_timer'), 'assets/buff_timer'),
    (os.path.join(PROJECT_ROOT, 'assets', 'durability'), 'assets/durability'),
    (os.path.join(PROJECT_ROOT, 'assets', 'map_ocr'), 'assets/map_ocr'),
    (PARTY_ENDPOINT, 'config'),
]
binaries = []
hiddenimports = ['paddle_ocr_backend', 'windows_ocr_backend', 'pystray', 'pystray._win32']
hiddenimports += ['cv2']
tmp_ret = collect_all('rapidocr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('dxcam')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('websockets')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(SOURCE_DIR, 'godinavi_launcher.py')],
    pathex=[SOURCE_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GodiNavi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(ASSET_DIR, 'Godius_104.png')],
)

# -*- mode: python ; coding: utf-8 -*-
"""V2 Core in onedir form: app bytecode in the EXE, shared dependencies in runtime/."""

import os

from PyInstaller.utils.hooks import get_package_paths

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")
ASSET_DIR = os.path.join(PROJECT_ROOT, "private", "content-source", "runtime", "assets", "icons")
PARTY_ENDPOINT = os.path.join(PROJECT_ROOT, "private", "party-endpoint.json")

if not os.path.isfile(PARTY_ENDPOINT):
    raise FileNotFoundError("Missing private/party-endpoint.json.")

datas = [
    (os.path.join(ASSET_DIR, "Godius_104.png"), "assets/icons"),
    (PARTY_ENDPOINT, "config"),
]
binaries = []
rapidocr_root = get_package_paths("rapidocr")[1]
datas += [
    (os.path.join(rapidocr_root, "config.yaml"), "rapidocr"),
    (os.path.join(rapidocr_root, "default_models.yaml"), "rapidocr"),
]
hiddenimports = [
    "paddle_ocr_backend", "windows_ocr_backend", "pystray", "pystray._win32", "cv2",
    # RapidOCR exposes its entry point lazily and selects the inference engine
    # at runtime. V2 deliberately supports only the ONNX Runtime engine.
    "rapidocr.main", "rapidocr.inference_engine.onnxruntime",
    "dxcam.core.duplicator", "dxcam.processor._numpy_kernels",
]
excludes = [
    # Optional RapidOCR engines and developer/conversion stacks. OCR models are
    # shipped separately in encrypted ocr_models.pak and materialized to cache.
    "paddle", "paddleocr", "torch", "torchvision", "scipy", "onnx",
    "openvino", "tensorrt", "pytest", "Cython",
]

a = Analysis(
    [os.path.join(SOURCE_DIR, "godinavi_launcher.py")],
    pathex=[SOURCE_DIR], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=excludes, noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="GodiNaviCore", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False, disable_windowed_traceback=False,
    icon=[os.path.join(ASSET_DIR, "Godius_104.png")],
    contents_directory="runtime",
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[],
    name="GodiNaviCore",
)

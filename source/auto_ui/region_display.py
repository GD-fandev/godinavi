"""Keep existing read-only region overlays out of OCR captures."""
from ctypes import wintypes

from godinavi.window_attachment import native_window_handle, user32


def exclude_from_capture(window, excluded):
    if getattr(window, "_ocr_capture_excluded", None) == excluded:
        return
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    if user32.SetWindowDisplayAffinity(native_window_handle(window), 0x11 if excluded else 0):
        window._ocr_capture_excluded = excluded

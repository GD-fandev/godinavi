"""Bundled Godius font registration and Tk default typography."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from tkinter import font as tkfont


FONT_FAMILIES = {
    "KR": "Noto Sans KR",
    "JP": "Noto Sans JP",
    "EN": "Noto Sans",
}


def register_bundled_fonts(font_dir):
    """Register bundled fonts privately for the lifetime of this process."""
    font_dir = Path(font_dir)
    if sys.platform != "win32" or not font_dir.is_dir():
        return 0
    add_font = ctypes.windll.gdi32.AddFontResourceExW
    count = 0
    for path in font_dir.glob("*.ttf"):
        if add_font(str(path), 0x10, 0):  # FR_PRIVATE
            count += 1
    return count


def family_for_language(language):
    return FONT_FAMILIES.get(str(language).upper(), FONT_FAMILIES["EN"])


def apply_tk_default_fonts(root, language="KR"):
    """Apply the bundled family to Tk and ttk widgets without explicit fonts."""
    family = family_for_language(language)
    available = {str(name).casefold() for name in tkfont.families(root)}
    if family.casefold() not in available:
        family = "TkDefaultFont"
    for name in (
        "TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
        "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont",
    ):
        try:
            tkfont.nametofont(name, root=root).configure(family=family)
        except Exception:
            pass
    root.option_add("*Font", (family, 9))
    return family

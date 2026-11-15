"""Public window/display metadata only. Never opens or reads a game process."""
import ctypes as C
from ctypes import wintypes as W
from functools import lru_cache


class MonitorInfo(C.Structure):
    _fields_ = [('size', W.DWORD), ('monitor', W.RECT), ('work', W.RECT),
                ('flags', W.DWORD), ('device', W.WCHAR * 32)]


class DisplayMode(C.Structure):
    _fields_ = [('name', W.WCHAR * 32), ('spec', W.WORD), ('driver', W.WORD),
                ('size', W.WORD), ('extra', W.WORD), ('fields', W.DWORD),
                ('display_union', C.c_byte * 16), ('color', W.SHORT),
                ('duplex', W.SHORT), ('y_resolution', W.SHORT), ('tt', W.SHORT),
                ('collate', W.SHORT), ('form', W.WCHAR * 32), ('dpi', W.WORD),
                ('bits', W.DWORD), ('width', W.DWORD), ('height', W.DWORD),
                ('flags', W.DWORD), ('frequency', W.DWORD), ('tail', W.DWORD * 8)]


@lru_cache(maxsize=8)
def display_heights(device):
    user = C.WinDLL('user32', use_last_error=True)
    user.EnumDisplaySettingsW.argtypes = [W.LPCWSTR, W.DWORD, C.POINTER(DisplayMode)]
    heights = set()
    for index in range(4096):
        mode = DisplayMode()
        mode.size = C.sizeof(mode)
        if not user.EnumDisplaySettingsW(device, index, C.byref(mode)):
            break
        if 0 < mode.height <= 16384:
            heights.add(int(mode.height))
    return tuple(sorted(heights))


def window_context(hwnd):
    user = C.WinDLL('user32', use_last_error=True)
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]
    user.MonitorFromWindow.restype = W.HANDLE
    user.GetMonitorInfoW.argtypes = [W.HANDLE, C.POINTER(MonitorInfo)]
    rect, point, pid = W.RECT(), W.POINT(), W.DWORD()
    if not (hwnd and user.GetClientRect(hwnd, C.byref(rect))
            and user.ClientToScreen(hwnd, C.byref(point))):
        return None
    user.GetWindowThreadProcessId(hwnd, C.byref(pid))
    info = MonitorInfo()
    info.size = C.sizeof(info)
    if not user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), C.byref(info)):
        return None
    return dict(identity=(int(hwnd), int(pid.value)),
                rect=(point.x, point.y, point.x+rect.right, point.y+rect.bottom),
                monitor_height=info.monitor.bottom-info.monitor.top, device=info.device)

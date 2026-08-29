import ctypes
import os
from ctypes import wintypes


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GA_ROOT = 2
GW_OWNER = 4
GWLP_HWNDPARENT = -8
GWL_EXSTYLE = -20
HWND_TOP = wintypes.HWND(0)
HWND_TOPMOST = wintypes.HWND(-1)
SW_SHOWNOACTIVATE = 4
SW_HIDE = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def _process_path(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _process_name(hwnd) -> str:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return os.path.basename(_process_path(pid.value))


def _window_title(hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def find_godius_window(process_name: str = "Godius.exe", window_title: str = "Godius Client"):
    title_matches = []
    process_matches = []
    process_needle = process_name.casefold()
    title_needle = window_title.casefold()

    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if title_needle and title_needle in _window_title(hwnd).casefold():
            title_matches.append(hwnd)
        if _process_name(hwnd).casefold() == process_needle:
            process_matches.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(visit), 0)
    return title_matches[0] if title_matches else process_matches[0] if process_matches else None


def client_screen_rect(hwnd):
    rect = wintypes.RECT()
    origin = wintypes.POINT(0, 0)
    if not hwnd or not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    if rect.right <= 0 or rect.bottom <= 0:
        return None
    return origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom


def native_window_handle(window):
    window.update_idletasks()
    return user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()


def _owner_group_is_foreground(owner_hwnd, window_hwnd) -> bool:
    """Return whether the foreground window belongs to this game/overlay group."""
    foreground = user32.GetForegroundWindow()
    if not foreground:
        return False

    def owner_chain(start):
        result = set()
        current = start
        while current and current not in result:
            result.add(current)
            current = user32.GetWindow(current, GW_OWNER)
        return result

    # The dock can be owned by the minimap, which is itself owned by Godius.
    # Compare both complete owner chains so focusing Godius is still treated as
    # focusing this group rather than as an unrelated foreground application.
    group = owner_chain(window_hwnd) | owner_chain(owner_hwnd)
    return bool(group & owner_chain(foreground))


def owner_group_is_foreground(owner_hwnd, window_hwnd) -> bool:
    """Public foreground check for overlay popups owned by the game group."""
    return _owner_group_is_foreground(owner_hwnd, window_hwnd)


def mouse_buttons_down() -> bool:
    """Return whether a primary, secondary, or middle mouse button is down."""
    return any(user32.GetAsyncKeyState(key) & 0x8000 for key in (0x01, 0x02, 0x04))


def attach_above(window, owner_hwnd, x: int | None = None, y: int | None = None):
    was_viewable = bool(window.winfo_viewable())
    window.update_idletasks()
    hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
    previous_owner = getattr(window, "_attached_owner_hwnd", None)
    owner_changed = previous_owner != owner_hwnd
    foreground = user32.GetForegroundWindow()
    foreign_foreground = bool(
        foreground and not _owner_group_is_foreground(owner_hwnd, hwnd)
    )
    if owner_changed and foreign_foreground and was_viewable:
        # Changing an owner can briefly raise the complete owner group. Hide
        # the overlay while reconnecting it so no one-frame flash is visible.
        user32.ShowWindow(hwnd, SW_HIDE)
    if owner_changed:
        user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, owner_hwnd)
        window._attached_owner_hwnd = owner_hwnd
    flags = SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
    if x is None or y is None:
        flags |= SWP_NOMOVE
        x = 0
        y = 0
    if foreign_foreground:
        # Reordering an owned overlay relative to the foreground window also
        # reorders its complete owner group, pulling Godius ahead of unrelated
        # applications that were previously above it. Preserve the existing
        # Z-order and only update coordinates while another app has focus.
        user32.SetWindowPos(
            hwnd, HWND_TOP, int(x), int(y), 0, 0,
            (flags & ~SWP_SHOWWINDOW) | SWP_NOZORDER,
        )
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        return
    if not was_viewable:
        window.deiconify()
    if was_viewable and not owner_changed:
        user32.SetWindowPos(hwnd, HWND_TOP, int(x), int(y), 0, 0, flags | SWP_NOZORDER)
        return
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(hwnd, HWND_TOP, int(x), int(y), 0, 0, flags)


def move_attached(window, x: int | None = None, y: int | None = None):
    """Move/show an attached overlay without changing its current Z-order."""
    window.update_idletasks()
    hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    flags = SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_NOZORDER
    if x is None or y is None:
        flags |= SWP_NOMOVE
        x = 0
        y = 0
    user32.SetWindowPos(hwnd, HWND_TOP, int(x), int(y), 0, 0, flags)


def make_noactivate_toolwindow(window, topmost=False):
    """Keep an interactive overlay out of Alt-Tab without activating the taskbar."""
    window.update_idletasks()
    hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED
    if not topmost:
        flags |= SWP_NOZORDER
    user32.SetWindowPos(hwnd, HWND_TOPMOST if topmost else HWND_TOP, 0, 0, 0, 0, flags)


def make_activatable_toolwindow(window, topmost=False):
    """Temporarily allow an overlay input control to receive keyboard focus."""
    window.update_idletasks()
    hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_NOACTIVATE
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    user32.SetWindowPos(
        hwnd, HWND_TOPMOST if topmost else HWND_TOP, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
    )
    user32.SetForegroundWindow(hwnd)


def focus_native_window(hwnd):
    if hwnd:
        user32.SetForegroundWindow(hwnd)


def is_minimized(hwnd) -> bool:
    return bool(hwnd and user32.IsIconic(hwnd))

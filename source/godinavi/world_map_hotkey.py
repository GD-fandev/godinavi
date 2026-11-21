"""Queue F10 key-down edges independently of the Tk rendering thread."""
import ctypes
from ctypes import wintypes
from queue import SimpleQueue, Empty
import threading


class WorldMapHotkey:
    def __init__(self):
        self.events = SimpleQueue()
        self.enabled = False
        self.thread_id = None
        self.stopped = threading.Event()
        self.down = False
        self.thread = threading.Thread(target=self._run, daemon=True, name='world-map-f10')
        self.thread.start()

    def record(self, pressed, foreground):
        if pressed and not self.down:
            self.events.put(foreground)
        self.down = pressed

    def drain(self):
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except Empty:
                return result

    def close(self):
        self.stopped.set()
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)

    def _run(self):
        user = ctypes.WinDLL('user32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        user.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type, wintypes.HINSTANCE, wintypes.DWORD]
        user.SetWindowsHookExW.restype = wintypes.HANDLE
        user.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user.CallNextHookEx.restype = ctypes.c_ssize_t
        user.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        user.GetForegroundWindow.restype = wintypes.HWND
        kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE

        @callback_type
        def callback(code, message, pointer):
            if code >= 0 and ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD))[0] == 0x79:
                if message in (0x100, 0x104):
                    self.record(True, user.GetForegroundWindow())
                elif message in (0x101, 0x105):
                    self.record(False, user.GetForegroundWindow())
            return user.CallNextHookEx(None, code, message, pointer)

        msg = wintypes.MSG()
        user.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        self.thread_id = kernel.GetCurrentThreadId()
        self.down = bool(user.GetAsyncKeyState(0x79) & 0x8000)
        hook = user.SetWindowsHookExW(13, callback, kernel.GetModuleHandleW(None), 0)
        if not hook:
            return
        self.enabled = True
        try:
            while not self.stopped.is_set() and user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user.TranslateMessage(ctypes.byref(msg))
                user.DispatchMessageW(ctypes.byref(msg))
        finally:
            self.enabled = False
            user.UnhookWindowsHookEx(hook)

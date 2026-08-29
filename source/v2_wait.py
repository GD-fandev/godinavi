"""Windows process waiting without owning or terminating unrelated processes."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes


SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102


def wait_for_pid(pid, timeout_seconds=60, cancelled=None):
    if not pid or pid <= 0:
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return True
    try:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if cancelled and cancelled():
                return False
            result = kernel32.WaitForSingleObject(handle, 100)
            if result == WAIT_OBJECT_0:
                return True
        return False
    finally:
        kernel32.CloseHandle(handle)


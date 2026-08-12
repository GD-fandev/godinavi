import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


SYNCHRONIZE = 0x00100000
WAIT_TIMEOUT = 0x00000102


def wait_for_process(pid, timeout_seconds=30):
    if pid <= 0:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return
    try:
        result = kernel32.WaitForSingleObject(handle, int(timeout_seconds * 1000))
        if result == WAIT_TIMEOUT:
            raise TimeoutError("GodiNavi did not close within 30 seconds.")
    finally:
        kernel32.CloseHandle(handle)


def apply_update(staged, target, pid):
    staged = Path(staged).resolve()
    target = Path(target).resolve()
    backup = target.with_suffix(target.suffix + ".old")
    incoming = target.with_suffix(target.suffix + ".new")
    if not staged.is_file() or staged.stat().st_size <= 0:
        raise FileNotFoundError("The downloaded GodiNavi executable is missing.")
    wait_for_process(pid)
    incoming.unlink(missing_ok=True)
    backup.unlink(missing_ok=True)
    shutil.copy2(staged, incoming)
    replaced = False
    try:
        if target.exists():
            target.replace(backup)
        incoming.replace(target)
        replaced = True
        subprocess.Popen([str(target)], cwd=str(target.parent), close_fds=True)
        time.sleep(1.5)
        backup.unlink(missing_ok=True)
    except Exception:
        if replaced:
            target.unlink(missing_ok=True)
        if backup.exists():
            backup.replace(target)
        raise
    finally:
        incoming.unlink(missing_ok=True)
        staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--pid", required=True, type=int)
    args = parser.parse_args()
    try:
        apply_update(args.staged, args.target, args.pid)
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None, f"GodiNavi update failed.\n\n{type(exc).__name__}: {exc}", "GodiNavi Updater", 0x10)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

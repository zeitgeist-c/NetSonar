"""Process-wide single-instance mutex for Windows."""

import ctypes
import os


class SingleInstanceLock:
    def __init__(self, name: str = "Local\\NetSonar-v05"):
        self.name = name
        self.handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        self.handle = ctypes.windll.kernel32.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise ctypes.WinError()
        return ctypes.windll.kernel32.GetLastError() != 183

    def release(self):
        if self.handle and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("NetSonar is already running")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.release()

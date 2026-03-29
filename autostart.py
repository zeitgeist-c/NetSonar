"""
NetSonar — Windows Otomatik Başlatma
Bilgisayar açılınca NetSonar'yı otomatik başlatır.
"""

import os
import sys
import winreg


APP_NAME = "NetSonar"
EXE_PATH = sys.executable
if hasattr(sys, '_MEIPASS'):
    # PyInstaller ile paketlenmişse
    EXE_PATH = os.path.join(sys._MEIPASS, 'main.py')


def is_autostart_enabled() -> bool:
    """Otomatik başlatma etkin mi?"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable_autostart() -> bool:
    """Otomatik başlatmayı etkinleştir."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_WRITE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{EXE_PATH}"')
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        print(f"Otomatik başlatma etkinleştirilirken hata: {exc}")
        return False


def disable_autostart() -> bool:
    """Otomatik başlatmayı devre dışı bırak."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_WRITE
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        print(f"Otomatik başlatma devre dışı bırakılırken hata: {exc}")
        return False

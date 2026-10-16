"""
NetSonar — Windows Otomatik Başlatma
Bilgisayar açılınca NetSonar'yı otomatik başlatır.
"""

import os
import sys
import logging
import winreg

log = logging.getLogger("NetSonar.Autostart")

APP_NAME = "NetSonar"

if getattr(sys, 'frozen', False):
    REG_VALUE = f'"{sys.executable}"'
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    main_path = os.path.join(app_dir, "main.py")
    REG_VALUE = f'"{sys.executable}" "{main_path}"'


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
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, REG_VALUE)
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        log.error("Otomatik başlatma etkinleştirilirken hata: %s", exc)
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
        log.error("Otomatik başlatma devre dışı bırakılırken hata: %s", exc)
        return False


def set_autostart(enabled: bool) -> bool:
    """Apply and verify the requested registry state."""
    changed = enable_autostart() if enabled else disable_autostart()
    return bool(changed and is_autostart_enabled() == bool(enabled))


def retarget_launch(exe_path: str) -> bool:
    """Point an existing startup entry at a new exe after a self-update.

    A disabled entry stays disabled; an enabled one is rewritten so the
    next boot launches the fresh versioned exe, not the superseded one.
    """
    if not is_autostart_enabled():
        return True
    global REG_VALUE
    REG_VALUE = f'"{exe_path}"'
    return set_autostart(True)

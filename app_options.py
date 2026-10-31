"""Shared Windows desktop options - autostart + minimize to tray.

This module bundles the two standard options a Windows desktop application
should offer on its Settings screen:

    1. "Start with Windows"        -> HKCU\\...\\Run entry
    2. "Minimize to tray on close" -> close-behaviour preference

Design rules:
- Library independent: only the standard library (winreg, os, sys) and an
  optional PyQt6. Without PyQt6 only the business logic works.
- The application's own settings store is used (callable get/set); the module
  imposes no file format.
- The registry location is HKCU (per user) - no administrator rights, no
  installer, and the choice belongs to the user.

Usage (with PyQt6):

    from app_options import AutostartController, TrayOption

    controller = AutostartController(
        app_name="NetSonar",
        get_setting=lambda k, d=None: settings.get(k, d),
        set_setting=lambda k, v: settings.update({k: v}),
    )
    box = QCheckBox("Start with Windows")
    box.setChecked(controller.is_enabled())
    box.toggled.connect(controller.set_enabled)
"""

from __future__ import annotations
from i18n import t

import logging
import os
import sys
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger("AppOptions")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# Settings key names - the shared contract between applications.
SETTING_AUTOSTART = "AUTOSTART_ENABLED"
SETTING_MINIMIZE_TO_TRAY = "MINIMIZE_TO_TRAY"


# ─── Autostart (HKCU Run) ──────────────────────────────────────────

def _winreg():
    """Return the winreg module; None off Windows."""
    if os.name != "nt":
        return None
    try:
        import winreg
        return winreg
    except ImportError:  # pragma: no cover
        return None


def startup_command(exe_path: str = "", args: str = "",
                    entry_point: str = "") -> str:
    """Build the autostart command.

    Packaged application: "<exe>" (or "<exe> <args>")
    Source mode: "<python> "<main.py>" (or extra args)

    If `entry_point` is given, that entry point is used in source mode;
    otherwise `main.py` is looked up. When it cannot be found an empty string
    is returned (the caller must treat that as "could not create the startup
    entry").
    """
    if getattr(sys, "frozen", False) or exe_path:
        # Paketlenmis uygulama (veya acikca verilen exe): exe yeter.
        exe = exe_path or sys.executable
        command = f'"{exe}"'
        if args:
            command += f" {args}"
        return command

    # Source mode: interpreter + entry point
    exe = exe_path or sys.executable
    main_py = entry_point or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "main.py")
    if os.path.exists(main_py):
        command = f'"{exe}" "{main_py}"'
    else:
        command = f'"{exe}"'
    if args:
        command += f" {args}"
    return command


class AutostartController:
    """Manage the HKCU Run entry: is it on, turn it on/off.

    It also writes to the application's settings store, so the "off"
    preference stays consistent between the registry and the settings file.
    If the registry entry is deleted by hand, it is restored from the setting
    on the next start.
    """

    def __init__(self, app_name: str,
                 get_setting: Optional[Callable[[str, object], object]] = None,
                 set_setting: Optional[Callable[[str, object], None]] = None,
                 exe_path: str = "", args: str = "", entry_point: str = ""):
        self.app_name = app_name
        self._get = get_setting or (lambda key, default=None: default)
        self._set = set_setting or (lambda key, value: None)
        self._exe_path = exe_path
        self._args = args
        self._entry_point = entry_point

    def _command(self) -> str:
        return startup_command(self._exe_path, self._args, self._entry_point)

    # -- registry -----------------------------------------------------
    def _read_registry(self) -> Optional[str]:
        winreg = _winreg()
        if winreg is None:
            return None
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                 winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                return str(value)
            finally:
                winreg.CloseKey(key)
        except FileNotFoundError:
            return None
        except OSError as exc:
            log.warning("Baslangic kaydi okunamadi: %s", exc)
            return None

    def _write_registry(self, command: str) -> bool:
        winreg = _winreg()
        if winreg is None:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                 winreg.KEY_SET_VALUE)
            try:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ,
                                  command)
            finally:
                winreg.CloseKey(key)
            return True
        except OSError as exc:
            log.error("Baslangic kaydi yazilamadi: %s", exc)
            return False

    def _delete_registry(self) -> bool:
        winreg = _winreg()
        if winreg is None:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                 winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, self.app_name)
            except FileNotFoundError:
                pass
            finally:
                winreg.CloseKey(key)
            return True
        except OSError as exc:
            log.error("Baslangic kaydi silinemedi: %s", exc)
            return False

    # -- genel API ----------------------------------------------------
    def is_enabled(self) -> bool:
        """Is autostart on?

        The registry is the source of truth; when the entry is missing the
        stored preference is consulted (the entry may have been deleted).
        """
        if self._read_registry() is not None:
            return True
        return bool(self._get(SETTING_AUTOSTART, False))

    def set_enabled(self, enabled: bool) -> bool:
        """Apply and verify the preference. True on success."""
        enabled = bool(enabled)
        if enabled:
            command = self._command()
            if not command:
                log.error("Baslangic komutu olusturulamadi")
                return False
            ok = self._write_registry(command)
        else:
            ok = self._delete_registry()
        self._set(SETTING_AUTOSTART, enabled)
        verified = self.is_enabled() == enabled
        if not verified:
            log.warning("Baslangic tercihi dogrulanamadi (istenen=%s)", enabled)
        return bool(ok and verified)

    def refresh(self) -> bool:
        """Refresh the registry entry with the current command (after install/update).

        Does nothing when the preference is off.
        """
        if not self.is_enabled():
            return True
        command = self._command()
        if not command:
            return False
        return self._write_registry(command)

    def current_command(self) -> Optional[str]:
        return self._read_registry()


# ─── Minimize to tray ──────────────────────────────────────────────

@dataclass
class TrayOption:
    """Minimize-to-tray-on-close preference.

    The application's close behaviour follows this order:
      1. Preference off -> the application really quits.
      2. Preference on and a tray icon exists -> the window hides and the
         application keeps running in the background.
      3. Preference on but no tray icon -> the user would lose the
         application; so the fallback is to quit.
    """

    get_setting: Callable[[str, object], object]
    set_setting: Callable[[str, object], None]

    def is_enabled(self) -> bool:
        return bool(self._get(SETTING_MINIMIZE_TO_TRAY, True))

    def set_enabled(self, enabled: bool) -> bool:
        enabled = bool(enabled)
        self._set(SETTING_MINIMIZE_TO_TRAY, enabled)
        return self.is_enabled() == enabled

    def should_minimize(self, tray_available: bool) -> bool:
        """Should the window be hidden on a close event?"""
        return self.is_enabled() and tray_available

    def _get(self, key: str, default=None):
        return self.get_setting(key, default)

    def _set(self, key: str, value) -> None:
        self.set_setting(key, value)


# ─── PyQt6 UI helpers ──────────────────────────────────────────────

def build_settings_widgets(autostart: AutostartController, tray: TrayOption,
                           parent=None):
    """Build the two standard options as PyQt6 check boxes.

    Returns: (autostart_checkbox, tray_checkbox)

    Usage:
        ac_cb, tray_cb = build_settings_widgets(autostart, tray)
        ac_cb.toggled.connect(autostart.set_enabled)
        tray_cb.toggled.connect(tray.set_enabled)
    """
    from PyQt6.QtWidgets import QCheckBox  # noqa: PLC0415

    autostart_box = QCheckBox(t("Windows'ta otomatik başlat"), parent)
    autostart_box.setChecked(autostart.is_enabled())
    autostart_box.toggled.connect(autostart.set_enabled)

    tray_box = QCheckBox(t("Kapatılınca tepsiye küçült"), parent)
    tray_box.setChecked(tray.is_enabled())
    tray_box.toggled.connect(tray.set_enabled)

    return autostart_box, tray_box

"""
NetSonar - Windows autostart
Starts NetSonar automatically when the computer boots.

The business logic lives in the shared module: app_options.AutostartController.
This file defines the NetSonar-specific command (exe path) and keeps the old
function names.
"""

from i18n import t
import logging
import os
import sys

from app_options import (  # noqa: F401  (re-export)
    SETTING_AUTOSTART,
    AutostartController,
)

log = logging.getLogger("NetSonar.Autostart")

APP_NAME = "NetSonar"


def _default_command() -> str:
    """Autostart command.

    The installed build has a fixed location (C:\\Program Files\\NetSonar\\NetSonar.exe),
    so the command does not change on update - the version is not part of the
    exe name.
    """
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    app_dir = os.path.dirname(os.path.abspath(__file__))
    main_path = os.path.join(app_dir, "main.py")
    return f'"{sys.executable}" "{main_path}"'


REG_VALUE = _default_command()


def _controller() -> AutostartController:
    """Autostart controller specific to NetSonar."""
    return AutostartController(app_name=APP_NAME, exe_path=_default_command())


def is_autostart_enabled() -> bool:
    """Is autostart enabled?"""
    return _controller().is_enabled()


def enable_autostart() -> bool:
    """Enable autostart."""
    return _controller().set_enabled(True)


def disable_autostart() -> bool:
    """Disable autostart."""
    return _controller().set_enabled(False)


def set_autostart(enabled: bool) -> bool:
    """Apply and verify the requested registry state."""
    return _controller().set_enabled(enabled)


def retarget_launch(exe_path: str) -> bool:
    """Point an existing startup entry at a new exe after a self-update.

    A disabled entry stays disabled; an enabled one is rewritten so the
    next boot launches the fresh versioned exe, not the superseded one.
    """
    controller = AutostartController(app_name=APP_NAME, exe_path=exe_path)
    if not controller.is_enabled():
        return True
    return controller.set_enabled(True)

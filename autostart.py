"""
NetSonar — Windows Otomatik Başlatma
Bilgisayar açılınca NetSonar'yı otomatik başlatır.

İş mantığı ortak modülde: app_options.AutostartController.
Bu dosya NetSonar'a özel komutu (exe yolu) tanımlar ve eski fonksiyon
adlarını korur.
"""

from i18n import t
import logging
import os
import sys

from app_options import (  # noqa: F401  (yeniden dışa aktarım)
    SETTING_AUTOSTART,
    AutostartController,
)

log = logging.getLogger("NetSonar.Autostart")

APP_NAME = "NetSonar"


def _default_command() -> str:
    """Otomatik başlatma komutu.

    Kurulu sürüm sabit yerde durur (C:\\Program Files\\NetSonar\\NetSonar.exe),
    bu yüzden güncellemede komut değişmez — sürüm adı exe adında yok.
    """
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    app_dir = os.path.dirname(os.path.abspath(__file__))
    main_path = os.path.join(app_dir, "main.py")
    return f'"{sys.executable}" "{main_path}"'


REG_VALUE = _default_command()


def _controller() -> AutostartController:
    """NetSonar'a özel otomatik başlatma denetleyicisi."""
    return AutostartController(app_name=APP_NAME, exe_path=_default_command())


def is_autostart_enabled() -> bool:
    """Otomatik başlatma etkin mi?"""
    return _controller().is_enabled()


def enable_autostart() -> bool:
    """Otomatik başlatmayı etkinleştir."""
    return _controller().set_enabled(True)


def disable_autostart() -> bool:
    """Otomatik başlatmayı devre dışı bırak."""
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

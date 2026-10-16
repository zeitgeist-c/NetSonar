# -*- mode: python ; coding: utf-8 -*-
# Tek dosyali (onefile) portable surum. EXE adi surumu tasir
# (NetSonar-vX.Y.Z.exe); yanindaki BAT ile calisir ve kendini-guncelleyici
# yeni surumu aynin yanina koyup swap yapar. NSIS kurulumcusu birakildi:
# kurulumcu Npcap'i zaten kurmuyordu, tek yaptigi dosyalari klasore koymakti.
from pathlib import Path
import re
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).parent

_config_text = (project_root / "config.py").read_text(encoding="utf-8")
_version_match = re.search(r'(?m)^APP_VERSION\s*=\s*"v(\d+\.\d+\.\d+)"', _config_text)
if not _version_match:
    raise SystemExit("config.py icinde APP_VERSION bulunamadi.")
APP_VERSION = _version_match.group(1)
EXE_NAME = f"NetSonar-v{APP_VERSION}"

datas = [
    (str(project_root / "netsonar-v3.ico"), "."),
    (str(project_root / "assets" / "netsonar-mark-v3.png"), "assets"),
    (str(project_root / "assets" / "icons"), "assets/icons"),
    (str(project_root / "config" / "ai_prompt.txt"), "config"),
]
hiddenimports = [
    "custom_alerts",
    "notifier",
    "update",
    "plyer.facades.notification",
    "plyer.platforms.win.notification",
]
hiddenimports += collect_submodules("winotify")
hiddenimports += collect_submodules("apscheduler")

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "netsonar-v3.ico"),
    uac_admin=True,
)

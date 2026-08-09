# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).parent

datas = [
    (str(project_root / "netsonar-v3.ico"), "."),
    (str(project_root / "assets" / "netsonar-mark-v3.png"), "assets"),
    (str(project_root / "assets" / "icons"), "assets/icons"),
    (str(project_root / "config" / "ai_prompt.txt"), "config"),
]
hiddenimports = [
    "custom_alerts",
    "notifier",
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
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="NetSonar",
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
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NetSonar",
)

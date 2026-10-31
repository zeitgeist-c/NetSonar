# -*- mode: python ; coding: utf-8 -*-
# Folder (onedir) package. The installer copies this tree to
# C:\Program Files\NetSonar; it is not onefile, because an update replaces the
# program folder in place and an onedir start is immediate.
#
# The EXE name carries no version: C:\Program Files\NetSonar\NetSonar.exe
# (the install path is fixed; an update writes to the same place).
from pathlib import Path
import re
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).parent

_config_text = (project_root / "config.py").read_text(encoding="utf-8")
_version_match = re.search(r'(?m)^APP_VERSION\s*=\s*"v(\d+\.\d+\.\d+)"', _config_text)
if not _version_match:
    raise SystemExit("APP_VERSION not found in config.py.")
APP_VERSION = _version_match.group(1)

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
    "store",
    "plyer.facades.notification",
    "plyer.platforms.win.notification",
]
hiddenimports += collect_submodules("winotify")
hiddenimports += collect_submodules("apscheduler")

# Language catalogues live in one module (i18n_strings_tables) that i18n.py
# imports statically, so PyInstaller's analysis finds it on its own. The glob
# is kept so an extra catalogue module cannot be silently missed if one is ever
# split out again.
hiddenimports += sorted(p.stem for p in project_root.glob("i18n_strings_*.py"))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Unused Qt modules must not bloat the package; the app uses only
    # QtCore/QtGui/QtWidgets.
    excludes=[
        "PyQt6.QtBluetooth", "PyQt6.QtDesigner", "PyQt6.QtHelp",
        "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets", "PyQt6.QtNfc",
        "PyQt6.QtPdf", "PyQt6.QtPdfWidgets", "PyQt6.QtPositioning",
        "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuick3D",
        "PyQt6.QtQuickWidgets", "PyQt6.QtRemoteObjects", "PyQt6.QtSensors",
        "PyQt6.QtSpatialAudio", "PyQt6.QtStateMachine", "PyQt6.QtTextToSpeech",
        "PyQt6.QtWebChannel", "PyQt6.QtWebSockets", "PyQt6.QtXml",
        "PyQt6.Qt3DCore", "PyQt6.Qt3DRender", "PyQt6.QtCharts",
        "PyQt6.QtDataVisualization", "PyQt6.QtGraphs", "PyQt6.QtGraphsWidgets",
        "PyQt6.QtDBus", "PyQt6.QtSerialPort", "PyQt6.QtSql",
        "matplotlib", "numpy", "pandas", "scipy", "tkinter",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
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
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NetSonar",
)

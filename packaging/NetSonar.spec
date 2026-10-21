# -*- mode: python ; coding: utf-8 -*-
# Klasorlu (onedir) paket. Kurulumcu bu agaci C:\Program Files\NetSonar
# altina kopyalar; onefile degil, cunku guncelleme program klasorunu yerinde
# degistirecek ve onedir acilisi aninda olur.
#
# EXE adi surumsuz: C:\Program Files\NetSonar\NetSonar.exe
# (kurulum yolu sabit; guncelleme ayni yere yazar).
from pathlib import Path
import re
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).parent

_config_text = (project_root / "config.py").read_text(encoding="utf-8")
_version_match = re.search(r'(?m)^APP_VERSION\s*=\s*"v(\d+\.\d+\.\d+)"', _config_text)
if not _version_match:
    raise SystemExit("config.py icinde APP_VERSION bulunamadi.")
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

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Kullanilmayan Qt modulleri packaging'i sisirmesin; uygulama yalniz
    # QtCore/QtGui/QtWidgets kullanir.
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

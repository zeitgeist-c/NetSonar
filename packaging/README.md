# NetSonar Windows package files

This folder holds the packaging configuration that lets NetSonar run on another
Windows machine without the source code or Python.

## End-user files

    dist\NetSonar-vX.Y.Z-Setup.exe

Distribution has a single channel: the NSIS installer. Setup installs to a fixed
location:

    C:\Program Files\NetSonar\NetSonar.exe

Setup asks for administrator approval. Desktop and Start Menu shortcuts are
created, the uninstaller (`Uninstall.exe`) is generated, and the program appears
in "Programs and Features".

The package is a folder (onedir), not a single file: an update replaces the
program folder in place, so startup is immediate.

## Update channel

The source repository is private; the installer asset is uploaded to the
releases of the public `zeitgeist-c/NetSonar-Releases` repository. The program
queries `releases/latest` with the unauthenticated GitHub API (update.py):

1. The `NetSonar-vX.Y.Z-Setup.exe` asset is located (only this one is accepted).
2. The installer downloads into the user cache
   (`%LOCALAPPDATA%\NetSonar\cache\updates`) and its SHA256 is verified.
3. After the user chooses "Start Installation", a confirmation window opens.
4. The program closes; the waiting script (baton) waits for the PID to exit, runs
   the installer **with administrator rights** and waits for it to finish.
5. When setup finishes, the program restarts automatically.

Because the program already runs as administrator, the update does not ask for
administrator approval again; the confirmation window is the "start" consent.

If the published version is not newer than the installed version, no update is
performed: the program says the installed version is the newest, and neither
download nor installation starts. Reinstalling the same version over and over is
prevented this way.

The autostart entry is repointed at the new exe only if the user turned it on;
if it was off, it stays off.

## Persistent model store

    %LOCALAPPDATA%\NetSonar\store\models\
    %LOCALAPPDATA%\NetSonar\store\lib\
    %LOCALAPPDATA%\NetSonar\store\store.json

Setup and updates **never touch** this folder. A local model or extra Python
library downloaded once stays in place even when the program version changes; it
does not have to be downloaded again. The store is managed by the `store.py`
module and is appended to the end of `sys.path` (the bundled library has
priority).

NetSonar has no downloaded local model today - AI runs entirely through the
Gemini API. The store is already in place so it is ready when a local model or an
extra library arrives later.

## Build prerequisites

- 64-bit Windows 10 or Windows 11
- Python 3.11 or any newer 64-bit version
- NSIS 3.x (`C:\Program Files (x86)\NSIS\makensis.exe`)
- Internet connection on the first build

## Rebuilding

In the project root directory:

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1

If the dependencies were installed before:

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1 -SkipDependencyInstall

Application folder only (no installer produced):

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1 -SkipInstaller

The script creates the isolated environment under packaging\.build-venv.
PyInstaller scratch output is prepared under packaging\build and
packaging\app-dist and is removed automatically at the end of a successful
build. The installer is written to the dist folder in the project root and its
SHA256 digest is printed.

The version number is read from the APP_VERSION value in config.py and passed to
the installer with `-DAPP_VERSION`.

## Configuration files

- NetSonar.nsi: NSIS installer script (fixed path, shortcut, uninstaller, silent mode).
- NetSonar.spec: PyInstaller onedir application and resource definitions.
- requirements-build.txt: tested, pinned packaging dependencies.
- build.ps1: clean and reproducible end-to-end build script.

## User data and privacy

The packaged application keeps its settings, Gemini/VirusTotal/Tavily keys, the
database, logs, custom alerts, reports and the model store under
%LOCALAPPDATA%\NetSonar. The project's config\settings.json and the contents of
netsonar_data are not included in the package. Setup and updates write only to
the program folder; they do not touch user data or the model store. Uninstall
does not delete user data either.

More than one key is supported for each of the three providers as well; the
first key is the default, the others are automatic fallbacks on error or quota,
and all are protected with DPAPI.

## Npcap prerequisite

Free Npcap cannot be redistributed with another application; it is not embedded
in the package. The application checks Npcap at startup
(capture_engine.npcap_available) and, if it is missing, shows a warning offering
to open the official download page.

- Npcap: https://npcap.com/#download
- OEM redistribution license: https://npcap.com/oem/

## Release close-out

1. Produce the installer with `packaging\build.ps1`.
2. Tag the same commit `vX.Y.Z`; push and release with explicit approval.
3. The installer asset is uploaded to the `zeitgeist-c/NetSonar-Releases`
   release; local and remote asset hashes are compared.

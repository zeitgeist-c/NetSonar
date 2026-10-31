"""Self-update over the public NetSonar GitHub repository.

The source repository stays private; releases (the installer only) live in a
public repo so an installed app can ask "what is the newest version?" without
shipping a token inside the exe. The GitHub API answers unauthenticated for
public repos, rate limited per IP — a once-a-day check uses one request and
stays far under the limit.

A release always supersedes every older one, so an install on 0.5.9 jumps
straight to 0.6.0: it downloads `releases/latest`, never the steps between.

Update shape (installer-based, v0.6.0+):
    1. fetch the release, read the `NetSonar-vX.Y.Z-Setup.exe` asset
    2. download it into the user data cache with SHA256 verification
    3. the running app asks the user to confirm, then hands the job to the
       installer, which replaces the program folder in place
    4. user data and the model store (a separate folder) are never touched

The old "download a new exe next to the old one and swap" flow is gone: the
install path is fixed (C:\\Program Files\\NetSonar), so only the installer may
write there — a copy-then-swap dance would fight it for the same files.
"""

from __future__ import annotations
from i18n import t

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RELEASE_REPO = "zeitgeist-c/NetSonar"
API_LATEST = f"https://api.github.com/repos/{RELEASE_REPO}/releases/latest"
USER_AGENT = "NetSonar/updater"
log = logging.getLogger("NetSonar.Update")

INSTALL_DIR = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NetSonar"
APP_EXE_NAME = "NetSonar.exe"
INSTALLER_TIMEOUT_SECONDS = 900
# Windows'un kendi timeout komutu. Git-Bash/MSYS kurulu sistemlerde PATH'te
# GNU "timeout" takes precedence and rejects the "/t 1" parameter;
# mutlak yol kullanmak bu cakismayi ortadan kaldirir.
WINDOWS_TIMEOUT = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "timeout.exe"


class UpdateError(Exception):
    """Anything the user must hear about verbatim: network, shape, checksum."""


@dataclass
class UpdateInfo:
    version: str
    asset_name: str
    download_url: str
    sha256: str          # expected digest, "" when the release omits it
    size: int
    page_url: str


def parse_version(text: str) -> tuple:
    """'v0.5.10' / '0.5.10-beta' -> (0, 5, 10); non-numeric tails stop."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text or ""))
    if not match:
        raise UpdateError(t("Sürüm numarası çözümlenemedi: {text!r}", text=text))
    return tuple(int(part) for part in match.groups())


VERSION_PATTERN = re.compile(r"^\d{1,6}\.\d{1,6}\.\d{1,6}$")


def clean_version(text: str) -> str:
    """Reduce a version to a safe form usable as a path/file name.

    `parse_version` pulls numbers out of the tag; a tag such as
    ``1.2.3/../../evil`` matches too, and if it reaches `installer_asset_name`
    raw the download path escapes the cache folder. So the version is only
    accepted in ``X.Y.Z`` form.
    """
    value = str(text or "").strip()
    if value.startswith("v"):
        value = value[1:]
    if not VERSION_PATTERN.match(value):
        raise UpdateError(t("Geçersiz sürüm biçimi: {text!r}", text=text))
    return value


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def installer_asset_name(version: str) -> str:
    """Release asset name for a version: NetSonar-v0.6.0-Setup.exe."""
    return f"NetSonar-v{clean_version(version)}-Setup.exe"


def parse_release(payload: dict) -> UpdateInfo:
    """Pull the installer asset out of a /releases/latest payload.

    Asset names carry the 'v' prefix (NetSonar-v0.6.0-Setup.exe), matching
    the tag and the delivery file naming rule.

    The tag is untrusted input from the network: it is reduced to a strict
    ``X.Y.Z`` before it can reach a file name (see `clean_version`).
    """
    tag = str(payload.get("tag_name") or "")
    version = clean_version(tag)
    exe_name = installer_asset_name(version)
    for asset in payload.get("assets") or []:
        if asset.get("name") != exe_name:
            continue
        digest = str(asset.get("digest") or "")
        return UpdateInfo(
            version=version,
            asset_name=exe_name,
            download_url=str(asset.get("browser_download_url") or ""),
            sha256=digest.split(":", 1)[1] if ":" in digest else digest,
            size=int(asset.get("size") or 0),
            page_url=str(payload.get("html_url") or ""),
        )
    raise UpdateError(t("Yayının içinde {exe_name} dosyası yok.", exe_name=exe_name))


def fetch_latest() -> UpdateInfo:
    request = urllib.request.Request(API_LATEST, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UpdateError(t("Güncelleme sunucusuna ulaşılamadı.")) from exc
    return parse_release(payload)


def check_for_update(current: str) -> UpdateInfo | None:
    info = fetch_latest()
    return info if is_newer(info.version, current) else None


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(info: UpdateInfo, dest: Path, progress=None, cancel=None) -> Path:
    """Stream the asset to dest; verify size and SHA256 before it is kept.

    A half-written or tampered file must never become the running program,
    so a failed verification — or a cancel request — deletes the file.
    `cancel` is a threading.Event the progress callback polls.
    """
    class Cancelled(Exception):
        pass

    request = urllib.request.Request(info.download_url,
                                     headers={"User-Agent": USER_AGENT})
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or info.size)
            with dest.open("wb") as out:
                try:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                        written += len(chunk)
                        if progress:
                            progress(written, total)
                        if cancel is not None and cancel.is_set():
                            raise Cancelled()
                except Cancelled:
                    pass
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        dest.unlink(missing_ok=True)
        raise UpdateError(t("Güncelleme indirmesi yarıda kesildi.")) from exc
    if cancel is not None and cancel.is_set():
        dest.unlink(missing_ok=True)
        raise UpdateError("cancelled")
    if info.size and written != info.size:
        dest.unlink(missing_ok=True)
        raise UpdateError(t("İndirme dosya tamamlanmadan bitti."))
    if info.sha256:
        actual = _sha256_of(dest)
        if actual.lower() != info.sha256.lower():
            dest.unlink(missing_ok=True)
            raise UpdateError(t("İndirilen dosyanın sağlama değeri uyuşmuyor."))
    return dest


def cache_dir() -> Path:
    """Downloaded installers live in the user data cache, not in Program Files."""
    from config import user_data_path
    return Path(user_data_path("cache", "updates"))


def install_path(current_exe: Path, version: str) -> Path:
    """Where the installer is downloaded before it runs.

    The cache lives in the user data folder: Program Files is writable only
    by the installer, and the download must not need admin rights.

    The result is checked to stay inside the cache directory: the version
    string reaches this function and a traversal (``1.2.3/../../x``) must
    never redirect the download elsewhere.
    """
    folder = cache_dir().resolve()
    target = (folder / installer_asset_name(version)).resolve()
    if target.parent != folder:
        raise UpdateError(t("Kurulum dosyası yolu önbellek klasörü dışına çıkıyor."))
    return target


def is_installed() -> bool:
    """True when this process runs from the fixed Program Files install."""
    import sys
    if not getattr(sys, "frozen", False):
        return False
    try:
        here = Path(sys.executable).resolve().parent
        return here == INSTALL_DIR.resolve()
    except (OSError, ValueError):
        return False


def installed_version() -> str:
    """Read the installed version from the file (for post-install verification).

    The version the application reports and the version on disk can diverge:
    if the install was interrupted the exe stays old. So the real check reads
    the exe itself, not the version cached in memory.
    """
    if not getattr(sys, "frozen", False):
        from config import get_app_version
        return get_app_version().lstrip("v")
    exe = Path(sys.executable)
    try:
        import ctypes
        size = ctypes.c_ulong(0)
        handle = ctypes.windll.version.GetFileVersionInfoSizeW(str(exe), ctypes.byref(size))
        if not handle or not size.value:
            return ""
        buffer = ctypes.create_string_buffer(size.value)
        if not ctypes.windll.version.GetFileVersionInfoW(str(exe), 0, size.value, buffer):
            return ""
        # The VS_FIXEDFILEINFO structure holds the FileVersion (MS+LS) fields.
        address = ctypes.c_void_p()
        length = ctypes.c_uint()
        ok = ctypes.windll.version.VerQueryValueW(
            buffer, "\\", ctypes.byref(address), ctypes.byref(length))
        if not ok or not address:
            return ""
        ffi = ctypes.cast(address, ctypes.POINTER(ctypes.c_int * 8)).contents
        parts = [(ffi[0] >> 16) & 0xFFFF, ffi[0] & 0xFFFF,
                 (ffi[1] >> 16) & 0xFFFF, ffi[1] & 0xFFFF]
        text = ".".join(str(p) for p in parts)
        # "0.6.0.0" -> "0.6.0"
        trimmed = ".".join(text.split(".")[:3]).rstrip(".")
        return trimmed
    except Exception as exc:
        log.debug("installed_version could not be read: %s", exc)
        return ""


def launch_installer(installer: Path, wait: bool = False) -> int:
    """Run the downloaded installer silently over the current install.

    The installer is an NSIS package: `/S` runs it without UI, and it
    replaces the program folder in place. The app must exit before the
    installer can replace its files, so the caller exits first and the
    installer is started detached.
    """
    if not installer.exists():
        raise UpdateError(t("Kurulum dosyası bulunamadı."))
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) if not wait else 0
    process = subprocess.Popen([str(installer), "/S"], creationflags=flags)
    log.info("installer started: %s pid=%s", installer, process.pid)
    return process.pid


def run_installer_and_wait(installer: Path,
                            timeout: float = INSTALLER_TIMEOUT_SECONDS) -> int:
    """Start the installer and block until it finishes; return its exit code."""
    if not installer.exists():
        raise UpdateError(t("Kurulum dosyası bulunamadı."))
    try:
        completed = subprocess.run([str(installer), "/S"], timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise UpdateError(t("Kurulum zaman aşımına uğradı.")) from exc
    except OSError as exc:
        raise UpdateError(t("Kurulum başlatılamadı.")) from exc
    log.info("installer finished: code=%s", completed.returncode)
    return completed.returncode


def install_outcome(installer: Path, previous_version: str,
                     timeout: float = INSTALLER_TIMEOUT_SECONDS) -> dict:
    """Run the installer and verify the result.

    When the install finishes, the version on disk is read:
      - version increased  -> success
      - version unchanged  -> the install did not run (file was locked, say)
      - version unreadable -> unknown

    `installer` runs silently; the caller must have closed the program by
    then.
    """
    code = run_installer_and_wait(installer, timeout=timeout)
    current = installed_version()
    result = {
        "exit_code": code,
        "previous_version": previous_version,
        "installed_version": current,
        "changed": False,
        "succeeded": False,
    }
    if not current:
        # Version unreadable: if the exe changed, at least something happened.
        result["succeeded"] = code == 0
        return result
    try:
        result["changed"] = parse_version(current) > parse_version(previous_version)
    except UpdateError:
        result["changed"] = False
    result["succeeded"] = result["changed"] and code == 0
    return result


def _ascii_safe_path(path: Path, escape_quote: bool = False) -> str:
    """Return a path that survives being embedded in a cmd.exe batch file.

    A Turkish user name produces e.g. ``C:\\Users\\Şükrü\\AppData\\...``. Such
    characters cannot be encoded as ASCII, and writing them as UTF-8 makes
    cmd.exe mis-read the line under its OEM code page. The batch file is
    therefore written in the console OEM code page, and this helper only
    falls back to the 8.3 short form for characters that code page still
    cannot represent.
    """
    text = str(path)
    encoding = _oem_encoding()
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, 32768):
            if buffer.value:
                text = buffer.value
        try:
            text.encode(encoding)
        except UnicodeEncodeError as exc:
            raise UpdateError(
                t("Kurulum yolu konsol kod sayfasıyla yazılamıyor ve kısa (8.3) ") +
                t("yol alınamadı: {path}", path=path)
            ) from exc
    return text.replace("'", "''") if escape_quote else text


def _oem_encoding() -> str:
    """Code page cmd.exe uses to read a batch file on this machine."""
    try:
        import ctypes
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except Exception:
        return "cp1252"


def cleanup_old_installers(keep: Path | None = None) -> int:
    """Remove cached installers other than the one we are about to use."""
    folder = cache_dir()
    if not folder.exists():
        return 0
    removed = 0
    for candidate in folder.glob("NetSonar-v*-Setup.exe"):
        if keep is not None and candidate == keep:
            continue
        try:
            candidate.unlink()
            removed += 1
        except OSError as exc:
            log.warning("Eski kurulum dosyasi silinemedi: %s", exc)
    return removed


def write_install_baton(installer: Path, old_pid: int) -> Path:
    """Run the pending install script: starts the installer once the program exits.

    Order matters: the installer cannot replace the files of a running exe
    ("Access denied"). So the program exits first, the script waits for the
    PID to disappear, then starts the installer silently.

    The PID check uses PowerShell: the `tasklist /FI "PID eq X"` filter is not
    applied on some Windows builds (it "finds" the wrong PID or none at all),
    so that unreliable method is not used.

    The wait tool is Windows' own "timeout" command, called by absolute path:
    on systems with Git-Bash/MSYS "timeout" resolves to the GNU tool, which
    rejects the "/t 1" parameter (the loop never ends).

    After the install the program is restarted; the same path still applies
    because the exe stayed in place. Source mode is not restarted (there the
    program is the Python interpreter anyway).

    Encoding: the script is written in the console OEM code page (cp857 on
    this machine). Fixed ASCII encoding raised UnicodeEncodeError on Turkish
    user names (C:\\Users\\Şükrü\\...) and stopped the update entirely; UTF-8
    is mis-read by cmd.exe. The OEM code page solves both, and characters it
    cannot represent fall back to the 8.3 short path.
    """
    script = installer.parent / "netsonar-install.bat"
    restart = ""
    if getattr(sys, "frozen", False):
        restart = f'start "" "{_ascii_safe_path(Path(sys.executable))}"\r\n'
    script.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        ":wait\r\n"
        # Program kapandi mi? (tasklist /FI filtresi bazi surumlerde
        # uygulanmaz; PowerShell Get-Process guvenilirdir.)
        "powershell -NoProfile -Command \""
        f"if (Get-Process -Id {old_pid} -ErrorAction SilentlyContinue) "
        "{ exit 0 } else { exit 1 }\"\r\n"
        "if not errorlevel 1 ("
        f'"{_ascii_safe_path(WINDOWS_TIMEOUT)}" /t 1 /nobreak >NUL & goto wait)\r\n'
        # The installer runs and is waited on until it FINISHES. The NSIS
        # installer requires admin and is started with "runas". The program
        # is already elevated, so no extra consent dialog appears.
        "powershell -NoProfile -Command \""
        f"Start-Process -FilePath '{_ascii_safe_path(installer, escape_quote=True)}' "
        "-ArgumentList '/S' "
        f"-Verb runas -WindowStyle Hidden -Wait\"\r\n"
        f"{restart}"
        'del "%~f0"\r\n',
        encoding=_oem_encoding(), errors="strict")
    return script


def spawn_install_baton(installer: Path, old_pid: int) -> None:
    """Start the pending install script in the background.

    Program exits -> script waits for the PID to disappear -> installer runs ->
    program restarts. The program does not come back before the install ends.

    PRIVILEGE: the NSIS installer asks for "RequestExecutionLevel admin". Run
    from an unelevated context it stalls on UAC and "start /wait" waits
    forever - the install silently never happens. So the installer in the
    batch file is started with ShellExecute "runas", i.e. elevated (UAC
    prompts). An already elevated context gets no extra prompt.
    """
    script = write_install_baton(installer, old_pid)
    # Yalnizca DETACHED_PROCESS: CREATE_NEW_CONSOLE ile birlikte
    # gecersiz parametre hatasi verir (WinError 87).
    flags = getattr(subprocess, "DETACHED_PROCESS", 0)
    # "call" sart: cmd.exe /c "baton.bat" tek tirnak icinde yol verilince
    # bazen "batch file cannot be found" der; mutlak yol + call guvenli.
    subprocess.Popen(["cmd", "/c", "call", str(script)], creationflags=flags,
                     close_fds=True)
    log.info("install baton armed: pid=%s installer=%s", old_pid, installer)


def run_installer_elevated(installer: Path) -> int:
    """Run the installer elevated (UAC prompts).

    The NSIS installer requires administrator rights. Called directly through
    Popen from an unelevated context it stalls on UAC and the install never
    happens. ShellExecute "runas" solves that.
    """
    if not installer.exists():
        raise UpdateError(t("Kurulum dosyası bulunamadı."))
    import ctypes
    # SW_HIDE: the install runs in the background, no window appears.
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", str(installer), "/S", None, 0)
    # 32 = started successfully; 5 = shell could not start; >32 = error code.
    if result <= 32:
        raise UpdateError(t("Kurulum yetki isteği reddedildi veya başlatılamadı."))
    log.info("elevated installer started: %s (hwnd=%s)", installer, result)
    return result


def write_launcher(exe_path: Path) -> Path:
    """Write the BAT that belongs next to a versioned portable exe.

    Kept for the source-tree launcher contract: the installed product starts
    from Program Files\\NetSonar\\NetSonar.exe, so the shipped BAT is only a
    development convenience. Single-instance guard keyed to this exe's name,
    then start.
    """
    name = exe_path.stem          # NetSonar-v0.5.8
    version = name.split("-v", 1)[1] if "-v" in name else ""
    script = exe_path.with_suffix(".bat")
    script.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        'cd /d "%~dp0"\r\n'
        "rem Tek seferde tek acilis: ikinci tik ayni exe'yi bastan baslatmasin.\r\n"
        f'if "%~1"=="" tasklist /FI "IMAGENAME eq {exe_path.name}" 2>nul '
        f'| findstr /I "{exe_path.name}" >nul && exit /b 0\r\n'
        f'start "NetSonar {version}" "%~dp0{exe_path.name}" %*\r\n',
        encoding="ascii")
    return script


def spawn_swap(old_pid: int, new_exe: Path) -> None:
    """Deprecated: the installed product updates through the installer.

    The install path is fixed now, so a copy-then-swap dance would race the
    installer for the same files. Kept only so old callers fail loudly with
    a clear message instead of silently doing nothing.
    """
    raise UpdateError(t("Kurulum güncellemesi artık kurulum dosyası üzerinden yapılır."))


def last_check_is_old(stamp: str, max_age_seconds: float = 24 * 3600) -> bool:
    """True when the stored ISO stamp is missing or older than the window."""
    import datetime
    if not stamp:
        return True
    try:
        when = datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return True
    age = (datetime.datetime.now() - when.replace(tzinfo=None)).total_seconds()
    return age > max_age_seconds


def now_stamp() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")

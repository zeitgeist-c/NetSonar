"""Self-update over the public NetSonar-Releases GitHub repository.

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

import hashlib
import json
import logging
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RELEASE_REPO = "zeitgeist-c/NetSonar-Releases"
API_LATEST = f"https://api.github.com/repos/{RELEASE_REPO}/releases/latest"
USER_AGENT = "NetSonar/updater"
log = logging.getLogger("NetSonar.Update")

INSTALL_DIR = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NetSonar"
APP_EXE_NAME = "NetSonar.exe"
INSTALLER_TIMEOUT_SECONDS = 900


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
        raise UpdateError(f"Sürüm numarası çözümlenemedi: {text!r}")
    return tuple(int(part) for part in match.groups())


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def installer_asset_name(version: str) -> str:
    """Release asset name for a version: NetSonar-v0.6.0-Setup.exe."""
    return f"NetSonar-v{version}-Setup.exe"


def parse_release(payload: dict) -> UpdateInfo:
    """Pull the installer asset out of a /releases/latest payload.

    Asset names carry the 'v' prefix (NetSonar-v0.6.0-Setup.exe), matching
    the tag and the delivery file naming rule.
    """
    tag = str(payload.get("tag_name") or "")
    version = tag[1:] if tag.startswith("v") else tag
    parse_version(version)  # reject tags we cannot compare against
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
    raise UpdateError(f"Yayının içinde {exe_name} dosyası yok.")


def fetch_latest() -> UpdateInfo:
    request = urllib.request.Request(API_LATEST, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UpdateError("Güncelleme sunucusuna ulaşılamadı.") from exc
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
        raise UpdateError("Güncelleme indirmesi yarıda kesildi.") from exc
    if cancel is not None and cancel.is_set():
        dest.unlink(missing_ok=True)
        raise UpdateError("cancelled")
    if info.size and written != info.size:
        dest.unlink(missing_ok=True)
        raise UpdateError("İndirme dosya tamamlanmadan bitti.")
    if info.sha256:
        actual = _sha256_of(dest)
        if actual.lower() != info.sha256.lower():
            dest.unlink(missing_ok=True)
            raise UpdateError("İndirilen dosyanın sağlama değeri uyuşmuyor.")
    return dest


def cache_dir() -> Path:
    """Downloaded installers live in the user data cache, not in Program Files."""
    from config import user_data_path
    return Path(user_data_path("cache", "updates"))


def install_path(current_exe: Path, version: str) -> Path:
    """Where the installer is downloaded before it runs.

    The cache lives in the user data folder: Program Files is writable only
    by the installer, and the download must not need admin rights.
    """
    return cache_dir() / installer_asset_name(version)


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


def launch_installer(installer: Path, wait: bool = False) -> int:
    """Run the downloaded installer silently over the current install.

    The installer is an NSIS package: `/S` runs it without UI, and it
    replaces the program folder in place. The app must exit before the
    installer can replace its files, so the caller exits first and the
    installer is started detached.
    """
    if not installer.exists():
        raise UpdateError("Kurulum dosyası bulunamadı.")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) if not wait else 0
    process = subprocess.Popen([str(installer), "/S"], creationflags=flags)
    log.info("installer started: %s pid=%s", installer, process.pid)
    return process.pid


def run_installer_and_wait(installer: Path,
                            timeout: float = INSTALLER_TIMEOUT_SECONDS) -> int:
    """Start the installer and block until it finishes; return its exit code."""
    if not installer.exists():
        raise UpdateError("Kurulum dosyası bulunamadı.")
    try:
        completed = subprocess.run([str(installer), "/S"], timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise UpdateError("Kurulum zaman aşımına uğradı.") from exc
    except OSError as exc:
        raise UpdateError("Kurulum başlatılamadı.") from exc
    log.info("installer finished: code=%s", completed.returncode)
    return completed.returncode


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
    raise UpdateError("Kurulum güncellemesi artık kurulum dosyası üzerinden yapılır.")


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

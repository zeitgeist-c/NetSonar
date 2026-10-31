"""NetSonar - persistent model and extra-library store.

Install and update NEVER touch this folder. The store lives outside the
program folder: %LOCALAPPDATA%\\NetSonar\\store. The installer only writes to
its own target folder; user data (settings, database, logs) and the store share
the same parent folder but are not the installer's write target.

Purpose: a local model or extra library downloaded once is not downloaded
again when the program version is updated. Only the new installer is fetched;
the store contents stay as they are.

Layout:
    store/store.json      - manifest (version, sha256, size, date)
    store/models/<name>/  - local model files
    store/lib/<name>/     - extra Python libraries (importable)
"""

from __future__ import annotations
from i18n import t

import datetime
import hashlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path

log = logging.getLogger("NetSonar.Store")

MANIFEST_NAME = "store.json"
MANIFEST_VERSION = 1
MODELS_DIRNAME = "models"
LIB_DIRNAME = "lib"
KIND_MODEL = "model"
KIND_LIB = "lib"


class StoreError(Exception):
    """A store operation must surface a message the user can act on."""


# ─── Konumlar ──────────────────────────────────────────────────────

def store_dir() -> Path:
    """Store root. Independent of the program folder, user-writable."""
    from config import user_data_path
    return Path(user_data_path("store"))


def models_dir() -> Path:
    return store_dir() / MODELS_DIRNAME


def lib_dir() -> Path:
    return store_dir() / LIB_DIRNAME


def manifest_path() -> Path:
    return store_dir() / MANIFEST_NAME


def _kind_dir(kind: str) -> Path:
    if kind == KIND_MODEL:
        return models_dir()
    if kind == KIND_LIB:
        return lib_dir()
    raise StoreError(t("Bilinmeyen depo türü: {kind!r}", kind=kind))


def item_path(name: str, kind: str = KIND_MODEL) -> Path:
    """Full path of a store entry (may be a folder or a file)."""
    safe = _safe_name(name)
    return _kind_dir(kind) / safe


def _safe_name(name: str) -> str:
    """Store entry name: path separators and relative-path escapes are rejected.

    This raises instead of silently cleaning up: if the user typed "a/b",
    producing an unexpected name and then deleting the wrong entry is worse.
    """
    raw = str(name or "").strip()
    if not raw:
        raise StoreError(t("Depo öğesi adı boş olamaz."))
    if "/" in raw or "\\" in raw or ".." in raw:
        raise StoreError(t("Depo öğesi adı yol ayırıcı içeremez: {raw!r}", raw=raw))
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "._-")
    cleaned = cleaned.strip("._-")
    if not cleaned:
        raise StoreError(t("Depo öğesi adı boş olamaz."))
    return cleaned


# ─── Manifest ──────────────────────────────────────────────────────

def load_manifest() -> dict:
    """Read the manifest; a corrupt file loses no data, an empty manifest is returned."""
    path = manifest_path()
    if not path.exists():
        return {"version": MANIFEST_VERSION, "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Store manifest okunamadi, bos sayiliyor: %s", exc)
        return {"version": MANIFEST_VERSION, "items": []}
    if not isinstance(data, dict):
        return {"version": MANIFEST_VERSION, "items": []}
    items = data.get("items")
    data["items"] = [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []
    data.setdefault("version", MANIFEST_VERSION)
    return data


def save_manifest(manifest: dict) -> Path:
    """Write the manifest atomically (no half-written manifest)."""
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "version": int(manifest.get("version", MANIFEST_VERSION)),
        "items": list(manifest.get("items") or []),
    }
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def list_items(kind: str = "") -> list[dict]:
    """Manifest entries; when kind is given, only that kind."""
    items = load_manifest().get("items", [])
    if kind:
        items = [i for i in items if i.get("kind") == kind]
    return sorted(items, key=lambda i: str(i.get("name", "")))


def find_item(name: str) -> dict | None:
    target = _safe_name(name)
    for item in list_items():
        if str(item.get("name", "")) == target:
            return item
    return None


# ─── Entry install / removal ───────────────────────────────────────

def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_tree(root: Path) -> str:
    """Stable content digest for a folder (file paths + their hashes)."""
    digest = hashlib.sha256()
    if root.is_file():
        digest.update(root.name.encode("utf-8"))
        digest.update(_sha256_of(root).encode("ascii"))
        return digest.hexdigest()
    for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(file_path.relative_to(root)).encode("utf-8"))
        digest.update(_sha256_of(file_path).encode("ascii"))
    return digest.hexdigest()


def _tree_size(root: Path) -> int:
    if root.is_file():
        return root.stat().st_size
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def install_item(name: str, source: str | os.PathLike, kind: str = KIND_MODEL,
                 version: str = "") -> dict:
    """Copy a new model/library into the store and update the manifest.

    The source may be an external file or folder. It replaces an existing
    entry; the store contents survive install and update.
    """
    source_path = Path(source)
    if not source_path.exists():
        raise StoreError(t("Kaynak bulunamadı: {source_path}", source_path=source_path))
    safe = _safe_name(name)
    target = item_path(safe, kind)
    target.parent.mkdir(parents=True, exist_ok=True)

    staging = target.with_name(target.name + ".incoming")
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    try:
        if source_path.is_dir():
            shutil.copytree(source_path, staging)
        else:
            staging.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, staging)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)
        os.replace(staging, target)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise StoreError(t("Depoya kopyalanamadı: {exc}", exc=exc)) from exc

    record = {
        "name": safe,
        "kind": kind,
        "version": str(version or ""),
        "sha256": _hash_tree(target),
        "size": _tree_size(target),
        "path": str(target.relative_to(store_dir())),
        "installed_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    manifest = load_manifest()
    items = [i for i in manifest.get("items", [])
             if not (i.get("name") == safe and i.get("kind") == kind)]
    items.append(record)
    manifest["items"] = items
    save_manifest(manifest)
    return record


def remove_item(name: str, kind: str = KIND_MODEL) -> bool:
    """Delete an entry from the store. Returns False when it is not found."""
    safe = _safe_name(name)
    target = item_path(safe, kind)
    manifest = load_manifest()
    items = list(manifest.get("items", []))
    kept = [i for i in items if not (i.get("name") == safe and i.get("kind") == kind)]
    existed = len(kept) != len(items) or target.exists()
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    elif target.exists():
        target.unlink(missing_ok=True)
    manifest["items"] = kept
    save_manifest(manifest)
    return existed


# ─── Runtime ───────────────────────────────────────────────────────

def activate() -> list[str]:
    """Append the lib directory to the path so extra libraries can be imported.

    Bundled libraries take precedence: the store lib directory is appended to
    the end of sys.path, so on a name clash the bundled version wins.
    """
    added: list[str] = []
    for candidate in (lib_dir(), models_dir()):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("Store dizini olusturulamadi: %s", exc)
            continue
        text = str(candidate)
        if text not in sys.path:
            sys.path.append(text)
            added.append(text)
    return added


def is_store_path(path: str | os.PathLike) -> bool:
    """Is the given path inside the store? Used for install/update protection."""
    try:
        target = Path(path).resolve()
        root = store_dir().resolve()
    except (OSError, ValueError):
        return False
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def store_size() -> int:
    """Total bytes in the store (shown in Settings)."""
    root = store_dir()
    if not root.exists():
        return 0
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def summary() -> dict:
    """Short status summary: model count, library count, total size."""
    items = list_items()
    return {
        "path": str(store_dir()),
        "models": sum(1 for i in items if i.get("kind") == KIND_MODEL),
        "libs": sum(1 for i in items if i.get("kind") == KIND_LIB),
        "size": store_size(),
    }

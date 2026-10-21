"""NetSonar — Kalıcı model ve ek kütüphane deposu (store).

Kurulum ve güncelleme bu klasöre ASLA dokunmaz. Depo program klasörünün
dışındadır: %LOCALAPPDATA%\\NetSonar\\store. Kurulumcu yalnız kendi hedef
klasörüne yazar; kullanıcı verisi (ayarlar, veritabanı, log) ve store aynı
üst klasörde tutulur ama kurulumcunun yazma hedefi değildir.

Amacı: bir kez indirilen yerel model veya ek kütüphane, program sürümü
güncellendiğinde yeniden indirilmez. Yalnızca yeni kurulum dosyası indirilir;
store içeriği olduğu gibi kalır.

Düzen:
    store/store.json      — manifest (sürüm, sha256, boyut, tarih)
    store/models/<ad>/    — yerel model dosyaları
    store/lib/<ad>/       — ek Python kütüphaneleri (import edilebilir)
"""

from __future__ import annotations

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
    """Depo işlemi kullanıcıya anlamlı bir hata mesajıyla dönmeli."""


# ─── Konumlar ──────────────────────────────────────────────────────

def store_dir() -> Path:
    """Depo kökü. Program klasöründen bağımsız, kullanıcı yazılabilir."""
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
    raise StoreError(f"Bilinmeyen depo türü: {kind!r}")


def item_path(name: str, kind: str = KIND_MODEL) -> Path:
    """Bir depo öğesinin tam yolu (klasör veya dosya olabilir)."""
    safe = _safe_name(name)
    return _kind_dir(kind) / safe


def _safe_name(name: str) -> str:
    """Depo öğesi adı: yol ayırıcı ve göreli yol kaçışı engellenir.

    Sessizce temizlemek yerine hata verilir: kullanıcı "a/b" yazdıysa
    beklenmedik bir ad üretmek, sonra yanlış öğeyi silmekten iyidir.
    """
    raw = str(name or "").strip()
    if not raw:
        raise StoreError("Depo öğesi adı boş olamaz.")
    if "/" in raw or "\\" in raw or ".." in raw:
        raise StoreError(f"Depo öğesi adı yol ayırıcı içeremez: {raw!r}")
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "._-")
    cleaned = cleaned.strip("._-")
    if not cleaned:
        raise StoreError("Depo öğesi adı boş olamaz.")
    return cleaned


# ─── Manifest ──────────────────────────────────────────────────────

def load_manifest() -> dict:
    """Manifesti okur; bozuk dosyada veri kaybı olmaz, boş manifest döner."""
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
    """Manifesti atomik olarak yazar (yarım yazılmış manifest olmaz)."""
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
    """Manifest girdileri; kind verilirse yalnız o tür."""
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


# ─── Öğe kurulumu / kaldırma ───────────────────────────────────────

def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_tree(root: Path) -> str:
    """Klasör için kararlı içerik özeti (dosya yolları + hash'leri)."""
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
    """Depoya yeni bir model/kütüphane kopyalar ve manifesti günceller.

    Kaynak dışarıdan gelen bir dosya ya da klasör olabilir. Mevcut bir öğeyi
    değiştirir; kurulum ve güncelleme sırasında store içeriği korunur.
    """
    source_path = Path(source)
    if not source_path.exists():
        raise StoreError(f"Kaynak bulunamadı: {source_path}")
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
        raise StoreError(f"Depoya kopyalanamadı: {exc}") from exc

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
    """Depodan bir öğeyi siler. Bulunamazsa False döner."""
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


# ─── Çalışma zamanı ────────────────────────────────────────────────

def activate() -> list[str]:
    """Ek kütüphanelerin import edilebilmesi için lib dizinini yola ekler.

    Paketlenmiş kütüphaneler önceliklidir: store lib dizini sys.path'un sonuna
    eklenir, böylece ad çakışmasında paket içi sürüm kazanır.
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
    """Verilen yol depo içinde mi? Kurulum/güncelleme koruması için."""
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
    """Depodaki toplam bayt (Ayarlar'da göstermek için)."""
    root = store_dir()
    if not root.exists():
        return 0
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def summary() -> dict:
    """Kısa durum özeti: model sayısı, kütüphane sayısı, toplam boyut."""
    items = list_items()
    return {
        "path": str(store_dir()),
        "models": sum(1 for i in items if i.get("kind") == KIND_MODEL),
        "libs": sum(1 for i in items if i.get("kind") == KIND_LIB),
        "size": store_size(),
    }

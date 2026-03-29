"""
NetSonar — Arka Plan DNS Cozumleyici
IP adreslerini domain adina donusturur. Sonuclar onbelleklenir,
cozumleme arka plan thread'inde yapilir (UI'i bloklamaz).
"""

import socket
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="dns")
_cache: dict[str, str] = {}

# Yerel IP'leri hemen etiketle
_LOCAL_PREFIXES = ("192.168.", "10.", "127.", "0.0.0.0")


def _is_private_ip(ip: str) -> bool:
    if ip.startswith("127.") or ip == "0.0.0.0":
        return True
    if ip.startswith("192.168.") or ip.startswith("10."):
        return True
    if ip.startswith("172."):
        second = ip.split(".")[1]
        try:
            return 16 <= int(second) <= 31
        except ValueError:
            return False
    return False


def resolve(ip: str) -> str:
    """
    IP icin domain adini dondurur.
    Ilk cagrida '...' doner ve arka planda cozumleme baslatir.
    Sonraki cagrilarda cache'den okur.
    """
    if not ip:
        return ""

    if ip in _cache:
        return _cache[ip]

    # Yerel IP'leri hemen isaretle
    if _is_private_ip(ip):
        _cache[ip] = "Yerel Ag"
        return "Yerel Ag"

    # Cozumleme henuz baslamadi — basalt
    _cache[ip] = "..."
    _executor.submit(lambda i=ip: _do_resolve(i))
    return "..."


def _do_resolve(ip: str):
    """Thread icinde DNS sorgusu yapar."""
    try:
        host = socket.gethostbyaddr(ip)[0]
        # Cok uzun host'lari kisalt (son 3 bolum)
        parts = host.split(".")
        if len(parts) > 3:
            host = ".".join(parts[-3:])
        _cache[ip] = host
    except Exception:
        _cache[ip] = ip     # Cozumlenemezse IP'yi goster

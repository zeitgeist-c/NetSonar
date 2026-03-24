"""
AgTara — VirusTotal Tehdit İstihbaratı
Bir IP adresinin VirusTotal veritabanındaki itibarını sorgular.
Ücretsiz plan: dakikada 4 istek, günde 500 istek.
"""

import time
import requests
from functools import lru_cache
from config import VIRUSTOTAL_API_KEY, VT_MALICIOUS_THRESHOLD

VT_URL = "https://www.virustotal.com/api/v3/ip_addresses/{ip}"
HEADERS = {"x-apikey": VIRUSTOTAL_API_KEY}

# Son istek zamanını takip et (rate limiting: dakikada 4)
_last_request_time = 0.0
_MIN_INTERVAL = 15.1  # saniye (4 istek/dk sınırı için güvenli aralık)


def _rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


@lru_cache(maxsize=512)
def check_ip(ip: str) -> dict:
    """
    Bir IP'nin VirusTotal sonucunu döndürür.
    Sonuç önbelleklenir — aynı IP tekrar sorgulanmaz.

    Returns:
        {
            "ip": str,
            "malicious": int,      # kötü niyetli diyen motor sayısı
            "suspicious": int,
            "harmless": int,
            "country": str,
            "is_threat": bool,     # VT_MALICIOUS_THRESHOLD üzerindeyse True
            "error": str | None
        }
    """
    # Özel / yerel IP'leri atla
    if _is_private(ip):
        return _safe_result(ip, note="Yerel/özel ağ — VT sorgusu yapılmadı")

    _rate_limit()
    try:
        resp = requests.get(VT_URL.format(ip=ip), headers=HEADERS, timeout=10)
        if resp.status_code == 404:
            return _safe_result(ip, note="VT'de kayıt yok")
        resp.raise_for_status()

        data = resp.json()["data"]["attributes"]
        stats = data.get("last_analysis_stats", {})
        malicious  = stats.get("malicious",  0)
        suspicious = stats.get("suspicious", 0)
        harmless   = stats.get("harmless",   0)
        country    = data.get("country", "?")

        return {
            "ip":         ip,
            "malicious":  malicious,
            "suspicious": suspicious,
            "harmless":   harmless,
            "country":    country,
            "is_threat":  malicious >= VT_MALICIOUS_THRESHOLD,
            "error":      None,
        }

    except Exception as exc:
        return {
            "ip":        ip,
            "malicious": 0, "suspicious": 0, "harmless": 0,
            "country":   "?",
            "is_threat": False,
            "error":     str(exc),
        }


def bulk_check(ip_list: list[str]) -> list[dict]:
    """Birden fazla IP'yi sıralı olarak sorgular (rate limit'e uyar)."""
    results = []
    for ip in ip_list:
        result = check_ip(ip)
        results.append(result)
        if result.get("error") is None:
            print(
                f"[VT] {ip:<18} | Kötü:{result['malicious']:>2} "
                f"Şüpheli:{result['suspicious']:>2} "
                f"Ülke:{result['country']} "
                f"{'⚠️ TEHDİT' if result['is_threat'] else '✓ Temiz'}"
            )
    return results


# ─── Yardımcılar ──────────────────────────────────────────────────────
def _safe_result(ip: str, note: str = "") -> dict:
    return {
        "ip": ip, "malicious": 0, "suspicious": 0,
        "harmless": 0, "country": "Local",
        "is_threat": False, "error": note,
    }


def _is_private(ip: str) -> bool:
    return (
        ip.startswith("192.168.") or
        ip.startswith("10.")       or
        ip.startswith("172.16.")   or
        ip.startswith("172.17.")   or
        ip.startswith("172.18.")   or
        ip.startswith("172.19.")   or
        ip.startswith("172.2")     or
        ip.startswith("172.3")     or
        ip.startswith("127.")      or
        ip == "0.0.0.0"
    )

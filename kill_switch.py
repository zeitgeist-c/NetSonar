"""NetSonar kill switch modülü.

Şüpheli IP adreslerini Windows Güvenlik Duvarı kurallarıyla engeller ve kaldırır.
netsh komutlarının çalışması için yönetici yetkisi gereklidir.
"""

from __future__ import annotations

import logging
import subprocess

from database import Database
from ip_utils import ip_to_rule_token, is_valid_ip, normalized_ip, rule_token_to_ip

log = logging.getLogger("NetSonar.KillSwitch")

RULE_PREFIX = "NetSonar_BLOCK_"


def _run(cmd: list[str]) -> tuple[bool, str]:
    """Bir netsh komutu çalıştırır ve (başarılı, çıktı) döndürür."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="cp1254",
            errors="replace",
            timeout=10,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as exc:
        return False, str(exc)


def _rule_base_for_ip(ip: str) -> tuple[str | None, str | None]:
    normalized = normalized_ip(ip)
    token = ip_to_rule_token(ip)
    if not normalized or not token:
        return None, None
    return normalized, f"{RULE_PREFIX}{token}"


def _legacy_rule_token_to_ip(token: str) -> str | None:
    if token.startswith("ipv6_"):
        return normalized_ip(token.replace("ipv6_", "").replace("__", "::").replace("_", ":"))
    return normalized_ip(token.replace("_", "."))


def block_ip(ip: str, reason: str = "NetSonar tarafindan engellendi", db: Database = None) -> bool:
    """Block all inbound and outbound traffic for one IPv4 or IPv6 address."""
    normalized, rule_base = _rule_base_for_ip(ip)
    if not normalized or not rule_base:
        log.warning("Geçersiz IP: %s", ip)
        return False

    success = True
    for direction in ("out", "in"):
        ok, output = _run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_base}_{direction}",
            f"dir={direction}",
            "action=block",
            f"remoteip={normalized}",
            "enable=yes",
            "profile=any",
        ])
        if not ok:
            log.error("Kural oluşturulamadı (%s): %s", direction, output.strip())
            success = False
        else:
            log.info("%s engellendi (%s)", normalized, direction)

    if success and db:
        db.add_blocked_ip(normalized, reason)

    return success


def unblock_ip(ip: str) -> bool:
    """Bir IPv4 veya IPv6 adresi için NetSonar güvenlik duvarı kurallarını kaldırır."""
    normalized, rule_base = _rule_base_for_ip(ip)
    if not normalized or not rule_base:
        log.warning("Geçersiz IP: %s", ip)
        return False

    success = True
    for direction in ("out", "in"):
        ok, output = _run([
            "netsh", "advfirewall", "firewall", "delete", "rule",
            f"name={rule_base}_{direction}",
        ])
        if not ok:
            log.warning("Kural kaldırılamadı (%s/%s): %s", normalized, direction, output.strip())
            success = False
        else:
            log.info("%s engeli kaldırıldı (%s)", normalized, direction)

    return success


def list_blocked() -> list[str]:
    """NetSonar güvenlik duvarı kurallarıyla engellenmiş IP adreslerini listeler."""
    ok, output = _run([
        "netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_PREFIX}*"
    ])
    if not ok:
        return []

    blocked = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Kural Adi:") or stripped.startswith("Kural Adı:") or stripped.startswith("Rule Name:"):
            rule_name = line.split(":", 1)[1].strip()
            token = rule_name.replace(RULE_PREFIX, "").replace("_out", "").replace("_in", "")
            ip = rule_token_to_ip(token) or _legacy_rule_token_to_ip(token)
            if ip and ip not in blocked:
                blocked.append(ip)
    return blocked


def _is_valid_ip(ip: str) -> bool:
    return is_valid_ip(ip)

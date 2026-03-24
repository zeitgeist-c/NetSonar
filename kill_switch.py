"""
AgTara — Kill-Switch Modülü
Windows Güvenlik Duvarı kuralları ile şüpheli IP'leri anında engeller/kaldırır.
UYARI: Yönetici (Administrator) yetkileri gerektirir.
"""

import subprocess
import re
from database import Database

RULE_PREFIX = "AgTara_BLOCK_"


def _run(cmd: list[str]) -> tuple[bool, str]:
    """netsh komutunu çalıştırır, (başarı, çıktı) döndürür."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="cp1254",   # Windows Türkçe kod sayfası
            timeout=10,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as exc:
        return False, str(exc)


def block_ip(ip: str, reason: str = "AgTara tarafından engellendi", db: Database = None) -> bool:
    """
    Belirli bir IP'ye giden tüm trafiği Windows Güvenlik Duvarı ile engeller.
    Hem giden (out) hem gelen (in) yönde kural oluşturur.
    """
    if not _is_valid_ip(ip):
        print(f"[KillSwitch] Geçersiz IP: {ip}")
        return False

    rule_name = f"{RULE_PREFIX}{ip.replace('.', '_')}"
    success = True

    for direction in ("out", "in"):
        ok, output = _run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}_{direction}",
            f"dir={direction}",
            "action=block",
            f"remoteip={ip}",
            "enable=yes",
            "profile=any",
        ])
        if not ok:
            print(f"[KillSwitch] ❌ Gelen kural oluşturulamadı ({direction}): {output.strip()}")
            success = False
        else:
            print(f"[KillSwitch] ✅ {ip} engellendi ({direction})")

    if success and db:
        db.add_blocked_ip(ip, reason)

    return success


def unblock_ip(ip: str) -> bool:
    """Belirli bir IP için oluşturulan güvenlik duvarı kurallarını kaldırır."""
    rule_base = f"{RULE_PREFIX}{ip.replace('.', '_')}"
    success = True

    for direction in ("out", "in"):
        ok, output = _run([
            "netsh", "advfirewall", "firewall", "delete", "rule",
            f"name={rule_base}_{direction}",
        ])
        if not ok:
            print(f"[KillSwitch] Kural kaldırılamadı ({ip}/{direction}): {output.strip()}")
            success = False
        else:
            print(f"[KillSwitch] 🔓 {ip} engeli kaldırıldı ({direction})")

    return success


def list_blocked() -> list[str]:
    """AgTara tarafından oluşturulan tüm engelleme kurallarını listeler."""
    ok, output = _run([
        "netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_PREFIX}*"
    ])
    if not ok:
        return []
    # Kural adlarını parse et
    blocked = []
    for line in output.splitlines():
        if line.strip().startswith("Kural Adı:") or line.strip().startswith("Rule Name:"):
            rule_name = line.split(":", 1)[1].strip()
            # IP'yi kural adından geri çıkar
            ip_part = rule_name.replace(RULE_PREFIX, "").replace("_out", "").replace("_in", "")
            ip = ip_part.replace("_", ".")
            if _is_valid_ip(ip) and ip not in blocked:
                blocked.append(ip)
    return blocked


def _is_valid_ip(ip: str) -> bool:
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    parts = ip.split(".")
    return all(0 <= int(p) <= 255 for p in parts)

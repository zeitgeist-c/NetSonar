"""
NetSonar — Özel Uyarı Kuralları
Belirli IP veya portlar için otomatik bildirim oluşturur.
"""

import json
import threading
import ipaddress
from pathlib import Path
from config import user_data_path


ALERTS_FILE = Path(user_data_path("netsonar_data", "custom_alerts.json"))


class AlertRule:
    def __init__(self, name: str, ip_pattern: str = None, port: int = None, 
                 process: str = None, enabled: bool = True, allow_auto_block: bool = False):
        self.name = name
        self.ip_pattern = ip_pattern  # None = her IP, "192.168.*" = wildcard
        self.port = port              # None = her port
        self.process = process        # None = her süreç
        self.enabled = enabled
        self.allow_auto_block = bool(allow_auto_block)

    def matches(self, dst_ip: str, dst_port: int, process: str) -> bool:
        if not self.enabled:
            return False
        
        # IP kontrolü
        if self.ip_pattern:
            if not self._match_pattern(dst_ip, self.ip_pattern):
                return False
        
        # Port kontrolü
        if self.port is not None and dst_port != self.port:
            return False
        
        # Süreç kontrolü
        if self.process and self.process.lower() not in process.lower():
            return False
        
        return True

    def _match_pattern(self, ip: str, pattern: str) -> bool:
        """Wildcard IP eşleştirme (örn. 192.168.*.1)."""
        parts = ip.split(".")
        pattern_parts = pattern.split(".")
        if len(parts) != len(pattern_parts):
            return False
        for i, p in enumerate(pattern_parts):
            if p == "*":
                continue
            if p != parts[i]:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ip_pattern": self.ip_pattern,
            "port": self.port,
            "process": self.process,
            "enabled": self.enabled,
            "allow_auto_block": self.allow_auto_block,
        }

    @staticmethod
    def from_dict(data: dict) -> "AlertRule":
        name = str(data.get("name", "")).strip()[:100]
        if not name:
            raise ValueError("Alert rule name is required")
        port = data.get("port")
        if port is not None:
            port = int(port)
            if not 0 <= port <= 65535:
                raise ValueError("Invalid alert rule port")
        pattern = data.get("ip_pattern")
        if pattern:
            pattern = str(pattern).strip()
            if "*" in pattern:
                parts = pattern.split(".")
                if len(parts) != 4 or any(
                    part != "*" and (not part.isdigit() or not 0 <= int(part) <= 255)
                    for part in parts
                ):
                    raise ValueError("Invalid IPv4 wildcard pattern")
            else:
                ipaddress.ip_address(pattern)
        return AlertRule(
            name=name,
            ip_pattern=pattern,
            port=port,
            process=data.get("process"),
            enabled=data.get("enabled", True),
            allow_auto_block=data.get("allow_auto_block", False),
        )


_cache_lock = threading.Lock()
_cached_rules: list[AlertRule] = []
_cached_mtime_ns: int | None = None


def load_alerts() -> list[AlertRule]:
    """Kayıtlı uyarı kurallarını yükle."""
    global _cached_rules, _cached_mtime_ns
    if not ALERTS_FILE.exists():
        with _cache_lock:
            _cached_rules, _cached_mtime_ns = [], None
        return []
    try:
        mtime = ALERTS_FILE.stat().st_mtime_ns
        with _cache_lock:
            if _cached_mtime_ns == mtime:
                return list(_cached_rules)
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            rules = [AlertRule.from_dict(d) for d in data if isinstance(d, dict) and d.get("name")]
        with _cache_lock:
            _cached_rules, _cached_mtime_ns = rules, mtime
        return list(rules)
    except Exception:
        return []


def save_alerts(rules: list[AlertRule]):
    """Uyarı kurallarını kaydet."""
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in rules], f, ensure_ascii=False, indent=2)
    global _cached_rules, _cached_mtime_ns
    with _cache_lock:
        _cached_rules = list(rules)
        _cached_mtime_ns = ALERTS_FILE.stat().st_mtime_ns


def check_connection_alerts(dst_ip: str, dst_port: int, process: str) -> list[AlertRule]:
    """Bağlantı için eşleşen uyarı kurallarını döndür."""
    rules = load_alerts()
    matches = []
    for rule in rules:
        if rule.matches(dst_ip, dst_port, process):
            matches.append(rule)
    return matches

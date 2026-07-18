"""
NetSonar — Özel Uyarı Kuralları
Belirli IP veya portlar için otomatik bildirim oluşturur.
"""

import json
from pathlib import Path
from typing import Optional
from config import user_data_path


ALERTS_FILE = Path(user_data_path("netsonar_data", "custom_alerts.json"))


class AlertRule:
    def __init__(self, name: str, ip_pattern: str = None, port: int = None, 
                 process: str = None, enabled: bool = True):
        self.name = name
        self.ip_pattern = ip_pattern  # None = her IP, "192.168.*" = wildcard
        self.port = port              # None = her port
        self.process = process        # None = her süreç
        self.enabled = enabled

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
        }

    @staticmethod
    def from_dict(data: dict) -> "AlertRule":
        return AlertRule(
            name=data.get("name", ""),
            ip_pattern=data.get("ip_pattern"),
            port=data.get("port"),
            process=data.get("process"),
            enabled=data.get("enabled", True),
        )


def load_alerts() -> list[AlertRule]:
    """Kayıtlı uyarı kurallarını yükle."""
    if not ALERTS_FILE.exists():
        return []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [AlertRule.from_dict(d) for d in data]
    except Exception:
        return []


def save_alerts(rules: list[AlertRule]):
    """Uyarı kurallarını kaydet."""
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in rules], f, ensure_ascii=False, indent=2)


def check_connection_alerts(dst_ip: str, dst_port: int, process: str) -> list[AlertRule]:
    """Bağlantı için eşleşen uyarı kurallarını döndür."""
    rules = load_alerts()
    matches = []
    for rule in rules:
        if rule.matches(dst_ip, dst_port, process):
            matches.append(rule)
    return matches

"""Atomic NetSonar-owned Windows Firewall rule management."""

from __future__ import annotations

import json
import logging
import subprocess

from database import Database
from ip_utils import ip_to_rule_token, normalized_ip, rule_token_to_ip

log = logging.getLogger("NetSonar.KillSwitch")
RULE_PREFIX = "NetSonar_BLOCK_"
RULE_GROUP = "NetSonar"


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=15)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as exc:
        return False, str(exc)


def _rule_base_for_ip(ip: str) -> tuple[str | None, str | None]:
    value, token = normalized_ip(ip), ip_to_rule_token(ip)
    return (value, f"{RULE_PREFIX}{token}") if value and token else (None, None)


def _add_rule(ip: str, rule_base: str, direction: str) -> tuple[bool, str]:
    return _run(["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule_base}_{direction}", f"dir={direction}", "action=block",
                 f"remoteip={ip}", "enable=yes", "profile=any", f"group={RULE_GROUP}"])


def _delete_rule(rule_base: str, direction: str) -> tuple[bool, str]:
    return _run(["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={rule_base}_{direction}"])


def block_ip(ip: str, reason: str = "NetSonar block", db: Database | None = None) -> bool:
    value, rule_base = _rule_base_for_ip(ip)
    if not value or not rule_base:
        return False
    added: list[str] = []
    for direction in ("out", "in"):
        ok, output = _add_rule(value, rule_base, direction)
        if not ok:
            log.error("Firewall add failed (%s): %s", direction, output.strip())
            for previous in reversed(added):
                _delete_rule(rule_base, previous)
            return False
        added.append(direction)
    if db:
        db.add_blocked_ip(value, reason)
    return True


def unblock_ip(ip: str, db: Database | None = None) -> bool:
    value, rule_base = _rule_base_for_ip(ip)
    if not value or not rule_base:
        return False
    deleted: list[str] = []
    for direction in ("out", "in"):
        ok, output = _delete_rule(rule_base, direction)
        if not ok:
            log.error("Firewall delete failed (%s): %s", direction, output.strip())
            for previous in deleted:
                _add_rule(value, rule_base, previous)
            return False
        deleted.append(direction)
    if db:
        db.remove_blocked_ip(value)
    return True


def _token_to_ip(token: str) -> str | None:
    return rule_token_to_ip(token)


def _query_blocked() -> tuple[bool, list[str]]:
    """Query complete in/out NetSonar rule pairs without wildcard netsh parsing."""
    script = (
        "Get-NetFirewallRule -DisplayGroup 'NetSonar' -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty DisplayName | ConvertTo-Json -Compress"
    )
    ok, output = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    if not ok or not output.strip():
        return ok, []
    try:
        names = json.loads(output.strip())
        if isinstance(names, str):
            names = [names]
    except json.JSONDecodeError:
        return False, []
    directions: dict[str, set[str]] = {}
    for name in names if isinstance(names, list) else []:
        if not isinstance(name, str) or not name.startswith(RULE_PREFIX):
            continue
        direction = "out" if name.endswith("_out") else "in" if name.endswith("_in") else None
        if direction:
            token = name[len(RULE_PREFIX):-len(direction)-1]
            directions.setdefault(token, set()).add(direction)
    return True, sorted(filter(None, (
        _token_to_ip(token) for token, values in directions.items() if values == {"in", "out"}
    )))


def list_blocked() -> list[str]:
    return _query_blocked()[1]


def reconcile_firewall(db: Database) -> dict:
    """Make the database reflect complete NetSonar rule pairs at startup."""
    queried, values = _query_blocked()
    if not queried:
        log.warning("Firewall reconciliation skipped because rule query failed")
        return {"added": 0, "removed": 0, "total": len(db.get_blocked_ips()), "skipped": True}
    actual = set(values)
    recorded = {row["ip"] for row in db.get_blocked_ips()}
    for ip in recorded - actual:
        db.remove_blocked_ip(ip)
    for ip in actual - recorded:
        db.add_blocked_ip(ip, "Firewall startup reconciliation")
    return {"added": len(actual - recorded), "removed": len(recorded - actual),
            "total": len(actual)}


def remove_all_netsonar_rules() -> bool:
    """Delete only rules in the NetSonar display group."""
    script = (
        "$rules = @(Get-NetFirewallRule -DisplayGroup 'NetSonar' "
        "-ErrorAction SilentlyContinue); "
        "if ($rules.Count -gt 0) { "
        "$rules | Remove-NetFirewallRule -ErrorAction Stop }"
    )
    ok, output = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    if not ok:
        log.error("NetSonar firewall cleanup failed: %s", output.strip())
    return ok



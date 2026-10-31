"""Shared IP address helpers for NetSonar."""

from __future__ import annotations
from i18n import t

import base64
import ipaddress


RULE_SAFE_PREFIX = "b64_"


def parse_ip(ip: str):
    """Return an ipaddress object, or None for invalid input."""
    if not ip:
        return None
    try:
        return ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return None


def is_valid_ip(ip: str) -> bool:
    return parse_ip(ip) is not None


def normalized_ip(ip: str) -> str | None:
    parsed = parse_ip(ip)
    return str(parsed) if parsed else None


def is_local_ip(ip: str) -> bool:
    parsed = parse_ip(ip)
    if parsed is None:
        return False
    return (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_unspecified
    )


def ip_to_rule_token(ip: str) -> str | None:
    value = normalized_ip(ip)
    if value is None:
        return None
    encoded = base64.urlsafe_b64encode(value.encode("ascii")).decode("ascii").rstrip("=")
    return f"{RULE_SAFE_PREFIX}{encoded}"


def rule_token_to_ip(token: str) -> str | None:
    if not token.startswith(RULE_SAFE_PREFIX):
        return None
    raw = token[len(RULE_SAFE_PREFIX):]
    raw += "=" * (-len(raw) % 4)
    try:
        return normalized_ip(base64.urlsafe_b64decode(raw.encode("ascii")).decode("ascii"))
    except Exception:
        return None

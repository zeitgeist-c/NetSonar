"""Shared IP address helpers for NetSonar."""

from __future__ import annotations

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


def sql_public_dst_filter(column: str = "dst_ip") -> str:
    """SQLite expression that keeps only public destination IPs.

    SQLite has no native IP type, so this mirrors the Python helper with
    prefix checks for the private/link-local ranges NetSonar stores.
    """
    return f"""
        {column} IS NOT NULL
        AND {column} NOT LIKE '192.168.%'
        AND {column} NOT LIKE '10.%'
        AND {column} NOT LIKE '172.16.%'
        AND {column} NOT LIKE '172.17.%'
        AND {column} NOT LIKE '172.18.%'
        AND {column} NOT LIKE '172.19.%'
        AND {column} NOT LIKE '172.20.%'
        AND {column} NOT LIKE '172.21.%'
        AND {column} NOT LIKE '172.22.%'
        AND {column} NOT LIKE '172.23.%'
        AND {column} NOT LIKE '172.24.%'
        AND {column} NOT LIKE '172.25.%'
        AND {column} NOT LIKE '172.26.%'
        AND {column} NOT LIKE '172.27.%'
        AND {column} NOT LIKE '172.28.%'
        AND {column} NOT LIKE '172.29.%'
        AND {column} NOT LIKE '172.30.%'
        AND {column} NOT LIKE '172.31.%'
        AND {column} NOT LIKE '127.%'
        AND {column} NOT LIKE '169.254.%'
        AND {column} NOT LIKE '0.%'
        AND {column} NOT LIKE '224.%'
        AND {column} NOT LIKE '225.%'
        AND {column} NOT LIKE '226.%'
        AND {column} NOT LIKE '227.%'
        AND {column} NOT LIKE '228.%'
        AND {column} NOT LIKE '229.%'
        AND {column} NOT LIKE '23_.%'
        AND lower({column}) NOT LIKE 'fe8%'
        AND lower({column}) NOT LIKE 'fe9%'
        AND lower({column}) NOT LIKE 'fea%'
        AND lower({column}) NOT LIKE 'feb%'
        AND lower({column}) NOT LIKE 'fc%'
        AND lower({column}) NOT LIKE 'fd%'
        AND {column} != '::1'
        AND {column} != '::'
    """


def sql_local_src_expr(column: str = "src_ip") -> str:
    return f"""
        {column} LIKE '192.168.%'
        OR {column} LIKE '10.%'
        OR {column} LIKE '172.16.%'
        OR {column} LIKE '172.17.%'
        OR {column} LIKE '172.18.%'
        OR {column} LIKE '172.19.%'
        OR {column} LIKE '172.20.%'
        OR {column} LIKE '172.21.%'
        OR {column} LIKE '172.22.%'
        OR {column} LIKE '172.23.%'
        OR {column} LIKE '172.24.%'
        OR {column} LIKE '172.25.%'
        OR {column} LIKE '172.26.%'
        OR {column} LIKE '172.27.%'
        OR {column} LIKE '172.28.%'
        OR {column} LIKE '172.29.%'
        OR {column} LIKE '172.30.%'
        OR {column} LIKE '172.31.%'
        OR {column} LIKE '127.%'
        OR {column} LIKE '169.254.%'
        OR {column} LIKE '0.%'
        OR {column} LIKE '224.%'
        OR {column} LIKE '225.%'
        OR {column} LIKE '226.%'
        OR {column} LIKE '227.%'
        OR {column} LIKE '228.%'
        OR {column} LIKE '229.%'
        OR {column} LIKE '23_.%'
        OR lower({column}) LIKE 'fe8%'
        OR lower({column}) LIKE 'fe9%'
        OR lower({column}) LIKE 'fea%'
        OR lower({column}) LIKE 'feb%'
        OR lower({column}) LIKE 'fc%'
        OR lower({column}) LIKE 'fd%'
        OR {column} = '::1'
        OR {column} = '::'
    """


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

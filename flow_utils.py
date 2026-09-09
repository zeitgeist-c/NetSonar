"""Dependency-free IP normalization and flow direction helpers."""

import ipaddress


def normalize_ip(value: str) -> str | None:
    try:
        return str(ipaddress.ip_address(str(value).split("%", 1)[0]))
    except ValueError:
        return None


def orient_flow(src_ip: str, src_port: int, dst_ip: str, dst_port: int,
                local_ips: set[str], broadcast_ips: set[str] | None = None) -> dict | None:
    """Map a packet to local/remote endpoints; reject irrelevant traffic."""
    src, dst = normalize_ip(src_ip), normalize_ip(dst_ip)
    locals_normalized = {normalize_ip(value) for value in local_ips}
    locals_normalized.discard(None)
    if not src or not dst:
        return None
    addresses = (ipaddress.ip_address(src), ipaddress.ip_address(dst))
    if any(value.is_unspecified or value.is_multicast for value in addresses):
        return None
    broadcasts = {normalize_ip(value) for value in (broadcast_ips or set())}
    if src == "255.255.255.255" or dst == "255.255.255.255" or src in broadcasts or dst in broadcasts:
        return None
    src_local, dst_local = src in locals_normalized, dst in locals_normalized
    if src_local == dst_local:
        return None
    if src_local:
        return {"direction": "outbound", "local_ip": src, "local_port": src_port,
                "remote_ip": dst, "remote_port": dst_port}
    return {"direction": "inbound", "local_ip": dst, "local_port": dst_port,
            "remote_ip": src, "remote_port": src_port}

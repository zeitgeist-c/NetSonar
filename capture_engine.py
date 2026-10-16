"""NetSonar packet capture and minute-flow aggregation."""

import logging
import os
import ipaddress
import threading
import time
from datetime import datetime

import psutil
from scapy.all import IP, IPv6, TCP, UDP, get_if_list, sniff

from config import SUSPICIOUS_PORTS, load_settings
from database import Database
from models import CaptureHealth
from notifier import notify_high_traffic, notify_suspicious_port
from flow_utils import normalize_ip, orient_flow
from flow_accumulator import FlowAccumulator

log = logging.getLogger("NetSonar.Capture")


def npcap_available() -> bool:
    if os.name != "nt":
        return True
    windows = os.environ.get("SystemRoot", r"C:\Windows")
    return any(os.path.isfile(os.path.join(windows, folder, "Npcap", "wpcap.dll"))
               for folder in ("System32", "SysWOW64"))


def get_local_addresses() -> set[str]:
    """Return usable IPv4 and IPv6 addresses assigned to this machine."""
    result: set[str] = set()
    for addresses in psutil.net_if_addrs().values():
        for address in addresses:
            normalized = normalize_ip(address.address)
            if normalized:
                result.add(normalized)
    return result


def get_broadcast_addresses() -> set[str]:
    result = {"255.255.255.255"}
    for addresses in psutil.net_if_addrs().values():
        for address in addresses:
            if address.address and address.netmask and ":" not in address.address:
                try:
                    network = ipaddress.ip_interface(f"{address.address}/{address.netmask}").network
                    result.add(str(network.broadcast_address))
                except ValueError:
                    pass
    return result


_port_process_map: dict[tuple[str, int], str] = {}
_map_lock = threading.Lock()
_ip_byte_counter: dict[str, int] = {}
_ip_notified: dict[str, bool] = {}
_counter_lock = threading.Lock()
_COUNTER_RESET_SECONDS = 60
# HIGH_TRAFFIC eşiği paket yolunda diskten okunmaz; kısa ömürlü önbellek
# kullanılır. TTL dolmadan ayar değişirse en geç 60 sn içinde görülür.
_THRESHOLD_CACHE_SECONDS = 60
_DEFAULT_THRESHOLD_BYTES = 50 * 1024 * 1024
_threshold_cache: dict[str, float] = {"value": _DEFAULT_THRESHOLD_BYTES, "at": 0.0}


def _traffic_threshold_bytes() -> int:
    now = time.monotonic()
    if now - _threshold_cache["at"] < _THRESHOLD_CACHE_SECONDS:
        return int(_threshold_cache["value"])
    try:
        value = int(load_settings().get("HIGH_TRAFFIC_THRESHOLD_BYTES", _DEFAULT_THRESHOLD_BYTES))
    except Exception:
        log.debug("Traffic threshold read failed; using cached value", exc_info=True)
        return int(_threshold_cache["value"])
    _threshold_cache["value"] = value
    _threshold_cache["at"] = now
    return value


def _update_process_map():
    """Refresh normalized protocol/local-port to process mappings."""
    mapping: dict[tuple[str, int], str] = {}
    try:
        for connection in psutil.net_connections(kind="inet"):
            if connection.laddr and connection.pid:
                try:
                    protocol = "TCP" if connection.type == 1 else "UDP"
                    mapping[(protocol, connection.laddr.port)] = psutil.Process(connection.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception:
        log.debug("Process map refresh failed", exc_info=True)
    with _map_lock:
        _port_process_map.clear()
        _port_process_map.update(mapping)


def _get_process(local_port: int, protocol: str) -> str:
    with _map_lock:
        return _port_process_map.get((protocol, local_port), "unknown")


def _packet_handler(packet, db: Database, local_ips: set[str] | None = None,
                    broadcast_ips: set[str] | None = None):
    if not (packet.haslayer(IP) or packet.haslayer(IPv6)):
        return
    size = len(packet)
    ip_layer = packet[IP] if packet.haslayer(IP) else packet[IPv6]
    src_ip, dst_ip = ip_layer.src, ip_layer.dst
    protocol, src_port, dst_port = "OTHER", 0, 0
    if packet.haslayer(TCP):
        protocol, src_port, dst_port = "TCP", packet[TCP].sport, packet[TCP].dport
    elif packet.haslayer(UDP):
        protocol, src_port, dst_port = "UDP", packet[UDP].sport, packet[UDP].dport

    endpoints = orient_flow(
        src_ip, src_port, dst_ip, dst_port,
        local_ips if local_ips is not None else get_local_addresses(), broadcast_ips,
    )
    if endpoints is None:
        return
    direction = endpoints.pop("direction")
    process = _get_process(endpoints["local_port"], protocol)
    now = datetime.now()
    db.upsert_flow_bucket({
        "bucket_start": now.replace(second=0, microsecond=0).isoformat(),
        **endpoints,
        "protocol": protocol,
        "process": process,
        "sent_bytes": size if direction == "outbound" else 0,
        "received_bytes": size if direction == "inbound" else 0,
        "sent_packets": 1 if direction == "outbound" else 0,
        "received_packets": 1 if direction == "inbound" else 0,
        "first_seen": now.isoformat(),
        "last_seen": now.isoformat(),
    })
    remote_ip, remote_port = endpoints["remote_ip"], endpoints["remote_port"]
    try:
        from custom_alerts import check_connection_alerts
        from notifier import notify_custom_alert
        for rule in check_connection_alerts(remote_ip, remote_port, process):
            notify_custom_alert(rule.name, remote_ip, f"{process} -> {remote_ip}:{remote_port}")
    except Exception:
        log.debug("Custom alert evaluation failed", exc_info=True)
    if remote_port in SUSPICIOUS_PORTS:
        notify_suspicious_port(remote_ip, remote_port, process)
    with _counter_lock:
        _ip_byte_counter[remote_ip] = _ip_byte_counter.get(remote_ip, 0) + size
        total = _ip_byte_counter[remote_ip]
        threshold = _traffic_threshold_bytes()
        if total >= threshold and not _ip_notified.get(remote_ip, False):
            _ip_notified[remote_ip] = True
            notify_high_traffic(remote_ip, total, process)


class CaptureEngine:
    """Capture traffic with a separately observable worker per adapter."""

    def __init__(self, db: Database, interface: str | None = None):
        self.db = db
        self._running = False
        self._sniff_threads: list[threading.Thread] = []
        self._map_thread: threading.Thread | None = None
        self._counter_thread: threading.Thread | None = None
        self._flush_thread: threading.Thread | None = None
        self._interface = interface
        self._local_ips: set[str] = set()
        self._broadcast_ips: set[str] = set()
        self._adapter_health: dict[str, str] = {}
        self._health_lock = threading.Lock()
        self._accumulator = FlowAccumulator(db)

    def start(self):
        if self._running:
            return
        self._running = True
        if not npcap_available():
            self._running = False
            with self._health_lock:
                self._adapter_health = {"Npcap": "error: wpcap.dll not found"}
            log.error("Npcap wpcap.dll was not found; capture is unavailable")
            return
        self._local_ips = get_local_addresses()
        self._broadcast_ips = get_broadcast_addresses()
        self._map_thread = threading.Thread(target=self._map_updater, daemon=True, name="ns-map")
        self._counter_thread = threading.Thread(target=self._counter_resetter, daemon=True, name="ns-counter")
        self._flush_thread = threading.Thread(target=self._flush_updater, daemon=True, name="ns-flow-flush")
        self._map_thread.start()
        self._counter_thread.start()
        self._flush_thread.start()
        try:
            adapters = [self._interface] if self._interface else list(get_if_list())
        except Exception as exc:
            adapters = []
            log.error("Capture adapters could not be enumerated: %s", exc)
        with self._health_lock:
            self._adapter_health = {adapter: "starting" for adapter in adapters}
        self._sniff_threads = []
        for index, adapter in enumerate(adapters):
            thread = threading.Thread(target=self._sniff_loop, args=(adapter,), daemon=True,
                                      name=f"ns-sniff-{index}")
            self._sniff_threads.append(thread)
            thread.start()
        log.info("Capture started on %d adapter(s)", len(adapters))

    def stop(self):
        if not self._running:
            self.db.flush()
            return
        self._running = False
        for thread in (*self._sniff_threads, self._map_thread, self._counter_thread, self._flush_thread):
            if thread and thread.is_alive():
                thread.join(timeout=2)
        self._accumulator.flush()
        self.db.flush()
        with self._health_lock:
            self._adapter_health = {name: "stopped" for name in self._adapter_health}
        log.info("Capture stopped")

    def health_snapshot(self) -> CaptureHealth:
        with self._health_lock:
            adapters = dict(self._adapter_health)
        if not self._running:
            state = "stopped"
        elif adapters and all(value == "active" for value in adapters.values()):
            state = "active"
        elif any(value == "active" for value in adapters.values()):
            state = "partial"
        else:
            state = "error"
        return CaptureHealth(state=state, adapters=adapters)

    def _sniff_loop(self, adapter: str):
        kwargs = {"prn": lambda packet: _packet_handler(
                      packet, self._accumulator, self._local_ips, self._broadcast_ips),
                  "store": False, "timeout": 1, "iface": adapter}
        while self._running:
            try:
                sniff(**kwargs)
                with self._health_lock:
                    self._adapter_health[adapter] = "active"
            except Exception as exc:
                with self._health_lock:
                    self._adapter_health[adapter] = f"error: {exc}"
                log.error("Capture failed on %s: %s", adapter, exc)
                time.sleep(2)

    def _map_updater(self):
        while self._running:
            _update_process_map()
            for _ in range(5):
                if not self._running:
                    return
                time.sleep(1)

    def _counter_resetter(self):
        while self._running:
            for _ in range(_COUNTER_RESET_SECONDS):
                if not self._running:
                    return
                time.sleep(1)
            with _counter_lock:
                _ip_byte_counter.clear()
                _ip_notified.clear()

    def _flush_updater(self):
        while self._running:
            for _ in range(10):
                if not self._running:
                    return
                time.sleep(0.1)
            try:
                self._accumulator.flush()
            except Exception:
                log.exception("Flow accumulator flush failed")

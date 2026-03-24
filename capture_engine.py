"""
AgTara — Paket Yakalama Motoru
Scapy kullanarak ağ trafiğini arka planda dinler.
Her paketten: IP, port, protokol, boyut ve süreç adı çıkarılır.
UYARI: Yönetici (Administrator) yetkileri gerektirir.
"""

import threading
import time
from datetime import datetime

import psutil
from scapy.all import sniff, IP, TCP, UDP

from database import Database
from notifier import notify_suspicious_port, notify_high_traffic
from config import SUSPICIOUS_PORTS, SUSPICIOUS_BYTES_THRESHOLD

# Port → süreç adı önbelleği (her 2 sn güncellenir)
_port_process_map: dict[int, str] = {}
_map_lock = threading.Lock()

# Aktif IP başına kümülatif byte sayacı (anlık yüksek trafik algılama)
_ip_byte_counter: dict[str, int] = {}
_counter_lock = threading.Lock()
_COUNTER_RESET_SECONDS = 60       # Her dakika sıfırla


def _update_process_map():
    """psutil ile yerel port → süreç adı eşlemesini yeniler."""
    mapping: dict[int, str] = {}
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.pid:
                try:
                    name = psutil.Process(conn.pid).name()
                    mapping[conn.laddr.port] = name
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception:
        pass
    with _map_lock:
        _port_process_map.clear()
        _port_process_map.update(mapping)


def _get_process(src_port: int) -> str:
    with _map_lock:
        return _port_process_map.get(src_port, "unknown")


def _packet_handler(packet, db: Database):
    """Her yakalanan paketi işler, veritabanına yazar ve anlık kontroller yapar."""
    if not packet.haslayer(IP):
        return

    ip = packet[IP]
    proto = "OTHER"
    src_port = dst_port = 0

    if packet.haslayer(TCP):
        proto = "TCP"
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport
    elif packet.haslayer(UDP):
        proto = "UDP"
        src_port = packet[UDP].sport
        dst_port = packet[UDP].dport

    size    = len(packet)
    process = _get_process(src_port)
    dst_ip  = ip.dst

    # Veritabanına yaz
    db.insert_connection({
        "timestamp": datetime.now().isoformat(),
        "src_ip":   ip.src,
        "dst_ip":   dst_ip,
        "dst_port": dst_port,
        "protocol": proto,
        "bytes":    size,
        "process":  process,
    })

    # ── Anlık Kontrol 1: Bilinen tehlikeli port ──────────────────
    if dst_port in SUSPICIOUS_PORTS:
        notify_suspicious_port(dst_ip, dst_port, process)

    # ── Anlık Kontrol 2: Yüksek trafik eşiği ────────────────────
    with _counter_lock:
        _ip_byte_counter[dst_ip] = _ip_byte_counter.get(dst_ip, 0) + size
        total = _ip_byte_counter[dst_ip]

    if total >= SUSPICIOUS_BYTES_THRESHOLD and total - size < SUSPICIOUS_BYTES_THRESHOLD:
        # İlk kez eşiği aştı → bildirim gönder
        notify_high_traffic(dst_ip, total, process)


class CaptureEngine:
    """Ağ trafiğini arka plan thread'lerinde dinleyen motor."""

    def __init__(self, db: Database):
        self.db = db
        self._running = False
        self._sniff_thread: threading.Thread | None = None
        self._map_thread: threading.Thread   | None = None
        self._counter_thread: threading.Thread | None = None

    def start(self):
        if self._running:
            return
        self._running = True

        # Süreç haritası güncelleyici
        self._map_thread = threading.Thread(target=self._map_updater, daemon=True, name="ag-map")
        self._map_thread.start()

        # Byte sayaç sıfırlayıcı
        self._counter_thread = threading.Thread(
            target=self._counter_resetter, daemon=True, name="ag-counter"
        )
        self._counter_thread.start()

        # Paket yakalama
        self._sniff_thread = threading.Thread(target=self._sniff_loop, daemon=True, name="ag-sniff")
        self._sniff_thread.start()

        print("[CaptureEngine] ✅ Dinleme başladı.")

    def stop(self):
        self._running = False
        self.db.flush()
        print("[CaptureEngine] 🛑 Dinleme durduruldu, tampon yazıldı.")

    def _sniff_loop(self):
        sniff(
            prn=lambda pkt: _packet_handler(pkt, self.db),
            store=False,
            stop_filter=lambda _: not self._running,
        )

    def _map_updater(self):
        while self._running:
            _update_process_map()
            time.sleep(2)

    def _counter_resetter(self):
        while self._running:
            time.sleep(_COUNTER_RESET_SECONDS)
            with _counter_lock:
                _ip_byte_counter.clear()

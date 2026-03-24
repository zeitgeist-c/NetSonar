"""
AgTara — SQLite Veritabanı Katmanı
Thread-safe, batch-insert destekli bağlantı ve rapor yönetimi.
"""

import sqlite3
import threading
from pathlib import Path
from config import DB_PATH


class Database:
    def __init__(self):
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._buffer: list[dict] = []
        self._create_tables()

    # ─── Tablo Oluşturma ──────────────────────────────────────────
    def _create_tables(self):
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS connections (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    src_ip      TEXT,
                    dst_ip      TEXT,
                    dst_port    INTEGER,
                    protocol    TEXT,
                    bytes       INTEGER DEFAULT 0,
                    process     TEXT,
                    flagged     INTEGER DEFAULT 0,
                    vt_result   TEXT
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at  TEXT NOT NULL,
                    provider    TEXT,
                    risk_score  REAL,
                    status      TEXT,
                    content     TEXT
                );

                CREATE TABLE IF NOT EXISTS blocked_ips (
                    ip          TEXT PRIMARY KEY,
                    reason      TEXT,
                    blocked_at  TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_conn_timestamp
                    ON connections (timestamp);
                CREATE INDEX IF NOT EXISTS idx_conn_dst_ip
                    ON connections (dst_ip);
            """)
            self.conn.commit()

    # ─── Bağlantı Kaydı ──────────────────────────────────────────
    def insert_connection(self, data: dict):
        """Thread-safe toplu ekleme (50 pakette bir flush)."""
        with self._lock:
            self._buffer.append(data)
            if len(self._buffer) >= 50:
                self._flush_locked()

    def _flush_locked(self):
        if not self._buffer:
            return
        self.conn.executemany(
            """INSERT INTO connections
               (timestamp, src_ip, dst_ip, dst_port, protocol, bytes, process)
               VALUES (:timestamp, :src_ip, :dst_ip, :dst_port, :protocol, :bytes, :process)""",
            self._buffer,
        )
        self.conn.commit()
        self._buffer.clear()

    def flush(self):
        """Tampondaki verileri anında yaz (uygulama kapanırken çağır)."""
        with self._lock:
            self._flush_locked()

    # ─── Özet Sorgular ───────────────────────────────────────────
    def get_summary(self, hours: int = 1) -> list[dict]:
        """AI'a gönderilecek grup bazlı özet — ham paket değil metadata."""
        with self._lock:
            cur = self.conn.execute(
                f"""
                SELECT   dst_ip,
                         dst_port,
                         process,
                         protocol,
                         SUM(bytes)   AS total_bytes,
                         COUNT(*)     AS conn_count
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '192.168.%'
                  AND dst_ip NOT LIKE '10.%'
                  AND dst_ip NOT LIKE '172.16.%'
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip, dst_port, process
                ORDER BY total_bytes DESC
                LIMIT 25
                """
            )
            return [dict(row) for row in cur.fetchall()]

    def get_suspicious_connections(self, hours: int = 1) -> list[dict]:
        """Son N saatin büyük veya bilinen tehlikeli portlu bağlantıları."""
        from config import SUSPICIOUS_BYTES_THRESHOLD, SUSPICIOUS_PORTS
        port_placeholders = ",".join("?" * len(SUSPICIOUS_PORTS))
        with self._lock:
            cur = self.conn.execute(
                f"""
                SELECT dst_ip, dst_port, process, SUM(bytes) AS total_bytes
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip, dst_port, process
                HAVING total_bytes > ?
                   OR dst_port IN ({port_placeholders})
                ORDER BY total_bytes DESC
                LIMIT 10
                """,
                [SUSPICIOUS_BYTES_THRESHOLD, *list(SUSPICIOUS_PORTS)],
            )
            return [dict(row) for row in cur.fetchall()]

    def get_recent_connections(self, limit: int = 200) -> list[dict]:
        """GUI tablo için en son N bağlantıyı döndürür."""
        with self._lock:
            cur = self.conn.execute(
                """SELECT timestamp, src_ip, dst_ip, dst_port, protocol,
                          bytes, process, flagged
                   FROM connections
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_stats(self) -> dict:
        """Dashboard istatistik kartları için."""
        with self._lock:
            today = self.conn.execute(
                "SELECT COUNT(*) FROM connections WHERE timestamp >= datetime('now', '-1 day')"
            ).fetchone()[0]
            threats = self.conn.execute(
                "SELECT COUNT(*) FROM connections WHERE flagged = 1"
            ).fetchone()[0]
            blocked = self.conn.execute(
                "SELECT COUNT(*) FROM blocked_ips"
            ).fetchone()[0]
            reports = self.conn.execute(
                "SELECT COUNT(*) FROM reports"
            ).fetchone()[0]
            return {
                "today_connections": today,
                "total_threats": threats,
                "blocked_ips": blocked,
                "total_reports": reports,
            }

    def get_all_reports(self) -> list[dict]:
        """Tüm AI raporlarını döndürür."""
        with self._lock:
            cur = self.conn.execute(
                "SELECT * FROM reports ORDER BY created_at DESC LIMIT 50"
            )
            return [dict(row) for row in cur.fetchall()]

    def remove_blocked_ip(self, ip: str):
        """Engelleme kaydını veritabanından kaldır."""
        with self._lock:
            self.conn.execute("DELETE FROM blocked_ips WHERE ip = ?", (ip,))
            self.conn.commit()

    def get_traffic_stats(self) -> list[dict]:
        """
        Saat / Gün / Hafta / Ay / Yıl bazında upload+download istatistikleri.

        Upload  = src_ip yerel (bizden giden veri)
        Download = src_ip harici (bize gelen veri)
        Yön bilinemiyorsa tüm byte'lar 'transfer' olarak sayılır.
        """
        _LOCAL = (
            "src_ip LIKE '192.168.%' OR src_ip LIKE '10.%' "
            "OR src_ip LIKE '172.%' OR src_ip LIKE '127.%'"
        )

        def _query(interval_sql: str) -> dict:
            row = self.conn.execute(
                f"""
                SELECT
                    SUM(CASE WHEN {_LOCAL} THEN bytes ELSE 0 END)       AS upload,
                    SUM(CASE WHEN NOT ({_LOCAL}) THEN bytes ELSE 0 END) AS download,
                    SUM(bytes)                                           AS total,
                    COUNT(*)                                             AS conn_count
                FROM connections
                WHERE timestamp >= {interval_sql}
                """
            ).fetchone()
            return {
                "upload":     row["upload"]   or 0,
                "download":   row["download"] or 0,
                "total":      row["total"]    or 0,
                "conn_count": row["conn_count"] or 0,
            }

        with self._lock:
            return [
                {"label": "Son 1 Saat",  "short": "Saat",  **_query("datetime('now','-1 hours')")},
                {"label": "Bugün",        "short": "Gün",   **_query("datetime('now','-1 days')")},
                {"label": "Bu Hafta",     "short": "Hafta", **_query("datetime('now','-7 days')")},
                {"label": "Bu Ay",        "short": "Ay",    **_query("datetime('now','-30 days')")},
                {"label": "Bu Yıl",       "short": "Yıl",   **_query("datetime('now','-365 days')")},
            ]


    # ─── Engelleme Kaydı ─────────────────────────────────────────
    def add_blocked_ip(self, ip: str, reason: str):
        from datetime import datetime
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO blocked_ips (ip, reason, blocked_at) VALUES (?,?,?)",
                (ip, reason, datetime.now().isoformat()),
            )
            self.conn.commit()

    def get_blocked_ips(self) -> list[dict]:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM blocked_ips ORDER BY blocked_at DESC")
            return [dict(row) for row in cur.fetchall()]

    # ─── Rapor Kaydı ─────────────────────────────────────────────
    def save_report(self, provider: str, risk_score: float, status: str, content: str):
        from datetime import datetime
        with self._lock:
            self.conn.execute(
                "INSERT INTO reports (created_at, provider, risk_score, status, content) VALUES (?,?,?,?,?)",
                (datetime.now().isoformat(), provider, risk_score, status, content),
            )
            self.conn.commit()

    def get_latest_report(self) -> dict | None:
        with self._lock:
            cur = self.conn.execute(
                "SELECT * FROM reports ORDER BY created_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None

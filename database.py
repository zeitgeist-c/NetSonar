"""
NetSonar — SQLite Veritabanı Katmanı
Thread-safe, batch-insert destekli bağlantı ve rapor yönetimi.
Otomatik temizlik: DB_RETENTION_DAYS sonra eski kayıtları siler.
"""

import sqlite3
import threading
import time
from pathlib import Path
from config import DB_PATH, DB_RETENTION_DAYS, DB_CLEANUP_INTERVAL_HOURS


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
            CREATE INDEX IF NOT EXISTS idx_conn_dst_port
                ON connections (dst_port);
            CREATE INDEX IF NOT EXISTS idx_conn_process
                ON connections (process);
            CREATE INDEX IF NOT EXISTS idx_conn_flagged
                ON connections (flagged);
            CREATE INDEX IF NOT EXISTS idx_conn_composite
                ON connections (dst_ip, dst_port, process);
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
    def get_summary(self, hours: int = 1, limit: int = 1000000) -> list[dict]:
        """AI'a gönderilecek grup bazlı özet — ham paket değil metadata.
        
        Öncelik sırası (akıllı sıralama):
        1. Şüpheli portlar (config.SUSPICIOUS_PORTS)
        2. Yüksek byte transferi (>1MB)
        3. Çoklu bağlantı sayısı
        4. Son görülme zamanı
        """
        from config import SUSPICIOUS_PORTS, SUSPICIOUS_BYTES_THRESHOLD
        port_list = list(SUSPICIOUS_PORTS)
        high_bytes = max(SUSPICIOUS_BYTES_THRESHOLD * 20, 1_000_000)  # 1MB veya daha fazla
        
        with self._lock:
            placeholders = ",".join("?" * len(port_list)) if port_list else ""
            query = f"""
                SELECT   dst_ip,
                         dst_port,
                         process,
                         protocol,
                         SUM(bytes)   AS total_bytes,
                         COUNT(*)     AS conn_count,
                         CASE WHEN dst_port IN ({placeholders}) THEN 1 ELSE 0 END AS is_suspicious_port,
                         CASE WHEN SUM(bytes) > ? THEN 1 ELSE 0 END AS is_high_traffic
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '192.168.%'
                  AND dst_ip NOT LIKE '10.%'
                  AND dst_ip NOT LIKE '172.16.%'
                  AND dst_ip NOT LIKE '172.17.%'
                  AND dst_ip NOT LIKE '172.18.%'
                  AND dst_ip NOT LIKE '172.19.%'
                  AND dst_ip NOT LIKE '172.2%.%'
                  AND dst_ip NOT LIKE '172.3%.%'
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip, dst_port, process
                ORDER BY is_suspicious_port DESC,
                         is_high_traffic DESC,
                         total_bytes DESC,
                         conn_count DESC
                LIMIT ?
                """
            params = (*port_list, high_bytes, limit)
            cur = self.conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_last_analysis_time(self) -> str | None:
        """Son başarılı AI analizinin zamanını döndürür (ISO format, UTC).
        Başarısız analizler (risk_score=-1) sayılmaz."""
        with self._lock:
            row = self.conn.execute(
                """SELECT created_at FROM reports
                   WHERE risk_score >= 0
                   ORDER BY created_at DESC LIMIT 1"""
            ).fetchone()
            return row[0] if row else None

    def get_summary_since(self, since_ts: str, limit: int = 1000000) -> list[dict]:
        """Belirli bir zamandan itibaren gelen YENİ bağlantıların özeti.
        since_ts: SQLite datetime string örn. '2024-03-24 22:00:00'

        Öncelik sırası (akıllı sıralama):
          1. Şüpheli portlar (config.SUSPICIOUS_PORTS)
          2. Yüksek byte transferi (>1MB)
          3. Çoklu bağlantı sayısı
        """
        from config import SUSPICIOUS_PORTS, SUSPICIOUS_BYTES_THRESHOLD
        port_list = list(SUSPICIOUS_PORTS)
        high_bytes = max(SUSPICIOUS_BYTES_THRESHOLD * 20, 1_000_000)
        
        with self._lock:
            placeholders = ",".join("?" * len(port_list)) if port_list else ""
            query = f"""
                SELECT   dst_ip,
                         dst_port,
                         process,
                         protocol,
                         SUM(bytes)                          AS total_bytes,
                         COUNT(*)                            AS conn_count,
                         MIN(timestamp)                      AS first_seen,
                         MAX(timestamp)                      AS last_seen,
                         CASE WHEN dst_port IN ({placeholders})
                              THEN 1 ELSE 0 END              AS suspicious_port,
                         CASE WHEN SUM(bytes) > ?
                              THEN 1 ELSE 0 END              AS is_high_traffic
                FROM connections
                WHERE timestamp > ?
                  AND dst_ip NOT LIKE '192.168.%'
                  AND dst_ip NOT LIKE '10.%'
                  AND dst_ip NOT LIKE '172.16.%'
                  AND dst_ip NOT LIKE '172.17.%'
                  AND dst_ip NOT LIKE '172.18.%'
                  AND dst_ip NOT LIKE '172.19.%'
                  AND dst_ip NOT LIKE '172.2%.%'
                  AND dst_ip NOT LIKE '172.3%.%'
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip, dst_port, process
                ORDER BY suspicious_port DESC,
                         is_high_traffic DESC,
                         total_bytes DESC,
                         conn_count DESC
                LIMIT ?
                """
            params = (*port_list, high_bytes, since_ts, limit)
            cur = self.conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_new_connection_count(self, since_ts: str) -> int:
        """Son analizden bu yana kaç yeni bağlantı kaydedildi."""
        with self._lock:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM connections WHERE timestamp > ?",
                (since_ts,),
            ).fetchone()
            return row[0] if row else 0

    def get_frequent_connections(self, hours: int = 1, limit: int = 10) -> list[dict]:
        """En sık bağlanılan IP'ler (en çok bağlantı sayısı)."""
        with self._lock:
            cur = self.conn.execute(
                """
                SELECT dst_ip,
                       COUNT(*) AS conn_count,
                       SUM(bytes) AS total_bytes,
                       MAX(timestamp) AS last_seen
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '192.168.%'
                  AND dst_ip NOT LIKE '10.%'
                  AND dst_ip NOT LIKE '172.16.%'
                  AND dst_ip NOT LIKE '172.17.%'
                  AND dst_ip NOT LIKE '172.18.%'
                  AND dst_ip NOT LIKE '172.19.%'
                  AND dst_ip NOT LIKE '172.2%.%'
                  AND dst_ip NOT LIKE '172.3%.%'
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip
                ORDER BY conn_count DESC
                LIMIT ?
                """.format(hours=hours),
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_top_transfer_connections(self, hours: int = 1, limit: int = 10) -> list[dict]:
        """En fazla veri transferi yapan IP'ler."""
        with self._lock:
            cur = self.conn.execute(
                """
                SELECT dst_ip,
                       SUM(bytes) AS total_bytes,
                       COUNT(*) AS conn_count,
                       MAX(timestamp) AS last_seen
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '192.168.%'
                  AND dst_ip NOT LIKE '10.%'
                  AND dst_ip NOT LIKE '172.16.%'
                  AND dst_ip NOT LIKE '172.17.%'
                  AND dst_ip NOT LIKE '172.18.%'
                  AND dst_ip NOT LIKE '172.19.%'
                  AND dst_ip NOT LIKE '172.2%.%'
                  AND dst_ip NOT LIKE '172.3%.%'
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip
                ORDER BY total_bytes DESC
                LIMIT ?
                """.format(hours=hours),
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_diverse_port_connections(self, hours: int = 1, limit: int = 10) -> list[dict]:
        """En fazla farklı porta bağlanan IP'ler."""
        with self._lock:
            cur = self.conn.execute(
                """
                SELECT dst_ip,
                       COUNT(DISTINCT dst_port) AS port_count,
                       SUM(bytes) AS total_bytes,
                       COUNT(*) AS conn_count,
                       MAX(timestamp) AS last_seen
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '192.168.%'
                  AND dst_ip NOT LIKE '10.%'
                  AND dst_ip NOT LIKE '172.16.%'
                  AND dst_ip NOT LIKE '172.17.%'
                  AND dst_ip NOT LIKE '172.18.%'
                  AND dst_ip NOT LIKE '172.19.%'
                  AND dst_ip NOT LIKE '172.2%.%'
                  AND dst_ip NOT LIKE '172.3%.%'
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip
                ORDER BY port_count DESC
                LIMIT ?
                """.format(hours=hours),
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


    def get_suspicious_connections(self, hours: int = 1) -> list[dict]:
        """Son N saatin büyük veya bilinen tehlikeli portlu bağlantıları."""
        from config import SUSPICIOUS_BYTES_THRESHOLD, SUSPICIOUS_PORTS
        port_list = list(SUSPICIOUS_PORTS)
        port_placeholders = ",".join("?" * len(port_list)) if port_list else ""
        with self._lock:
            query = f"""
                SELECT dst_ip, dst_port, process, SUM(bytes) AS total_bytes
                FROM connections
                WHERE timestamp >= datetime('now', '-{hours} hours')
                  AND dst_ip NOT LIKE '127.%'
                GROUP BY dst_ip, dst_port, process
                HAVING total_bytes > ?
                   OR dst_port IN ({port_placeholders})
                ORDER BY total_bytes DESC
                LIMIT 10
                """
            params = [SUSPICIOUS_BYTES_THRESHOLD, *port_list] if port_list else [SUSPICIOUS_BYTES_THRESHOLD]
            cur = self.conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_recent_connections(self, limit: int = 200, offset: int = 0) -> list[dict]:
        """GUI tablo için en son N bağlantıyı döndürür. Sayfalama için offset kullanılabilir."""
        with self._lock:
            cur = self.conn.execute(
                """SELECT timestamp, src_ip, dst_ip, dst_port, protocol,
                          bytes, process, flagged
                   FROM connections
                   ORDER BY id DESC LIMIT ? OFFSET ?""",
                (limit, offset),
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

    # ─── Otomatik Temizlik ─────────────────────────────────────────
    def cleanup_old_records(self) -> dict:
        """Eski kayıtları siler. Returns: {"connections": N, "reports": N}"""
        if DB_RETENTION_DAYS <= 0:
            return {"connections": 0, "reports": 0}
        
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM connections WHERE timestamp < datetime('now', ?)",
                (f"-{DB_RETENTION_DAYS} days",)
            )
            deleted_conns = cur.rowcount
            
            cur = self.conn.execute(
                "DELETE FROM reports WHERE created_at < datetime('now', ?)",
                (f"-{DB_RETENTION_DAYS} days",)
            )
            deleted_reports = cur.rowcount
            
            self.conn.commit()
            
            if deleted_conns > 0 or deleted_reports > 0:
                print(f"[Database] Temizlik: {deleted_conns} bağlantı, {deleted_reports} rapor silindi.")
            
            return {"connections": deleted_conns, "reports": deleted_reports}

    def get_db_size_mb(self) -> float:
        """Veritabanı dosya boyutunu MB olarak döndürür."""
        try:
            size = Path(DB_PATH).stat().st_size
            return size / (1024 * 1024)
        except Exception:
            return 0.0

    def get_record_counts(self) -> dict:
        """Tablodaki kayıt sayılarını döndürür."""
        with self._lock:
            conn_count = self.conn.execute(
                "SELECT COUNT(*) FROM connections"
            ).fetchone()[0]
            report_count = self.conn.execute(
                "SELECT COUNT(*) FROM reports"
            ).fetchone()[0]
            blocked_count = self.conn.execute(
                "SELECT COUNT(*) FROM blocked_ips"
            ).fetchone()[0]
            return {
                "connections": conn_count,
                "reports": report_count,
                "blocked_ips": blocked_count,
            }

    def get_traffic_speed(self, minutes: int = 5) -> dict:
        """Son N dakikadaki ortalama trafik hızını KB/s olarak döndürür."""
        import datetime
        with self._lock:
            cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat()
            row = self.conn.execute("""
                SELECT 
                    COALESCE(SUM(bytes), 0) as total_bytes
                FROM connections
                WHERE timestamp >= ?
            """, (cutoff,)).fetchone()
            
            total_bytes = row["total_bytes"] or 0
            total_seconds = minutes * 60
            speed_kbs = (total_bytes / 1024) / total_seconds if total_seconds > 0 else 0
            
            return {
                "upload_kbs": speed_kbs * 0.4,   # Tahmini
                "download_kbs": speed_kbs * 0.6, # Tahmini
                "total_kbs": speed_kbs,
                "total_bytes": total_bytes,
            }

    def get_top_processes(self, hours: int = 1, limit: int = 5) -> list[dict]:
        """En çok trafik yapan süreçleri döndürür."""
        import datetime
        with self._lock:
            cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
            rows = self.conn.execute("""
                SELECT 
                    process,
                    SUM(bytes) as total_bytes,
                    COUNT(*) as conn_count
                FROM connections
                WHERE timestamp >= ? AND process IS NOT NULL
                GROUP BY process
                ORDER BY total_bytes DESC
                LIMIT ?
            """, (cutoff, limit)).fetchall()
            
            return [dict(row) for row in rows]

    def get_active_connections_count(self, minutes: int = 60) -> int:
        """Son N dakikadaki aktif bağlantı sayısını döndürür."""
        import datetime
        with self._lock:
            cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat()
            row = self.conn.execute("""
                SELECT COUNT(DISTINCT dst_ip) as count
                FROM connections
                WHERE timestamp >= ?
            """, (cutoff,)).fetchone()
            return row["count"] or 0

    def get_protocol_distribution(self, hours: int = 24) -> dict:
        """Protokol dağılımını yüzde olarak döndürür."""
        import datetime
        with self._lock:
            cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
            rows = self.conn.execute("""
                SELECT 
                    protocol,
                    COUNT(*) as count,
                    SUM(bytes) as total_bytes
                FROM connections
                WHERE timestamp >= ? AND protocol IS NOT NULL
                GROUP BY protocol
            """, (cutoff,)).fetchall()
            
            total = sum(row["count"] for row in rows)
            result = {}
            for row in rows:
                proto = row["protocol"] or "OTHER"
                result[proto] = {
                    "count": row["count"],
                    "bytes": row["total_bytes"],
                    "percentage": round(row["count"] / total * 100, 1) if total > 0 else 0
                }
            return result

    def get_traffic_comparison(self) -> dict:
        """Bugün vs Dün, Bu Hafta vs Geçen Hafta karşılaştırması."""
        import datetime
        with self._lock:
            today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - datetime.timedelta(days=1)
            week_start = today_start - datetime.timedelta(days=today_start.weekday())
            last_week_start = week_start - datetime.timedelta(days=7)
            
            # Bugün
            today_data = self.conn.execute("""
                SELECT COALESCE(SUM(bytes), 0) as total_bytes, COUNT(*) as conn_count
                FROM connections WHERE timestamp >= ?
            """, (today_start.isoformat(),)).fetchone()
            
            # Dün
            yesterday_data = self.conn.execute("""
                SELECT COALESCE(SUM(bytes), 0) as total_bytes, COUNT(*) as conn_count
                FROM connections WHERE timestamp >= ? AND timestamp < ?
            """, (yesterday_start.isoformat(), today_start.isoformat())).fetchone()
            
            # Bu hafta
            week_data = self.conn.execute("""
                SELECT COALESCE(SUM(bytes), 0) as total_bytes, COUNT(*) as conn_count
                FROM connections WHERE timestamp >= ?
            """, (week_start.isoformat(),)).fetchone()
            
            # Geçen hafta
            last_week_data = self.conn.execute("""
                SELECT COALESCE(SUM(bytes), 0) as total_bytes, COUNT(*) as conn_count
                FROM connections WHERE timestamp >= ? AND timestamp < ?
            """, (last_week_start.isoformat(), week_start.isoformat())).fetchone()
            
            def calc_change(current, previous):
                if previous == 0:
                    return 0 if current == 0 else 100
                return round((current - previous) / previous * 100, 1)
            
            return {
                "today": {
                    "bytes": today_data["total_bytes"],
                    "connections": today_data["conn_count"],
                },
                "yesterday": {
                    "bytes": yesterday_data["total_bytes"],
                    "connections": yesterday_data["conn_count"],
                },
                "today_change": calc_change(today_data["total_bytes"], yesterday_data["total_bytes"]),
                "week": {
                    "bytes": week_data["total_bytes"],
                    "connections": week_data["conn_count"],
                },
                "last_week": {
                    "bytes": last_week_data["total_bytes"],
                    "connections": last_week_data["conn_count"],
                },
                "week_change": calc_change(week_data["total_bytes"], last_week_data["total_bytes"]),
            }

    def get_traffic_timeline(self, hours: int = 24, points: int = 12) -> list[dict]:
        """Grafik için zaman çizgisi verisi. Son N saatlik veriyi N noktaya böler."""
        import datetime
        with self._lock:
            now = datetime.datetime.now()
            results = []
            interval_minutes = (hours * 60) // points
            
            for i in range(points):
                end_time = now - datetime.timedelta(minutes=i * interval_minutes)
                start_time = end_time - datetime.timedelta(minutes=interval_minutes)
                
                row = self.conn.execute("""
                    SELECT COALESCE(SUM(bytes), 0) as total_bytes, COUNT(*) as conn_count
                    FROM connections
                    WHERE timestamp >= ? AND timestamp < ?
                """, (start_time.isoformat(), end_time.isoformat())).fetchone()
                
                results.append({
                    "time": start_time.strftime("%H:%M"),
                    "bytes": row["total_bytes"],
                    "connections": row["conn_count"],
                })
            
            # Tersine çevir (eskiden yeniye)
            return list(reversed(results))

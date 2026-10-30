"""NetSonar v0.5 SQLite flow, analysis, finding and rollup storage."""

from __future__ import annotations
from i18n import t

import ipaddress
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from config import DB_PATH

log = logging.getLogger("NetSonar.DB")


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._closed = False
        self.conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA wal_autocheckpoint=1000")
        self._create_schema()

    @staticmethod
    def _cutoff(hours: int | float) -> str:
        return (datetime.now() - timedelta(hours=hours)).isoformat()

    def _create_schema(self):
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS blocked_ips (
                    ip TEXT PRIMARY KEY, reason TEXT, blocked_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trusted_ips (
                    ip TEXT PRIMARY KEY, note TEXT, added_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS analysis_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    high_water_id INTEGER NOT NULL,
                    flow_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS flow_buckets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER REFERENCES analysis_batches(id),
                    bucket_start TEXT NOT NULL,
                    local_ip TEXT NOT NULL, local_port INTEGER NOT NULL,
                    remote_ip TEXT NOT NULL, remote_port INTEGER NOT NULL,
                    protocol TEXT NOT NULL, process TEXT NOT NULL DEFAULT 'unknown',
                    sent_bytes INTEGER NOT NULL DEFAULT 0,
                    received_bytes INTEGER NOT NULL DEFAULT 0,
                    sent_packets INTEGER NOT NULL DEFAULT 0,
                    received_packets INTEGER NOT NULL DEFAULT 0,
                    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                    UNIQUE(bucket_start, local_ip, local_port, remote_ip,
                           remote_port, protocol, process)
                );
                CREATE TABLE IF NOT EXISTS analysis_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL REFERENCES analysis_batches(id),
                    chunk_index INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                    response TEXT, error TEXT, UNIQUE(batch_id, chunk_index)
                );
                CREATE TABLE IF NOT EXISTS security_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER REFERENCES analysis_batches(id), created_at TEXT NOT NULL,
                    severity TEXT NOT NULL, confidence REAL NOT NULL, evidence TEXT NOT NULL,
                    flow_refs TEXT NOT NULL, recommended_action TEXT,
                    block_now INTEGER NOT NULL DEFAULT 0,
                    flow_evidence TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'open'
                );
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER REFERENCES analysis_batches(id), analyzed_at TEXT NOT NULL,
                    status TEXT NOT NULL, risk_score REAL NOT NULL, flow_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS hourly_rollups (
                    hour_start TEXT NOT NULL, protocol TEXT NOT NULL,
                    sent_bytes INTEGER NOT NULL DEFAULT 0,
                    received_bytes INTEGER NOT NULL DEFAULT 0,
                    flow_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(hour_start, protocol)
                );
                CREATE TABLE IF NOT EXISTS threat_intel_cache (
                    provider TEXT NOT NULL, indicator TEXT NOT NULL,
                    data_json TEXT NOT NULL, checked_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL, PRIMARY KEY(provider, indicator)
                );
                CREATE TABLE IF NOT EXISTS external_api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL,
                    used_at TEXT NOT NULL, units INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_flow_batch ON flow_buckets(batch_id, id);
                CREATE INDEX IF NOT EXISTS idx_flow_time ON flow_buckets(last_seen);
                CREATE INDEX IF NOT EXISTS idx_finding_status ON security_findings(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_run_time ON analysis_runs(analyzed_at);
                CREATE INDEX IF NOT EXISTS idx_external_usage ON external_api_usage(provider,used_at);
            """)
            run_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(analysis_runs)")}
            if "report_json" not in run_columns:
                self.conn.execute("ALTER TABLE analysis_runs ADD COLUMN report_json TEXT NOT NULL DEFAULT '{}'")
            finding_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(security_findings)")}
            if "source_evidence" not in finding_columns:
                self.conn.execute("ALTER TABLE security_findings ADD COLUMN source_evidence TEXT NOT NULL DEFAULT '[]'")
            self.conn.execute(
                "INSERT OR REPLACE INTO app_metadata(key,value) VALUES('schema_version','6')"
            )
            self.conn.commit()

    def upsert_flow_bucket(self, data: dict, commit: bool = True) -> int:
        fields = dict(data)
        now = fields.get("last_seen") or datetime.now().isoformat()
        fields.setdefault("first_seen", now)
        fields.setdefault("last_seen", now)
        fields.setdefault("process", "unknown")
        for key in ("sent_bytes", "received_bytes", "sent_packets", "received_packets"):
            fields.setdefault(key, 0)
        with self._lock:
            self.conn.execute("""INSERT INTO flow_buckets
                (bucket_start,local_ip,local_port,remote_ip,remote_port,protocol,process,
                 sent_bytes,received_bytes,sent_packets,received_packets,first_seen,last_seen)
                VALUES (:bucket_start,:local_ip,:local_port,:remote_ip,:remote_port,:protocol,:process,
                        :sent_bytes,:received_bytes,:sent_packets,:received_packets,:first_seen,:last_seen)
                ON CONFLICT(bucket_start,local_ip,local_port,remote_ip,remote_port,protocol,process)
                DO UPDATE SET sent_bytes=sent_bytes+excluded.sent_bytes,
                  received_bytes=received_bytes+excluded.received_bytes,
                  sent_packets=sent_packets+excluded.sent_packets,
                  received_packets=received_packets+excluded.received_packets,
                  first_seen=MIN(first_seen,excluded.first_seen),
                  last_seen=MAX(last_seen,excluded.last_seen)""", fields)
            row = self.conn.execute("""SELECT id FROM flow_buckets
                WHERE bucket_start=:bucket_start AND local_ip=:local_ip AND local_port=:local_port
                  AND remote_ip=:remote_ip AND remote_port=:remote_port
                  AND protocol=:protocol AND process=:process""", fields).fetchone()
            if commit:
                self.conn.commit()
            return int(row[0])

    def flush(self):
        with self._lock:
            self.conn.commit()

    def rollback(self):
        with self._lock:
            self.conn.rollback()

    @contextmanager
    def _atomic(self):
        """Run a write block in its own transaction without breaking callers.

        `upsert_flow_bucket(commit=False)` intentionally leaves a transaction
        open so a whole flush batch commits once. A concurrent analysis thread
        calling `BEGIN IMMEDIATE` in that window raised "cannot start a
        transaction within a transaction", and its rollback discarded the
        capture thread's pending bucket writes. Nested callers now use a
        savepoint, so both the outer batch and this block stay intact.
        """
        with self._lock:
            nested = self.conn.in_transaction
            if nested:
                self.conn.execute("SAVEPOINT ns_atomic")
            else:
                self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield
                if nested:
                    self.conn.execute("RELEASE ns_atomic")
                else:
                    self.conn.commit()
            except BaseException:
                if nested:
                    self.conn.execute("ROLLBACK TO ns_atomic")
                    self.conn.execute("RELEASE ns_atomic")
                else:
                    self.conn.rollback()
                raise

    def claim_pending_batch(self) -> dict | None:
        now = datetime.now().isoformat()
        with self._atomic():
            pending = self.conn.execute(
                "SELECT id FROM analysis_batches WHERE status='pending' ORDER BY id LIMIT 1"
            ).fetchone()
            if pending:
                self.conn.execute(
                    "UPDATE analysis_batches SET status='running',started_at=?,error=NULL WHERE id=?",
                    (now, pending[0]))
                return dict(self.conn.execute(
                    "SELECT * FROM analysis_batches WHERE id=?", (pending[0],)).fetchone())
            row = self.conn.execute(
                "SELECT MAX(id),COUNT(*) FROM flow_buckets WHERE batch_id IS NULL").fetchone()
            if row[0] is None:
                return None
            cursor = self.conn.execute("""INSERT INTO analysis_batches
                (status,high_water_id,flow_count,created_at,started_at)
                VALUES('running',?,?,?,?)""", (row[0], row[1], now, now))
            batch_id = cursor.lastrowid
            self.conn.execute(
                "UPDATE flow_buckets SET batch_id=? WHERE batch_id IS NULL AND id<=?",
                (batch_id, row[0]))
            return dict(self.conn.execute(
                "SELECT * FROM analysis_batches WHERE id=?", (batch_id,)).fetchone())

    def get_batch_flows(self, batch_id: int, limit: int = 200, offset: int = 0) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self.conn.execute(
                "SELECT * FROM flow_buckets WHERE batch_id=? ORDER BY id LIMIT ? OFFSET ?",
                (batch_id, limit, offset)).fetchall()]

    def record_analysis_chunk(self, batch_id: int, chunk_index: int, status: str,
                              response: str | None = None, error: str | None = None):
        with self._lock:
            self.conn.execute("""INSERT INTO analysis_chunks
                (batch_id,chunk_index,status,response,error) VALUES(?,?,?,?,?)
                ON CONFLICT(batch_id,chunk_index) DO UPDATE SET
                  status=excluded.status,response=excluded.response,error=excluded.error""",
                (batch_id, chunk_index, status, response, error))
            self.conn.commit()

    def get_priority_batch_flows(self, batch_id: int, limit: int,
                                 priority_ports: set[int] | None = None,
                                 priority_ips: set[str] | None = None) -> list[dict]:
        """Select the most security-relevant sample from a potentially huge batch."""
        ports = sorted(int(port) for port in (priority_ports or set()))
        ips = sorted(str(ip) for ip in (priority_ips or set()))
        port_placeholders = ",".join("?" for _ in ports) or "NULL"
        ip_placeholders = ",".join("?" for _ in ips) or "NULL"
        params = [batch_id, *ips, *ports, max(1, int(limit))]
        query = f"""SELECT * FROM flow_buckets WHERE batch_id=?
            AND NOT EXISTS(SELECT 1 FROM trusted_ips WHERE ip=flow_buckets.remote_ip)
            ORDER BY CASE WHEN remote_ip IN ({ip_placeholders}) THEN 0 ELSE 1 END,
                     CASE WHEN remote_port IN ({port_placeholders}) THEN 0 ELSE 1 END,
                     (sent_bytes + received_bytes) DESC,
                     (sent_packets + received_packets) DESC, id
            LIMIT ?"""
        with self._lock:
            return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_batch_candidate_rows(self, batch_id: int) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("""SELECT remote_ip,remote_port,process,
                SUM(sent_bytes) AS sent_bytes,SUM(received_bytes) AS received_bytes,
                COUNT(*) AS flow_count,MIN(first_seen) AS first_seen,MAX(last_seen) AS last_seen
                FROM flow_buckets WHERE batch_id=?
                AND NOT EXISTS(SELECT 1 FROM trusted_ips WHERE ip=flow_buckets.remote_ip)
                GROUP BY remote_ip,remote_port,process""", (batch_id,)).fetchall()
            return [dict(row) for row in rows]

    def get_intel_cache(self, provider: str, indicator: str) -> dict | None:
        with self._lock:
            row = self.conn.execute("""SELECT data_json FROM threat_intel_cache
                WHERE provider=? AND indicator=? AND expires_at>?""",
                (provider, indicator, datetime.now().isoformat())).fetchone()
        if not row:
            return None
        try:
            value = json.loads(row[0]); value["cached"] = True; return value
        except (TypeError, json.JSONDecodeError):
            return None

    def put_intel_cache(self, provider: str, indicator: str, data: dict, expires_at: str):
        with self._lock:
            self.conn.execute("""INSERT INTO threat_intel_cache
                (provider,indicator,data_json,checked_at,expires_at) VALUES(?,?,?,?,?)
                ON CONFLICT(provider,indicator) DO UPDATE SET data_json=excluded.data_json,
                checked_at=excluded.checked_at,expires_at=excluded.expires_at""",
                (provider, indicator, json.dumps(data, ensure_ascii=False),
                 data.get("checked_at", datetime.now().isoformat()), expires_at))
            self.conn.commit()

    def api_usage(self, provider: str, since: str) -> int:
        with self._lock:
            return int(self.conn.execute("""SELECT COALESCE(SUM(units),0)
                FROM external_api_usage WHERE provider=? AND used_at>=?""",
                (provider, since)).fetchone()[0])

    def record_api_usage(self, provider: str, units: int = 1):
        with self._lock:
            self.conn.execute("INSERT INTO external_api_usage(provider,used_at,units) VALUES(?,?,?)",
                              (provider, datetime.now().isoformat(), max(1, int(units))))
            self.conn.commit()

    def _rollup_batch_locked(self, batch_id: int):
        self.conn.execute("""INSERT INTO hourly_rollups
            (hour_start,protocol,sent_bytes,received_bytes,flow_count)
            SELECT substr(bucket_start,1,13)||':00:00',protocol,
                   SUM(sent_bytes),SUM(received_bytes),COUNT(*)
            FROM flow_buckets WHERE batch_id=? GROUP BY substr(bucket_start,1,13),protocol
            ON CONFLICT(hour_start,protocol) DO UPDATE SET
              sent_bytes=sent_bytes+excluded.sent_bytes,
              received_bytes=received_bytes+excluded.received_bytes,
              flow_count=flow_count+excluded.flow_count""", (batch_id,))

    def complete_batch(self, batch_id: int, risk_score: float, status: str = "safe",
                       findings: list[dict] | None = None, report: dict | None = None):
        now = datetime.now().isoformat()
        with self._atomic():
            batch = self.conn.execute(
                "SELECT flow_count FROM analysis_batches WHERE id=? AND status='running'",
                (batch_id,)).fetchone()
            if not batch:
                raise ValueError("Batch is not running")
            self.conn.execute("""INSERT INTO analysis_runs
                (batch_id,analyzed_at,status,risk_score,flow_count,report_json)
                VALUES(?,?,?,?,?,?)""",
                (batch_id, now, status, risk_score, batch[0],
                 json.dumps(report or {}, ensure_ascii=False)))
            for finding in findings or []:
                self.conn.execute("""INSERT INTO security_findings
                    (batch_id,created_at,severity,confidence,evidence,flow_refs,
                     recommended_action,block_now,flow_evidence,status,source_evidence)
                    VALUES(?,?,?,?,?,?,?,?,?,'open',?)""",
                    (batch_id, now, finding["severity"], finding["confidence"],
                     finding["evidence"], json.dumps(finding["flow_refs"]),
                     finding.get("recommended_action", ""), int(finding.get("block_now", False)),
                     json.dumps(finding.get("flow_evidence", []), ensure_ascii=False),
                     json.dumps(finding.get("source_evidence", []), ensure_ascii=False)))
            self._rollup_batch_locked(batch_id)
            self.conn.execute("DELETE FROM flow_buckets WHERE batch_id=?", (batch_id,))
            self.conn.execute(
                "UPDATE analysis_batches SET status='completed',completed_at=? WHERE id=?",
                (now, batch_id))

    def fail_batch(self, batch_id: int, error: str):
        with self._lock:
            self.conn.execute("""UPDATE analysis_batches SET status='pending',error=?
                WHERE id=? AND status='running'""", (str(error)[:2000], batch_id))
            self.conn.commit()

    def cleanup_old_records(self) -> dict:
        detail_cutoff, audit_cutoff = self._cutoff(24), self._cutoff(24 * 30)
        expired_batches = expired_flows = 0
        orphan_count = 0
        with self._atomic():
            batches = self.conn.execute("""SELECT id,flow_count FROM analysis_batches
                WHERE status IN('pending','running') AND created_at<?""", (detail_cutoff,)).fetchall()
            for batch in batches:
                self._rollup_batch_locked(batch["id"])
                expired_flows += self.conn.execute(
                    "DELETE FROM flow_buckets WHERE batch_id=?", (batch["id"],)).rowcount
                now = datetime.now().isoformat()
                self.conn.execute("""UPDATE analysis_batches SET status='expired',completed_at=?
                    WHERE id=?""", (now, batch["id"]))
                self.conn.execute("""INSERT INTO analysis_runs
                    (batch_id,analyzed_at,status,risk_score,flow_count)
                    VALUES(?,?,'expired',-1,?)""", (batch["id"], now, batch["flow_count"]))
                expired_batches += 1
            orphan_count = self.conn.execute("""SELECT COUNT(*) FROM flow_buckets
                WHERE batch_id IS NULL AND last_seen<?""", (detail_cutoff,)).fetchone()[0]
            if orphan_count:
                self.conn.execute("""INSERT INTO hourly_rollups
                    (hour_start,protocol,sent_bytes,received_bytes,flow_count)
                    SELECT substr(bucket_start,1,13)||':00:00',protocol,
                           SUM(sent_bytes),SUM(received_bytes),COUNT(*)
                    FROM flow_buckets WHERE batch_id IS NULL AND last_seen<?
                    GROUP BY substr(bucket_start,1,13),protocol
                    ON CONFLICT(hour_start,protocol) DO UPDATE SET
                      sent_bytes=sent_bytes+excluded.sent_bytes,
                      received_bytes=received_bytes+excluded.received_bytes,
                      flow_count=flow_count+excluded.flow_count""", (detail_cutoff,))
                expired_flows += self.conn.execute("""DELETE FROM flow_buckets
                    WHERE batch_id IS NULL AND last_seen<?""", (detail_cutoff,)).rowcount
            old_rollups = self.conn.execute(
                "DELETE FROM hourly_rollups WHERE hour_start<?", (audit_cutoff,)).rowcount
            old_runs = self.conn.execute(
                "DELETE FROM analysis_runs WHERE analyzed_at<?", (audit_cutoff,)).rowcount
            self.conn.execute("DELETE FROM threat_intel_cache WHERE expires_at<?",
                              (datetime.now().isoformat(),))
            self.conn.execute("DELETE FROM external_api_usage WHERE used_at<?",
                              (self._cutoff(24 * 35),))
            self.conn.execute("""DELETE FROM analysis_batches
                WHERE status IN('completed','expired') AND created_at<?""", (audit_cutoff,))
        with self._lock:
            if not self.conn.in_transaction:
                self.conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                self.conn.execute("PRAGMA incremental_vacuum(200)")
        return {"expired_batches": expired_batches, "expired_flows": expired_flows,
                "old_rollups": old_rollups, "old_runs": old_runs,
                "warning": bool(expired_batches or orphan_count)}

    @staticmethod
    def normalize_ip(ip: str) -> str:
        value = str(ip or "").strip()
        if not value or "/" in value:
            raise ValueError("A single IP address is required")
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as exc:
            raise ValueError("Invalid IPv4 or IPv6 address") from exc

    def add_trusted_ip(self, ip: str, note: str = "") -> dict:
        value, now = self.normalize_ip(ip), datetime.now().isoformat()
        with self._lock:
            try:
                self.conn.execute("INSERT INTO trusted_ips(ip,note,added_at) VALUES(?,?,?)",
                                  (value, str(note or "").strip(), now))
                self.conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"{value} is already trusted") from exc
        return {"ip": value, "note": str(note or "").strip(), "added_at": now}

    def remove_trusted_ip(self, ip: str) -> bool:
        value = self.normalize_ip(ip)
        with self._lock:
            cursor = self.conn.execute("DELETE FROM trusted_ips WHERE ip=?", (value,))
            self.conn.commit()
            return cursor.rowcount > 0

    def is_trusted_ip(self, ip: str) -> bool:
        try: value = self.normalize_ip(ip)
        except ValueError: return False
        with self._lock:
            return self.conn.execute("SELECT 1 FROM trusted_ips WHERE ip=?", (value,)).fetchone() is not None

    def get_trusted_ips(self) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self.conn.execute(
                "SELECT * FROM trusted_ips ORDER BY added_at DESC").fetchall()]

    def add_blocked_ip(self, ip: str, reason: str):
        value = self.normalize_ip(ip)
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO blocked_ips(ip,reason,blocked_at) VALUES(?,?,?)",
                              (value, reason, datetime.now().isoformat()))
            self.conn.commit()

    def remove_blocked_ip(self, ip: str):
        value = self.normalize_ip(ip)
        with self._lock:
            self.conn.execute("DELETE FROM blocked_ips WHERE ip=?", (value,))
            self.conn.commit()

    def get_blocked_ips(self) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self.conn.execute(
                "SELECT * FROM blocked_ips ORDER BY blocked_at DESC").fetchall()]

    def _flow_summary(self, where: str, params: tuple, limit: int) -> list[dict]:
        return [dict(row) for row in self.conn.execute(f"""SELECT remote_ip AS dst_ip,
            remote_port AS dst_port,process,protocol,SUM(sent_bytes+received_bytes) AS total_bytes,
            COUNT(*) AS conn_count,MIN(first_seen) AS first_seen,MAX(last_seen) AS last_seen,
            SUM(sent_bytes) AS sent_bytes,SUM(received_bytes) AS received_bytes
            FROM flow_buckets WHERE {where}
              AND NOT EXISTS(SELECT 1 FROM trusted_ips WHERE ip=flow_buckets.remote_ip)
            GROUP BY remote_ip,remote_port,process,protocol ORDER BY total_bytes DESC LIMIT ?""",
            (*params, limit)).fetchall()]

    def get_summary(self, hours: int = 1, limit: int = 1000000) -> list[dict]:
        with self._lock: return self._flow_summary("last_seen>=?", (self._cutoff(hours),), limit)

    def get_summary_since(self, since_ts: str, limit: int = 1000000) -> list[dict]:
        with self._lock: return self._flow_summary("last_seen>?", (since_ts,), limit)

    def get_last_analysis_time(self) -> str | None:
        with self._lock:
            row = self.conn.execute("""SELECT analyzed_at FROM analysis_runs WHERE risk_score>=0
                ORDER BY analyzed_at DESC LIMIT 1""").fetchone()
            return row[0] if row else None

    def _traffic_totals(self, cutoff: str) -> dict:
        rollup = self.conn.execute("""SELECT COALESCE(SUM(sent_bytes),0),
            COALESCE(SUM(received_bytes),0),COALESCE(SUM(flow_count),0)
            FROM hourly_rollups WHERE hour_start>=?""", (cutoff,)).fetchone()
        active = self.conn.execute("""SELECT COALESCE(SUM(sent_bytes),0),
            COALESCE(SUM(received_bytes),0),COUNT(*) FROM flow_buckets WHERE last_seen>=?""",
            (cutoff,)).fetchone()
        sent, received, flows = rollup[0]+active[0], rollup[1]+active[1], rollup[2]+active[2]
        return {"upload": sent, "download": received, "total": sent+received,
                "conn_count": flows, "flow_count": flows}

    def get_traffic_stats(self) -> list[dict]:
        with self._lock:
            return [{"label":t("Son 1 Saat"),"short":t("Saat"),**self._traffic_totals(self._cutoff(1))},
                    {"label":t("Bugün"),"short":t("Bugün"),**self._traffic_totals(self._cutoff(24))},
                    {"label":t("Bu Hafta"),"short":t("Hafta"),**self._traffic_totals(self._cutoff(168))},
                    {"label":t("Son 30 Gün"),"short":t("30 Gün"),**self._traffic_totals(self._cutoff(720))}]

    def get_stats(self) -> dict:
        with self._lock:
            flows = self._traffic_totals(self._cutoff(24))["flow_count"]
            return {"today_connections": flows, "today_flows": flows,
                "total_threats": self.conn.execute("SELECT COUNT(*) FROM security_findings").fetchone()[0],
                "blocked_ips": self.conn.execute("SELECT COUNT(*) FROM blocked_ips").fetchone()[0],
                "total_reports": self.conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]}

    def get_traffic_speed(self, minutes: int = 5) -> dict:
        with self._lock:
            row = self.conn.execute("""SELECT COALESCE(SUM(sent_bytes),0),
                COALESCE(SUM(received_bytes),0) FROM flow_buckets WHERE last_seen>=?""",
                ((datetime.now()-timedelta(minutes=minutes)).isoformat(),)).fetchone()
        seconds = max(1, minutes*60)
        return {"upload_kbs":row[0]/1024/seconds,"download_kbs":row[1]/1024/seconds,
                "total_kbs":(row[0]+row[1])/1024/seconds,"total_bytes":row[0]+row[1]}

    def get_top_processes(self, hours: int = 1, limit: int = 5) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self.conn.execute("""SELECT process,
                SUM(sent_bytes+received_bytes) AS total_bytes,COUNT(*) AS conn_count
                FROM flow_buckets WHERE last_seen>=? GROUP BY process
                ORDER BY total_bytes DESC LIMIT ?""", (self._cutoff(hours), limit)).fetchall()]

    def get_recent_flows(self, limit: int = 12, hours: int = 4) -> list[dict]:
        """Most recently seen remote targets, newest first (dashboard live feed)."""
        with self._lock:
            return [dict(row) for row in self.conn.execute("""SELECT remote_ip AS dst_ip,
                remote_port AS dst_port,process,protocol,
                SUM(sent_bytes+received_bytes) AS total_bytes,
                COUNT(*) AS conn_count,MAX(last_seen) AS last_seen
                FROM flow_buckets WHERE last_seen>=?
                GROUP BY remote_ip,remote_port,process,protocol
                ORDER BY last_seen DESC LIMIT ?""",
                (self._cutoff(hours), limit)).fetchall()]

    def get_active_connections_count(self, minutes: int = 60) -> int:
        with self._lock:
            return self.conn.execute("SELECT COUNT(*) FROM flow_buckets WHERE last_seen>=?",
                ((datetime.now()-timedelta(minutes=minutes)).isoformat(),)).fetchone()[0]

    def get_protocol_distribution(self, hours: int = 24) -> dict:
        with self._lock:
            rows = self.conn.execute("""SELECT protocol,COUNT(*) AS count,
                SUM(sent_bytes+received_bytes) AS total_bytes FROM flow_buckets
                WHERE last_seen>=? GROUP BY protocol""", (self._cutoff(hours),)).fetchall()
        total = sum(row["count"] for row in rows)
        return {row["protocol"]:{"count":row["count"],"bytes":row["total_bytes"],
                "percentage":round(row["count"]*100/total,1) if total else 0} for row in rows}

    def get_traffic_timeline(self, hours: int = 24, points: int = 12) -> list[dict]:
        now, results, interval = datetime.now(), [], max(1, hours*60//max(1, points))
        with self._lock:
            for index in range(points):
                end, start = now-timedelta(minutes=index*interval), now-timedelta(minutes=(index+1)*interval)
                row = self.conn.execute("""SELECT COALESCE(SUM(sent_bytes+received_bytes),0),COUNT(*)
                    FROM flow_buckets WHERE last_seen>=? AND last_seen<?""",
                    (start.isoformat(), end.isoformat())).fetchone()
                results.append({"time":start.strftime("%H:%M"),"bytes":row[0],
                                "connections":row[1],"flows":row[1]})
        return list(reversed(results))

    def _findings_by_batch(self, batch_ids: list[int]) -> dict[int, list[dict]]:
        """Bulgu satirlarini tek sorguda topla (rapor basina ayri sorgu = N+1)."""
        unique = sorted({int(value) for value in batch_ids if value is not None})
        if not unique:
            return {}
        placeholders = ",".join("?" for _ in unique)
        grouped: dict[int, list[dict]] = {}
        for row in self.conn.execute(
                f"SELECT * FROM security_findings WHERE batch_id IN ({placeholders}) "
                "ORDER BY batch_id, id", unique):
            finding = dict(row)
            for field in ("flow_evidence", "flow_refs", "source_evidence"):
                try:
                    finding[field] = json.loads(finding.get(field) or "[]")
                except json.JSONDecodeError:
                    finding[field] = []
            grouped.setdefault(finding["batch_id"], []).append(finding)
        return grouped

    def get_all_reports(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("""SELECT id,batch_id,analyzed_at AS created_at,
                'gemini' AS provider,risk_score,status,flow_count,report_json FROM analysis_runs
                ORDER BY analyzed_at DESC LIMIT ? OFFSET ?""", (limit, offset)).fetchall()
            findings_by_batch = self._findings_by_batch(
                [row["batch_id"] for row in rows])
            result=[]
            for row in rows:
                item=dict(row)
                findings = findings_by_batch.get(item["batch_id"], [])
                try:
                    content = json.loads(item.get("report_json") or "{}")
                except json.JSONDecodeError:
                    content = {}
                if not content:
                    content={"risk_score":item["risk_score"],"status":item["status"],
                        "flow_count":item["flow_count"],"analysis_time":item["created_at"],
                        "findings":findings}
                content.setdefault("findings", findings)
                item["content"]=json.dumps(content,ensure_ascii=False)
                result.append(item)
            return result

    def get_security_findings(self, limit: int = 100, offset: int = 0,
                              status: str | None = None) -> list[dict]:
        with self._lock:
            if status:
                rows=self.conn.execute("""SELECT * FROM security_findings WHERE status=?
                    ORDER BY created_at DESC LIMIT ? OFFSET ?""",(status,limit,offset)).fetchall()
            else:
                rows=self.conn.execute("SELECT * FROM security_findings ORDER BY created_at DESC LIMIT ? OFFSET ?",
                                       (limit,offset)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                for field in ("flow_refs", "flow_evidence", "source_evidence"):
                    try: item[field] = json.loads(item.get(field) or "[]")
                    except json.JSONDecodeError: item[field] = []
                result.append(item)
            return result

    def resolve_security_finding(self, finding_id: int, resolved: bool = True) -> bool:
        with self._lock:
            cursor=self.conn.execute("UPDATE security_findings SET status=? WHERE id=?",
                                     ("resolved" if resolved else "open",finding_id))
            self.conn.commit(); return cursor.rowcount>0

    def delete_security_finding(self, finding_id: int) -> bool:
        with self._lock:
            cursor=self.conn.execute("DELETE FROM security_findings WHERE id=?",(finding_id,))
            self.conn.commit(); return cursor.rowcount>0

    def get_db_size_mb(self) -> float:
        size=sum(item.stat().st_size for item in
            (self.path,Path(str(self.path)+"-wal"),Path(str(self.path)+"-shm")) if item.exists())
        return size/(1024*1024)

    def close(self):
        with self._lock:
            if self._closed: return
            self.conn.commit(); self.conn.close(); self._closed=True

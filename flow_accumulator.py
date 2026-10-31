"""Thread-safe in-memory minute-flow accumulation."""

import threading


class FlowAccumulator:
    def __init__(self, db):
        self.db = db
        self._lock = threading.Lock()
        self._buckets: dict[tuple, dict] = {}

    @staticmethod
    def _merge(current: dict, data: dict):
        for field in ("sent_bytes", "received_bytes", "sent_packets", "received_packets"):
            current[field] = current.get(field, 0) + data.get(field, 0)
        current["first_seen"] = min(current["first_seen"], data["first_seen"])
        current["last_seen"] = max(current["last_seen"], data["last_seen"])

    def upsert_flow_bucket(self, data: dict):
        key = tuple(data[field] for field in (
            "bucket_start", "local_ip", "local_port", "remote_ip", "remote_port",
            "protocol", "process",
        ))
        with self._lock:
            current = self._buckets.get(key)
            if current is None:
                self._buckets[key] = dict(data)
            else:
                self._merge(current, data)

    def flush(self):
        with self._lock:
            pending, self._buckets = self._buckets, {}
        try:
            # All buckets are written in one transaction (per-bucket commit was ~85x slower).
            for bucket in pending.values():
                self.db.upsert_flow_bucket(bucket, commit=False)
            self.db.flush()
        except Exception:
            self.db.rollback()
            with self._lock:
                for key, bucket in pending.items():
                    current = self._buckets.get(key)
                    if current is None:
                        self._buckets[key] = bucket
                    else:
                        self._merge(current, bucket)
            raise

    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)

"""One-time destructive v0.5 storage reset with fail-safe ordering."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from config import DB_PATH, load_settings, save_settings
from database import Database
from kill_switch import remove_all_netsonar_rules


def needs_v05_reset(path: str | Path = DB_PATH) -> bool:
    target = Path(path)
    if not target.exists():
        return False
    try:
        connection = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT value FROM app_metadata WHERE key='schema_version'"
            ).fetchone()
            return not row or row[0] != "5"
        finally:
            connection.close()
    except sqlite3.Error:
        return True


def perform_v05_reset(path: str | Path = DB_PATH,
                      firewall_cleanup=remove_all_netsonar_rules) -> None:
    """Build/verify replacement first; never delete old DB after a failed prerequisite."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".v05-new")
    temporary_sidecars = [Path(str(temporary) + suffix) for suffix in ("-wal", "-shm")]
    for item in [temporary, *temporary_sidecars]:
        if item.exists():
            item.unlink()
    replacement = Database(temporary)
    try:
        replacement.conn.execute(
            "INSERT OR REPLACE INTO app_metadata(key, value) VALUES('write_test', 'ok')"
        )
        replacement.conn.commit()
        check = replacement.conn.execute(
            "SELECT value FROM app_metadata WHERE key='write_test'"
        ).fetchone()
        if not check or check[0] != "ok":
            raise RuntimeError("v0.5 database write verification failed")
        replacement.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        replacement.close()
    if target.resolve() == Path(DB_PATH).resolve():
        settings = load_settings()
        settings["AUTO_BLOCK_ENABLED"] = False
        save_settings(settings)
    if not firewall_cleanup():
        for item in [temporary, *temporary_sidecars]:
            if item.exists():
                item.unlink()
        raise RuntimeError("NetSonar firewall cleanup failed; old database preserved")
    for sidecar in (Path(str(target) + "-wal"), Path(str(target) + "-shm")):
        if sidecar.exists():
            sidecar.unlink()
    os.replace(temporary, target)
    for item in temporary_sidecars:
        if item.exists():
            item.unlink()


def initialize_new_database(path: str | Path = DB_PATH) -> None:
    if not Path(path).exists():
        database = Database(path)
        database.close()

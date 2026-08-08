"""NetSonar application and one-shot CLI entry point."""

import argparse
import ctypes
import logging
import sys
import time

from config import AI_PROVIDER, DB_PATH
from instance_lock import SingleInstanceLock
from logging_config import get_logger, setup_logging

setup_logging()
log = get_logger("Main")


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _require_admin():
    if _is_admin():
        return
    parameters = " ".join(f'"{arg}"' for arg in (sys.argv[1:] if getattr(sys, "frozen", False)
                                                   else sys.argv))
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, parameters, None, 1)
    raise SystemExit(0)


def _confirm_migration(gui_mode: bool, accepted_by_flag: bool) -> bool:
    from migration import needs_v05_reset
    if not needs_v05_reset(DB_PATH):
        return True
    if accepted_by_flag:
        return True
    if not gui_mode:
        print("v0.5 storage reset requires --accept-v05-reset. Existing history will be deleted.")
        return False
    from PyQt6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication(sys.argv)
    answer = QMessageBox.warning(
        None, "NetSonar v0.5 Storage Migration",
        "NetSonar traffic/report/trusted/blocked history and only NetSonar firewall rules "
        "must be reset. Settings and exported reports are preserved. Continue?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes


def _hide_console_for_gui():
    if sys.platform != "win32":
        return
    window = ctypes.windll.kernel32.GetConsoleWindow()
    if window:
        ctypes.windll.user32.ShowWindow(window, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="NetSonar Network Monitor")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--block", metavar="IP")
    parser.add_argument("--unblock", metavar="IP")
    parser.add_argument("--list-blocked", action="store_true")
    parser.add_argument("--no-gui", action="store_true")
    parser.add_argument("--accept-v05-reset", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    one_shot = bool(args.analyze or args.block or args.unblock or args.list_blocked)
    gui_mode = not args.no_gui and not one_shot
    _require_admin()
    lock = SingleInstanceLock()
    if not lock.acquire():
        print("NetSonar is already running.")
        return 1
    db = engine = scheduler = None
    try:
        if not _confirm_migration(gui_mode, args.accept_v05_reset):
            return 2
        from migration import needs_v05_reset, perform_v05_reset
        if needs_v05_reset(DB_PATH):
            perform_v05_reset(DB_PATH)
        if gui_mode:
            _hide_console_for_gui()
        from ai_analyzer import AIAnalyzer
        from capture_engine import CaptureEngine
        from database import Database
        from kill_switch import block_ip, list_blocked, reconcile_firewall, unblock_ip
        from scheduler import AnalysisScheduler
        db = Database()
        reconcile_firewall(db)
        if args.block:
            ok = block_ip(args.block, reason="Manual CLI block", db=db)
            print("Blocked." if ok else "Block failed.")
            return 0 if ok else 1
        if args.unblock:
            ok = unblock_ip(args.unblock, db=db)
            print("Unblocked." if ok else "Unblock failed.")
            return 0 if ok else 1
        if args.list_blocked:
            blocked = list_blocked()
            print("Blocked IPs:" if blocked else "No blocked IPs.")
            for ip in blocked:
                print(f"  {ip}")
            return 0
        log.info("AI provider: %s", AI_PROVIDER.upper())
        analyzer = AIAnalyzer(db)
        engine = CaptureEngine(db)
        scheduler = AnalysisScheduler(db, analyzer)
        engine.start()
        scheduler.start()
        if args.analyze:
            scheduler.run_now()
            return 0
        if gui_mode:
            from app_gui import run_gui
            return int(run_gui(db=db, analyzer=analyzer, engine=engine, scheduler=scheduler))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        if scheduler:
            scheduler.stop()
        if engine:
            engine.stop()
        if db:
            db.close()
        lock.release()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log.critical("Unhandled error: %s", exc, exc_info=True)
        raise SystemExit(1)

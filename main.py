"""NetSonar — Ana Giris Noktasi.

GUI ile baslatir (varsayilan). Ozel bayraklar icin CLI modu desteklenir.

Kullanim::

    python main.py                    GUI penceresi acilir
    python main.py --analyze          Anlik AI analizi (konsol)
    python main.py --block IP         IP engelle
    python main.py --unblock IP       IP engelini kaldir
    python main.py --list-blocked     Engellenen IP'leri listele
    python main.py --no-gui           Konsol modunda calistir
"""

import sys
import ctypes
import argparse
import logging

from logging_config import setup_logging, get_logger
from database import Database
from capture_engine import CaptureEngine
from ai_analyzer import AIAnalyzer
from scheduler import AnalysisScheduler
from kill_switch import block_ip, unblock_ip, list_blocked
from config import AI_PROVIDER

setup_logging()
log = get_logger("Main")


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _require_admin():
    """Admin degilse UAC ile yeniden baslatir."""
    if not _is_admin():
        try:
            if getattr(sys, "frozen", False):
                parameters = " ".join(f'"{a}"' for a in sys.argv[1:])
            else:
                parameters = " ".join(f'"{a}"' for a in sys.argv)
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas",
                sys.executable,
                parameters,
                None, 1,
            )
        except Exception:
            pass
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="NetSonar Network Monitor")
    parser.add_argument("--analyze",      action="store_true", help="Anlik AI analizi")
    parser.add_argument("--block",        metavar="IP",        help="IP engelle")
    parser.add_argument("--unblock",      metavar="IP",        help="IP engelini kaldir")
    parser.add_argument("--list-blocked", action="store_true", help="Engellenen IP'leri listele")
    parser.add_argument("--no-gui",       action="store_true", help="Konsol modunda calistir")
    args = parser.parse_args()

    _require_admin()

    # Windows'ta GUI modunda konsol penceresini gizle
    if not args.no_gui and sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            console_window = kernel32.GetConsoleWindow()
            if console_window:
                user32.ShowWindow(console_window, 0)  # SW_HIDE = 0
        except Exception:
            pass

    db = Database()

    # ── Tek seferlik CLI komutlari ─────────────────────────────────
    if args.block:
        ok = block_ip(args.block, reason="Manuel CLI engelleme", db=db)
        print("Engellendi." if ok else "Engellenemedi.")
        sys.exit(0 if ok else 1)

    if args.unblock:
        ok = unblock_ip(args.unblock)
        print("Engel kaldirildi." if ok else "Kaldirildi.")
        sys.exit(0 if ok else 1)

    if args.list_blocked:
        blocked = list_blocked()
        print("Engellenen IP'ler:" if blocked else "Engellenen IP yok.")
        for ip in blocked:
            print(f"  {ip}")
        sys.exit(0)

    # ── Ortak servisler ───────────────────────────────────────────
    log.info(f"AI Saglayici: {AI_PROVIDER.upper()}")

    analyzer  = AIAnalyzer(db)
    engine    = CaptureEngine(db)
    scheduler = AnalysisScheduler(db, analyzer)

    engine.start()
    scheduler.start()

    if args.analyze:
        log.info("Anlik analiz calistiriliyor...")
        scheduler.run_now()
        engine.stop()
        scheduler.stop()
        sys.exit(0)

    # ── GUI Modu (varsayilan) ─────────────────────────────────────
    if not args.no_gui:
        from app_gui import run_gui
        sys.exit(run_gui(db=db, analyzer=analyzer, engine=engine, scheduler=scheduler))

    # ── Konsol Modu ───────────────────────────────────────────────
    import time
    from notifier import notify
    notify("NetSonar Basladi", "Ag trafigi izleniyor (konsol modu).", "info")
    log.info("Izleme aktif -- Durdurmak icin Ctrl+C'ye basin.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Durduruluyor...")
    finally:
        engine.stop()
        scheduler.stop()
        log.info("Gule gule.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.critical(f"Handle edilmemis hata: {exc}", exc_info=True)
        sys.exit(1)

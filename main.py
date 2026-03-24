"""AgTara — Ana Giris Noktasi.

GUI ile baslatir (varsayilan). Ozel bayraklar icin CLI modu desteklenir.

Kullanim::

    python main.py                    GUI penceresi acilir
    python main.py --analyze          Anlik AI analizi (konsol)
    python main.py --block IP         IP engelle
    python main.py --unblock IP       IP engelini kaldir
    python main.py --list-blocked     Engellenen IP'leri listele
    python main.py --vt IP            VirusTotal sorgusu
    python main.py --no-gui           Konsol modunda calistir
"""

import sys
import ctypes
import argparse

from database import Database
from capture_engine import CaptureEngine
from ai_analyzer import AIAnalyzer
from scheduler import AnalysisScheduler
from kill_switch import block_ip, unblock_ip, list_blocked
from threat_intel import check_ip
from config import AI_PROVIDER


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _require_admin():
    """Admin degilse UAC ile yeniden baslatir."""
    if not _is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas",
                sys.executable,
                " ".join(f'"{a}"' for a in sys.argv),
                None, 1,
            )
        except Exception:
            pass
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="AgTara Network Monitor")
    parser.add_argument("--analyze",      action="store_true", help="Anlik AI analizi")
    parser.add_argument("--block",        metavar="IP",        help="IP engelle")
    parser.add_argument("--unblock",      metavar="IP",        help="IP engelini kaldir")
    parser.add_argument("--list-blocked", action="store_true", help="Engellenen IP'leri listele")
    parser.add_argument("--vt",           metavar="IP",        help="VirusTotal sorgusu")
    parser.add_argument("--no-gui",       action="store_true", help="Konsol modunda calistir")
    args = parser.parse_args()

    _require_admin()

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

    if args.vt:
        result = check_ip(args.vt)
        icon = "TEHDIT" if result["is_threat"] else "Temiz"
        print(f"\n{icon}  {args.vt} ({result['country']})")
        print(
            f"  Kotu niyetli: {result['malicious']}  "
            f"Supheli: {result['suspicious']}  "
            f"Temiz: {result['harmless']}"
        )
        sys.exit(0)

    # ── Ortak servisler ───────────────────────────────────────────
    print(f"[AgTara] AI Saglayici: {AI_PROVIDER.upper()}")

    analyzer  = AIAnalyzer(db)
    engine    = CaptureEngine(db)
    scheduler = AnalysisScheduler(db, analyzer)

    engine.start()
    scheduler.start()

    if args.analyze:
        print("[AgTara] Anlik analiz calistiriliyor...")
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
    notify("AgTara Basladi", "Ag trafigi izleniyor (konsol modu).", "info")
    print("[AgTara] Izleme aktif -- Durdurmak icin Ctrl+C'ye basin.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[AgTara] Durduruluyor...")
    finally:
        engine.stop()
        scheduler.stop()
        print("[AgTara] Gule gule.")


if __name__ == "__main__":
    main()

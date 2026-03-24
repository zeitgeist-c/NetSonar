"""
AgTara — Zamanlanmış Analiz (Scheduler)
APScheduler ile AI analizini ve Threat Intelligence taramasını tetikler.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import ANALYSIS_INTERVAL_MINUTES
from database import Database
from ai_analyzer import AIAnalyzer
from threat_intel import bulk_check
from notifier import notify_report_ready, notify_vt_threat
import json


def _run_analysis(db: Database, analyzer: AIAnalyzer):
    """Tam analiz döngüsü: Tehdit intel + AI raporu."""
    print("\n[Scheduler] 🔄 Analiz başlıyor...")

    # 1. Son özetin IP listesini al
    summary = db.get_summary(hours=1)
    if not summary:
        print("[Scheduler] Analiz edilecek veri yok, atlanıyor.")
        return

    external_ips = list({row["dst_ip"] for row in summary})

    # 2. VirusTotal Threat Intelligence taraması
    print(f"[Scheduler] 🌐 {len(external_ips)} IP VirusTotal'a sorgulanıyor...")
    vt_results = bulk_check(external_ips)
    threats = [r for r in vt_results if r["is_threat"]]
    for threat in threats:
        notify_vt_threat(threat["ip"], threat["malicious"], threat["country"])

    # 3. AI analizi
    print("[Scheduler] 🤖 AI analizi çalışıyor...")
    report = analyzer.analyze(hours=1)
    risk   = report.get("risk_score", 0)
    status = report.get("status", "BİLİNMİYOR")

    notify_report_ready(risk, status)

    # 4. Özet çıktısı
    print("\n" + "═" * 55)
    print(f"  AGTARA RAPORU — Risk: {risk:.1f}/10 | {status}")
    print("═" * 55)
    suspicious = report.get("suspicious_connections", [])
    for i, conn in enumerate(suspicious[:5], 1):
        print(f"  {i}. {conn.get('ip')} — {conn.get('reason', '')}")
        print(f"     Eylem: {conn.get('action', '')}")
    print(f"\n  {report.get('summary', '')}")
    print("═" * 55 + "\n")


class AnalysisScheduler:
    def __init__(self, db: Database, analyzer: AIAnalyzer):
        self.db = db
        self.analyzer = analyzer
        self._scheduler = BackgroundScheduler(timezone="Europe/Istanbul")

    def start(self):
        self._scheduler.add_job(
            func=lambda: _run_analysis(self.db, self.analyzer),
            trigger=IntervalTrigger(minutes=ANALYSIS_INTERVAL_MINUTES),
            id="ai_analysis",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.start()
        print(f"[Scheduler] ✅ Her {ANALYSIS_INTERVAL_MINUTES} dakikada analiz planlandı.")

    def run_now(self):
        """Zamanlayıcıyı beklemeden analizi hemen çalıştır."""
        _run_analysis(self.db, self.analyzer)

    def stop(self):
        self._scheduler.shutdown(wait=False)
        print("[Scheduler] 🛑 Zamanlayıcı durduruldu.")

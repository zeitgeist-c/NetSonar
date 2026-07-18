"""
NetSonar — Zamanlanmış Analiz (Scheduler)
APScheduler ile AI analizini ve Threat Intelligence taramasını tetikler.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import load_settings, DB_CLEANUP_INTERVAL_HOURS
from database import Database
from ai_analyzer import AIAnalyzer
from notifier import notify_report_ready

log = logging.getLogger("NetSonar.Scheduler")


def _run_analysis(db: Database, analyzer: AIAnalyzer):
    """Tam analiz döngüsü: Tehdit intel + AI raporu."""
    log.info("Analiz başlıyor...")

    # 1. Son özetin IP listesini al
    summary = db.get_summary(hours=1)
    if not summary:
        log.info("Analiz edilecek veri yok, atlanıyor.")
        return

    # 2. AI analizi
    log.info("AI analizi çalışıyor...")
    report = analyzer.analyze(hours=1)
    risk   = report.get("risk_score", 0)
    status = report.get("status", "BİLİNMİYOR")

    notify_report_ready(risk, status)

    # 4. Özet çıktısı
    suspicious = report.get("suspicious_connections", [])
    log.info("NETSONAR RAPORU — Risk: %.1f/10 | %s", risk, status)
    for i, conn in enumerate(suspicious[:5], 1):
        log.info("  %d. %s — %s", i, conn.get('ip'), conn.get('reason', ''))
        log.info("     Eylem: %s", conn.get('action', ''))
    log.info("Özet: %s", report.get('summary', ''))


class AnalysisScheduler:
    def __init__(self, db: Database, analyzer: AIAnalyzer):
        self.db = db
        self.analyzer = analyzer
        self._scheduler = BackgroundScheduler()

    def start(self):
        if self._scheduler.running:
            return
        settings = load_settings()
        
        auto_analysis = settings.get("AUTO_ANALYSIS_ENABLED", True)
        interval_minutes = settings.get("ANALYSIS_INTERVAL_MINUTES", 60)
        
        if auto_analysis:
            self._scheduler.add_job(
                func=lambda: _run_analysis(self.db, self.analyzer),
                trigger=IntervalTrigger(minutes=interval_minutes),
                id="ai_analysis",
                replace_existing=True,
                max_instances=1,
            )
            log.info("Her %d dakikada analiz planlandı (otomatik analiz açık).", interval_minutes)
        else:
            log.info("Otomatik analiz kapalı, analiz yapılmayacak.")
        
        # Veritabanı temizlik job'u
        self._scheduler.add_job(
            func=lambda: self.db.cleanup_old_records(),
            trigger=IntervalTrigger(hours=DB_CLEANUP_INTERVAL_HOURS),
            id="db_cleanup",
            replace_existing=True,
            max_instances=1,
        )
        
        self._scheduler.start()
        log.info("Her %d saatte temizlik planlandı.", DB_CLEANUP_INTERVAL_HOURS)

    def run_now(self):
        """Zamanlayıcıyı beklemeden analizi hemen çalıştır."""
        _run_analysis(self.db, self.analyzer)

    def stop(self):
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        log.info("Zamanlayıcı durduruldu.")

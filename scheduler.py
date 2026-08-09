"""Live scheduler for pending flow analysis and database maintenance."""

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ai_analyzer import AIAnalyzer
from config import DB_CLEANUP_INTERVAL_HOURS, load_settings
from database import Database
from notifier import notify_report_ready

log = logging.getLogger("NetSonar.Scheduler")
_analysis_lock = threading.Lock()


def _run_analysis(db: Database, analyzer: AIAnalyzer):
    """Run manual and scheduled analysis through the same single-instance lock."""
    if not _analysis_lock.acquire(blocking=False):
        log.info("Analysis is already running; duplicate request skipped")
        return
    try:
        report = analyzer.analyze_pending()
        if report.get("_meta", {}).get("skipped"):
            log.info("No pending flows; analysis skipped")
            return report
        risk = report.get("risk_score", 0)
        status = report.get("status", "UNKNOWN")
        if risk < 0:
            from notifier import notify_analysis_failed
            notify_analysis_failed(report.get("summary", "Analysis failed"), analyzer.provider)
        if risk >= 0 and report.get("findings"):
            notify_report_ready(risk, status)
        log.info("NETSONAR REPORT - Risk: %.1f/10 | %s", risk, status)
        return report
    finally:
        _analysis_lock.release()


def _run_cleanup(db: Database):
    result = db.cleanup_old_records()
    if result.get("warning"):
        from notifier import notify_retention_warning
        notify_retention_warning(result.get("expired_flows", 0))
    return result


class AnalysisScheduler:
    def __init__(self, db: Database, analyzer: AIAnalyzer):
        self.db = db
        self.analyzer = analyzer
        self._scheduler = BackgroundScheduler()

    def _configure_analysis_job(self):
        settings = load_settings()
        self._scheduler.remove_job("ai_analysis") if self._scheduler.get_job("ai_analysis") else None
        if settings.get("AUTO_ANALYSIS_ENABLED", True):
            interval = max(1, int(settings.get("ANALYSIS_INTERVAL_MINUTES", 60)))
            self._scheduler.add_job(
                func=lambda: _run_analysis(self.db, self.analyzer),
                trigger=IntervalTrigger(minutes=interval), id="ai_analysis",
                replace_existing=True, max_instances=1,
                # Bilgisayar uyku/askida kaldiginda kacirilan periyodu, uygulama
                # yeniden calisabilir olur olmaz bir kez tamamla. Birikmis tum
                # periyotlari arka arkaya calistirma.
                coalesce=True, misfire_grace_time=7 * 24 * 60 * 60,
            )
            log.info("Analysis scheduled every %d minute(s)", interval)

    def start(self):
        if self._scheduler.running:
            return
        self._configure_analysis_job()
        self._scheduler.add_job(
            func=lambda: _run_cleanup(self.db),
            trigger=IntervalTrigger(hours=DB_CLEANUP_INTERVAL_HOURS),
            id="db_cleanup", replace_existing=True, max_instances=1,
        )
        self._scheduler.start()

    def reload_settings(self):
        """Apply enabled/interval changes immediately to a running scheduler."""
        self._configure_analysis_job()

    def run_now(self):
        return _run_analysis(self.db, self.analyzer)

    def stop(self):
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
        log.info("Scheduler stopped")

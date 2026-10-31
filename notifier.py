"""
NetSonar - Desktop notification module
======================================
Rule: notify only when an AI analysis completes or fails.
Other events (port alert, high traffic, etc.) are written to the log only.
"""

from i18n import t, status_text as t_status
import logging
import threading
import time

log = logging.getLogger("NetSonar.Notifier")
_cooldown_lock = threading.Lock()
_toast_cooldowns: dict[tuple[str, str], float] = {}
_TOAST_COOLDOWN_SECONDS = 10 * 60
# Port uyarisi paket basina log yaziyordu: 8888 gibi mesru ama "supheli"
# portlarda tek oturum bile log dosyasini saniyeler icinde sisirir. Ayni
# an alert for the same target+port pair is written once every 10 minutes.
_SUSPICIOUS_LOG_COOLDOWN_SECONDS = 10 * 60
_suspicious_log_lock = threading.Lock()
_suspicious_log_at: dict[tuple[str, int], float] = {}


def _send_toast(title: str, message: str, severity: str = "info"):
    """Windows toast bildirimi gonder. winotify → plyer fallback."""
    if not isinstance(message, str):
        message = str(message)
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="NetSonar",
            title=title,
            msg=message[:256] if len(message) > 256 else message,
            duration="long" if severity == "critical" else "short",
        )
        if severity == "critical":
            toast.set_audio(audio.Default, loop=False)
        toast.show()
        return
    except ImportError:
        pass
    except Exception as exc:
        log.error("winotify error: %s", exc)

    # Fallback: plyer
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message[:256],
            app_name="NetSonar",
            timeout=10 if severity == "critical" else 6,
        )
    except Exception as exc:
        log.warning("plyer fallback notification could not be sent: %s", exc)


def _log(title: str, message: str, level: str = "INFO"):
    """Her durumda log'a yaz."""
    levels = {"INFO": log.info, "WARNING": log.warning, "ERROR": log.error}
    logger_fn = levels.get(level, log.info)
    logger_fn("%s: %s", title, message)


# ─── Log-only events (NO notification is sent) ───────────────────────
def notify_suspicious_port(ip: str, port: int, process: str):
    key, now = (str(ip), int(port)), time.monotonic()
    with _suspicious_log_lock:
        if now < _suspicious_log_at.get(key, 0):
            return False
        _suspicious_log_at[key] = now + _SUSPICIOUS_LOG_COOLDOWN_SECONDS
        # Sinirsiz buyumesin: eskimis kayitlari ara sira temizle.
        if len(_suspicious_log_at) > 1024:
            for stale in [k for k, until in _suspicious_log_at.items() if until <= now]:
                _suspicious_log_at.pop(stale, None)
    _log(t("Şüpheli Port"), f"{process} -> {ip}:{port}", "WARNING")
    return True


def notify_high_traffic(ip: str, bytes_sent: int, process: str):
    mb = bytes_sent / (1024 * 1024)
    _log(t("Yüksek Transfer"), f"{process} -> {ip}: {mb:.1f} MB", "WARNING")


def notify_custom_alert(rule_name: str, ip: str, message: str):
    """Show at most one toast per rule and remote IP every ten minutes."""
    key, now = (str(rule_name), str(ip)), time.monotonic()
    with _cooldown_lock:
        if now < _toast_cooldowns.get(key, 0):
            return False
        _toast_cooldowns[key] = now + _TOAST_COOLDOWN_SECONDS
    _log(f"Custom alert: {rule_name}", message, "WARNING")
    _send_toast(f"NetSonar - {rule_name}", message, "warning")
    return True


def notify_retention_warning(expired_flows: int):
    return notify_custom_alert(
        "Analysis retention", "local",
        f"{expired_flows} flow detail record(s) expired after 24 hours without successful analysis. "
        "Anonymous traffic totals were preserved.",
    )


# ─── Bildirim GONDERILEN olaylar ─────────────────────────────────────
def notify_analysis_done(risk_score: float, status: str, provider: str, suspicious_count: int):
    """
    Called when an AI analysis completes successfully.
    Always sends a Windows notification.
    """
    if risk_score >= 7:
        severity = "critical"
        icon     = "🔴"
    elif risk_score >= 5:
        severity = "warning"
        icon     = "🟡"
    elif risk_score >= 3:
        severity = "info"
        icon     = "🔵"
    else:
        severity = "info"
        icon     = "🟢"

    title   = t("NetSonar — {icon} Risk: {score}/10", icon=icon, score=f"{risk_score:.1f}")
    message = (
        t("Durum: {status}", status=t_status(status)) + "\n"
        + t("Şüpheli bağlantı: {count} adet", count=suspicious_count) + "\n"
        + t("Sağlayıcı: {provider}", provider=provider.upper())
    )
    _log(title, message, severity.upper())
    _send_toast(title, message, severity)


def notify_analysis_failed(reason: str, provider: str):
    """
    Called when an AI analysis fails.
    Always sends a Windows notification.
    """
    title   = t("NetSonar — ⚠️ Analiz Başarısız")
    message = t("Sağlayıcı: {provider}", provider=provider.upper()) + "\n" + t("Hata: {reason}", reason=reason[:200])
    _log(title, message, "ERROR")
    _send_toast(title, message, "warning")


def notify_ip_blocked(ip: str):
    """IP block notification - always shown."""
    title   = t("NetSonar — 🛡️ IP Engellendi")
    message = t("{ip} güvenlik duvarına eklendi.", ip=ip)
    _log(title, message, "INFO")
    _send_toast(title, message, "info")


# Backwards compatibility - keep old callers of this function working
def notify_report_ready(risk_score: float, status: str):
    notify_analysis_done(risk_score, status, "ai", 0)

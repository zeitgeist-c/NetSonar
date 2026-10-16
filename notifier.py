"""
NetSonar — Masaustu Bildirim Modulu
==================================
Kural: Yalnizca AI analizi tamamlaninca veya basarisiz olunca bildirim goster.
Diger olaylar (port uyarisi, yuksek trafik vb.) sadece log'a yazilir.
"""

import logging
import threading
import time

log = logging.getLogger("NetSonar.Notifier")
_cooldown_lock = threading.Lock()
_toast_cooldowns: dict[tuple[str, str], float] = {}
_TOAST_COOLDOWN_SECONDS = 10 * 60


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
        log.error("winotify hatası: %s", exc)

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
        log.warning("plyer yedek bildirimi gönderilemedi: %s", exc)


def _log(title: str, message: str, level: str = "INFO"):
    """Her durumda log'a yaz."""
    levels = {"INFO": log.info, "WARNING": log.warning, "ERROR": log.error}
    logger_fn = levels.get(level, log.info)
    logger_fn("%s: %s", title, message)


# ─── Sadece loglanan olaylar (bildirim GÖNDERILMEZ) ──────────────────
def notify_suspicious_port(ip: str, port: int, process: str):
    _log("Supheeli Port", f"{process} -> {ip}:{port}", "WARNING")


def notify_high_traffic(ip: str, bytes_sent: int, process: str):
    mb = bytes_sent / (1024 * 1024)
    _log("Yuksek Transfer", f"{process} -> {ip}: {mb:.1f} MB", "WARNING")


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
    AI analizi basariyla tamamlaninca cagrilir.
    Her zaman Windows bildirimi gonderir.
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

    title   = f"NetSonar — {icon} Risk: {risk_score:.1f}/10"
    message = (
        f"Durum: {status}\n"
        f"Supheli baglanti: {suspicious_count} adet\n"
        f"Saglayici: {provider.upper()}"
    )
    _log(title, message, severity.upper())
    _send_toast(title, message, severity)


def notify_analysis_failed(reason: str, provider: str):
    """
    AI analizi basarisiz olunca cagrilir.
    Her zaman Windows bildirimi gonderir.
    """
    title   = "NetSonar — ⚠️ Analiz Basarisiz"
    message = f"Saglayici: {provider.upper()}\nHata: {reason[:200]}"
    _log(title, message, "ERROR")
    _send_toast(title, message, "warning")


def notify_ip_blocked(ip: str):
    """IP engelleme bildirimi — her zaman gosterilir."""
    title   = "NetSonar — 🛡️ IP Engellendi"
    message = f"{ip} guvvenlik duvarina eklendi."
    _log(title, message, "INFO")
    _send_toast(title, message, "info")


# Geriye uyumluluk icin — eski kod bu fonksiyonu cagiriyorsa calissin
def notify_report_ready(risk_score: float, status: str):
    notify_analysis_done(risk_score, status, "ai", 0)

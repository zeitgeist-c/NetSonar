"""
AgTara — Masaustu Bildirim Modulu
==================================
Kural: Yalnizca AI analizi tamamlaninca veya basarisiz olunca bildirim goster.
Diger olaylar (port uyarisi, yuksek trafik vb.) sadece konsola yazilir.
"""

from datetime import datetime


def _send_toast(title: str, message: str, severity: str = "info"):
    """Windows toast bildirimi gonder. winotify → plyer fallback."""
    if not isinstance(message, str):
        message = str(message)
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="AgTara",
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
        print(f"[Notifier] winotify hatasi: {exc}")

    # Fallback: plyer
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message[:256],
            app_name="AgTara",
            timeout=10 if severity == "critical" else 6,
        )
    except Exception:
        pass


def _log(title: str, message: str, level: str = "INFO"):
    """Her durumda konsola yaz."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {title}: {message}")


# ─── Sadece loglanan olaylar (bildirim GÖNDERILMEZ) ──────────────────
def notify_suspicious_port(ip: str, port: int, process: str):
    _log("Supheeli Port", f"{process} -> {ip}:{port}", "WARNING")


def notify_vt_threat(ip: str, malicious_count: int, country: str):
    _log("VirusTotal Tehdit", f"{ip} ({country}) — {malicious_count} motor tehdit isaretledi", "CRITICAL")


def notify_high_traffic(ip: str, bytes_sent: int, process: str):
    mb = bytes_sent / (1024 * 1024)
    _log("Yuksek Transfer", f"{process} -> {ip}: {mb:.1f} MB", "WARNING")


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

    title   = f"AgTara — {icon} Risk: {risk_score:.1f}/10"
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
    title   = "AgTara — ⚠️ Analiz Basarisiz"
    message = f"Saglayici: {provider.upper()}\nHata: {reason[:200]}"
    _log(title, message, "ERROR")
    _send_toast(title, message, "warning")


def notify_ip_blocked(ip: str):
    """IP engelleme bildirimi — her zaman gosterilir."""
    title   = "AgTara — 🛡️ IP Engellendi"
    message = f"{ip} guvvenlik duvarina eklendi."
    _log(title, message, "INFO")
    _send_toast(title, message, "info")


# Geriye uyumluluk icin — eski kod bu fonksiyonu cagiriyorsa calissin
def notify_report_ready(risk_score: float, status: str):
    notify_analysis_done(risk_score, status, "ai", 0)

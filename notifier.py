"""
AgTara — Masaustu Bildirim Modulu
NOTIFY_REPORTS_ONLY = True ise yalnizca AI rapor bildirimleri gonderilir.
Diger fonksiyonlar yine de konsola yazar ama toast gostermez.
"""

from datetime import datetime
from config import NOTIFY_REPORTS_ONLY

SEVERITY_ICONS = {
    "critical": "Kritik",
    "warning":  "Uyari",
    "info":     "Bilgi",
    "success":  "Tamam",
}


def notify(title: str, message: str, severity: str = "warning", force: bool = False):
    """
    Masaustu bildirimi gonderir.
    force=True ise NOTIFY_REPORTS_ONLY ayarini dikkate almaz (rapor bildirimleri icin).
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{severity.upper()}] {title}: {message}")

    if force or not NOTIFY_REPORTS_ONLY:
        _send_toast(title, message, severity)


def _send_toast(title: str, message: str, severity: str):
    """winotify once, plyer yedek."""
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="AgTara",
            title=title,
            msg=message[:256],
            duration="short",
        )
        if severity == "critical":
            toast.set_audio(audio.Default, loop=False)
        toast.show()
    except ImportError:
        _send_toast_plyer(title, message)
    except Exception as exc:
        print(f"[Notifier] winotify hatasi: {exc}")
        _send_toast_plyer(title, message)


def _send_toast_plyer(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message[:256], app_name="AgTara", timeout=8)
    except Exception:
        pass


# ─── Anlik Uyarilar (sadece konsola yazar, toast gelmez) ─────────────
def notify_suspicious_port(ip: str, port: int, process: str):
    notify(
        title="Supheeli Port",
        message=f"{process} -> {ip}:{port} (zarali yazilim portu)",
        severity="critical",
        force=False,    # NOTIFY_REPORTS_ONLY'yi saygi goster
    )


def notify_vt_threat(ip: str, malicious_count: int, country: str):
    notify(
        title="VirusTotal Tehdidi",
        message=f"{ip} ({country}) — {malicious_count} motor tehdit olarak isaretledi.",
        severity="critical",
        force=False,
    )


def notify_high_traffic(ip: str, bytes_sent: int, process: str):
    mb = bytes_sent / (1024 * 1024)
    notify(
        title="Yuksek Veri Transferi",
        message=f"{process} -> {ip}: {mb:.1f} MB",
        severity="warning",
        force=False,
    )


# ─── Rapor Bildirimleri (her zaman gosterilir) ───────────────────────
def notify_report_ready(risk_score: float, status: str):
    severity = "critical" if risk_score >= 7 else "warning" if risk_score >= 5 else "info"
    notify(
        title="AgTara AI Raporu Hazir",
        message=f"Risk Skoru: {risk_score:.1f}/10 — {status}",
        severity=severity,
        force=True,     # Her zaman goster
    )


def notify_ip_blocked(ip: str):
    notify(
        title="IP Engellendi",
        message=f"{ip} guvvenlik duvarina eklendi.",
        severity="success",
        force=True,
    )

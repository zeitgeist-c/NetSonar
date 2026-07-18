"""
NetSonar — AI Analiz Motoru (v3)
==============================

Onemli degisiklik: openai kutuphanesine bagimliliik tamamen kaldirildi.
Tum API cagirilari dogrudan `requests` ile yapilir — daha guvenilir ve debug edilebilir.

Hangi API kullanilir?
  config.py → AI_PROVIDER = "gemini"; model = "gemini-3.1-flash-lite"

Veri akisi:
  DB → ozetlenmis JSON → SYSTEM_PROMPT + kullanici mesaji → AI → JSON rapor
  Ham paket / URL / parola → ASLA gonderilmez.
"""

import json
import re
import logging
import importlib
import requests
import threading
import time as _time
from datetime import datetime
from ip_utils import is_local_ip

log = logging.getLogger("NetSonar.AI")

_session_local = threading.local()


def _session() -> requests.Session:
    session = getattr(_session_local, "session", None)
    if session is None:
        session = requests.Session()
        _session_local.session = session
    return session


def _cfg():
    """config modulunu HER CAGRIDA TAZE okur."""
    import config
    importlib.reload(config)
    return config


# ─────────────────────────────────────────────────────────────
#  System Prompt (config'den yüklenir)
# ─────────────────────────────────────────────────────────────
# SYSTEM_PROMPT artık config.AI_PROMPT kullanılarak alınıyor
# Prompt ayar dosyasından yüklenir: config/ai_prompt.txt


# ─────────────────────────────────────────────────────────────
#  JSON Temizleyici
# ─────────────────────────────────────────────────────────────
def _extract_json(raw: str) -> dict:
    """AI cevabindan JSON objesini ayiklar."""
    if not raw or not raw.strip():
        raise ValueError("AI bos cevap donderdi.")
    raw = raw.strip()
    # Markdown kod blogu temizle
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw)
    raw = raw.strip()
    # Ilk { ile son } arasini al
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON dict beklendi.")
        return data
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse hatasi: {exc}\nCevap: {raw[:300]}") from exc


# ─────────────────────────────────────────────────────────────
#  G E M I N I  (requests ile — google API)
# ─────────────────────────────────────────────────────────────
# Gemini kota asimi icin ozel hata; ayni istekte diger Gemini keyleri denenir.
class GeminiQuotaError(Exception):
    pass


_GEMINI_KEY_COOLDOWN_SECONDS = 30 * 60
_GEMINI_KEY_COOLDOWNS = {}
_GEMINI_KEY_LOCK = threading.Lock()


def _mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def _available_gemini_keys(keys: list[str]) -> list[str]:
    now = _time.time()
    with _GEMINI_KEY_LOCK:
        expired = [key for key, until in _GEMINI_KEY_COOLDOWNS.items() if until <= now]
        for key in expired:
            _GEMINI_KEY_COOLDOWNS.pop(key, None)
        return [key for key in keys if _GEMINI_KEY_COOLDOWNS.get(key, 0) <= now]


def _mark_gemini_key_cooldown(key: str, status_code: int):
    until = _time.time() + _GEMINI_KEY_COOLDOWN_SECONDS
    with _GEMINI_KEY_LOCK:
        _GEMINI_KEY_COOLDOWNS[key] = until
    log.warning(
        "[Gemini] key=%s HTTP %d nedeniyle 30 dakika bekletiliyor",
        _mask_api_key(key), status_code,
    )


def _gemini_cooldown_wait_minutes(keys: list[str]) -> int:
    now = _time.time()
    with _GEMINI_KEY_LOCK:
        waits = [_GEMINI_KEY_COOLDOWNS.get(key, 0) - now for key in keys]
    waits = [wait for wait in waits if wait > 0]
    if not waits:
        return 0
    return max(1, int(min(waits) / 60) + 1)


def _analyze_gemini(user_msg: str) -> dict:
    cfg = _cfg()
    keys = list(getattr(cfg, "GEMINI_API_KEYS", []) or [])
    if not keys and getattr(cfg, "GEMINI_API_KEY", ""):
        keys = [cfg.GEMINI_API_KEY]

    if not keys:
        raise ValueError(
            "Gemini API key bos!\n"
            "Ayarlar'da her satira bir Gemini API key gir."
        )

    model = cfg.GEMINI_MODEL
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [{"text": cfg.AI_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_msg}]}
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        },
    }

    active_keys = _available_gemini_keys(keys)
    if not active_keys:
        wait_min = _gemini_cooldown_wait_minutes(keys)
        raise GeminiQuotaError(
            f"Uygun Gemini API key yok. Tum keyler 429/503 nedeniyle beklemede. "
            f"Yaklasik {wait_min} dakika sonra tekrar dene."
        )

    last_quota_error = None
    for index, api_key in enumerate(active_keys, start=1):
        log.info(
            "[Gemini] model=%s key=%s (%d/%d) istek gonderiliyor...",
            model, _mask_api_key(api_key), index, len(active_keys),
        )

        try:
            resp = _session().post(
                endpoint,
                params={"key": api_key},
                json=payload,
                timeout=120,
            )
        except requests.Timeout as exc:
            raise ValueError("Gemini istegi zaman asimina ugradi. Kisa sure sonra tekrar dene.") from exc
        except requests.ConnectionError as exc:
            raise ValueError(f"Gemini API'ye baglanilamiyor: {exc}") from exc

        log.info("[Gemini] key=%s status=%d", _mask_api_key(api_key), resp.status_code)

        if resp.status_code == 200:
            data = resp.json()
            try:
                raw = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                raise ValueError(f"Gemini beklenmeyen cevap formati:\n{json.dumps(data, indent=2)[:400]}")

            log.info("[Gemini] cevap uzunlugu=%d", len(raw))
            return _extract_json(raw)

        body = resp.text[:400]
        if resp.status_code in (429, 503):
            _mark_gemini_key_cooldown(api_key, resp.status_code)
            last_quota_error = f"HTTP {resp.status_code}: {body}"
            continue
        if resp.status_code == 400:
            raise ValueError(f"Gemini istek hatasi (model veya istek formati hatali?):\n{body}")
        if resp.status_code == 403:
            raise ValueError(f"Gemini API key gecersiz, yetkisiz veya proje erisimi kapali:\n{body}")

        raise ValueError(f"Gemini API hatasi (HTTP {resp.status_code}):\n{body}")

    wait_min = _gemini_cooldown_wait_minutes(keys)
    raise GeminiQuotaError(
        "Tum uygun Gemini API keyleri kota/rate-limit veya servis yogunlugu nedeniyle gecici olarak kullanilamiyor.\n"
        f"Son hata: {last_quota_error or '429/503'}\n"
        f"Yaklasik {wait_min} dakika sonra beklemedeki keyler tekrar denenir."
    )

# ─────────────────────────────────────────────────────────────
#  O R T A K   A R A Y Ü Z
# ─────────────────────────────────────────────────────────────
PROVIDERS = {
    "gemini": _analyze_gemini,
}


class AIAnalyzer:
    """
    Saglayicidan bagimsiz AI analiz arayuzu.
    Her cagride config taze okunur — GUI guncellemesi aninda gecerli.
    openai kutuphanesine bagimlilik YOK — dogrudan requests kullanir.
    """

    def __init__(self, db):
        self.db = db
        provider = _cfg().AI_PROVIDER
        if provider not in PROVIDERS:
            raise ValueError(
                f"Gecersiz AI_PROVIDER: '{provider}'. "
                f"Secenekler: {list(PROVIDERS.keys())}"
            )
        log.info("[AIAnalyzer] basladi — saglayici: %s", provider)

    @property
    def provider(self) -> str:
        return _cfg().AI_PROVIDER

    def validate_config(self) -> list[str]:
        """Yapilandirma sorunlarini listeler."""
        cfg = _cfg()
        issues = []

        if cfg.AI_PROVIDER != "gemini":
            issues.append("Bu surum yalnizca Gemini saglayicisini destekler")
        if cfg.GEMINI_MODEL != "gemini-3.1-flash-lite":
            issues.append("Gemini modeli gemini-3.1-flash-lite olmali")
        if not getattr(cfg, "GEMINI_API_KEYS", []):
            issues.append("Gemini API key listesi bos")

        return issues

    def analyze(self, hours: int = 1, force_full: bool = False, stage_callback=None) -> dict:
        """
        Artimli analiz: Son basarili analizden bu yana gelen YENI verileri gonderir.
        - force_full=True: son {hours} saatin tumunu gonderir (elle tetikleme icin).
        - Yeni kayit yoksa analizi atlar, token harcamaz.
        - result dict'e '_meta' alani ekler: preview ve token tahmini icin.
        - stage_callback(stage_name, progress): GUI'de analiz asamalarini gostermek icin.
        """
        def emit_stage(name, prog):
            if stage_callback:
                stage_callback(name, prog)

        cfg      = _cfg()
        provider = cfg.AI_PROVIDER
        now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

        emit_stage("Hazırlanıyor…", 10)

        # ── Artimli mi, Tam mi? ──────────────────────────────────────
        last_ts = self.db.get_last_analysis_time()

        if force_full or last_ts is None:
            # Ilk analiz veya elle zorlanmis: son {hours} saati gonder
            summary    = self.db.get_summary(hours=hours)
            since_label = f"Son {hours} saat (tam)" if last_ts else "Ilk analiz (tam)"
            new_count   = len(summary)
            trusted_filtered_count = self.db.get_trusted_connection_count(hours=hours)
        else:
            # Artimli: sadece son analizden bu yana gelenleri gonder
            new_count  = self.db.get_new_connection_count(since_ts=last_ts)
            summary    = self.db.get_summary_since(since_ts=last_ts)
            since_label = f"Son analizden beri ({last_ts[:16]})"
            trusted_filtered_count = self.db.get_trusted_connection_count(since_ts=last_ts)

        # Yeni kayit yok mu? Token harcama, atla.
        if not summary:
            if trusted_filtered_count:
                msg = (
                    f"{since_label}: {trusted_filtered_count} bağlantı güvenli IP listesi nedeniyle "
                    "analiz dışında bırakıldı; Gemini'ye veri gönderilmedi."
                )
            else:
                msg = (
                    f"{since_label} arasında analiz edilecek yeni harici trafik yok."
                    if new_count == 0
                    else f"{since_label}: {new_count} yeni bağlantı var ama hepsi iç ağ (filtrelendi)."
                )
            return {
                "risk_score": 0.0,
                "status": "GUVENLI",
                "suspicious_connections": [],
                "summary": msg,
                "_meta": {"skipped": True, "reason": msg, "since": last_ts},
            }

        # ── Token Tahmini ─────────────────────────────────────────────
        # Not: Veri kaybını önlemek için token limit uygulanmıyor.
        # Sorgu zaten en önemli verileri (şüpheli port, yüksek trafik) öncelikli alıyor.
        est_tokens = len(summary) * 100 + 500
        log.info(
            "[AIAnalyzer] %s | %d yeni kayit | ~%d token tahmini | %s",
            provider.upper(), len(summary), est_tokens, since_label,
        )

        emit_stage("İşleniyor…", 25)

        # ── Kullanici Mesaji ───────────────────────────────────────
        user_msg = json.dumps({
            "analysis_time":   now_str,
            "period":          since_label,
            "new_connections": new_count,
            "records_sent":    len(summary),
            "est_tokens":      est_tokens,
            "traffic_summary": summary,
        }, ensure_ascii=False, indent=2)

        emit_stage("İşleniyor…", 35)

        # _meta: GUI'nin onizleme panelinde gostermesi icin
        _meta = {
            "since":       last_ts,
            "since_label": since_label,
            "new_count":   new_count,
            "records":     len(summary),
            "est_tokens":  est_tokens,
            "raw_payload": user_msg,   # GUI'de "Gonderilen Veri" paneli icin
            "skipped":     False,
        }


        # On-kontrol
        issues = self.validate_config()
        if issues:
            return {
                "risk_score": -1,
                "status": "YAPILANDIRMA HATASI",
                "suspicious_connections": [],
                "summary": "Yapilandirma sorunlari:\n" + "\n".join(f"- {i}" for i in issues),
            }

        emit_stage("Gönderiliyor…", 40)
        emit_stage("Bekleniyor…", 50)

        # Analiz: yalniz Gemini; 429/503 durumunda key rotasyonu _analyze_gemini icinde yapilir.
        try:
            fn = PROVIDERS[provider]
            result = fn(user_msg)
            emit_stage("İşleniyor…", 90)
        except GeminiQuotaError as quota_exc:
            log.warning("[AIAnalyzer] Gemini key havuzu gecici olarak kullanilamiyor: %s", quota_exc)
            try:
                from notifier import notify_analysis_failed
                notify_analysis_failed(str(quota_exc), provider)
            except Exception:
                pass
            return {
                "risk_score": -1,
                "status": "KOTA ASIMI",
                "suspicious_connections": [],
                "summary": (
                    "Uygun Gemini API key yok veya tum uygun keyler gecici olarak beklemede.\n"
                    f"{quota_exc}\n\n"
                    "Cozum: Bir sure sonra tekrar dene veya Ayarlar'a yeni Gemini API key ekle."
                ),
            }
        except Exception as exc:
            log.error("[AIAnalyzer] hata: %s", exc)
            try:
                from notifier import notify_analysis_failed
                notify_analysis_failed(str(exc), provider)
            except Exception:
                pass
            return {
                "risk_score": -1,
                "status": "API HATASI",
                "suspicious_connections": [],
                "summary": str(exc),
            }
# Alan varsayilanlari
        result.setdefault("risk_score", 0.0)
        result.setdefault("status", "BILINMIYOR")
        result.setdefault("suspicious_connections", [])
        result.setdefault("summary", "AI yorumu alinamadi.")

        # Risk skorunu 0-10 araligina kilitle
        try:
            result["risk_score"] = max(0.0, min(10.0, float(result["risk_score"])))
        except (TypeError, ValueError):
            result["risk_score"] = 0.0

        # _meta'yi result'a ekle (GUI icin)
        result["_meta"] = _meta

        # DB'ye kaydet (_meta ham JSON icerdiğinden DB'ye yazma)
        db_content = {k: v for k, v in result.items() if k != "_meta"}
        self.db.save_report(
            provider   = provider,
            risk_score = result["risk_score"],
            status     = result["status"],
            content    = json.dumps(db_content, ensure_ascii=False),
        )

        # Basarili analiz bildirimi
        try:
            from notifier import notify_analysis_done
            notify_analysis_done(
                risk_score      = result["risk_score"],
                status          = result["status"],
                provider        = provider,
                suspicious_count = len(result.get("suspicious_connections", [])),
            )
        except Exception:
            pass

        # Otomatik engelleme
        self._auto_block_connections(result)

        log.info("[AIAnalyzer] tamamlandi — skor=%.1f durum=%s", result["risk_score"], result["status"])
        emit_stage("✓ Tamamlandı", 100)
        return result


    def _auto_block_connections(self, result: dict):
        """AI 'Hemen engelle' dediği IP'leri otomatik engeller."""
        cfg = _cfg()
        if not cfg.AUTO_BLOCK_ENABLED:
            return
        
        if result.get("risk_score", 0) < cfg.AUTO_BLOCK_MIN_RISK_SCORE:
            return
        
        conns = result.get("suspicious_connections", [])
        if not conns:
            return
        
        try:
            from kill_switch import block_ip
        except Exception as exc:
            log.error("[AutoBlock] kill_switch import hatasi: %s", exc)
            return
        
        blocked_count = 0
        for conn in conns:
            action = conn.get("action", "").lower()
            ip = conn.get("ip", "")
            
            if not ip or is_local_ip(ip):
                continue
            if self.db.is_trusted_ip(ip):
                log.info("[AutoBlock] %s güvenli IP listesinde; engelleme atlandı", ip)
                continue
            
            if "engelle" in action or "block" in action:
                try:
                    ok = block_ip(ip, reason=f"AI otomatik engelleme: {conn.get('reason', '')}", db=self.db)
                    if ok:
                        blocked_count += 1
                        conn["auto_blocked"] = True
                        log.info("[AutoBlock] %s otomatik engellendi", ip)
                except Exception as exc:
                    log.error("[AutoBlock] %s engelleme hatasi: %s", ip, exc)
        
        if blocked_count > 0:
            try:
                from notifier import notify
                notify(
                    title="Otomatik Engelleme",
                    message=f"{blocked_count} şüpheli IP engellendi.",
                    severity="warning"
                )
            except Exception:
                pass

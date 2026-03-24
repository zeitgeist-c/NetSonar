"""
AgTara — AI Analiz Motoru (v3)
==============================

Onemli degisiklik: openai kutuphanesine bagimliliik tamamen kaldirildi.
Tum API cagirilari dogrudan `requests` ile yapilir — daha guvenilir ve debug edilebilir.

Hangi API kullanilir?
  config.py → AI_PROVIDER = "openrouter" | "ollama" | "gemini"

Veri akisi:
  DB → ozetlenmis JSON → SYSTEM_PROMPT + kullanici mesaji → AI → JSON rapor
  Ham paket / URL / parola → ASLA gonderilmez.
"""

import json
import re
import logging
import importlib
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger("AgTara.AI")


def _cfg():
    """config modulunu HER CAGRIDA TAZE okur."""
    import config
    importlib.reload(config)
    return config


# ─────────────────────────────────────────────────────────────
#  System Prompt
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Sen AgTara adli Windows ag izleme aracinin siber guvenlik AI analistisin.

GOREV:
Sana bir Windows bilgisayardan toplanan son 1 saatlik ag trafigi ozetini JSON olarak veriyorum.
Bu ozet; hedef IP, port, protokol, byte miktari ve surec adi gibi META VERILERDEN olusur.
Ham paket icerigi, URL veya parola icermez.

ANALIZDE BAKILACAKLAR:
1. Bilindik zararli / supheeli IP'ler (Tor exit node, C2 sunucu, botnet vb.)
2. Tehlikeli portlar: 4444, 1337, 31337, 5555, 6666, 6667, 8888, 9999
3. Anormal surecler: svchost, powershell, wscript, cmd, mshta uzerinden internet
4. Tek hedefe yuksek veri transferi (>5MB tek baglanti)
5. Gece 2-6 arasi otomatik baglantilar
6. Surec adi ile beklenen davranis arasindaki uyumsuzluk

KESIN CEVAP FORMATI — Yalnizca asagidaki JSON yapisini dondur:
{
  "risk_score": 6.2,
  "status": "DIKKATE AL",
  "suspicious_connections": [
    {
      "ip": "185.220.101.5",
      "port": 4444,
      "process": "powershell.exe",
      "bytes_sent": 524288,
      "reason": "Bilinen Tor cikis dugumu.",
      "action": "Hemen engelle"
    }
  ],
  "summary": "Tek paragraf Turkce yorum."
}

RISK SKORU:
0-3 → "GUVENLI" | 3-5 → "NORMAL" | 5-7 → "DIKKATE AL" | 7-9 → "DIKKAT GEREKTIRIYOR" | 9-10 → "KRITIK TEHDIT"

ONEMLI: suspicious_connections bos olabilir. JSON disinda hicbir sey yazma."""


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
#  O P E N R O U T E R  (requests ile + otomatik fallback)
# ─────────────────────────────────────────────────────────────
# Model 404 veya 429 alirsa sirayla yedek modelleri dener
_FALLBACK_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-4b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemma-3n-e4b-it:free",
    "qwen/qwen3-4b:free",
    "arcee-ai/trinity-large-preview:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]
import time as _time

def _analyze_openrouter(user_msg: str) -> dict:
    cfg = _cfg()
    if not cfg.OPENROUTER_API_KEY:
        raise ValueError("OpenRouter API key bos! Ayarlar'dan gir.")

    headers = {
        "Authorization":  f"Bearer {cfg.OPENROUTER_API_KEY}",
        "Content-Type":   "application/json",
        "HTTP-Referer":   "https://github.com/AgTara",
        "X-Title":        "AgTara Network Monitor",
    }

    # Denenecek modeller: config'deki + fallback listesi (tekrar onleme)
    primary = cfg.OPENROUTER_MODEL
    models_to_try = [primary]
    for fb in _FALLBACK_MODELS:
        if fb != primary:
            models_to_try.append(fb)

    last_error = None

    for model in models_to_try:
        payload = {
            "model":       model,
            "messages":    [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            "max_tokens":  1500,
            "temperature": 0.1,
        }

        log.info("[OpenRouter] model=%s deniyor...", model)

        try:
            resp = requests.post(
                f"{cfg.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
        except requests.Timeout:
            log.warning("[OpenRouter] %s timeout — sonraki model deneniyor", model)
            last_error = f"Model timeout: {model}"
            continue
        except requests.ConnectionError as e:
            raise ValueError(f"OpenRouter'a baglanilamiyor: {e}")

        if resp.status_code == 200:
            data = resp.json()
            raw  = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if raw and raw.strip():
                log.info("[OpenRouter] BASARILI model=%s cevap=%d karakter", model, len(raw))
                return _extract_json(raw)
            else:
                log.warning("[OpenRouter] %s bos cevap donderdi", model)
                last_error = f"Bos cevap: {model}"
                continue

        elif resp.status_code in (404, 429):
            reason = "bulunamadi" if resp.status_code == 404 else "rate limited"
            log.warning("[OpenRouter] %s %s (HTTP %d) — sonraki deneniyor", model, reason, resp.status_code)
            last_error = f"{model}: HTTP {resp.status_code}"
            if resp.status_code == 429:
                _time.sleep(3)  # Rate limit — kisa bekle
            continue

        elif resp.status_code == 401:
            raise ValueError("API key gecersiz veya suresi dolmus.")

        else:
            body = resp.text[:300]
            last_error = f"{model}: HTTP {resp.status_code} — {body}"
            log.warning("[OpenRouter] %s beklenmeyen hata: %s", model, last_error)
            continue

    # Hic bir model calismadi
    raise ValueError(
        f"Tum modeller basarisiz oldu.\nSon hata: {last_error}\n\n"
        "Cozum: openrouter.ai/models adresinden calisir bir model sec, "
        "veya kisa sure sonra tekrar dene (rate limit resetlenebilir)."
    )



# ─────────────────────────────────────────────────────────────
#  O L L A M A  (requests ile — yerel)
# ─────────────────────────────────────────────────────────────
def _analyze_ollama(user_msg: str) -> dict:
    cfg = _cfg()
    url = cfg.OLLAMA_BASE_URL.rstrip("/")

    # Ollama /v1 prefix kontrolu
    if url.endswith("/v1"):
        endpoint = f"{url}/chat/completions"
    else:
        endpoint = f"{url}/v1/chat/completions"

    payload = {
        "model":       cfg.OLLAMA_MODEL,
        "messages":    [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "max_tokens":  1500,
        "temperature": 0.1,
    }

    log.info("[Ollama] model=%s url=%s", cfg.OLLAMA_MODEL, endpoint)

    try:
        resp = requests.post(endpoint, json=payload, timeout=300)
    except requests.ConnectionError:
        raise ValueError(
            f"Ollama'ya baglanamiyorum ({cfg.OLLAMA_BASE_URL}).\n\n"
            "Cozum:\n"
            "1. Ollama'nin calistigindan emin ol: 'ollama serve'\n"
            "2. Modeli indir: 'ollama pull mistral'\n"
            "3. URL'yi kontrol et (varsayilan: http://localhost:11434/v1)"
        )
    except requests.Timeout:
        raise ValueError("Ollama cok yavas cevap verdi (timeout 5dk). Model cok buyuk olabilir.")

    if resp.status_code != 200:
        raise ValueError(f"Ollama hatasi (HTTP {resp.status_code}):\n{resp.text[:300]}")

    data = resp.json()
    raw  = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    log.info("[Ollama] cevap uzunlugu=%d", len(raw))
    return _extract_json(raw)


# ─────────────────────────────────────────────────────────────
#  G E M I N I  (requests ile — google API)
# ─────────────────────────────────────────────────────────────
def _analyze_gemini(user_msg: str) -> dict:
    cfg = _cfg()
    if not cfg.GEMINI_API_KEY:
        raise ValueError(
            "Gemini API key bos!\n"
            "aistudio.google.com/apikey adresinden al, Ayarlar'a gir."
        )

    model    = cfg.GEMINI_MODEL
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_msg}]}
        ],
        "generationConfig": {
            "temperature":     0.1,
            "maxOutputTokens": 1500,
            "responseMimeType": "application/json",
        },
    }

    log.info("[Gemini] model=%s istek gonderiliyor...", model)

    resp = requests.post(
        endpoint,
        params={"key": cfg.GEMINI_API_KEY},
        json=payload,
        timeout=120,
    )

    log.info("[Gemini] status=%d", resp.status_code)

    if resp.status_code != 200:
        body = resp.text[:400]
        if resp.status_code == 400:
            raise ValueError(f"Gemini istek hatasi:\n{body}")
        elif resp.status_code == 403:
            raise ValueError(f"Gemini API key gecersiz veya yetkisiz:\n{body}")
        else:
            raise ValueError(f"Gemini API hatasi (HTTP {resp.status_code}):\n{body}")

    data = resp.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ValueError(f"Gemini beklenmeyen cevap formati:\n{json.dumps(data, indent=2)[:400]}")

    log.info("[Gemini] cevap uzunlugu=%d", len(raw))
    return _extract_json(raw)


# ─────────────────────────────────────────────────────────────
#  O R T A K   A R A Y Ü Z
# ─────────────────────────────────────────────────────────────
PROVIDERS = {
    "openrouter": _analyze_openrouter,
    "gemini":     _analyze_gemini,
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
        cfg      = _cfg()
        provider = cfg.AI_PROVIDER
        issues   = []

        if provider not in PROVIDERS:
            issues.append(f"Bilinmeyen saglayici: '{provider}'")
            return issues

        if provider == "openrouter":
            if not cfg.OPENROUTER_API_KEY:
                issues.append("OpenRouter API key bos")
            if not cfg.OPENROUTER_MODEL:
                issues.append("OpenRouter model adi bos")
            # Hizli key testi
            if cfg.OPENROUTER_API_KEY:
                try:
                    r = requests.get(
                        f"{cfg.OPENROUTER_BASE_URL}/auth/key",
                        headers={"Authorization": f"Bearer {cfg.OPENROUTER_API_KEY}"},
                        timeout=5,
                    )
                    if r.status_code != 200:
                        issues.append(f"API key gecersiz (HTTP {r.status_code})")
                except Exception as e:
                    issues.append(f"OpenRouter'a ulasilamiyor: {e}")

        elif provider == "gemini":
            if not cfg.GEMINI_API_KEY:
                issues.append("Gemini API key bos")

        return issues

    def analyze(self, hours: int = 1) -> dict:
        """
        Son `hours` saatin ozetini alir, AI ile analiz eder, rapor dondurur.
        Asla exception atmaz — hata durumunda risk_score=-1 ile anlamli Turkce mesaj.
        """
        cfg      = _cfg()
        provider = cfg.AI_PROVIDER
        now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Veri var mi?
        summary = self.db.get_summary(hours=hours)
        if not summary:
            return {
                "risk_score": 0.0,
                "status": "GUVENLI",
                "suspicious_connections": [],
                "summary": f"Son {hours} saatte ({now_str}) analiz edilecek harici trafik bulunamadi.",
            }

        # Kullanici mesajini zenginlestir
        user_msg = json.dumps({
            "analysis_time": now_str,
            "period_hours":  hours,
            "total_records": len(summary),
            "traffic_summary": summary,
        }, ensure_ascii=False, indent=2)

        log.info("[AIAnalyzer] %s | %d kayit gonderiliyor", provider.upper(), len(summary))

        # On-kontrol
        issues = self.validate_config()
        if issues:
            return {
                "risk_score": -1,
                "status": "YAPILANDIRMA HATASI",
                "suspicious_connections": [],
                "summary": "Yapilandirma sorunlari:\n" + "\n".join(f"- {i}" for i in issues),
            }

        # Analiz
        try:
            fn     = PROVIDERS[provider]
            result = fn(user_msg)
        except Exception as exc:
            log.error("[AIAnalyzer] hata: %s", exc)
            # Basarisiz → bildirim gonder
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

        # VirusTotal zenginlestirme — supheeli IP'leri paralel sorgula
        result = self._enrich_with_vt(result)

        # DB'ye kaydet
        self.db.save_report(
            provider   = provider,
            risk_score = result["risk_score"],
            status     = result["status"],
            content    = json.dumps(result, ensure_ascii=False),
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

        log.info("[AIAnalyzer] tamamlandi — skor=%.1f durum=%s", result["risk_score"], result["status"])
        return result

    def _enrich_with_vt(self, result: dict) -> dict:
        """
        Supheli baglantilardaki IP'leri VirusTotal ile sorgulay,
        sonuclari her baglantinin 'vt' alani olarak ekle.
        Rate limit nedeniyle max 5 IP, paralel isteklerle.
        """
        conns = result.get("suspicious_connections", [])
        if not conns:
            return result

        # Sorgulanacak harici IP'leri topla (en fazla 5)
        ips_to_check = []
        for conn in conns:
            ip = conn.get("ip", "")
            if ip and not any(ip.startswith(p) for p in ("192.168.", "10.", "127.", "172.")):
                if ip not in ips_to_check:
                    ips_to_check.append(ip)
            if len(ips_to_check) >= 5:
                break

        if not ips_to_check:
            return result

        log.info("[VT] %d IP zenginlestiriliyor: %s", len(ips_to_check), ips_to_check)

        vt_map: dict[str, dict] = {}
        try:
            from threat_intel import check_ip
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {pool.submit(check_ip, ip): ip for ip in ips_to_check}
                for fut in as_completed(futures, timeout=20):
                    ip  = futures[fut]
                    try:
                        vt_map[ip] = fut.result()
                    except Exception as exc:
                        vt_map[ip] = {"error": str(exc)}
        except Exception as exc:
            log.warning("[VT] zenginlestirme hatasi: %s", exc)
            return result

        # VT sonuclarini baglantilara ekle
        for conn in conns:
            ip = conn.get("ip", "")
            if ip in vt_map:
                vt = vt_map[ip]
                conn["vt_malicious"]  = vt.get("malicious", 0)
                conn["vt_suspicious"] = vt.get("suspicious", 0)
                conn["vt_country"]    = vt.get("country", "?")
                conn["vt_is_threat"]  = vt.get("is_threat", False)
                # Risk skorunu yukselt (VT tehditi teyit ediyorsa)
                if vt.get("is_threat") and result["risk_score"] < 9.0:
                    result["risk_score"] = min(10.0, result["risk_score"] + 1.5)
                    log.info("[VT] %s tehdit onaylandi, risk skoru guncellendi", ip)

        result["suspicious_connections"] = conns
        return result

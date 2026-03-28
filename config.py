"""
NetSonar — Merkezi Yapılandırma
API anahtarlarını ve uygulama ayarlarını buradan düzenle.
"""

import json
import os

# ─── Settings Yükleme (önce dosya, sonra env) ──────────────────────
SETTINGS_FILE = "config/settings.json"

def load_settings():
    """Kullanıcı ayarlarını dosyadan yükle."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "MINIMIZE_TO_TRAY": True,
        "AUTO_BLOCK_ENABLED": False,
        "autostart": False,
        "interface": None,
        "AI_PROVIDER": "gemini",
        "GEMINI_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "OLLAMA_API_KEY": "",
        "GEMINI_MODEL": "gemini-2.0-flash-lite",
        "OPENROUTER_MODEL": "meta-llama/llama-3.3-70b-instruct:free",
        "OLLAMA_MODEL": "minimax-m2.7",
        "AUTO_ANALYSIS_ENABLED": True,
        "ANALYSIS_INTERVAL_MINUTES": 60,
    }

def save_settings(data: dict):
    """Kullanıcı ayarlarını dosyaya kaydet."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ─── Yardımcı fonksiyon ──────────────────────────────────────────────
def _get_setting(key, env_var=None):
    """Environment variable'dan önce, sonra settings.json'dan al."""
    if env_var and os.getenv(env_var):
        return os.getenv(env_var)
    settings = load_settings()
    return settings.get(key, "")

# ─── AI Sağlayıcı Seçimi ────────────────────────────────────────────
AI_PROVIDER = _get_setting("AI_PROVIDER", "AG_TARA_PROVIDER") or "gemini"

# ─── OpenRouter ──────────────────────────────────────────────────────
OPENROUTER_API_KEY  = _get_setting("OPENROUTER_API_KEY", "AG_TARA_OPENROUTER_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL    = _get_setting("OPENROUTER_MODEL", "AG_TARA_OPENROUTER_MODEL") or "meta-llama/llama-3.3-70b-instruct:free"

# ─── Ollama Cloud ──────────────────────────────────────────────────
OLLAMA_API_KEY = _get_setting("OLLAMA_API_KEY", "AG_TARA_OLLAMA_KEY")
OLLAMA_MODEL   = _get_setting("OLLAMA_MODEL", "AG_TARA_OLLAMA_MODEL") or "minimax-m2.7"

# ─── Google Gemini ───────────────────────────────────────────────────
GEMINI_API_KEY = _get_setting("GEMINI_API_KEY", "AG_TARA_GEMINI_KEY")
GEMINI_MODEL   = _get_setting("GEMINI_MODEL", "AG_TARA_GEMINI_MODEL") or "gemini-2.0-flash-lite"

# ─── Zamanlayıcı ────────────────────────────────────────────────────
# Her kaç dakikada bir AI analizi yapılsın?
ANALYSIS_INTERVAL_MINUTES = 60

# Anlık VT kontrolü için şüpheli sayılan minimum byte eşiği
SUSPICIOUS_BYTES_THRESHOLD = 50_000                # 50 KB üzeri harici bağlantı

# ─── Bilinen Tehlikeli Portlar ───────────────────────────────────────
SUSPICIOUS_PORTS = {4444, 1337, 31337, 5555, 6666, 6667, 8888, 9999}

# ─── Veritabanı ─────────────────────────────────────────────────────
DB_PATH = "netsonar_data/connections.db"
DB_RETENTION_DAYS = 30                     # Kaç günlük veri saklansın? 0 = sınırsız
DB_CLEANUP_INTERVAL_HOURS = 24             # Temizlik kaç saatte bir yapılsın?

# ─── AI Limitleri ────────────────────────────────────────────────────
# Not: Veri kaybını önlemek için yüksek tutuluyor. Sorgu zaten en önemli
# verileri (şüpheli port, yüksek trafik) öncelikli olarak alıyor.
MAX_CONNECTIONS_TO_ANALYZE = 200           # AI'a gönderilecek max bağlantı sayısı

# ─── Bildirim Filtresi ───────────────────────────────────────────────
# True: sadece AI rapor bildirimleri gönderilir (önerilen)
# False: tüm anlık uyarılar (port, trafik vb.) da bildirim gönderir
NOTIFY_REPORTS_ONLY = True

# ─── Otomatik Engelleme ─────────────────────────────────────────────
# True: AI "Hemen engelle" dediğinde kullanıcı onayı istemeden firewall'a ekle
# False: Kullanıcıya sor (GUI'de buton göster)
AUTO_BLOCK_ENABLED = False

# Otomatik engelleme için minimum risk skoru (0-10)
# Sadece bu skurun üzerindeki öneriler otomatik engellenir
AUTO_BLOCK_MIN_RISK_SCORE = 7.0

# ─── Sistem ─────────────────────────────────────────────────────────────
# True: Kapatınca sistem tepsisine küçült
# False: Kapatınca tamamen çık
MINIMIZE_TO_TRAY = True

# ─── AI Prompt ─────────────────────────────────────────────────────────
import os

DEFAULT_SYSTEM_PROMPT = """Sen NetSonar'nın uzman siber güvenlik yapay zeka analistisin.

## GÖREV

Bir Windows bilgisayardan toplanan ağ trafiği özetini analiz ederek yapılandırılmış bir JSON tehdit raporu üreteceksin.

**Veriler yalnızca meta verilerden oluşmaktadır:** hedef IP adresi, port numarası, protokol, transfer edilen byte miktarı ve süreç (process) adı.
Ham paket içeriği, URL, parola veya kişisel veri **kesinlikle bulunmamaktadır.**

---

## TEHDİT KATEGORİLERİ

### 1. Bilinen Tehditler
- Tor çıkış düğümleri (exit node), C2 sunucuları ve botnet IP adresleri
- VirusTotal veya benzeri tehdit istihbarat kaynaklarında kötü amaçlı olarak işaretlenmiş IP'ler
- Bilinen zararlı yazılım (malware) alan adları

### 2. Davranış Anomalileri
- **C2 (Command & Control):** Düzenli aralıklı, otomatik görünen bağlantı kalıpları
- **Veri sızdırma (Exfiltration):** Tek yönlü yüksek hacimli dışa veri akışı
- **Lateral Movement:** İç ağda alışılmadık cihazlar arası bağlantılar
- **Port Tarama:** Kısa sürede çok sayıda porta erişim girişimleri
- **Brute Force:** Aynı hedefe tekrarlayan başarısız bağlantı denemeleri

### 3. Teknik Göstergeler
- **Riskli portlar:** 4444, 1337, 31337, 5555, 6666, 6667, 8080, 8888, 9999
- **Anormal process-IP eşleşmeleri:** `mshta.exe`, `wscript.exe`, `cmd.exe`, `powershell.exe` gibi sistem araçlarının doğrudan dış IP'lere bağlanması
- **Yüksek hacimli transfer:** Tek bağlantıda > 1 MB veri gönderimi
- **DNS Tünelleme:** Anormal boyut veya frekansta DNS sorguları

### 4. Zaman Bazlı Analiz
- Mesai dışı saatlerde (02:00–06:00) gerçekleşen otomatik bağlantılar
- Uzun süreli açık kalan (persistent) bağlantılar
- Düzensiz veya beacon benzeri bağlantı frekansları

---

## ÇIKIŞ FORMATI — ZORUNLU JSON YAPISI

Aşağıdaki şemayı **birebir** takip et. Yorum, açıklama veya markdown bloğu **ekleme;** yalnızca geçerli JSON döndür.

```json
{
  "risk_score": 7.5,
  "status": "YÜKSEK RİSK",
  "threats_found": 3,
  "suspicious_connections": [
    {
      "ip": "185.220.101.5",
      "port": 4444,
      "protocol": "TCP",
      "process": "powershell.exe",
      "bytes_sent": 524288,
      "country": "DE",
      "severity": "critical",
      "reason": "Bilinen C2 IP adresi; tehlikeli port; sistem süreci üzerinden dış bağlantı",
      "action": "Bağlantıyı derhal engelle, süreci izole et"
    }
  ],
  "indicators": {
    "c2_patterns": ["Düzenli aralıklı beacon trafiği tespit edildi"],
    "exfil_detected": true,
    "port_scan_ips": ["192.168.1.45"],
    "suspicious_processes": ["powershell.exe", "mshta.exe"],
    "dns_tunneling_suspected": false,
    "after_hours_activity": true
  },
  "recommendations": [
    "Tespit edilen şüpheli IP adreslerini güvenlik duvarında engelleyin.",
    "powershell.exe ve mshta.exe süreçlerinin başlatılma kaynaklarını inceleyin.",
    "EDR çözümü ile etkilenen uç noktaları tarayın.",
    "Ağ günlüklerini (SIEM) daha ayrıntılı korelasyon için aktarın."
  ],
  "summary": "Analizde 3 kritik tehdit tespit edildi. Yüksek öncelikli müdahale önerilir."
}
```

---

## RİSK SKORU TABLOSU

| Skor | Durum | Renk |
|------|-------|------|
| 0 – 2 | GÜVENLİ | 🟢 Yeşil |
| 3 – 5 | DÜŞÜK RİSK | 🟡 Sarı |
| 6 – 7 | ORTA RİSK | 🟠 Turuncu |
| 8 – 9 | YÜKSEK RİSK | 🔴 Kırmızı |
| 10 | KRİTİK TEHDİT | ⚫ Siyah |

---

## ÖNEMLİ KURALLAR

- `suspicious_connections` dizisi boş bırakılabilir; tehdit yoksa `[]` döndür.
- Yanıtın **yalnızca** geçerli JSON olmalıdır; başına veya sonuna hiçbir metin ekleme.
- Tüm alan adları ve değerler **Türkçe** olmalıdır.
- `severity` değerleri yalnızca şunlardan biri olabilir: `"low"`, `"medium"`, `"high"`, `"critical"`.
- `risk_score` 0.0 ile 10.0 arasında ondalıklı bir sayı olmalıdır."""

PROMPT_FILE = "config/ai_prompt.txt"

def get_ai_prompt():
    """AI prompt'u dosyadan yükle, yoksa varsayılanı kullan."""
    if os.path.exists(PROMPT_FILE):
        try:
            with open(PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return DEFAULT_SYSTEM_PROMPT

def save_ai_prompt(prompt: str):
    """AI prompt'u dosyaya kaydet."""
    os.makedirs(os.path.dirname(PROMPT_FILE), exist_ok=True)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(prompt)

AI_PROMPT = get_ai_prompt()

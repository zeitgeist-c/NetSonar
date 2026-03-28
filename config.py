"""
AgTara — Merkezi Yapılandırma
API anahtarlarını ve uygulama ayarlarını buradan düzenle.
"""

import json

# ─── AI Sağlayıcı Seçimi ────────────────────────────────────────────
# Kullanmak istediğin sağlayıcıyı seç: "openrouter" | "gemini"
AI_PROVIDER = "gemini"

# ─── OpenRouter ──────────────────────────────────────────────────────
OPENROUTER_API_KEY  = "REDACTED_OPENROUTER_KEY"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL    = "meta-llama/llama-3.3-70b-instruct:free"

# ─── Google Gemini ───────────────────────────────────────────────────
GEMINI_API_KEY = "REDACTED_GEMINI_KEY"
GEMINI_MODEL   = "gemini-2.0-flash-lite"          # Hızlı ve ücretsiz katman mevcut

# ─── Tehdit İstihbaratı (VirusTotal) ────────────────────────────────
VIRUSTOTAL_API_KEY     = "3abbf52d72bdd24acc636afa4120961c856f62fe9ade509cba9ca8e4519a5403"
VT_MALICIOUS_THRESHOLD = 3                         # Kaç motor kötü derse flagle?

# ─── Zamanlayıcı ────────────────────────────────────────────────────
# Her kaç dakikada bir AI analizi yapılsın?
ANALYSIS_INTERVAL_MINUTES = 60

# Anlık VT kontrolü için şüpheli sayılan minimum byte eşiği
SUSPICIOUS_BYTES_THRESHOLD = 50_000                # 50 KB üzeri harici bağlantı

# ─── Bilinen Tehlikeli Portlar ───────────────────────────────────────
SUSPICIOUS_PORTS = {4444, 1337, 31337, 5555, 6666, 6667, 8888, 9999}

# ─── Veritabanı ─────────────────────────────────────────────────────
DB_PATH = "agtara_data/connections.db"
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

DEFAULT_SYSTEM_PROMPT = """Sen AgTara'nin uzman siber guvenlik AI analistisin.

GOREV:
 Bir Windows bilgisayardan toplanan ag trafigi ozetini analiz edip JSON rapor uretmelisin.
 Veriler sadece META VERILERDIR: hedef IP, port, protokol, byte miktari, surec adi.
 Ham paket icerigi, URL, parola veya kisisel veri YOKTUR.

--- TEHDIT KATEGORILARI ---

1. BILINEN TEHDITLER:
   - Tor exit node, C2 sunucular, botnet IP'leri
   - VirusTotal'da kotu niyetli olarak isaretlenmis IP'ler
   - Bilinen malware domain'leri

2. DAVRANIS ANOMALILARI:
   - C2 (Command & Control) iletisim kalipjlari
   - Veri sizdirma (exfiltration) pattern'lari
   - Lateral movement (yatay hareket)
   - Port tarama aktiviteleri
   - Brute force girisimleri

3. TEKNIK INDIKATORLER:
   - Tehlikeli portlar: 4444, 1337, 31337, 5555, 6666, 6667, 8080, 8888, 9999
   - Anormal process-IP eslesmeleri (mshta.exe, wscript.exe, cmd.exe disinda)
   - Yuksek hacimli veri transferi (>1MB tek baglantida)
   - DNS tunneling belirtileri

4. ZAMAN BAZLI ANALIZ:
   - Mesai disi saatlerde (gece 02:00-06:00) otomatik baglantilar
   - Duzzensiz baglanti pattern'lari
   - Uzun sureli bekleyen baglantilar

--- CIKIS FORMATI (ZORUNLU JSON) ---
{
  "risk_score": 7.5,
  "status": "YUKSEK RISK",
  "threats_found": 3,
  "suspicious_connections": [
    {
      "ip": "185.220.101.5",
      "port": 4444,
      "process": "powershell.exe",
      "bytes_sent": 524288,
      "reason": "C2 iletisim pattern'i + Bilinen tehdit IP'si",
      "action": "Hemen engelle",
      "severity": "critical",
      "country": "DE"
    }
  ],
  "indicators": {
    "c2_patterns": ["..."],
    "exfil_detected": true,
    "port_scan_ips": ["..."],
    "suspicious_processes": ["powershell.exe"]
  },
  "recommendations": [
    "1. Ilgili IP'leri engelleyin",
    "2. powershell.exe surecini inceleyin",
    "3. Ag trafigini daha detayli izleyin"
  ],
  "summary": "3 adet kritik tehdit tespit edildi..."
}

--- RISK SKORU ---
0-2  → "GUVENLI"        (yesil)
3-5  → "DUSUK RISK"     (sari)
6-7  → "ORTA RISK"      (turuncu)
8-9  → "YUKSEK RISK"   (kirmizi)
10   → "KRITIK TEHDIT"  (siyah)

ONEMLI: 
- suspicious_connections BOS olabilir
- Sadece JSON dondur, baska yazi YAZMA
- Turkce cevapla"""

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

# ─── Kullanıcı Ayarları ─────────────────────────────────────────────
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
    }

def save_settings(data: dict):
    """Kullanıcı ayarlarını dosyaya kaydet."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

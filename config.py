"""
AgTara — Merkezi Yapılandırma
API anahtarlarını ve uygulama ayarlarını buradan düzenle.
"""

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

# ─── Bildirim Filtresi ───────────────────────────────────────────────
# True: sadece AI rapor bildirimleri gönderilir (önerilen)
# False: tüm anlık uyarılar (port, trafik vb.) da bildirim gönderir
NOTIFY_REPORTS_ONLY = True

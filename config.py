"""
NetSonar - Central configuration
Edit API keys and application settings here.
"""

import json
import logging
import os
import sys
from settings_service import protect_secret, unprotect_secret, validate_settings

log = logging.getLogger("NetSonar.Config")

APP_VERSION = "v0.6.5"
IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

if IS_FROZEN:
    USER_DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "NetSonar",
    )
else:
    # Gelistirme ortamindaki mevcut veri yerlesimini koru.
    USER_DATA_DIR = APP_DIR


def app_path(*parts: str) -> str:
    """Return the path for read-only resources shipped with the package."""
    return os.path.join(APP_DIR, *parts)


def user_data_path(*parts: str) -> str:
    """Return a writable path for settings, database, logs and reports."""
    return os.path.join(USER_DATA_DIR, *parts)


# Persistent model/extra-library store. Install and update never touch this
# folder; downloaded content survives a program version change.
STORE_DIR = user_data_path("store")


def install_language_file() -> str:
    """Path to install-language.txt in the install folder (NSIS language handoff)."""
    try:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base = APP_DIR
    return os.path.join(base, "install-language.txt")


def get_language() -> str:
    """Saved explicit UI choice; else the install handoff; else English."""
    try:
        from i18n import resolve as _resolve
        code = _settings.get("LANGUAGE")
        if code:
            return _resolve(code)
        try:
            with open(install_language_file(), "r", encoding="utf-8") as f:
                raw = (f.read() or "").strip()
            inst = raw.split()[0] if raw else ""
        except Exception:
            inst = ""
        if inst:
            return _resolve(inst)
        return "en"
    except Exception:
        return "en"


def set_language(code: str) -> str:
    """Persist the UI language choice and return the resolved code."""
    try:
        from i18n import resolve as _resolve, set_language as _set
        resolved = _resolve(code)
    except Exception:
        resolved = "en"
    _settings["LANGUAGE"] = resolved
    try:
        save_settings(_settings)
    except Exception:
        pass
    return resolved


def get_app_version() -> str:
    """Return the product version independently of the development Git tag."""
    return APP_VERSION


# ─── Settings loading (file first, then env) ──────────────────────
SETTINGS_FILE = user_data_path("config", "settings.json")
GEMINI_MODEL_OPTIONS = {
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
}
SUPPORTED_GEMINI_MODELS = tuple(GEMINI_MODEL_OPTIONS)
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_MODEL_SELECTION_VERSION = 1
# Default model alias kept for compatibility with older external callers.
GEMINI_MODEL_ID = DEFAULT_GEMINI_MODEL


def _default_settings() -> dict:
    return {
        "MINIMIZE_TO_TRAY": True,
        "AUTO_BLOCK_ENABLED": False,
        "AUTO_BLOCK_MIN_RISK_SCORE": 7.0,
        "autostart": False,
        "interface": None,
        "AI_PROVIDER": "gemini",
        "GEMINI_API_KEY": "",
        "GEMINI_API_KEYS": [],
        "GEMINI_MODEL": DEFAULT_GEMINI_MODEL,
        "GEMINI_MODEL_SELECTION_VERSION": GEMINI_MODEL_SELECTION_VERSION,
        "VIRUSTOTAL_API_KEY": "",
        "VIRUSTOTAL_API_KEYS": [],
        "TAVILY_API_KEY": "",
        "TAVILY_API_KEYS": [],
        "AUTO_ANALYSIS_ENABLED": True,
        "ANALYSIS_INTERVAL_MINUTES": 60,
        "HIGH_TRAFFIC_THRESHOLD_BYTES": 50 * 1024 * 1024,
        "UPDATE_LAST_CHECK": "",
        "LANGUAGE": "en",
        "UPDATE_LAST_SEEN_VERSION": "",
        "UPDATE_AVAILABLE": False,
        "AUTOSTART_ENABLED": False,
    }


def _write_settings(data: dict):
    data = dict(data)
    keys = _split_api_keys(data.get("GEMINI_API_KEYS", []))
    if not keys:
        keys = _split_api_keys(data.get("GEMINI_API_KEY", ""))
    protected = [protect_secret(key) for key in keys]
    data["GEMINI_API_KEYS"] = protected
    data["GEMINI_API_KEY"] = protected[0] if protected else ""
    for singular, plural in (("VIRUSTOTAL_API_KEY", "VIRUSTOTAL_API_KEYS"),
                             ("TAVILY_API_KEY", "TAVILY_API_KEYS")):
        provider_keys = _split_api_keys(data.get(plural, [])) or _split_api_keys(
            data.get(singular, ""))
        protected_provider_keys = [protect_secret(key) for key in provider_keys]
        data[plural] = protected_provider_keys
        data[singular] = protected_provider_keys[0] if protected_provider_keys else ""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    tmp_path = SETTINGS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, SETTINGS_FILE)


def _normalize_model_setting(data: dict) -> tuple[dict, bool]:
    """Validate the model setting and migrate the old pinned 3.1 entry to 3.5 once."""
    normalized = dict(data)
    changed = False

    if normalized.get("GEMINI_MODEL_SELECTION_VERSION") != GEMINI_MODEL_SELECTION_VERSION:
        normalized["GEMINI_MODEL"] = DEFAULT_GEMINI_MODEL
        normalized["GEMINI_MODEL_SELECTION_VERSION"] = GEMINI_MODEL_SELECTION_VERSION
        changed = True
    elif normalized.get("GEMINI_MODEL") not in SUPPORTED_GEMINI_MODELS:
        normalized["GEMINI_MODEL"] = DEFAULT_GEMINI_MODEL
        changed = True

    return normalized, changed

def load_settings():
    """Load user settings from disk."""
    if not os.path.exists(SETTINGS_FILE):
        return _default_settings()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Settings file root value must be an object")
    except Exception:
        log.warning("Settings file unreadable; using defaults: %s", SETTINGS_FILE)
        return _default_settings()

    data, changed = _normalize_model_setting(data)
    stored_keys = _split_api_keys(data.get("GEMINI_API_KEYS", [])) or _split_api_keys(
        data.get("GEMINI_API_KEY", ""))
    if any(not key.startswith("dpapi:") for key in stored_keys):
        changed = True
    for singular, plural in (("VIRUSTOTAL_API_KEY", "VIRUSTOTAL_API_KEYS"),
                             ("TAVILY_API_KEY", "TAVILY_API_KEYS")):
        stored_provider_keys = _split_api_keys(data.get(plural, [])) or _split_api_keys(
            data.get(singular, ""))
        if any(not key.startswith("dpapi:") for key in stored_provider_keys):
            changed = True
    data = validate_settings(data, _default_settings())
    try:
        keys = [unprotect_secret(key) for key in _split_api_keys(data.get("GEMINI_API_KEYS", []))]
        if not keys and data.get("GEMINI_API_KEY"):
            keys = [unprotect_secret(data["GEMINI_API_KEY"])]
        data["GEMINI_API_KEYS"] = keys
        data["GEMINI_API_KEY"] = keys[0] if keys else ""
    except Exception:
        log.warning("Stored Gemini keys undecryptable; continuing without them")
        data["GEMINI_API_KEYS"] = []
        data["GEMINI_API_KEY"] = ""
    for singular, plural in (("VIRUSTOTAL_API_KEY", "VIRUSTOTAL_API_KEYS"),
                             ("TAVILY_API_KEY", "TAVILY_API_KEYS")):
        try:
            provider_keys = [unprotect_secret(key) for key in _split_api_keys(
                data.get(plural, []))]
            if not provider_keys and data.get(singular):
                provider_keys = [unprotect_secret(str(data[singular]))]
            data[plural] = provider_keys
            data[singular] = provider_keys[0] if provider_keys else ""
        except Exception:
            log.warning("Stored %s keys undecryptable; continuing without them", plural)
            data[plural] = []
            data[singular] = ""
    if changed:
        try:
            _write_settings(data)
        except OSError:
            # A read-only settings file must not override other values such as the API key.
            pass
    return data


def save_settings(data: dict):
    """Save user settings to disk."""
    normalized = validate_settings(dict(data), _default_settings())
    if normalized.get("GEMINI_MODEL") not in SUPPORTED_GEMINI_MODELS:
        normalized["GEMINI_MODEL"] = DEFAULT_GEMINI_MODEL
    normalized["GEMINI_MODEL_SELECTION_VERSION"] = GEMINI_MODEL_SELECTION_VERSION
    _write_settings(normalized)


def _split_api_keys(value) -> list[str]:
    """API key listesini settings/env kaynaklarindan normalize et."""
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = value.replace(",", "\n").replace(";", "\n").splitlines()
    else:
        raw_items = []

    keys = []
    seen = set()
    for item in raw_items:
        key = str(item).strip()
        if key and key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def split_api_keys(value) -> list[str]:
    """API key listesini settings/env kaynaklarindan normalize et (public alias)."""
    return _split_api_keys(value)

# ─── AI provider selection ──────────────────────────────────────────
AI_PROVIDER = "gemini"

# ─── Google Gemini ───────────────────────────────────────────────────
_settings = load_settings()
_env_gemini_keys = os.getenv("AG_TARA_GEMINI_KEYS")
_env_gemini_key = os.getenv("AG_TARA_GEMINI_KEY")
GEMINI_API_KEYS = (
    _split_api_keys(_env_gemini_keys)
    or _split_api_keys(_env_gemini_key)
    or _split_api_keys(_settings.get("GEMINI_API_KEYS", []))
    or _split_api_keys(_settings.get("GEMINI_API_KEY", ""))
)
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
GEMINI_MODEL = _settings.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
if GEMINI_MODEL not in SUPPORTED_GEMINI_MODELS:
    GEMINI_MODEL = DEFAULT_GEMINI_MODEL
VIRUSTOTAL_API_KEYS = (
    _split_api_keys(os.getenv("AG_TARA_VIRUSTOTAL_KEYS"))
    or _split_api_keys(_settings.get("VIRUSTOTAL_API_KEYS", []))
    or _split_api_keys(_settings.get("VIRUSTOTAL_API_KEY", ""))
)
VIRUSTOTAL_API_KEY = VIRUSTOTAL_API_KEYS[0] if VIRUSTOTAL_API_KEYS else ""
TAVILY_API_KEYS = (
    _split_api_keys(os.getenv("AG_TARA_TAVILY_KEYS"))
    or _split_api_keys(_settings.get("TAVILY_API_KEYS", []))
    or _split_api_keys(_settings.get("TAVILY_API_KEY", ""))
)
TAVILY_API_KEY = TAVILY_API_KEYS[0] if TAVILY_API_KEYS else ""

# ─── Scheduler ──────────────────────────────────────────────────────
# How often, in minutes, the AI analysis runs?
ANALYSIS_INTERVAL_MINUTES = int(_settings.get("ANALYSIS_INTERVAL_MINUTES", 60))

# Minimum byte threshold for suspicious-connection detection
SUSPICIOUS_BYTES_THRESHOLD = int(
    _settings.get("HIGH_TRAFFIC_THRESHOLD_BYTES", 50 * 1024 * 1024)
)

# ─── Bilinen Tehlikeli Portlar ───────────────────────────────────────
SUSPICIOUS_PORTS = {4444, 1337, 31337, 5555, 6666, 6667, 8888, 9999}

# ─── Database ───────────────────────────────────────────────────────
DB_PATH = user_data_path("netsonar_data", "connections.db")
DB_RETENTION_HOURS = 2                     # Hours of raw data to keep; 0 = unlimited
DB_CLEANUP_INTERVAL_HOURS = 1              # How often cleanup runs, in hours

# ─── AI Limitleri ────────────────────────────────────────────────────
# Note: kept high to avoid data loss. The query already fetches the most
# important rows first (suspicious port, high traffic).
MAX_CONNECTIONS_TO_ANALYZE = 200           # Max connections sent to the AI
VIRUSTOTAL_MAX_LOOKUPS_PER_RUN = 4
VIRUSTOTAL_DAILY_SOFT_LIMIT = 480
VIRUSTOTAL_MAX_ANALYSIS_AGE_DAYS = 30
TAVILY_MAX_SEARCHES_PER_RUN = 2
TAVILY_MONTHLY_SOFT_LIMIT = 900
THREAT_INTEL_CACHE_HOURS = 24
THREAT_INTEL_UNKNOWN_CACHE_HOURS = 6
THREAT_INTEL_ERROR_BACKOFF_MINUTES = 15
SUSPICIOUS_PROCESSES = {
    "mshta.exe", "wscript.exe", "cscript.exe", "cmd.exe", "powershell.exe",
    "rundll32.exe", "regsvr32.exe", "certutil.exe",
}

# ─── Bildirim Filtresi ───────────────────────────────────────────────
# True: only AI report notifications are sent (recommended)
# False: all instant alerts (port, traffic, etc.) also send a notification
NOTIFY_REPORTS_ONLY = True

# ─── Otomatik Engelleme ─────────────────────────────────────────────
# True: when the AI says "block now", add to the firewall without asking
# False: ask the user (show a button in the GUI)
AUTO_BLOCK_ENABLED = bool(_settings.get("AUTO_BLOCK_ENABLED", False))

# Minimum risk score for auto-blocking (0-10)
# Only suggestions above this score are blocked automatically
AUTO_BLOCK_MIN_RISK_SCORE = float(_settings.get("AUTO_BLOCK_MIN_RISK_SCORE", 7.0))

# ─── Sistem ─────────────────────────────────────────────────────────────
# True: closing the window minimizes to the system tray
# False: closing the window quits for real
MINIMIZE_TO_TRAY = True

# ─── AI Prompt ─────────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """Sen NetSonar’nın uzman siber güvenlik yapay zekâ analistisin.

Görevin, bir Windows bilgisayardan toplanan ağ trafiği özetini analiz ederek yalnızca geçerli JSON formatında yapılandırılmış bir tehdit raporu üretmektir.

Girdi verileri yalnızca ağ trafiği meta verilerinden oluşur. Varsayılan olarak şu alanlar bulunabilir:

- hedef IP adresi
- port numarası
- protokol
- transfer edilen byte miktarı
- süreç adı

Girdide ayrıca varsa şu alanları da kullanabilirsin:

- zaman damgası
- bağlantı süresi
- bağlantı sayısı
- gönderilen byte miktarı
- alınan byte miktarı
- ülke bilgisi
- tehdit istihbaratı / IOC eşleşmesi
- bağlantı yönü
- DNS sorgu bilgileri

Ham paket içeriği, URL, parola, kişisel veri veya dosya içeriği bulunmadığını varsay.

Temel ilke:
Veride olmayan bilgiyi uydurma. Bir bulgu yalnızca verilen meta verilerle destekleniyorsa rapora ekle. Desteklenmeyen konuları kesin tespit gibi yazma.

TEHDİT ANALİZİ KAPSAMI

Aşağıdaki kategorilerde analiz yap:

1. Bilinen Tehditler

- Bilinen C2 sunucuları
- Botnet IP adresleri
- Tehdit istihbaratı kaynaklarında şüpheli olarak işaretlenmiş IP adresleri
- Zararlı yazılım altyapısıyla ilişkilendirilmiş göstergeler

Önemli kural:
Girdide açık bir tehdit istihbaratı, IOC listesi veya güvenilir eşleşme bilgisi yoksa hiçbir IP adresini “bilinen C2”, “bilinen botnet” veya “bilinen zararlı IP” olarak etiketleme.

2. Davranış Anomalileri

Aşağıdaki anomalileri yalnızca gerekli veri varsa değerlendir:

- C2 / beacon davranışı:
  Düzenli aralıklarla tekrar eden, otomatik görünen bağlantı kalıpları varsa şüpheli kabul et.
  Zaman damgası veya tekrar bilgisi yoksa bu tespiti kesin yapma.

- Veri sızdırma:
  Dış hedefe doğru yüksek hacimli gönderim varsa değerlendir.
  Yalnızca toplam byte bilgisi varsa bunu “yüksek hacimli transfer” olarak yorumla; yön bilgisi yoksa kesin exfiltration deme.

- Lateral movement:
  İç ağ IP’leri arasında alışılmadık bağlantılar varsa değerlendir.
  Kaynak IP veya iç ağ bağlamı yoksa kesin lateral movement tespiti yapma.

- Port tarama:
  Kısa sürede çok sayıda porta bağlantı girişimi varsa değerlendir.
  Zaman veya bağlantı sayısı yoksa kesin port tarama deme.

- Brute force:
  Aynı hedefe çok sayıda başarısız bağlantı veya kimlik doğrulama denemesi varsa değerlendir.
  Başarısız deneme bilgisi yoksa brute force tespiti yapma.

3. Teknik Göstergeler

Aşağıdaki teknik göstergeleri analiz et:

Riskli portlar:
4444, 1337, 31337, 5555, 6666, 6667, 8080, 8888, 9999

Şüpheli süreçler:
mshta.exe, wscript.exe, cscript.exe, cmd.exe, powershell.exe, rundll32.exe, regsvr32.exe, certutil.exe

Anormal process-IP eşleşmeleri:
Yukarıdaki sistem araçlarından birinin doğrudan dış IP adresine bağlantı kurması şüpheli kabul edilir.

Yüksek hacimli transfer:
Tek bağlantıda 1 MB üzeri veri transferi varsa risk göstergesi olarak değerlendir.
Yön bilgisi varsa ve trafik dışa doğruysa exfiltration şüphesini artır.
Yön bilgisi yoksa yalnızca “yüksek hacimli transfer” olarak belirt.

DNS tünelleme:
DNS tünelleme şüphesini yalnızca DNS sorgu adı, sorgu boyutu, sorgu frekansı, TXT kayıtları veya anormal DNS tekrarları gibi veri varsa değerlendir.
Sadece IP, port, protokol, byte ve process bilgisiyle DNS tünelleme tespiti yapma.

4. Zaman Bazlı Analiz

Aşağıdaki analizleri yalnızca zaman verisi varsa yap:

- 02:00–06:00 arasında gerçekleşen otomatik bağlantılar
- Uzun süre açık kalan bağlantılar
- Beacon benzeri düzenli bağlantı frekansları
- Mesai dışı anormal trafik

Zaman verisi yoksa after_hours_activity değerini false yap.

RİSK SKORLAMA

risk_score 0.0 ile 10.0 arasında ondalıklı sayı olmalıdır.

Aşağıdaki eşikleri kullan:

- 0.0 – 2.9: GÜVENLİ
- 3.0 – 5.9: DÜŞÜK RİSK
- 6.0 – 7.9: ORTA RİSK
- 8.0 – 9.4: YÜKSEK RİSK
- 9.5 – 10.0: KRİTİK TEHDİT

Skoru belirlerken şu sinyalleri birlikte değerlendir:

- Bilinen IOC / tehdit istihbaratı eşleşmesi
- Riskli port kullanımı
- Şüpheli sistem süreci
- Dış IP bağlantısı
- Yüksek hacimli transfer
- Tekrarlı / beacon benzeri davranış
- Mesai dışı aktivite
- Çok sayıda porta erişim denemesi
- DNS tünelleme göstergesi
- Aynı anda birden fazla risk göstergesinin bulunması

Şüpheli tek bir zayıf sinyal varsa skoru abartma.
Birden fazla güçlü sinyal birleşiyorsa skoru yükselt.
Veri yetersizse kesin tehdit dili kullanma.

ÇIKIŞ FORMATI

Yanıtın yalnızca geçerli JSON olmalıdır.
Markdown, açıklama, başlık, yorum veya kod bloğu ekleme.
JSON dışında hiçbir metin yazma.
JSON alan adlarını aşağıdaki şemadaki gibi birebir kullan.
severity değerleri yalnızca şu dört değerden biri olabilir:
"low", "medium", "high", "critical"

Şema:

{
  "risk_score": 0.0,
  "status": "GÜVENLİ",
  "threats_found": 0,
  "suspicious_connections": [
    {
      "ip": "string",
      "port": 0,
      "protocol": "string",
      "process": "string",
      "bytes_sent": 0,
      "bytes_received": 0,
      "country": "unknown",
      "severity": "low",
      "reason": "string",
      "action": "string"
    }
  ],
  "indicators": {
    "c2_patterns": [],
    "exfil_detected": false,
    "port_scan_ips": [],
    "suspicious_processes": [],
    "dns_tunneling_suspected": false,
    "after_hours_activity": false,
    "known_threat_matches": [],
    "high_volume_transfers": [],
    "risky_ports_detected": []
  },
  "recommendations": [],
  "summary": "string"
}

ALAN KURALLARI

risk_score:
Genel risk skorunu 0.0–10.0 arasında ver.

status:
Risk skoruna göre yalnızca şu değerlerden birini kullan:
"GÜVENLİ", "DÜŞÜK RİSK", "ORTA RİSK", "YÜKSEK RİSK", "KRİTİK TEHDİT"

threats_found:
suspicious_connections dizisindeki şüpheli bağlantı sayısını yaz.

suspicious_connections:
Yalnızca kanıtlanabilir şekilde şüpheli görünen bağlantıları ekle.
Tehdit yoksa boş dizi döndür: []

ip:
Hedef IP adresini yaz.

port:
Port numarasını yaz.

protocol:
TCP, UDP, DNS, ICMP veya girdide verilen protokol değerini yaz.

process:
Bağlantıyı yapan süreç adını yaz.

bytes_sent:
Girdide gönderilen byte bilgisi varsa yaz.
Yoksa ve yalnızca toplam byte bilgisi varsa bu alana toplam byte değerini yaz.

bytes_received:
Girdide alınan byte bilgisi varsa yaz.
Yoksa 0 yaz.

country:
Girdide ülke bilgisi varsa yaz.
Yoksa "unknown" yaz.
Ülke bilgisi uydurma.

severity:
Bağlantı riskine göre "low", "medium", "high" veya "critical" değerlerinden birini kullan.

reason:
Şüphe nedenini kısa, net ve kanıta dayalı yaz.
Örnek:
"Riskli port kullanımı; powershell.exe süreci üzerinden dış IP bağlantısı; yüksek hacimli transfer"

action:
Önerilen müdahaleyi kısa ve uygulanabilir yaz.
Örnek:
"Süreci incele, hedef IP bağlantısını geçici olarak engelle, uç noktayı EDR ile tara"

indicators.c2_patterns:
Yalnızca zaman, tekrar veya düzenli bağlantı bilgisi varsa doldur.
Yoksa boş dizi kullan.

indicators.exfil_detected:
Yön bilgisi ve yüksek dışa veri gönderimi varsa true yap.
Yön bilgisi yoksa yalnızca toplam byte yüksek diye true yapma.

indicators.port_scan_ips:
Port tarama davranışı kanıtlanabiliyorsa ilgili IP’leri ekle.
Yoksa boş dizi kullan.

indicators.suspicious_processes:
Şüpheli süreç adlarını listele.
Tekrar edenleri yalnızca bir kez yaz.

indicators.dns_tunneling_suspected:
Yalnızca DNS tünelleme için yeterli DNS verisi varsa true yap.
Yoksa false yap.

indicators.after_hours_activity:
Zaman verisi varsa ve aktivite 02:00–06:00 aralığında gerçekleşmişse true yap.
Zaman verisi yoksa false yap.

indicators.known_threat_matches:
Yalnızca girdide tehdit istihbaratı / IOC eşleşmesi açıkça verilmişse doldur.
Yoksa boş dizi kullan.

indicators.high_volume_transfers:
1 MB üzeri transfer içeren bağlantıları kısa açıklamalarla listele.
Yoksa boş dizi kullan.

indicators.risky_ports_detected:
Tespit edilen riskli portları listele.
Yoksa boş dizi kullan.

recommendations:
Bulgulara göre uygulanabilir savunma önerileri üret.
Öneriler genel ama pratik olmalıdır.
Örnekler:
- Şüpheli hedef IP adreslerini güvenlik duvarında geçici olarak engelleyin.
- Şüpheli süreçlerin başlatılma kaynağını inceleyin.
- Uç noktayı EDR veya antivirüs ile tarayın.
- SIEM üzerinde aynı IP, süreç ve port kombinasyonları için geçmiş korelasyon yapın.
- Gerekiyorsa kullanıcı hesabı ve cihaz izolasyonu uygulayın.

summary:
Genel sonucu kısa ve net özetle.
Veri yetersizliği varsa bunu açıkça belirt.
Kesin olmayan bulguları kesin tehdit gibi sunma.

JSON GEÇERLİLİK KURALLARI

- Yalnızca JSON döndür.
- JSON içinde yorum satırı kullanma.
- Sondaki virgüllerden kaçın.
- Boolean değerleri true / false olarak yaz.
- Sayısal değerleri tırnak içine alma.
- Boş veri varsa [] veya false kullan.
- Bilinmeyen ülke için "unknown" kullan.
- Tehdit yoksa risk_score değerini düşük tut, suspicious_connections alanını [] yap ve threats_found değerini 0 yaz."""

PROMPT_FILE = user_data_path("config", "ai_prompt.txt")
DEFAULT_PROMPT_FILE = app_path("config", "ai_prompt.txt")

def get_ai_prompt():
    """Load the AI prompt from disk, falling back to the built-in default."""
    for prompt_file in (PROMPT_FILE, DEFAULT_PROMPT_FILE):
        if not os.path.exists(prompt_file):
            continue
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
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

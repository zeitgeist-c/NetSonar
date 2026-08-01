"""
NetSonar — Merkezi Yapılandırma
API anahtarlarını ve uygulama ayarlarını buradan düzenle.
"""

import json
import os
import subprocess
import sys

APP_VERSION = "v0.4.6"
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
    """Paketle gelen salt-okunur kaynaklar icin yol dondur."""
    return os.path.join(APP_DIR, *parts)


def user_data_path(*parts: str) -> str:
    """Ayar, veritabani, log ve raporlar icin yazilabilir yol dondur."""
    return os.path.join(USER_DATA_DIR, *parts)


def get_app_version() -> str:
    """Git tag üzerinden dinamik uygulama versiyonunu döndürür."""
    if IS_FROZEN:
        return APP_VERSION
    try:
        # Popen kullanarak arkaplan penceresi oluşturmadan komutu çalıştır (Windows GUI için)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=APP_DIR, stderr=subprocess.DEVNULL, creationflags=creationflags, text=True
        ).strip()
        # Eğer sadece hash dönüyorsa (ör: 16cdc88), başına v eklemiyoruz çünkü "v0.4.6-1-g..." formatı daha makul
        return version if version.startswith("v") else f"v{version}"
    except Exception:
        return APP_VERSION


# ─── Settings Yükleme (önce dosya, sonra env) ──────────────────────
SETTINGS_FILE = user_data_path("config", "settings.json")
GEMINI_MODEL_OPTIONS = {
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
}
SUPPORTED_GEMINI_MODELS = tuple(GEMINI_MODEL_OPTIONS)
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_MODEL_SELECTION_VERSION = 1
# Eski dış kullanımlarla uyumluluk için varsayılan model takma adı.
GEMINI_MODEL_ID = DEFAULT_GEMINI_MODEL


def _default_settings() -> dict:
    return {
        "MINIMIZE_TO_TRAY": True,
        "AUTO_BLOCK_ENABLED": False,
        "autostart": False,
        "interface": None,
        "AI_PROVIDER": "gemini",
        "GEMINI_API_KEY": "",
        "GEMINI_API_KEYS": [],
        "GEMINI_MODEL": DEFAULT_GEMINI_MODEL,
        "GEMINI_MODEL_SELECTION_VERSION": GEMINI_MODEL_SELECTION_VERSION,
        "AUTO_ANALYSIS_ENABLED": True,
        "ANALYSIS_INTERVAL_MINUTES": 60,
    }


def _write_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _normalize_model_setting(data: dict) -> tuple[dict, bool]:
    """Model ayarını doğrula ve eski sabit 3.1 kaydını bir kez 3.5'e taşı."""
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
    """Kullanıcı ayarlarını dosyadan yükle."""
    if not os.path.exists(SETTINGS_FILE):
        return _default_settings()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Ayar dosyasının kök değeri nesne olmalı")
    except Exception:
        return _default_settings()

    data, changed = _normalize_model_setting(data)
    if changed:
        try:
            _write_settings(data)
        except OSError:
            # Salt-okunur bir ayar dosyası API key gibi diğer değerleri geçersiz kılmamalı.
            pass
    return data


def save_settings(data: dict):
    """Kullanıcı ayarlarını dosyaya kaydet."""
    normalized = dict(data)
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

# ─── AI Sağlayıcı Seçimi ────────────────────────────────────────────
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

# ─── Zamanlayıcı ────────────────────────────────────────────────────
# Her kaç dakikada bir AI analizi yapılsın?
ANALYSIS_INTERVAL_MINUTES = 60

# Şüpheli bağlantı tespiti için minimum byte eşiği
SUSPICIOUS_BYTES_THRESHOLD = 50_000                # 50 KB üzeri harici bağlantı

# ─── Bilinen Tehlikeli Portlar ───────────────────────────────────────
SUSPICIOUS_PORTS = {4444, 1337, 31337, 5555, 6666, 6667, 8888, 9999}

# ─── Veritabanı ─────────────────────────────────────────────────────
DB_PATH = user_data_path("netsonar_data", "connections.db")
DB_RETENTION_HOURS = 2                     # Kaç saatlik ham veri saklansın? 0 = sınırsız
DB_CLEANUP_INTERVAL_HOURS = 1              # Temizlik kaç saatte bir yapılsın?

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
    """AI prompt'u dosyadan yükle, yoksa varsayılanı kullan."""
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

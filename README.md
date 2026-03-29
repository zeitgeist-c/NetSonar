# NetSonar — AI Destekli Ağ İzleme Aracı

> Windows tabanlı, PyQt6 GUI'li, yapay zeka entegreli ağ trafiği izleme ve anomali tespiti aracı.

---

## Özellikler

| Özellik | Detay |
|---|---|
| **Canlı İzleme** | Scapy + Npcap ile tüm ağ trafiğini paket düzeyinde yakalar |
| **AI Analizi** | OpenRouter, Ollama (yerel) veya Gemini API ile anormalileri tespit eder |
| **Kill-Switch** | Şüpheli IP'leri Windows Güvenlik Duvarı'na tek tıkla ekler |
| **Zeka Analizi** | AI modelleri (Gemini, Llama vb.) ile davranışsal analiz |
| **Masaüstü Bildirimi** | Şüpheli port veya yüksek trafik anında Windows toast bildirimi |
| **Dark-theme GUI** | PyQt6 tabanlı, 4 sekmelik modern arayüz |
| **System Tray** | Arka planda sessizce çalışır |

---

## Kurulum

### 1. Gereksinimler
- **Python 3.11+** → [python.org](https://python.org)
- **Npcap** (Scapy için zorunlu) → [npcap.com](https://npcap.com)

### 2. Bağımlılıkları Kur

```bash
pip install -r requirements.txt
```

### 3. Başlat

**Önerilen** (otomatik kurulum + admin kontrolü):
```
NetSonar.bat dosyasını çift tıkla
```

**Manuel:**
```bash
# Administrator olarak CMD/PowerShell aç
python main.py
```

---

## Yapılandırma

`config.py` dosyasını düzenle:

```python
# AI sağlayıcı seç
AI_PROVIDER = "openrouter"   # "openrouter" | "ollama" | "gemini"

# API Anahtarları
OPENROUTER_API_KEY = "sk-or-..."
GEMINI_API_KEY     = "AIza..."

# Analiz Aralığı
ANALYSIS_INTERVAL_MINUTES = 60
```

> **Not:** Ayarlar GUI içindeki "Ayarlar" sekmesinden de değiştirilebilir.

---

## Kullanım

### GUI Modu (Varsayılan)
```
python main.py
```

### CLI Komutları
```bash
python main.py --analyze              # Anlık AI analizi
python main.py --block 185.220.101.5  # IP engelle
python main.py --unblock 1.2.3.4      # IP engeli kaldır
python main.py --list-blocked         # Engellenen IP'leri listele
# AI analizi dashboard üzerinden veya otomatik çalışır
python main.py --no-gui               # Konsol modu
```

---

## Proje Yapısı

```
NetSonar/
├── main.py              # Giriş noktası (GUI + CLI)
├── app_gui.py           # PyQt6 arayüzü
├── config.py            # API anahtarları ve ayarlar
├── database.py          # SQLite veritabanı katmanı
├── capture_engine.py    # Scapy paket yakalama
├── ai_analyzer.py       # OpenRouter / Ollama / Gemini
├── ai_analyzer.py       # AI analiz motoru
├── kill_switch.py       # Windows Güvenlik Duvarı
├── notifier.py          # Windows toast bildirimleri
├── scheduler.py         # APScheduler zamanlayıcı
├── requirements.txt     # Python bağımlılıkları
└── NetSonar.bat           # Windows başlatıcı
```

---

## Güvenlik Notu

- Uygulama **Yönetici (Administrator)** yetkisi gerektirir.
- AI modelleri (Gemini, OpenRouter) kendi kullanım limitlerine tabidir.
- AI'a **ham paket verisi gönderilmez** — sadece özetlenmiş metadata.

---

## Lisans

MIT License — Kişisel ve ticari kullanım serbesttir.

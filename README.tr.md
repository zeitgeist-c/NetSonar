# NetSonar — Windows için yapay zekâ destekli ağ görünürlüğü

> English: [README.md](./README.md)

Yerel ağ trafiği analizi ve SOC yardımcısı: Npcap ile dakikalık çift yönlü akış özetleri, VirusTotal + web bağlamlı Gemini risk analizi ve denetimli Windows Güvenlik Duvarı engelleme. Ham detay tasarım gereği silinir — içerik, URL, parola kaydı yok.

![NetSonar ekran görüntüleri](./docs/screenshots/)

> Ekran görüntüleri temiz kurulumdan ekleniyor (örnek veri yok). Yukarıdaki klasöre konacak.

## Gereksinimler

- Windows 10/11, Python 3.11+, yönetici yetkisi
- Npcap (`C:\Windows\System32\Npcap\wpcap.dll`)

## Hızlı başlangıç

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Tek seferlik komutlar:

```powershell
.\.venv\Scripts\python.exe main.py --analyze
.\.venv\Scripts\python.exe main.py --block 8.8.8.8
.\.venv\Scripts\python.exe main.py --unblock 8.8.8.8
.\.venv\Scripts\python.exe main.py --list-blocked
```

Diğer bayraklar: `--no-gui`, `--accept-v05-reset` (v0.5 depolama sıfırlama onayı). Hazır derleme: `dist\NetSonar-v0.5.7.exe` + `.bat`.

## Özellikler

- **Canlı yakalama** — Npcap/scapy + dakikalık çift yönlü `FlowBucket` özetleri.
- **Süreç eşleme** — süreç, uç, port, protokol sayaçları (bayt/paket, gönderilen/alınan ayrı).
- **YZ analizi** — toplu yapılandırılmış Gemini analizi; sahte IP/kaynak yerel doğrulamada reddedilir.
- **Tehdit istihbaratı** — VirusTotal itibarı + web bağlamı; yalnızca seçilmiş genel uzak IP'ler gönderilir.
- **Anahtar yedekliliği** — çoklu API anahtarı + otomatik geçiş, DPAPI şifreli saklama.
- **Duvar engelleme** — denetimli çift yönlü kurallar (`NetSonar` grubu); varsayılan kapalı, otomatik engel yalnız kritik + ≥0.95 güven + `block_now`.
- **SOC paneli** — PyQt6 canlı akış tablosu, metrik kartları, rapor görünümü, tepsi simgesi.
- **Zamanlayıcı** — periyodik analiz + DB bakımı, masaüstü bildirimler.
- **Raporlar** — JSON/CSV/TXT dışa aktarma.
- **Gizlilik öncelikli saklama** — ham detay silinir, IP'siz saatlik toplam + 30 gün denetim, analizsiz detay 24 saatte anonimleşir.

## Proje yapısı

```text
main.py              CLI + GUI girişi (UAC yükseltme, tek örnek)
app_gui.py           SOC paneli (ui_components.py, ui_theme.py)
capture_engine.py    canlı yakalama (flow_accumulator.py, flow_utils.py)
ai_analyzer.py       Gemini analizi (config/ai_prompt.txt)
threat_intel.py      VirusTotal + web bağlamı
database.py          depolama (models.py, migration.py)
scheduler.py         periyodik işler (notifier.py, custom_alerts.py)
kill_switch.py       duvar engelleme
config.py            ayarlar (settings_service.py, DPAPI)
exporter.py          JSON/CSV/TXT raporlar
packaging/  assets/  tests/  dist/
```

## Katkı

Küçük PR, test verisine yakalama/anahtar konmaz. Bkz. [.github/PULL_REQUEST_TEMPLATE.md](./.github/PULL_REQUEST_TEMPLATE.md).

## Lisans

Bkz. [LICENSE](./LICENSE) (bekliyor — teyit edilecek).

# NetSonar - AI Destekli Ağ İzleme Aracı

Windows tabanlı, PyQt6 arayüzlü ağ trafiği izleme ve anomali analizi aracı.

## Özellikler

| Özellik | Detay |
|---|---|
| Canlı izleme | Scapy + Npcap ile ağ trafiğini paket düzeyinde yakalar. |
| AI analizi | Gemini 3.1 Flash Lite ile özet trafik verisini analiz eder; çoklu Gemini API key desteklenir. |
| Kill switch | Şüpheli IP adreslerini Windows Güvenlik Duvarı kurallarıyla engeller. |
| Güvenli IP listesi | Kullanıcının güvenli olarak onayladığı IP adreslerini sonraki AI analizlerinden ve otomatik engellemeden çıkarır. |
| Masaüstü bildirimi | Şüpheli port, yüksek trafik ve analiz sonuçlarında bildirim gösterir. |
| Sistem tepsisi | Uygulama arka planda çalışmaya devam edebilir. |
| Veri saklama | SQLite üzerinde bağlantı ve rapor geçmişi tutar, eski kayıtları temizler. |

## Kurulum

### Gereksinimler

- Python 3.11+
- Npcap
- Windows üzerinde yönetici yetkisi

### Bağımlılıkları kurma

```bash
pip install -r requirements.txt
```

### Başlatma

Önerilen yol:

```text
NetSonar.bat dosyasını yönetici olarak çalıştırın.
```

Manuel kullanım:

```bash
python main.py
```

## CLI Komutları

```bash
python main.py --analyze
python main.py --block 185.220.101.5
python main.py --unblock 1.2.3.4
python main.py --list-blocked
python main.py --no-gui
```

## Yapılandırma

Ayarlar uygulama içindeki Ayarlar sekmesinden veya `config/settings.json` dosyasından yönetilir.

Önemli ayarlar:

- `AI_PROVIDER`: sabit `gemini`
- `GEMINI_MODEL`: sabit `gemini-3.1-flash-lite`
- `GEMINI_API_KEYS`: her satıra bir Gemini API key olacak şekilde çoklu key listesi
- `GEMINI_API_KEY`: eski tek-key uyumluluğu için ilk key olarak okunur
- `AUTO_ANALYSIS_ENABLED`
- `ANALYSIS_INTERVAL_MINUTES`
- `AUTO_BLOCK_ENABLED`

Bir Gemini API key 429 veya 503 dönerse 30 dakika bekletilir ve aynı analiz isteği listedeki sıradaki uygun key ile denenir.

## Veri ve Gizlilik

AI servislerine ham paket içeriği gönderilmez. Analiz için yalnızca bağlantı özeti kullanılır: hedef IP, port, protokol, süreç adı, bağlantı sayısı ve byte toplamı.

Güvenli IP'ler menüsünden eklenen adresler bağlantı geçmişinde görünmeye devam eder ancak Gemini'ye gönderilmez ve otomatik engellenmez. Kayıt, kullanıcı listeden çıkarana kadar kalıcıdır.

## Proje Yapısı

```text
main.py             Uygulama giriş noktası
app_gui.py          PyQt6 arayüzü
capture_engine.py   Scapy tabanlı paket yakalama
database.py         SQLite veri katmanı
ai_analyzer.py      AI sağlayıcı entegrasyonları
kill_switch.py      Windows Firewall engelleme işlemleri
config.py           Ayarlar, dosya yolları ve varsayılanlar
```

## Notlar

- Paket yakalama ve firewall işlemleri yönetici yetkisi gerektirir.
- Npcap kurulu değilse canlı izleme çalışmayabilir.
- Gemini API kullanım limitleri ve kota kuralları geçerlidir; çoklu key kullanımı kota hatalarında geçici key değişimi sağlar.

# NetSonar - AI Destekli Ağ İzleme Aracı

Windows tabanlı, PyQt6 arayüzlü ağ trafiği izleme ve anomali analizi aracı.

## Özellikler

| Özellik | Detay |
|---|---|
| Canlı izleme | Scapy + Npcap ile ağ trafiğini paket düzeyinde yakalar. |
| AI analizi | Varsayılan Gemini 3.5 Flash-Lite ile özet trafik verisini analiz eder; Gemini 3.1 seçeneği ve çoklu API key desteklenir. |
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
- `GEMINI_MODEL`: `gemini-3.5-flash-lite` (varsayılan) veya `gemini-3.1-flash-lite`; Ayarlar ekranından seçilir
- `GEMINI_MODEL_SELECTION_VERSION`: eski sabit model ayarının tek seferlik geçişini izleyen dahili sürüm
- `GEMINI_API_KEYS`: her satıra bir Gemini API key olacak şekilde çoklu key listesi
- `GEMINI_API_KEY`: eski tek-key uyumluluğu için ilk key olarak okunur
- `AUTO_ANALYSIS_ENABLED`
- `ANALYSIS_INTERVAL_MINUTES`
- `AUTO_BLOCK_ENABLED`

Model seçimi kaydedildikten sonra uygulamayı yeniden başlatmadan bir sonraki otomatik veya manuel analizde kullanılır. Eski sabit 3.1 ayarı, model seçimi özelliğinin ilk çalışmasında bir kez varsayılan 3.5'e geçirilir; bundan sonraki kullanıcı seçimi korunur.

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

# NetSonar — Windows için yapay zekâ destekli ağ görünürlüğü

> English: [README.md](./README.md)

**Makinenin kiminle konuştuğunu gör, bir sorun olup olmadığını yapay zekâ söylesin.**

NetSonar, yerel ağ trafiğini Npcap üzerinden yakalar, dakikalık çift yönlü akışlara özetler, her akışı onu açan süreçle eşler ve özeti VirusTotal itibarı ile web bağlamıyla desteklenmiş bir risk değerlendirmesi için Gemini'ye gönderir. Bir şeyin engellenmesi gerektiğine sen karar verdiğinde denetimli bir Windows Güvenlik Duvarı kuralı yazar.

Ham yük tasarım gereği atılır — içerik, URL, parola kaydedilmez.

![NetSonar · Panel](./docs/screenshots/01-panel.png)

---

## İçindekiler

- [Ne yapar](#ne-yapar)
- [Ekranlar, tek tek](#ekranlar-tek-tek)
  - [1. Panel](#1-panel)
  - [2. Analiz](#2-analiz)
  - [3. Akışlar](#3-akışlar)
  - [4. Kurallar](#4-kurallar)
  - [5. Anahtarlar](#5-anahtarlar)
  - [6. Ayarlar](#6-ayarlar)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Komut satırı](#komut-satırı)
- [Analiz nasıl çalışır](#analiz-nasıl-çalışır)
- [Gizlilik ve saklama](#gizlilik-ve-saklama)
- [Proje yapısı](#proje-yapısı)
- [Lisans](#lisans)

---

## Ne yapar

| Yetenek | Ayrıntı |
|---|---|
| **Canlı yakalama** | Npcap + scapy, dakikalık çift yönlü akış kovalarına özetlenir |
| **Süreç eşleme** | süreç, uç nokta, port ve protokol sayaçları; gönderilen/alınan ayrımıyla |
| **AI analizi** | toplu yapılandırılmış Gemini analizi; uydurulan IP, kaynak ve akış kimlikleri yerel doğrulamayla reddedilir |
| **Tehdit istihbaratı** | yalnız seçilmiş genel uzak IP'ler için VirusTotal itibarı ve web bağlamı |
| **Anahtar yedekleme** | birden çok API anahtarı, otomatik yedekleme, DPAPI ile şifreli saklama |
| **Güvenlik duvarı engelleme** | `NetSonar` grubunda denetimli çift yönlü kurallar; varsayılan kapalı |
| **SOC paneli** | canlı akış tablosu, metrik kartları, rapor görünümü, tepsi simgesi |
| **Zamanlayıcı** | zamanlanmış analiz ve veritabanı bakımı, masaüstü bildirimleri |
| **Raporlar** | JSON, CSV ve TXT dışa aktarımı |
| **Saklama** | ham detay atılır, IP'siz saatlik toplamlar 30 gün, analiz edilmemiş detay 24 saatte anonimleşir |

---

## Ekranlar, tek tek

Aşağıdaki görüntüler veri içermeyen temiz bir kurulumdan alındı; sayaçların sıfır okunması ilk açılışın gerçek görüntüsüdür.

### 1. Panel

![Panel](./docs/screenshots/01-panel.png)

Operasyon merkezi. Üstte dört kart:

| Kart | Anlamı |
|---|---|
| **Bugünkü Akış** | bugün yakalanan akış sayısı, canlı güncellenir |
| **Tehdit** | yapay zekânın işaretlediği toplam tehdit |
| **Engellenen** | güvenlik duvarı kuralıyla engellenen IP sayısı |
| **AI Raporu** | saklanan analiz raporu sayısı |

Kartların altında **trafik grafiği** — saat / gün / hafta / 30 gün toplamları ve gönderilen-alınan ayrımı — ile **en yüksek trafik** paneli yer alır. Sağda **Canlı Akış**, yeni hedefleri yakalandığı anda gösterir; analiz beklemez.

Üst çubuk sensör durumunu (`SENSÖR AKTİF`), yakalama durumunu (`YAKALAMA KAPALI` / açık) ve `AI Analizi Başlat` eylemini taşır. Durum çubuğu özetleri tekrarlar: izleme durumu, etkin arayüz, AI sağlayıcısı, sonraki zamanlanmış analiz, veritabanı durumu.

### 2. Analiz

![Analiz](./docs/screenshots/02-analiz.png)

Son AI çalıştırmasının sonucu.

- **Risk skoru** ve etiketi (`riskli`, `orta risk`, `temiz`), üreten sağlayıcı ve zaman damgası.
- **Kısa sonuç** — düz dille karar; tetikleyen süreci, portu ve hedefi adıyla söyler.
- **Tespit edilen riskler** — her bulgu için bir madde.
- **Önerilen işlemler** — sırada neyi kontrol edeceğin veya ne yapacağın.
- **Şüpheli akışlar** tablosu: IP/port, süreç, neden işaretlendiği, öneri, durum ve `Güven` ile güvenli listeye alma eylemi.
- Sağda **rapor geçmişi**: her saklanan rapor için tarih, sağlayıcı, risk ve durum.
- `JSON`, `CSV`, `TXT` dışa aktarım düğmeleri.

Boş durum açıkça söylenir — veri varmış gibi sıfır çizilmiş bir grafik yerine `Henüz analiz yapılmadı`.

**Doğrulama.** Bir sonuç gösterilmeden önce modelin döndürdüğü akış kimlikleri, kaynak IP'ler ve adresler gerçekten yakalananlarla karşılaştırılır. Modelin uydurduğu ne varsa reddedilir; yani hayali bir IP bulgu olarak görünemez.

### 3. Akışlar

![Akışlar](./docs/screenshots/03-akislar.png)

Kaydedilen her akış, en yenisi üstte.

| Sütun | Anlamı |
|---|---|
| **Durum** | önem rozeti (`YÜKSEK`, `NORMAL`) |
| **Bağ** | akışın bağlantı sayısı |
| **Hedef IP** | hedef adres |
| **Port** | hedef port |
| **Proto** | TCP / UDP |
| **Veri** | aktarılan bayt |
| **Süreç** | akışı açan süreç |

Filtreler: `Tümü`, `Şüpheli port`, `>50MB`, `Mesai dışı`, ayrıca sayfa boyutu seçici ve IP veya süreç üzerinde serbest arama. `Listeyi Yenile` veritabanından yeniden okur.

Satır eylemleri doğrudan IP engeller — bu yol da Kurallar sayfasıyla aynı denetimli güvenlik duvarı kodundan geçer.

### 4. Kurallar

![Kurallar](./docs/screenshots/04-kurallar.png)

İki sekme: **Engellenenler** ve **Güvenli IP'ler**.

Engellenen hedefler savunma katmanıdır: her girdi, `NetSonar` grubunda iki yönde oluşturulmuş bir Windows Güvenlik Duvarı kuralına karşılık gelir. Güvenli listedeki adresler analizden tamamen çıkarılır — hiçbir dış servise gönderilmez.

Üstteki sayaçlar (`TOPLAM`, `BUGÜN`) ve arama kutusu iki sekmede de çalışır. Boş durum `Engellenen IP yok` der ve girdilerin nerede görüneceğini açıklar.

### 5. Anahtarlar

![Anahtarlar](./docs/screenshots/05-anahtarlar.png)

Sağlayıcı kimlik bilgileri ve kotaları, sağlayıcı başına bir kart:

| Sağlayıcı | Ne için |
|---|---|
| **Gemini** | AI analiz motoru |
| **VirusTotal** | IP itibarı |
| **Tavily** | güncel web araştırması |

Her kartta durum rozeti (ayarlanmamışsa `YOK`) ve `Yönet` eylemi var. Kullanım sayaçları bugünkü veya bu aylık tüketimi sınıra göre gösterir — VirusTotal için günlük `0 / 480`, Tavily için aylık `0 / 900`.

Anahtarlar geçerli Windows kullanıcısı için DPAPI ile şifrelenir; veritabanına düz metin olarak asla yazılmaz ve bir raporda asla görünmez. Birden çok Gemini anahtarı saklanabilir ve biri sınıra takıldığında veya reddedildiğinde otomatik yedeklemeyle kullanılır.

### 6. Ayarlar

![Ayarlar](./docs/screenshots/06-ayarlar.png)

Solda beş bölüm:

| Bölüm | İçeriği |
|---|---|
| **Genel** | Windows başlangıcında çalıştır, kapatınca tepsiye küçült |
| **Analiz** | analiz sıklığı, toplu işleme, sağlayıcı ve model seçimi |
| **Güvenlik** | engelleme davranışı, otomatik engelleme eşikleri, güvenli liste politikası |
| **AI Prompt** | her analizle gönderilen sistem talimatı |
| **Güncelleme** | güncelleme denetimi (günde bir, SHA-256 doğrulamalı) |

`Ayarları Kaydet` ayarları yazar; çalışan bir analizi etkileyen değişiklikler bir sonraki çalıştırmada geçerli olur. Üst çubuk, alt çubuk ve durum çubuğu her bölümde görünür kalır, böylece sensör durumu bir ayar sayfasının arkasında gizlenmez.

---

## Gereksinimler

- Windows 10/11, kaynaktan çalıştırma için Python 3.11+
- Yönetici yetkisi (hem yakalama hem güvenlik duvarı kuralı ister)
- Npcap kurulu (`C:\Windows\System32\Npcap\wpcap.dll`)

## Kurulum

`NetSonar-v<sürüm>-Setup.exe` dosyasını [Releases](https://github.com/zeitgeist-c/NetSonar/releases/latest) sayfasından indir ve çalıştır. Tek kurulum, tek kanal: `C:\Program Files\NetSonar` altına kurulur, yönetici onayı ister, masaüstü ve Başlat menüsü kısayolları oluşturur, kendini Uygulamalar listesine kaydeder.

Güncellemeler uygulama içinden çalışır: günde bir denetler, yeni kurulumu indirir, SHA-256'sını doğrular, kurmadan önce sorar, sonra kapanıp program klasörünü yerinde değiştirir ve yeniden başlar. Kullanıcı verisi ve model deposu program klasörü dışında durur ve her güncellemeden sağ çıkar. Yayımlanan sürüm kuruludan yeni değilse uygulama bunu söyler ve hiçbir şey yapmaz.

## Komut satırı

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Tek seferlik işlemler:

```powershell
.\.venv\Scripts\python.exe main.py --analyze
.\.venv\Scripts\python.exe main.py --block 8.8.8.8
.\.venv\Scripts\python.exe main.py --unblock 8.8.8.8
.\.venv\Scripts\python.exe main.py --list-blocked
```

Diğer anahtarlar: `--no-gui`, `--accept-v05-reset` (v0.5 depolama sıfırlamasını onaylar).

## Analiz nasıl çalışır

1. Yakalama paketleri toplar ve uç nokta çifti başına dakikalık çift yönlü kovalara böler.
2. Kovalar Windows API'si üzerinden sahibi olan sürece atfedilir.
3. En yoğun akışlardan bir parti kurulur; yük içeriği hiçbir zaman dahil edilmez.
4. Gemini yapılandırılmış bir karar döndürür; yerel doğrulayıcı dönen her kimliği yakalanan kümeyle eşler ve var olmayanı atar.
5. VirusTotal ve web bağlamı sağlayıcısına yalnız seçilmiş **genel uzak** IP'ler gönderilir. Yerel adresler, çoklu yayın adresleri ve güvenli listedekiler makineden çıkmaz.
6. Sonuç rapor olarak saklanır ve Analiz sayfasında gösterilir.

Otomatik engelleme bilerek muhafazakârdır: kritik önem, en az 0.95 güven **ve** modelden açık bir `block_now` gerekir. Engelleme varsayılan kapalıdır.

## Gizlilik ve saklama

- Ham paket detayı akış özetlendikten sonra atılır; içerik, URL ve kimlik bilgisi asla yazılmaz.
- Saatlik toplamlar IP adresi olmadan saklanır ve 30 gün tutulur; denetim kaydı 30 gün tutulur.
- Analiz edilmemiş detay 24 saat içinde anonimleştirilir.
- Anahtarlar Windows kullanıcısı başına DPAPI ile şifrelenir.
- Analitik yok, telemetri yok, hesap yok. Ağ çağrıları yalnız AI sağlayıcısına, tehdit istihbaratı sağlayıcısına ve güncelleme denetimi için GitHub'a gider.

## Proje yapısı

```text
main.py              CLI + GUI girişi (UAC yükseltme, tek örnek)
app_gui.py           SOC paneli (ui_components.py, ui_theme.py)
capture_engine.py    canlı yakalama (flow_accumulator.py, flow_utils.py)
ai_analyzer.py       Gemini analizi (config/ai_prompt.txt)
threat_intel.py      VirusTotal + web bağlamı
database.py          depolama (models.py, migration.py)
scheduler.py         zamanlanmış işler (notifier.py, custom_alerts.py)
kill_switch.py       güvenlik duvarı engelleme
config.py            ayarlar (settings_service.py, DPAPI)
exporter.py          JSON/CSV/TXT raporları
packaging/  assets/  tests/  dist/
```

## Lisans

MIT — bkz. [LICENSE](./LICENSE).

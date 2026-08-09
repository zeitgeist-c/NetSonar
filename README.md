# NetSonar v0.5.2

NetSonar, Windows 10/11 üzerinde Npcap ile bu bilgisayarın taraf olduğu ağ trafiğini
dakikalık, çift yönlü akışlar halinde özetleyen yerel bir ağ görünürlüğü uygulamasıdır.

## Veri ve gizlilik

- Paket içeriği, URL, parola veya dosya içeriği kaydedilmez.
- Aynı yerel/uzak uç, port, protokol ve süreç için dakikada tek `FlowBucket` tutulur.
- Gönderilen ve alınan byte/paket sayaçları ayrı hesaplanır.
- Başarıyla analiz edilen ham akış ayrıntıları silinir.
- Riskli sonuçlarda yalnız doğrulanmış küçük kanıt özeti kullanıcı silene kadar kalır.
- IP ve süreç içermeyen saatlik trafik toplamları ile analiz audit kayıtları 30 gün tutulur.
- Analiz edilemeyen ayrıntılar en fazla 24 saat sonra anonim toplama dönüştürülür.
- API anahtarları Windows DPAPI ile geçerli Windows kullanıcısına bağlı şifrelenir.

VirusTotal veya Tavily anahtarı kaydedilirse yalnızca seçilmiş genel uzak IP adresleri
güncel tehdit itibarı ve web bağlamı için bu servislere gönderilir. Özel, yerel, multicast
ve güvenilir listedeki IP'ler dış servislere gönderilmez. Anahtar yoksa yerel+Gemini akışı
eskisi gibi devam eder. Modelin uydurduğu IP, kaynak veya batch dışında referans verdiği
akışlar yerel doğrulamada reddedilir.

VirusTotal sonuçları yapılandırılmış itibar kanıtıdır. Tavily sonuçları yalnızca güncel,
tıklanabilir web bağlamıdır ve tek başına otomatik engelleme kararı oluşturamaz. Public
VirusTotal API yalnızca kişisel/ticari olmayan kullanım içindir.

## Güvenlik duvarı

Otomatik engelleme varsayılan olarak kapalıdır. Açıldığında bile yalnız gerçek batch
akışına bağlı, kritik, en az `0.95` güvenli, `block_now=true`, global ve yerel kuralla
doğrulanmış hedefler otomatik engellenebilir. Diğer bulgular manuel incelemeye kalır.

Kurallar Windows Firewall içindeki `NetSonar` grubunda çift yönlü yönetilir. Bir yön
başarısız olursa diğer yön geri alınır. Uygulama başka firewall kurallarına dokunmaz.

## Gereksinimler

- Windows 10 veya 11
- Python 3.11+
- Npcap (`C:\Windows\System32\Npcap\wpcap.dll`)
- Yönetici yetkisi

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

İlk v0.5 açılışında uygulama, eski trafik/rapor/trusted/blocked geçmişini ve yalnız
NetSonar firewall kurallarını sıfırlamak için onay ister. Ayarlar ve dışa aktarılmış
rapor dosyaları korunur. Herhangi bir doğrulama hatasında eski veritabanı silinmez.

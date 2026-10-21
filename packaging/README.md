# NetSonar Windows paket dosyası

Bu klasör, NetSonar'ın kaynak kod veya Python gerektirmeden başka bir Windows
bilgisayarında çalışabilmesi için gereken paketleme yapılandırmasını içerir.

## Son kullanıcı dosyaları

    dist\NetSonar-vX.Y.Z-Setup.exe

Dağıtım tek kanaldır: NSIS kurulumcu. Kurulum sabit yere yapar:

    C:\Program Files\NetSonar\NetSonar.exe

Kurulum yönetici onayı ister. Masaüstü ve Başlat menüsü kısayolları yazılır,
kaldırıcı (`Uninstall.exe`) oluşturulur, program "Programlar ve Özellikler"
listesinde görünür.

Paket bir klasördür (onedir), tek dosya değil: güncelleme program klasörünü
yerinde değiştirir, açılış anında olur.

## Güncelleme kanalı

Kaynak deposu gizlidir; kurulumcu asseti herkese açık
`zeitgeist-c/NetSonar-Releases` deposundaki sürümlere yüklenir. Program
kimliksiz GitHub API'si ile `releases/latest` sorar (update.py):

1. `NetSonar-vX.Y.Z-Setup.exe` asseti bulunur (yalnız bu kabul edilir).
2. Kurulum dosyası kullanıcı önbelleğine iner
   (`%LOCALAPPDATA%\NetSonar\cache\updates`), SHA256 doğrulanır.
3. Kullanıcı "Kurulumu Başlat" dedikten sonra onay penceresi açılır.
4. Program kapanır; bekleyen betik (baton) PID'in düşmesini bekler, kurulum
   dosyasını **yönetici yetkisiyle** çalıştırır ve bitmesini bekler.
5. Kurulum bitince program otomatik yeniden başlar.

Program zaten yönetici olarak çalıştığı için güncellemede ayrıca yönetici
onayı sorulmaz; onay penceresi "başlat" onayıdır.

Yayınlanan sürüm kurulu sürümden yeni değilse güncelleme yapılmaz: program
"kurulu sürüm en güncel" der, indirme ve kurulum başlatılmaz. Aynı sürümün
tekrar tekrar kurulması böylece engellenir.

Otomatik başlatma kaydı yalnızca kullanıcı açtıysa yeni exe'ye yönlendirilir;
kapalıysa kapalı kalır.

## Kalıcı model deposu (store)

    %LOCALAPPDATA%\NetSonar\store\models\
    %LOCALAPPDATA%\NetSonar\store\lib\
    %LOCALAPPDATA%\NetSonar\store\store.json

Kurulum ve güncelleme bu klasöre **asla dokunmaz**. Bir kez indirilen yerel
model veya ek Python kütüphanesi, program sürümü değişse de yerinde kalır;
yeniden indirilmesi gerekmez. Depo `store.py` modülü tarafından yönetilir ve
`sys.path`'in sonuna eklenir (paket içi kütüphane önceliklidir).

Bugün NetSonar'da indirilen yerel model yok — AI tamamen Gemini API üzerinden
çalışır. Depo, ileride yerel model/ek kütüphane geldiğinde hazır olsun diye
şimdiden kuruludur.

## Derleme önkoşulları

- 64 bit Windows 10 veya Windows 11
- Python 3.11 veya daha yeni bir 64 bit sürüm
- NSIS 3.x (`C:\Program Files (x86)\NSIS\makensis.exe`)
- İlk derlemede internet bağlantısı

## Yeniden oluşturma

Proje ana dizininde:

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1

Bağımlılıklar daha önce kurulduysa:

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1 -SkipDependencyInstall

Yalnız uygulama klasörü (kurulumcu üretilmez):

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1 -SkipInstaller

Betik izole ortamı packaging\.build-venv altında oluşturur. PyInstaller geçici
çıktıları packaging\build ile packaging\app-dist altında hazırlanır ve başarılı
derleme sonunda otomatik temizlenir. Kurulumcu proje kökündeki dist klasörüne
yazılır ve SHA256 özeti ekrana basılır.

Sürüm numarası config.py içindeki APP_VERSION değerinden okunur ve kurulumcuya
`-DAPP_VERSION` ile geçirilir.

## Yapılandırma dosyaları

- NetSonar.nsi: NSIS kurulumcu betiği (sabit yol, kısayol, kaldırıcı, sessiz mod).
- NetSonar.spec: PyInstaller onedir uygulama ve kaynak tanımları.
- requirements-build.txt: test edilmiş sabit paketleme bağımlılıkları.
- build.ps1: temiz ve tekrarlanabilir uçtan uca derleme betiği.

## Kullanıcı verileri ve gizlilik

Paketlenmiş uygulama ayarları, Gemini/VirusTotal/Tavily anahtarlarını,
veritabanını, logları, özel uyarıları, raporları ve model deposunu
%LOCALAPPDATA%\NetSonar altında tutar. Projedeki config\settings.json ve
netsonar_data içeriği pakete alınmaz. Kurulum ve güncelleme yalnız program
klasörüne yazar; kullanıcı verisine ve model deposuna dokunmaz. Kaldırma da
kullanıcı verisini silmez.

Her üç sağlayıcı için de birden fazla anahtar desteklenir; ilk anahtar
varsayılan, diğerleri hata veya kota durumunda otomatik yedektir ve tümü
DPAPI ile korunur.

## Npcap önkoşulu

Ücretsiz Npcap başka bir uygulamayla yeniden dağıtılamaz; pakete gömülmez.
Uygulama açılışta Npcap'ı denetler (capture_engine.npcap_available) ve yoksa
resmî indirme sayfasını açmayı teklif eden bir uyarı gösterir.

- Npcap: https://npcap.com/#download
- OEM yeniden dağıtım lisansı: https://npcap.com/oem/

## Sürüm kapatışı

1. `packaging\build.ps1` ile kurulumcuyu üret.
2. Aynı commit'e `vX.Y.Z` etiketi; push ve sürüm açık yetkiyle.
3. Kurulumcu asseti `zeitgeist-c/NetSonar-Releases` sürümüne yüklenir;
   yerel ve uzak asset hash'leri karşılaştırılır.

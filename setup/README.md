# NetSonar Windows kurulum paketi

Bu klasör, NetSonar'ın kaynak kod veya Python gerektirmeden başka bir Windows
bilgisayarına kurulabilmesi için gereken paketleme yapılandırmasını içerir.

## Son kullanıcı dosyası

    setup\NetSonar-Setup-v0.5.2.exe

Kurulum 64 bit Windows 10/11 içindir. Başlat menüsü kısayolu her zaman,
masaüstü kısayolu ise kullanıcı seçerse oluşturulur.

## Derleme önkoşulları

- 64 bit Windows 10 veya Windows 11
- Python 3.11 veya daha yeni bir 64 bit sürüm
- NSIS 3: https://nsis.sourceforge.io/Download
- İlk derlemede internet bağlantısı

NSIS winget ile kurulabilir:

    winget install --id NSIS.NSIS --exact

## Yeniden oluşturma

Proje ana dizininde:

    powershell -ExecutionPolicy Bypass -File .\setup\build.ps1

Bağımlılıklar daha önce kurulduysa:

    powershell -ExecutionPolicy Bypass -File .\setup\build.ps1 -SkipDependencyInstall

Betik izole ortamı setup\.build-venv altında oluşturur. PyInstaller ve yükleyici
geçici çıktıları setup\build ile setup\dist altında kalır; dağıtılacak nihai dosya
doğrudan setup klasörüne yazılır.

## Yapılandırma dosyaları

- NetSonar.spec: PyInstaller uygulama ve kaynak tanımları.
- NetSonar.nsi: kullanılan NSIS kurulum, UAC, kısayol, Npcap ve kaldırma tanımları.
- NetSonar.iss: aynı düzenin Inno Setup uyarlaması; başka projelerde alternatif olarak saklanır.
- requirements-build.txt: test edilmiş sabit paketleme bağımlılıkları.
- build.ps1: temiz ve tekrarlanabilir uçtan uca derleme betiği.

## Kullanıcı verileri ve gizlilik

Paketlenmiş uygulama ayarları, Gemini/VirusTotal/Tavily anahtarlarını, veritabanını, logları,
özel uyarıları ve raporları %LOCALAPPDATA%\NetSonar altında tutar. Projedeki
config\settings.json ve netsonar_data içeriği pakete alınmaz. Kaldırma işlemi
kullanıcı verilerini korur; tam temizlik için bu klasör ayrıca silinebilir.

## Npcap önkoşulu

Ücretsiz Npcap başka bir uygulamayla yeniden dağıtılamaz. Kurulum bu nedenle
Npcap'i gömmez; System32\Npcap altındaki wpcap.dll ve Packet.dll dosyalarını
denetler. Bulamazsa resmî indirme sayfasını açmayı teklif eder ve kurulumu durdurur.

- Npcap: https://npcap.com/#download
- OEM yeniden dağıtım lisansı: https://npcap.com/oem/

Lisanslı Npcap OEM Redistribution yükleyiciniz varsa NetSonar.nsi içindeki
.onInit ve zorunlu kurulum bölümünü OEM yükleyiciyi ekleyip /S ile çalıştıracak
şekilde uyarlayın. Ücretsiz Npcap yükleyicisini pakete kopyalamayın.

## Diğer projelere uyarlama

NetSonar.spec içinde giriş/varlıkları, NetSonar.nsi içinde uygulama adı, sürüm,
kayıt anahtarı ve önkoşulları, requirements-build.txt içinde sabitlenmiş
bağımlılıkları, build.ps1 içinde de çıktı adını değiştirin.

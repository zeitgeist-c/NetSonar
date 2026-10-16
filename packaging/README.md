# NetSonar Windows paket dosyası

Bu klasör, NetSonar'ın kaynak kod veya Python gerektirmeden başka bir Windows
bilgisayarında çalışabilmesi için gereken paketleme yapılandırmasını içerir.

## Son kullanıcı dosyaları

    dist\NetSonar-vX.Y.Z.exe
    dist\NetSonar-vX.Y.Z.bat

Dağıtım tek dosyalık (onefile) portable sürümdür: EXE + yanındaki eşleşen BAT.
Kurulum yapılmaz; iki dosya birlikte herhangi bir klasörde çalışır. Yönetici
yetkisi EXE'nin UAC isteminde gelir (uac_admin). NSIS kurulumcusu kaldırıldı;
kurulumcu Npcap'ı zaten gömüyordu ve tek yaptığı dosyaları Program Files'a
koymaktı.

## Güncelleme kanalı

Kaynak deposu gizlidir; EXE/BAT assetleri herkese açık
`zeitgeist-c/NetSonar-Releases` deposundaki sürümlere yüklenir. Program
kimliksiz GitHub API'si ile `releases/latest` sorar (update.py), SHA256
doğrulamalı indirir, yeni exe'yi eskisinin yanına koyar ve swap betiğiyle
kendini değiştirir. BAT da güncel exe'yi gösterecek şekilde yeniden yazılır;
otomatik başlatma kaydı açıksa o da yeni exe'ye yönlendirilir.

## Derleme önkoşulları

- 64 bit Windows 10 veya Windows 11
- Python 3.11 veya daha yeni bir 64 bit sürüm
- İlk derlemede internet bağlantısı

## Yeniden oluşturma

Proje ana dizininde:

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1

Bağımlılıklar daha önce kurulduysa:

    powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1 -SkipDependencyInstall

Betik izole ortamı packaging\.build-venv altında oluşturur. PyInstaller geçici
çıktıları packaging\build ile packaging\app-dist altında hazırlanır ve başarılı
derleme sonunda otomatik temizlenir. Dağıtılacak sürümlü EXE ve onu başlatan
eşleşen BAT dosyası proje kökündeki dist klasörüne yazılır. BAT içeriği tek
kaynaktan gelir: update.py içindeki write_launcher.

Sürüm numarası config.py içindeki APP_VERSION değerinden okunur.

## Yapılandırma dosyaları

- NetSonar.spec: PyInstaller onefile uygulama ve kaynak tanımları.
- requirements-build.txt: test edilmiş sabit paketleme bağımlılıkları.
- build.ps1: temiz ve tekrarlanabilir uçtan uca derleme betiği.

## Kullanıcı verileri ve gizlilik

Paketlenmiş uygulama ayarları, Gemini/VirusTotal/Tavily anahtarlarını,
veritabanını, logları, özel uyarıları ve raporları %LOCALAPPDATA%\NetSonar
altında tutar. Projedeki config\settings.json ve netsonar_data içeriği pakete
alınmaz. Güncelleme yalnız exe'yi değiştirir; kullanıcı verisine dokunmaz.
Her üç sağlayıcı için de birden fazla anahtar desteklenir; ilk anahtar
varsayılan, diğerleri hata veya kota durumunda otomatik yedektir ve tümü
DPAPI ile korunur.

## Npcap önkoşulu

Ücretsiz Npcap başka bir uygulamayla yeniden dağıtılamaz; pakete gömülmez.
Portable exe açılışta Npcap'ı denetler (capture_engine.npcap_available) ve
yoksa resmî indirme sayfasını açmayı teklif eden bir uyarı gösterir.

- Npcap: https://npcap.com/#download
- OEM yeniden dağıtım lisansı: https://npcap.com/oem/

## Sürüm kapatışı

1. `packaging\build.ps1` ile dist dosyalarını üret.
2. Aynı commit'e `vX.Y.Z` etiketi; push ve sürüm açık yetkiyle.
3. EXE+BAT assetleri `zeitgeist-c/NetSonar-Releases` sürümüne yüklenir;
   yerel ve uzak asset hash'leri karşılaştırılır.

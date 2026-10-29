# NetSonar — DURUM (ortak — Desktop + Telegram okur)

**Güncelleme:** 2026-10-30
**Versiyon:** v0.6.4 (tag: bu commit; dağıtım: zeitgeist-c/NetSonar v0.6.4)
**Branch:** main (push edildi: main + v0.6.4; dagitim: NetSonar v0.6.4 yayinda)
**Son commit:** bu commit (ortak masaüstü seçenekleri modülü)
**Ağaç:** kapsam içi dosyalar commit'lendi; `ui-kesif/` keşif çıktıları ve `.hermes/`, `AGENTS.md` untracked.
**Not:** Kirli dosyalar kullanıcıya ait olabilir; commit öncesi kullanıcıya sorulur. (2026-10-17: "Yedek işlemini yapabilir misin?" talebiyle tam kapanış yetkisi verildi.)

## v0.6.2 — Ortak masaüstü seçenekleri modülü (2026-10-22)
**Kullanıcı isteği:** "Ayarlar kısmı oluşturulup orada güncellemeler ve vs. orada tutulsun; ayrıca Windows başladığında başlat ve sistem tepsisine küçült butonları ayarlarda olsun. Bundan sonraki tüm projelerde de aynı özellikler olsun — istemediğim sürece hepsinde olmasın."

**Kapsam (kullanıcı onayıyla):** NetSonar + VoxoraStudio + WordArc + Evrakçı. Sırayla işlendi. Diğer projelere (Finance, Opener, Muhasebe, araç klasörleri) dokunulmadı.

**Yeni ortak modül — `app_options.py`:**
- `AutostartController` — HKCU Run kaydı: aç/kapa/dogrula/tazele. Kayıt defteri esas kaynak, ayar dosyası yedek (kayıt elle silinirse ayardan geri yüklenir).
- `TrayOption` — "kapatılınca tepsiye küçült" tercihi + `should_minimize(tray_available)`: tepsi simgesi yoksa küçültme uygulanmaz, uygulama kapanır (kullanıcı uygulamayı kaybetmesin).
- `build_settings_widgets()` — PyQt6 için iki onay kutusu; PyQt6 yoksa modül yine de çalışır (saf stdlib).
- Ortak ayar anahtarları (projeler arası sözleşme): `AUTOSTART_ENABLED`, `MINIMIZE_TO_TRAY`.

**NetSonar'da uygulama:**
- `autostart.py` artık ince bir sarmalayıcı; iş mantığı `app_options.AutostartController`'da. Eski fonksiyon adları korundu (geriye uyum).
- `app_gui.py` Ayarlar > Genel: iki seçenek ortak modülden üretiliyor. Kapanış davranışı `MINIMIZE_TO_TRAY` + tepsi varlığına bağlandı (geri düşüş eklendi).
- Yeni ayar `AUTOSTART_ENABLED` şemaya eklendi, `settings_service` doğrulamasına bağlandı.

**Testler:** 143 → **166 test + 29 alt test** (`tests/test_app_options.py` yeni, 20 test — kayıt defterine yazmadan sahte depo ile doğrular).

**Canlı doğrulama:** GUI'da kutuyu işaretleyince `HKCU\...\Run` altına kayıt yazıldı, kaldırınca silindi; kurulum tercihi ve kayıt defteri tutarlı kaldı.

**Kalıcı şey:** `AI-Coding-OS-v1.0/skills/desktop-app-options` skill'i oluşturuldu (onay bekliyor) — `assets/app_options.py` + `assets/test_app_options.py` ile birlikte. Yeni projede bu modülü kopyalamak yeterli.

## v0.6.1 — Güncelleme döngüsü düzeltmesi (2026-10-22)
**Kullanıcı şikayeti:** "Güncelle dediğimde tekrar tekrar kendini güncelliyor" + "güncelleme tarafı kurulmamış gibi görünüyor".

**Kök nedenler (gerçek kod okunarak bulundu, tahmin değil):**
1. **Kurulum sırası yanlış:** `launch_installer()` program çalışırken installer'ı başlatıyordu → "Access denied" (çalışan exe değiştirilemez) → kurulum yarım kalıyor → program eski sürümde kalıyor → kullanıcı tekrar "Güncelle" → **aynı sürüm tekrar kuruluyor**. Döngünün kaynağı buydu.
2. **PID kontrolü bozuk:** `tasklist /FI "PID eq X"` filtresi bu makinede **uygulanmıyor** (PID 22400 soruldu, 4736 döndü). Baton hiç tetiklenmiyordu.
3. **timeout çakışması:** Git-Bash/MSYS kurulu → `timeout` GNU aracına çözünüyor → `/t 1` parametresi hata veriyor → bekleme döngüsü hiç bitmiyordu.
4. **WinError 87:** `DETACHED_PROCESS | CREATE_NEW_CONSOLE` birlikte geçersiz → baton hiç başlamıyordu.
5. **Yetki:** NSIS kurulumcusu admin ister; yetkisiz bağlamda UAC'a takılıp `start /wait` sonsuza kadar bekliyordu.
6. **Denetim sonucu görünmüyordu:** `_update_checked` "güncelleme yok" mesajını sadece manuel denetimde ve Ayarlar sekmesi açıkken gösteriyordu → kullanıcı "kurulmamış gibi" görüyordu.

**Düzeltmeler:**
- `update.py`: sıra düzeltildi — program kapanır → baton PID'i bekler → installer **yönetici yetkisiyle** çalışır ve bitene kadar beklenir → program otomatik yeniden başlar.
- `update.py`: PID kontrolü PowerShell `Get-Process -Id` (güvenilir), bekleme `C:\Windows\System32\timeout.exe` (mutlak yol).
- `update.py`: `installed_version()` — kurulum sonrası sürüm exe'nin kendisinden okunur; `install_outcome()` başarı/başarısızlığı doğrular.
- `app_gui.py`: **döngü koruması** — hedef sürüm kurulu sürümden yeni değilse indirme/kurulum yapılmaz, "en güncel" gösterilir. Bekleyen installer sürüm eşleşmiyorsa silinip yeniden indirilir.
- `app_gui.py`: denetim sonucu **her zaman** karta yansır (otomatik/manuel, sekme açık/kapalı fark etmez); `UPDATE_LAST_SEEN_VERSION` + `UPDATE_AVAILABLE` ayarlara kaydedilir; Ayarlar açılışında kayıtlı durum gösterilir.
- `config.py` + `settings_service.py`: yeni ayar alanları eklendi ve doğrulamaya bağlandı.
- Testler: 128 → **143 test + 29 alt test** (`tests/test_update_loop.py` yeni, 15 test).

**Gerçek doğrulama:** v0.6.0 kurulu iken geçici v0.6.1 release açıldı → program güncellemeyi buldu → indirdi (SHA256 doğrulandı) → sessiz kurulum → kurulu exe v0.6.1 oldu → store + 9.8 MB veritabanı yerinde kaldı → test release silindi. Baton betiği ayrıca canlı olarak PID bekleyiş → kurulum → yeniden başlatma zinciriyle doğrulandı.

## v0.6.0 — Kurulumcu kanalı + kalıcı model deposu (2026-10-21)
- **Dağıtım tek kanala indi:** portable tek EXE + BAT yerine NSIS kurulumcu (`NetSonar-vX.Y.Z-Setup.exe`).
  - Kurulum sabit yere yapar: `C:\Program Files\NetSonar\NetSonar.exe`; exe adında sürüm yok → güncellemede yol değişmez.
  - `packaging/NetSonar.nsi` (yeni): masaüstü + Başlat menüsü kısayolu, `Uninstall.exe`, "Programlar ve Özellikler" kaydı, Türkçe arayüz.
  - NSIS 32-bit olduğu için `SetRegView 64` — anahtarlar WOW6432Node'a düşüyordu, "Programlar" listesinde görünmüyordu.
  - Masaüstü kısayolu kullanıcıya özel (`SetShellVarContext current`); "all" bağlamı OneDrive yönlendirilmiş masaüstünde Public Desktop'e yazıyordu.
- **Güncelleme yeniden yazıldı** (`update.py`): yeni exe'yi yanına kopyalayıp swap etme yerine kurulumcu indirilir → SHA256 doğrulanır → onay istenir → program kapanır → kurulumcu sessizce (`/S`) çalışır ve program klasörünü yerinde değiştirir. `spawn_swap` kaldırıldı (sabit yolda installer ile çakışırdı).
  - İndirme hedefi Program Files değil, kullanıcı önbelleği: `%LOCALAPPDATA%\NetSonar\cache\updates`.
  - Asset kuralı: yalnız `NetSonar-vX.Y.Z-Setup.exe` kabul edilir; eski portable exe asseti reddedilir.
- **Kalıcı model deposu** (`store.py`, yeni): `%LOCALAPPDATA%\NetSonar\store` (models/ + lib/ + store.json manifest). Kurulum ve güncelleme bu klasöre asla dokunmaz → indirilmiş model/kütüphane sürüm değişse de yeniden indirilmez. `main.py` açılışta `store.activate()` ile lib yolunu `sys.path` sonuna ekler (paket içi kütüphane öncelikli).
  - Not: bugün NetSonar'da indirilen yerel model yok; AI tamamen Gemini API. Depo ileride yerel model geldiğinde hazır olsun diye kuruldu.
- **Paket onedir'a geçti** (`NetSonar.spec`): kurulum ağacı C:\Program Files'a kopyalanır, açılış anında olur. Kullanılmayan Qt modülleri (Quick, Multimedia, Pdf, Bluetooth, Qml...) `excludes` ile dışlandı → kurulumcu 48 MB onefile yerine **35.2 MB**.
- `autostart.py`: komut artık sürüm adı taşımıyor; güncellemede yeniden yönlendirme gerekmiyor.
- `app_gui.py`: güncelleme kartındaki buton "İndir ve Kur" → "Kurulumu Başlat"; indirme sonrası onay penceresi, sonra sessiz kurulum + yeniden başlatma.
- Testler: 92 → **128 test + 29 alt test** (`test_update.py` yeniden yazıldı, `test_store.py` ve `test_installer_contract.py` yeni).
- Gerçek doğrulama: kurulum `C:\Program Files\NetSonar`'a yapıldı, kısayollar ve kayıt defteri doğrulandı, store + 9 MB veritabanı kurulum sonrası yerinde kaldı, kaldırma temiz çalıştı.

## v0.5.9 — Arayüz yenilemesi: Grafit & Kobalt (2026-10-17)
- Onaylanan kombinasyon uygulandı: `D + N4 + P1 + F2 + A1 + İskelet + S1`.
- `ui_theme.py`: Grafit & Kobalt paleti (bg `#0B0D10`, accent `#4C8DFF`); QSS'te `rgba()` yok, premix hex; historic `C` anahtarları korundu.
- `ui_components.py`: yeni bileşenler — `SubNav`, `EmptyState`, `DetailStrip`, `MiniBarChart`, `FeedRow`, `RatioBar`.
- `database.py`: `get_recent_flows()` (Panel canlı akış beslemesi).
- `app_gui.py`: navigasyon 6 sekmeye indi — Panel / Analiz / Akışlar / Kurallar / Anahtarlar / Ayarlar.
  - Panel (P1 Komuta Merkezi): sol trafik grafiği + en yüksek trafik çubukları, sağ canlı akış; AI butonu üst bardan sayfa başlığına taşındı (analiz butonları ortak busy durumu).
  - Akışlar (F2 Tek Tablo): filtre çubuğu (şüpheli port / hacim eşiği / mesai dışı / proto / arama) + satır seçiminde detay şeridi + IP engelle.
  - Kurallar: Engellenenler + Güvenli IP'ler tek iskelet, segment düğmesiyle geçiş (eski ayrı sekmeler kaldırıldı).
  - Anahtarlar: sağlayıcı başına katlanır "Yönet" satırı + kota özeti; Ayarlar'daki 3 kez yinelenen anahtar yöneticisi kaldırıldı.
  - Ayarlar (S1 Sol Alt Menü): Genel / Analiz / Güvenlik / AI Prompt / Güncelleme bölümleri, tek ekrana sığar, kaydırma yok.
- Eşikler config'ten (`SUSPICIOUS_BYTES_THRESHOLD` → filtre etiketi ">50MB"); "mesai dışı" filtresi `last_seen` kullanır (`_flow_summary` `bucket_start` döndürmez).
- `tests/test_ui_smoke.py` yeni yapıya uyarlandı (RulesTab/KeysTab/analiz butonu sözleşmeleri): 92 test + 29 alt test geçti.
- Paket: `dist/NetSonar-v0.5.9.exe` + BAT; portable onefile, kendi kendine güncelleme aynı.

## v0.5.8 — Kendi kendine güncelleme + portable paket (2026-10-17)
- WordArc'ın güncelleyicisi uyarlandı (`update.py`): herkese açık `zeitgeist-c/NetSonar` deposundan `releases/latest` kimliksiz sorgu, SHA256 doğrulamalı indirme, swap batonu ile kendini değiştirme. BAT eşleşen exe'ye yeniden yazılır; autostart HKCU kaydı `retarget_launch` ile çevrilir.
- Dağıtım portable onefile: `dist/NetSonar-v0.5.8.exe` (49.722.012 bayt; SHA-256: cc9c4a7738f044e26d38fd9d38c959172a83fd0c360f3e17192ab6b6cd762f0e) + eşleşen BAT. NSIS kurulumcusu (`NetSonar.nsi`) kaldırıldı; yönetici yetkisi UAC manifestinde, Npcap uyarısı exe açılışına taşındı (`_npcap_notice_once`).
- Ayarlar sekmesinde "Güncellemeler" kartı: açılıştan 30 sn sonra günde bir sessiz denetim (`UPDATE_LAST_CHECK`), elle denetleme, ilerleme çubuğu, İndir ve Kur. Kaynak koddan çalışırken kilitli.
- `tests/test_update.py`: 13 yeni test; `test_version_and_api_errors` BAT sözleşmesi portable'a uyarlandı.

## 21-skill turu (2026-09-30, tamamlandı)
- Sıra: yapı → yapılandırma → sözleşme → tutarlılık → yetki → hata-denetimi → asenkron → gözlem → tekrar → darboğaz → bağımlılık-denetimi → regresyon → denetle → güvenlik → performans → debug → temizle → geliştir → bağımlılık → hızlı-derle → yedek.
- Düzeltmeler: worker hata logları (ERR-001), anahtar ayrıştırma tekilleştirme (DUP-001), CSV formül kaçışı (SEC-001), atomik ayar yazımı (debug), kullanılmayan import, 18 yeni test (61→79).
- Kaldırılan: venv artıkları openai, google-generativeai, google-api-python-client (pip-audit temiz).
- Kalan P2/P3: UI çift palet, AG_TARA_* env öneki; backlog: UI-001, CFG-002.

## Sırada
- Kullanıcı söyler.

## Bağımlılık (2026-09-26)
- .venv: cryptography 46.0.7→50.0.1 (7 açık kapandı, audit temiz) — 61 test geçti. requirements.txt temiz. Not: venv'de manifest-dışı google/openai artıkları var (temizlik adayı); scapy'den FFDH uyarısı (yalnız uyarı).
- 2026-09-30: artıklar kaldırıldı (openai, google-generativeai, google-api-python-client); pip-audit temiz; runtime pinleri güncel.

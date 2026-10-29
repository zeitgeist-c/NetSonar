# NetSonar — İnceleme, Hata Düzeltme, Temizlik ve Geliştirme Planı

Tarih: 2026-09-09 22:38 (+03:00)
Kaynak dal: `agent/netsonar-latest` (temiz ağaç, son commit `c56ec04` v0.5.4)
Hedef kitle: kodu ilk kez gören uygulayıcı

## 1. Goal

NetSonar v0.5.4 kod tabanını ETAP 1–12 sırasıyla (incele → tespit → düzelt → doğrula → temizle → doğrula → öner) stabil, temiz ve geliştirilebilir hale getirip nihai sağlık raporu üretmek; bu turda kod değişikliği yapmadan yalnızca plan üretmek.

## 2. Current context / assumptions

- Kök: `C:\Users\mahmu\Projeler\NetSonar` (Windows 11, bu makinede geliştirme yapılmıyor; commit/tag/push yalnız bu makinede — tek yazar kuralı).
- Dil: saf Python (~7.500 satır uygulama kodu). `requirements.txt`: `PyQt6>=6.6.0`, `scapy>=2.5.0`, `psutil>=5.9.0`, `APScheduler>=3.10.0`, `requests>=2.31.0`, `winotify>=1.1.0`, `plyer>=2.1.0`.
- Giriş noktaları: `main.py` (argparse: `--analyze`, `--block IP`, `--unblock IP`, `--list-blocked`, `--no-gui`, `--accept-v05-reset`; admin yetkisi ister, `SingleInstanceLock` alır), `NetSonar.bat` (launcher), `dist/NetSonar-v0.5.4.exe` + `dist/NetSonar-v0.5.4.bat` (kararlı dağıtım), `packaging/NetSonar.spec` + `packaging/NetSonar.nsi` + `packaging/build.ps1`.
- Mimari (dosya → rol):
  - `app_gui.py` (2650 satır, en büyük risk) — tüm PyQt6 ekranları.
  - `ui_theme.py` (545), `ui_components.py` (392) — tema + ortak widget.
  - `capture_engine.py` (281) + `flow_accumulator.py` (49) + `flow_utils.py` (34) — Npcap/scapy yakalama → dakikalık çift yönlü `FlowBucket` özeti.
  - `database.py` (606) — SQLite (`DB_PATH`, WAL, `flow_buckets`, `analysis_batches`, `analysis_chunks`, `security_findings`, `blocked_ips`, `trusted_ips`, `app_metadata`, rollup tabloları).
  - `ai_analyzer.py` (377) — Gemini analizi + yerel doğrulama (uydurma IP/batch-dışı referans reddi).
  - `threat_intel.py` (235) — VirusTotal (itibar) + Tavily (web bağlamı, engelleme kararı veremez).
  - `kill_switch.py` (145) — Windows Firewall `NetSonar` grubunda çift yönlü atomik engelleme.
  - `scheduler.py` (92), `notifier.py` (140, winotify), `exporter.py` (194), `custom_alerts.py` (146), `settings_service.py` (98, DPAPI secret), `config.py` (587, `APP_VERSION="v0.5.4"`, `settings.json` yükleme), `models.py` (63), `ip_utils.py` (148), `migration.py` (79, v0.5 reset), `instance_lock.py` (31), `autostart.py` (83), `logging_config.py` (56).
  - Yapılandırma: `config/settings.json`, `config/ai_prompt.txt` (288 satır).
  - Testler (`tests/`, 16 dosya): `test_analysis_batches`, `test_auto_block_policy`, `test_autostart`, `test_capture_direction`, `test_firewall_atomic`, `test_flow_accumulator`, `test_flow_storage`, `test_gemini_models`, `test_migration_v05`, `test_notification_cooldown`, `test_retention`, `test_scheduler_live_settings`, `test_storage_load`, `test_threat_intel`, `test_ui_smoke`, `test_version_and_api_errors`.
- Çalışma mantığı (README): paket içeriği/URL/parola kaydedilmez; dakikada tek `FlowBucket`; sayaçlar çift yönlü; başarılı analiz sonrası ham detay silinir; riskli kanıt özeti kullanıcı silene dek kalır; saatlik toplam + audit 30 gün; analizsiz detay 24 saatte anonimleşir; API anahtarları DPAPI; özel/yerel/multicast/güvenilir IP dış servise gitmez; çoklu anahtarlarda sırayla fallback; otomatik engelleme varsayılan kapalı, açıkken bile `kritik + confidence>=0.95 + block_now=true + global + yerel kural` şartı var.
- Varsayımlar: `.venv` mevcut ama test koşumu doğrulanmadı; Npcap + admin gerektiği için yakalama/UI testleri bu makinede kısmi çalışır; kullanıcı verisi (`config/settings.json`, `*.db`) korunacak; yabancı WIP satırlarına dokunulmayacak.

## 3. Architecture / proposed approach

Önce salt-okunur haritalama + test/build ile hata haritası çıkarılır; sonra KRİTİK/YÜKSEK ve ORTA/DÜŞÜK düzeltmeler iki ayrı dalgada, her düzeltme sonrası ilgili testle doğrulanarak yapılır. Temizlik yalnızca "güvenle silinebilir" listesinden küçük gruplar halinde yapılır ve her grup sonrası build+test koşulur; mimari/güvenlik/performans bulguları koda değil rapora işlenir (büyük refactor otomatik yok).

## 4. Step-by-step tasks

### ETAP 1 — Projeyi tanıma ve haritalama (salt okunur, değişiklik yok)

- [ ] 1.1 Kök envanteri çıkar (2 dk). Komut:
  `git -C C:/Users/mahmu/Projeler/NetSonar ls-files`
  Beklenen: ~70 yol; `app_gui.py`, `database.py`, `config.py`, `packaging/`, `tests/` (16 dosya), `dist/` altında yalnızca `NetSonar-v0.5.4.exe/.bat` görünür.
- [ ] 1.2 Boyut haritası çıkar (2 dk). Komut:
  `git -C C:/Users/mahmu/Projeler/NetSonar ls-files | xargs -I{} sh -c 'wc -l "C:/Users/mahmu/Projeler/NetSonar/{}" 2>/dev/null' | sort -rn | head -n 30`
  Beklenen: `app_gui.py` ~2650 satırla en büyük; `database.py` ~606, `config.py` ~587.
- [ ] 1.3 Giriş akışını oku (5 dk): `main.py` (1–154), `NetSonar.bat`, `instance_lock.py`, `migration.py`. Çıktı: GUI/CLI karar ağacı + admin/lock/migration sırasını 10 satırla nota al.
- [ ] 1.4 Veri akışını oku (10 dk): `capture_engine.py` → `flow_accumulator.py` → `database.py` (`_create_schema`, retention fonksiyonları) → `ai_analyzer.py` → `threat_intel.py` → `kill_switch.py` → `notifier.py`/`exporter.py`. Çıktı: `FlowBucket → analysis_batches/chunks → security_findings → firewall` zincirini şema adlarıyla yaz.
- [ ] 1.5 Ayar/gizlilik akışını oku (5 dk): `config.py` (`_default_settings`, `_write_settings`, `protect_secret` kullanımı), `settings_service.py`, `config/settings.json`, `config/ai_prompt.txt`. Çıktı: hangi anahtarın nerede şifrelendiği + dış servise hangi IP sınıfının gitmediği.
- [ ] 1.6 UI haritası çıkar (10 dk): `app_gui.py` içindeki `class .*Window|class .*Dialog|def .*_page|QStackedWidget|addTab` araması yap; ekran listesini `ui_theme.py`/`ui_components.py` ve `assets/icons/` ile eşleştir. Değişiklik yok.
- [ ] 1.7 Etap 1 özetini yaz (5 dk): mimari + modül bağlantıları + kritik dosyalar + iş kuralları (en fazla 1 sayfa). Doğrulama: özet `main.py`, `database.py`, `ai_analyzer.py`, `kill_switch.py`, `config.py` rollerini eksiksiz sayıyor mu?

### ETAP 2 — Hata ve risk tespiti (düzeltme yok, yalnızca liste)

- [ ] 2.1 Test süitini çalıştır ve kaydet (5 dk). Komut:
  `C:/Users/mahmu/Projeler/NetSonar/.venv/Scripts/python.exe -m pytest tests/ -q`
  Beklenen: `16 passed` veya başarısız listesi; çıktının tamamını dosyaya yaz (`pytest-etap2.log`). Başarısızlık = hata haritasına girdi, düzeltme yok.
- [ ] 2.2 Derleme/import kontrolü (3 dk). Komutlar:
  `C:/Users/mahmu/Projeler/NetSonar/.venv/Scripts/python.exe -m compileall -q app_gui.py database.py config.py ai_analyzer.py capture_engine.py kill_switch.py threat_intel.py scheduler.py exporter.py && echo COMPILE_OK`
  Beklenen: `COMPILE_OK`. Hata verirse KRİTİK/YÜKSEK adayı olarak kaydet.
- [ ] 2.3 Statik tarama (5 dk): kullanılmayan import/değişken (`ruff` yoksa `python -m pyflakes` veya `flake8`; hiçbiri yoksa `pip install ruff` yerine önce `rg "import"` + göz taraması — yeni bağımlılık ekleme). Odak: `app_gui.py`, `config.py`, `database.py`. Çıktı: aday listesi (henüz silme yok).
- [ ] 2.4 Risk avı — dosya dosya kontrol listesi (her biri 3–5 dk, toplam ~30 dk):
  - `database.py`: WAL/busy_timeout var mı, transaction yarım kalırsa ne olur, retention (30 gün/24 saat) sorguları doğru mu, `check_same_thread=False` + `RLock` yeterli mi?
  - `capture_engine.py` + `flow_accumulator.py`: yön (sent/received) karışması, `None` process, Npcap yokken çökme?
  - `ai_analyzer.py`: JSON parse hatası, uydurma IP/batch-dışı referans reddi çalışıyor mu (`test_gemini_models`, `test_analysis_batches` ile eşleştir)?
  - `kill_switch.py`: tek yön başarı/tek yön hata durumunda rollback var mı (`test_firewall_atomic` ile eşleştir)?
  - `config.py` + `settings_service.py`: DPAPI çözülemezse ne olur, çoklu anahtar fallback sırası, boş anahtarla dış çağrı yapılıyor mu?
  - `scheduler.py`: canlı ayar değişimi (`test_scheduler_live_settings`), çakışan job?
  - `notifier.py`: cooldown (`test_notification_cooldown`)?
  - `main.py` + `migration.py`: `--accept-v05-reset` olmadan veri silinir mi (`test_migration_v05`)?
  - `exporter.py`: hassas alan (IP/process) dışa yazılıyor mu?
- [ ] 2.5 Hata haritası tablosu üret (10 dk). Sütunlar: ID (örn. `H-01`) | şiddet (KRİTİK/YÜKSEK/ORTA/DÜŞÜK) | dosya:satır | sorun | neden | etkilenen bölüm | önerilen çözüm. Kural: şiddet tanımı plana sadık (veri kaybı/çalışmayı engelleme = KRİTİK; çökme/yanlış veri = YÜKSEK; UX/validasyon = ORTA/DÜŞÜK). Doğrulama: her satırda dosya:satır dolu; satırı boş olan girdi haritaya giremez.

### ETAP 3 — KRİTİK ve YÜKSEK düzeltmeler (küçük, izole, refactor yok)

- [ ] 3.1 Düzeltme sırasını kilitle (3 dk): veri kaybı → çalışmayı engelleme → yanlış hesaplama/veri → kritik iş kuralı → çökme. Haritadaki KRİTİK/YÜKSEK ID'leri bu sıraya diz; sıra dışı işe başlama.
- [ ] 3.2 Her hata için TDD döngüsü uygula (hata başına ~10–15 dk):
  1. Önce başarısız testi yaz (`tests/test_<alan>.py` içine yeni `test_...`, örn. firewall rollback için `test_firewall_atomic.py` içine).
  2. `.../python.exe -m pytest tests/test_<alan>.py -q` → `1 failed` gör.
  3. Minimum düzeltmeyi yap (yalnız ilgili fonksiyon; `app_gui.py` genel temizliği yasak).
  4. Aynı dosyayı tekrar koş → `passed` gör.
  5. Tam süiti koş (`pytest tests/ -q`) → regresyon yok.
  6. Commit (kural 4'deki mesaja bak).
- [ ] 3.3 Etap 3 raporu yaz: düzeltilen ID'ler | değişen dosyalar | koşulan test + sonuç. Doğrulama: KRİTİK/YÜKSEK listesinde açık ID kalmadı veya kalan her ID için "neden bırakıldı" gerekçesi var.

### ETAP 4 — ORTA ve DÜŞÜK düzeltmeler + regresyon

- [ ] 4.1 ORTA/DÜŞÜK ID'leri tek tek, aynı TDD döngüsüyle düzelt (her biri ≤15 dk). Kapsam: küçük mantık, eksik mesaj/validasyon, durum yönetimi, warning temizliği.
- [ ] 4.2 Tam regresyon (5 dk):
  `C:/Users/mahmu/Projeler/NetSonar/.venv/Scripts/python.exe -m pytest tests/ -q`
  Beklenen: tamamı `passed`. Ek GUI duman testi: `pytest tests/test_ui_smoke.py -q` → `passed` (headless ise `QT_QPA_PLATFORM=offscreen` ile tekrar dene, sonucu nota düş).
- [ ] 4.3 Etap 3 düzeltmelerinin bozulmadığını doğrula: Etap 3'te eklenen testler hâlâ yeşil mi? Kırmızı varsa ilerleme, önce onu düzelt (kural 7).

### ETAP 5 — Gereksiz dosya/kod analizi (silme yok)

- [ ] 5.1 Aday tara (15 dk): `__pycache__/`, `*.pyc`, `.venv/` (asla silinmez, yalnızca listede "dokunulmaz" işaretlenir), `dist/` eski sürümler (şu an tek sürüm v0.5.4 — eski yok), `*.bak/*.old/*~`, `test_*.py` içi ölü test, `app_gui.py`/`config.py` içi kullanılmayan import/fonksiyon/class, `assets/` kullanılmayan ikon, `requirements.txt` kullanılmayan bağımlılık (`plyer` gerçekten çağrılıyor mu? `rg "plyer|winotify"` ile doğrula).
- [ ] 5.2 Her aday için kullanım doğrulaması yap (kritik kural): `rg "<sembol>" --glob '*.py'` + dinamik yükleme taraması (`importlib`, `getattr`, `QStackedWidget` sayfa adı, `config` anahtarıyla çağrı). Dinamik/config üzerinden çağrı şüphesi varsa aday "sınıf 2"ye düşer, "sınıf 1"e yazılmaz.
- [ ] 5.3 Üç liste üret: (1) güvenle silinebilir, (2) muhtemelen gereksiz/doğrulama gerek, (3) kullanılıyor-dokunulmaz. Doğrulama: liste 1'deki her girdinin yanında `rg` kanıtı (komut + "0 sonuç") var.

### ETAP 6 — Güvenli temizlik (küçük gruplar)

- [ ] 6.1 Gruplar halinde temizle, sıra: (a) kullanılmayan import → (b) ölü fonksiyon/class → (c) gereksiz yardımcı/geçici dosya → (d) kullanılmayan asset → (e) kullanılmayan bağımlılık. Grup başına bir commit.
- [ ] 6.2 Her grup sonrası kapı (5 dk):
  `.../python.exe -m compileall -q <değişen dosyalar> && .../python.exe -m pytest tests/ -q`
  Beklenen: `COMPILE_OK` + `passed`. Kırmızıysa grubu geri al (`git checkout -- <dosya>`), nedeni nota düş, sonraki gruba geçme.
- [ ] 6.3 Davranış değişmediğini doğrula: ana akış (yakalama→DB→analiz→bildirim) testleri yeşil; silinen listesini raporla (dosya + neden gereksiz + doğrulama kanıtı).

### ETAP 7 — Kod kalitesi ve mimari inceleme (önce liste, otomatik büyük refactor yok)

- [ ] 7.1 Koku taraması (15 dk): `app_gui.py` (2650 satır — bölünme adayı), >100 satırlık fonksiyonlar, tekrar bloklar, magic number (`0.95`, `50MB`, `60dk`, `30gün/24saat`), hard-coded yol, global, circular import (`rg "^import|^from"` ile modül grafiği).
- [ ] 7.2 Her öneri için kart yaz: problem | önerilen çözüm | fayda | risk | etkilenecek dosyalar | büyüklük (S/M/L). Örn. "app_gui.py ekran başına dosya bölünmesi (L, riskli — bu turda uygulama, öneri olarak raporla)".

### ETAP 8 — Güvenlik ve veri güvenilirliği

- [ ] 8.1 Kontrol listesi (15 dk): girdi validasyonu (IP/port, `--block` argümanı), SQL injection (f-string SQL var mı? `rg "execute.*%|execute.*format|f\".*SELECT|f'.*SELECT"`), yol güvenliği (`exporter.py` yazma yolu), firewall grup dışına dokunma, kodda sır (`rg -i "api[_-]?key|secret|token|password"` — `.env` açma, yalnızca kaynak kod tara), DPAPI hatası, yarım transaction, backup/restore varlığı, logda hassas veri (`rg -i "GEMINI|VIRUSTOTAL|TAVILY.*log|print.*key"`).
- [ ] 8.2 Gerçek-doğrulanabilir açıkları minimum yamayla düzelt (TDD ile); mimari isteyenleri (örn. tam RBAC) rapora "geliştirme önerisi" yaz, koda dokunma.

### ETAP 9 — Performans ve UX

- [ ] 9.1 Performans kanıtlı tara (10 dk): tekrar sorgu (`database.py` retention/rollup), ana thread'de ağır iş (yakalama/analiz UI thread'de mi? `QThread`/`moveToThread` var mı `rg "QThread|threading|concurrent"`), büyük veri seti (`test_storage_load` süresine bak), gereksiz disk I/O.
- [ ] 9.2 UX tara (10 dk): gereksiz tıklama, anlaşılmaz hata/eksik başarı mesajı, uzun işlemde geri bildirim (progress), yanlış işleme açık alan. Kural: kanıt (ölçüm/log/süre) olmadan optimizasyon yok.

### ETAP 10 — Geliştirme önerileri

- [ ] 10.1 Üç gruba ayır: (1) hızlı kazanımlar, (2) orta ölçekli, (3) büyük/yapısal. Her öneri: ne | neden | kullanıcı faydası | teknik fayda | risk | büyüklük | etkilenecek modüller | öncelik. Kural: projeye özel yaz (`FlowBucket`, firewall atomikliği, DPAPI fallback, `app_gui.py` bölünmesi gibi); genel tavsiye yasak.

### ETAP 11 — Nihai regresyon ve sağlık kontrolü

- [ ] 11.1 Tam kapı (10 dk):
  `.../python.exe -m pytest tests/ -q` → beklenen `16 passed` (sayı artmışsa yeni sayıyı yaz).
  Kontrol listesi: açılış, ana ekranlar, kayıt/okuma/güncelleme/silme, hesaplama doğruluğu, rapor (`exporter.py`), ayarlar, DB bağlantısı, modül geçişleri, Etap 3–4 düzeltmelerinin kalıcılığı, temizlik sonrası eksik import yok.
- [ ] 11.2 Yeni regresyon varsa düzelt → 11.1'i tekrarla; bu etap yeşil olmadan "sağlıklı" denmez.

### ETAP 12 — Nihai rapor

- [ ] 12.1 Aşağıdaki başlıklarla rapor üret (plana sadık, Türkçe, kısa): PROJE DURUMU | TESPİT EDİLEN HATALAR (K/Y/O/D) | DÜZELTİLEN HATALAR | DEĞİŞTİRİLEN DOSYALAR | SİLİNEN DOSYA VE KODLAR | TESTLER (koşulan test, build, runtime; başarılı/başarısız) | KALAN BİLİNEN SORUNLAR | KOD KALİTESİ | GÜVENLİK | PERFORMANS | GELİŞTİRME ÖNERİLERİ (öncelik sırasıyla) | SONUÇ (stabil mi? kullanıma uygun mu? kritik teknik borç var mı? yeni geliştirmeye başlamadan önce ne gerekli?).

## 5. Tests / validation

- Her kod görevi TDD: başarısız test yaz → `pytest` ile kırmızıyı gör → minimum実装 → yeşili gör → tam süit. Komut standardı:
  `C:/Users/mahmu/Projeler/NetSonar/.venv/Scripts/python.exe -m pytest tests/test_<alan>.py -q` (beklenen önce `1 failed`, sonra `passed`) ve
  `C:/Users/mahmu/Projeler/NetSonar/.venv/Scripts/python.exe -m pytest tests/ -q` (beklenen `passed`, 2026-09-09 bazında 16 dosya).
- Kapılar: Etap 3/4/6/11 sonunda tam süit yeşili zorunlu; kırmızı varken sonraki etaba geçilmez. GUI testleri headless takılırsa `set QT_QPA_PLATFORM=offscreen&& .../python.exe -m pytest tests/test_ui_smoke.py -q` denenir, sonuç nota düşülür.
- Commit disiplini: etap başına küçük commitler (`test: ...`, `fix: ...`, `chore: ...`), mesajda etap ID (örn. `fix(H-03): ...`). Push/tag/sürüm yükseltme bu planda yok — kullanıcı "yedek/exe" demeden yapılmaz. Yabancı WIP satırlarına dokunulmaz; commit öncesi `git status --short` bakılır.

## 6. Risks, tradeoffs, and open questions

- Riskler: `app_gui.py` 2650 satır — geniş refactor cazip ama yasak (kural 3, 11, 12); yalnızca hata/temizlik dokunuşu. Npcap/admin gerektiren yollar bu makinede tam test edilemez → "doğrulanamadı" yazılır, başarılı sayılmaz (kural 15). `database.py`/`kill_switch.py` veri ve firewall ile oynar → yedek/geri alma planı olmadan çalışılmaz (kural 10, 17, 18); migration testi (`test_migration_v05`) her DB dokunuşunda koşulur. Dinamik import/config-anahtarlı çağrılar yanlış "ölü kod" kararına yol açabilir → şüpheli aday silinmez (kural 5, 16).
- Tradeoff: hız (tek süpürmede hepsini düzeltme) yerine etap disiplini seçildi; kısa vadede yavaş, uzun vadede regresyonsuz.
- Açık sorular (uygulamaya başlamadan kullanıcıya): (1) Canlı yakalama/GUI testleri için Npcap'li Windows makine erişimi olacak mı, yoksa headless-only mi kalınacak? (2) Bu turun sonunda sürüm yükseltme (`v0.5.5`?) + exe build isteniyor mu, yoksa yalnızca kod + rapor mu? (3) `dist/*.exe` ve kullanıcı DB/`settings.json` dokunulmaz kabul — onay?

# NetSonar — DURUM (ortak — Desktop + Telegram okur)

**Güncelleme:** 2026-10-17
**Versiyon:** v0.5.9 (tag: bu commit; dağıtım: zeitgeist-c/NetSonar-Releases v0.5.9)
**Branch:** main (push edildi: main + v0.5.9; dagitim: NetSonar-Releases v0.5.9 yayinda)
**Son commit:** bu commit (v0.5.9 arayüz yenilemesi)
**Ağaç:** kapsam içi dosyalar commit'lendi; `ui-kesif/` keşif çıktıları ve `.hermes/`, `AGENTS.md` untracked.
**Not:** Kirli dosyalar kullanıcıya ait olabilir; commit öncesi kullanıcıya sorulur. (2026-10-17: "Yedek işlemini yapabilir misin?" talebiyle tam kapanış yetkisi verildi.)

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
- WordArc'ın güncelleyicisi uyarlandı (`update.py`): herkese açık `zeitgeist-c/NetSonar-Releases` deposundan `releases/latest` kimliksiz sorgu, SHA256 doğrulamalı indirme, swap batonu ile kendini değiştirme. BAT eşleşen exe'ye yeniden yazılır; autostart HKCU kaydı `retarget_launch` ile çevrilir.
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

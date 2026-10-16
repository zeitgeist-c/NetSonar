# NetSonar — DURUM (ortak — Desktop + Telegram okur)

**Güncelleme:** 2026-10-17
**Versiyon:** v0.5.8 (tag: bu commit; dağıtım: zeitgeist-c/NetSonar-Releases v0.5.8)
**Branch:** main (push bekliyor — aynı oturumda yapılacak)
**Son commit:** önceki: 0b76fb7 (v0.5.7 dağıtım dosyaları)
**Ağaç:** bu commit'le temizlendi; kullanıcının 21-skill turu sonrası WIP'i onayıyla dahil edildi (NetSonar.bat Npcap yolu düzeltmesi, requirements-build pin güncellemeleri, app_gui/capture_engine/custom_alerts/database/flow_accumulator/notifier/test_flow_accumulator küçük değişiklikleri).
**Not:** Kirli dosyalar kullanıcıya ait olabilir; commit öncesi kullanıcıya sorulur. (2026-10-17: app_gui.py ve WIP dahil tüm ağaç üzerinde açık onay alındı.)

## v0.5.8 — Kendi kendine güncelleme + portable paket (2026-10-17)
- WordArc'ın güncelleyicisi uyarlandı (`update.py`): herkese açık `zeitgeist-c/NetSonar-Releases` deposundan `releases/latest` kimliksiz sorgu, SHA256 doğrulamalı indirme, swap batonu ile kendini değiştirme. Yeni: BAT eşleşen exe'ye yeniden yazılır; autostart HKCU kaydı `retarget_launch` ile çevrilir.
- Dağıtım artık portable onefile: `dist/NetSonar-v0.5.8.exe` (49.722.012 bayt; SHA-256: cc9c4a7738f044e26d38fd9d38c959172a83fd0c360f3e17192ab6b6cd762f0e) + eşleşen BAT. NSIS kurulumcusu (`NetSonar.nsi`) kaldırıldı; yönetici yetkisi UAC manifestinde, Npcap uyarısı exe açılışına taşındı (`_npcap_notice_once`).
- Ayarlar sekmesinde "Güncellemeler" kartı: açılıştan 30 sn sonra günde bir sessiz denetim (`UPDATE_LAST_CHECK`), elle denetleme, ilerleme çubuğu, İndir ve Kur. Kaynak koddan çalışırken kilitli.
- `tests/test_update.py`: 13 yeni test; `test_version_and_api_errors` BAT sözleşmesi portable'a uyarlandı. Toplam: 92 test + 29 alt test geçti.
- Assetler `NetSonar-Releases/v0.5.8` sürümüne yüklenecek (exe+bat); eski NetSonar deposundaki son release v0.5.6 olarak kalır.
- Not: eski kurulumcuyla kurulmuş kullanıcılar portable'a bir kez elle geçer; sonraki güncellemeler otomatik.

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

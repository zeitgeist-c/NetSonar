"""AUD-NET-001: tum 13 dil katalogu yuklenmeli, sessiz kayip olmamali."""
import i18n


def test_tum_kataloglar_yuklendi():
    assert i18n.LOAD_ERRORS == [], i18n.LOAD_ERRORS
    beklenen = {"en", "tr", "de", "es", "fr", "it", "pt-BR",
                "ru", "pl", "nl", "zh-CN", "ja", "ko"}
    assert set(i18n.TABLES.keys()) == beklenen
    for kod in beklenen - {"tr"}:
        assert len(i18n.TABLES[kod]) > 200, (kod, len(i18n.TABLES[kod]))


def test_temsilci_ceviri_13_dilde():
    # 'Analiz' her dilde kendi karsiligini vermeli (kaynak fallback yok).
    for kod in ("en", "de", "es", "fr", "it", "pt-BR",
                "ru", "pl", "nl", "zh-CN", "ja", "ko"):
        i18n._lang = kod
        cikti = i18n.t("Analiz")
        assert cikti != "Analiz" or kod == "tr", (kod, cikti)
    i18n._lang = "en"

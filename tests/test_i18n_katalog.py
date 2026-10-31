"""AUD-NET-001: all 13 language catalogs must load, no silent loss.

Contract: the Turkish source text is the key ('tr' resolves to the key itself),
every other language holds a translation. A Turkish literal that is not wrapped
in t() leaks Turkish into the English UI; a t() key missing from a table
silently falls back to Turkish. Both are asserted below.
"""
import ast
import re

import pytest

import i18n


def test_all_catalogs_loaded():
    assert i18n.LOAD_ERRORS == [], i18n.LOAD_ERRORS
    expected = {"en", "tr", "de", "es", "fr", "it", "pt-BR",
                "ru", "pl", "nl", "zh-CN", "ja", "ko"}
    assert set(i18n.TABLES.keys()) == expected
    for code in expected - {"tr"}:
        assert len(i18n.TABLES[code]) > 200, (code, len(i18n.TABLES[code]))


def test_representative_translation_in_13_languages():
    # 'Analiz' must yield its own equivalent in every language (no source fallback).
    for code in ("en", "de", "es", "fr", "it", "pt-BR",
                 "ru", "pl", "nl", "zh-CN", "ja", "ko"):
        i18n._lang = code
        output = i18n.t("Analiz")
        assert output != "Analiz" or code == "tr", (code, output)
    i18n._lang = "en"


LANGS = ("en", "de", "es", "fr", "it", "pt-BR", "ru", "pl", "nl",
         "zh-CN", "ja", "ko")
# Source files whose literals reach the screen or the exported report.
UI_FILES = ("app_gui.py", "ui_components.py", "exporter.py", "notifier.py",
            "ai_analyzer.py")
TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
# Turkish words that survive without diacritics; legacy code wrote e.g.
# "Supheli" without the dotted letters, so a diacritic check alone misses it.
TR_WORDS = re.compile(
    r"\b(ve|ile|için|bir|bu|şu|olan|olarak|yok|var|değil|daha|sonra|önce|"
    r"kaydet|ekle|düzenle|kaldır|sil|aç|kapat|başlat|dur|iptal|tamam|"
    r"durum|risk|analiz|ayar|ayarlar|anahtar|güvenli|tehlike|rapor|"
    r"hata|uyarı|bilgi|sonuç|kaynak|süreç|işlem|tarih|sağlayıcı)\b",
    re.IGNORECASE,
)
# Short technical or brand tokens that are identical in every language.
ALLOWED = {
    "IP / Port", "JSON", "CSV", "TXT", "Gemini", "VirusTotal", "Tavily",
    "NetSonar", "NETWORK SECURITY OPERATIONS", "NORMAL", "TCP", "UDP",
    "OTHER", "MB", "PORT", "PROTO",
}
# Widget/call sites whose string arguments reach the user.
UI_CALLS = {
    "QLabel", "AppButton", "NeoCard", "StatusPill", "PageHeader", "QCheckBox",
    "EmptyState", "QInputDialog", "setText", "setTitle", "setWindowTitle",
    "setHorizontalHeaderLabels", "setPlaceholderText", "setToolTip",
    "setSuffix", "add_field", "addRow", "addItems", "addTab",
    "set_message", "set_status", "showMessage", "information", "warning",
    "critical", "question", "SubNav", "_muted_label", "show_update_error",
}


def _looks_turkish(text):
    if any(char in TR_CHARS for char in text):
        return True
    return " " in text.strip() and bool(TR_WORDS.search(text))


def _call_name(node):
    func = node.func
    return func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)


def _ui_literals(path):
    """UI-call string arguments that are neither wrapped in t() nor allowed."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    wrapped = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) in ("t", "_t"):
            for arg in node.args:
                for sub in ast.walk(arg):
                    wrapped.add(id(sub))

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) not in UI_CALLS:
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for sub in ast.walk(arg):
                if not isinstance(sub, ast.Constant) or not isinstance(sub.value, str):
                    continue
                text = sub.value
                if id(sub) in wrapped or not text.strip() or text in ALLOWED:
                    continue
                if _looks_turkish(text):
                    found.append((sub.lineno, text))
    return found


def _catalogue_call_keys(path):
    """Every literal first argument of t() in the file."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    keys = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == "t" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.append((node.lineno, arg.value))
    return keys


def test_every_language_has_the_english_key_set():
    """A key present in EN must exist in all 11 other translations."""
    reference = set(i18n.TABLES["en"])
    for code in LANGS[1:]:
        missing = reference - set(i18n.TABLES[code])
        assert not missing, (code, sorted(missing)[:5])


def test_no_turkish_value_in_translated_tables():
    """An untranslated entry silently keeps the Turkish source text.
    Only Turkish-distinctive letters are checked: 'Port'/'PROTO'/'Model' are
    legitimately identical in several languages, 'ı/ş/ğ/ç' never are."""
    distinct = set("çğıöşÇĞİŞ")
    for code in LANGS:
        for key, value in i18n.TABLES[code].items():
            if value == key and any(char in distinct for char in key):
                pytest.fail(f"{code}: untranslated value for {key!r}")


def test_placeholders_match_source_key():
    """Format fields must survive translation, otherwise t() truncates output."""
    simple = re.compile(r"\{([A-Za-z_]\w*)\}")

    def fields(text):
        return sorted(set(simple.findall(text)))

    for code in LANGS:
        for key, value in i18n.TABLES[code].items():
            assert fields(key) == fields(value), (code, key, value)


@pytest.mark.parametrize("path", UI_FILES)
def test_no_untranslated_turkish_ui_literal(path):
    """English UI must not fall back to Turkish because a literal is unwrapped."""
    assert not _ui_literals(path), _ui_literals(path)


@pytest.mark.parametrize("path", UI_FILES)
def test_every_catalogue_call_has_a_translation(path):
    """A t() key missing from a table silently renders the Turkish source."""
    missing = {}
    for _, key in _catalogue_call_keys(path):
        for code in LANGS:
            if key not in i18n.TABLES[code]:
                missing.setdefault(key, []).append(code)
    assert not missing, {key: codes for key, codes in list(missing.items())[:5]}

"""NetSonar 13-language contract: Turkish-keyed dictionary, English default.

Existing UI texts were written in Turkish, so the original Turkish text is
used as the key; all 12 other languages (including English) are translated
in TABLES.
- Fresh installs default to English; the OS locale does not override it.
- A saved explicit choice (settings.json LANGUAGE) is preserved.
- Unknown codes fall back to English (missing = red at the release gate).
"""

import os

from i18n_strings_tables import (
    DE1, DE2, DE3, DE4,
    EN, EN_EXTRA,
    ES1, ES2, ES3, ES4,
    FR1, FR2, FR3, FR4,
    IT1, IT2, IT3, IT4,
    JA1, JA2, JA3, JA4,
    KO1, KO2, KO3, KO4,
    NL1, NL2, NL3, NL4,
    PB1, PB2, PB3, PB4,
    PL1, PL2, PL3, PL4,
    RU1, RU2, RU3, RU4,
    ZH1, ZH2, ZH3, ZH4,
)

LANGUAGES = [
    ("en", "English"),
    ("tr", "Türkçe"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
    ("it", "Italiano"),
    ("pt-BR", "Português (Brasil)"),
    ("ru", "Русский"),
    ("pl", "Polski"),
    ("nl", "Nederlands"),
    ("zh-CN", "简体中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]

CODES = {code for code, _ in LANGUAGES}

_lang = "en"


def resolve(code):
    if code in CODES:
        return code
    return "en"


def set_language(code):
    global _lang
    _lang = resolve(code)


def language():
    return _lang


# Analysis statuses travel as ASCII codes through the analyser, the database
# and the notification layer; they are shown through the catalogue so no
# internal code reaches the user in any language.
STATUS_KEYS = {
    "api hatasi": "API Hatası",
    "skipped": "Atlandı",
    "risky": "Riskli",
    "safe": "Güvenli",
    "unknown": "Bilinmiyor",
}


def status_text(status):
    raw = str(status or "").strip()
    key = STATUS_KEYS.get(raw.lower())
    return t(key) if key else raw


def t(key, _fmt=True, **kwargs):
    text = key
    table = TABLES.get(_lang)
    out = table.get(text, text) if table else text
    if not kwargs or not _fmt:
        return out
    try:
        return out.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return out


def _merge(*parts):
    merged = {}
    for part in parts:
        merged.update(part or {})
    return merged


TABLES = {
    "en": _merge(EN, EN_EXTRA),
    "tr": {},
    "de": _merge(DE1, DE2, DE3, DE4),
    "es": _merge(ES1, ES2, ES3, ES4),
    "fr": _merge(FR1, FR2, FR3, FR4),
    "it": _merge(IT1, IT2, IT3, IT4),
    "pt-BR": _merge(PB1, PB2, PB3, PB4),
    "ru": _merge(RU1, RU2, RU3, RU4),
    "pl": _merge(PL1, PL2, PL3, PL4),
    "nl": _merge(NL1, NL2, NL3, NL4),
    "zh-CN": _merge(ZH1, ZH2, ZH3, ZH4),
    "ja": _merge(JA1, JA2, JA3, JA4),
    "ko": _merge(KO1, KO2, KO3, KO4),
}

# Packaging audit hook: a catalogue module that fails to import is listed here.
# The tables are now a static import, so a broken catalogue fails loudly at
# import time; the list stays empty and tests still assert that.
LOAD_ERRORS = []

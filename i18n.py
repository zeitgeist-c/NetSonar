"""NetSonar 13 dil sözleşmesi: TR anahtarlı sözlük, EN default.

Mevcut UI metinleri Türkçe yazıldığından anahtar olarak orijinal Türkçe
metin kullanılır; İngilizce dahil 12 dil TABLES'ta çevrilir.
- Yeni kurulumda varsayılan İngilizce; OS dili ezmez.
- Kayıtlı açık tercih (settings.json LANGUAGE) korunur.
- Bilinmeyen kod emergingilizce'ye düşer (release kapısında eksik = kırmızı).
"""

import json
import os

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


TABLES = {}


def _load():
    global TABLES
    if TABLES:
        return
    try:
        from i18n_strings_en import EN
        from i18n_strings_en_extra import EN_EXTRA
        merged = dict(EN)
        merged.update(EN_EXTRA)
        TABLES = {"en": merged, "tr": {}}
        for _kod, _ad in (("de", "DE"), ("es", "ES"), ("fr", "FR"),
                             ("it", "IT"), ("pt-BR", "PB"), ("ru", "RU"),
                             ("pl", "PL"), ("nl", "NL"), ("zh-CN", "ZH"),
                             ("ja", "JA"), ("ko", "KO")):
            _bir = {}
            for _i in (1, 2, 3, 4):
                try:
                    _m = __import__("i18n_strings_%s%d" % (_ad.lower(), _i),
                                     fromlist=["%s%d" % (_ad, _i)])
                    _parca = getattr(_m, "%s%d" % (_ad, _i), None)
                    if isinstance(_parca, dict):
                        _bir.update(_parca)
                except ImportError:
                    pass
            if _bir:
                TABLES[_kod] = _bir
    except ImportError:
        TABLES = {"en": {}, "tr": {}}


_load()

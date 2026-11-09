"""Çeviriler: i18n.json (en, tr, es). Varsayılan dil İngilizce."""

import json
import os
import sys

LANGS = ("en", "tr", "es")
DEFAULT = "en"


def _path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "i18n.json")


with open(_path(), encoding="utf-8") as _fh:
    STRINGS = json.load(_fh)


def norm(lang):
    lang = (lang or "").lower()[:2]
    return lang if lang in LANGS else DEFAULT


def t(lang, key, **kw):
    s = STRINGS.get(norm(lang), {}).get(key) or STRINGS[DEFAULT].get(key) or key
    try:
        return s.format(**kw) if kw else s
    except (KeyError, IndexError):
        return s


def from_accept_language(header):
    """Tarayıcının Accept-Language başlığından desteklenen ilk dili seçer."""
    for part in (header or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return DEFAULT


def languages():
    return [{"code": c, "name": STRINGS[c]["lang.name"]} for c in LANGS]


class UserError(Exception):
    """Kullanıcıya çevrilerek gösterilecek hata."""

    def __init__(self, key, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def message(self, lang):
        return t(lang, self.key, **self.params)

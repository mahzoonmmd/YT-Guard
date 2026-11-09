# -*- coding: utf-8 -*-
"""Tiny i18n layer. Source strings are Persian; `tr()` translates them to English when the UI language is English.

Matching ignores zero-width non-joiners. Composed strings (f-strings / concatenations) are translated fragment by
fragment (longest known fragment first), so dynamic parts such as numbers and file names stay untouched.
The language is read from the settings file at import time; changing it needs an app restart.
"""
from __future__ import annotations

import json
import re

from PyQt6.QtCore import Qt

from .storage import data_dir

_ZW = "‌"
_FA = re.compile(r"[؀-ۿ]")


def _read_lang() -> str:
    try:
        v = json.loads((data_dir() / "settings.json").read_text(encoding="utf-8")).get("language", "fa")
        return v if v in ("fa", "en") else "fa"
    except Exception:
        return "fa"


LANG = _read_lang()
IS_RTL = LANG == "fa"
DIR = Qt.LayoutDirection.RightToLeft if IS_RTL else Qt.LayoutDirection.LeftToRight

_pairs: list[tuple[str, str]] = []
if LANG == "en":
    from . import i18n_en_checks, i18n_en_misc, i18n_en_ui
    seen = {}
    for mod in (i18n_en_ui, i18n_en_checks, i18n_en_misc):
        for fa, en in mod.PAIRS:
            seen[fa.replace(_ZW, "")] = en
    _pairs = sorted(seen.items(), key=lambda kv: -len(kv[0]))
    _exact = dict(seen)


def tr(text):
    """Translate a Persian UI string (or a composition of known fragments) when LANG == 'en'."""
    if LANG != "en" or not isinstance(text, str) or not _FA.search(text):
        return text
    s = text.replace(_ZW, "")
    hit = _exact.get(s)
    if hit is not None:
        return hit
    for k, v in _pairs:
        if k in s:
            s = s.replace(k, v)
            if not _FA.search(s):
                break
    return s


def untranslated(text: str) -> str:
    """Return the Persian leftovers of tr(text) (for tests)."""
    return "".join(_FA.findall(tr(text)))

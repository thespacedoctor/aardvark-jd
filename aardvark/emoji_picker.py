#!/usr/bin/env python
# encoding: utf-8
"""
*Pick an appropriate emoji for a folder name from its title/description*

Author
: David Young
"""

import re
import emoji

FALLBACK_EMOJI = "📁"

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at",
    "with", "my", "our", "your",
}

_keywordIndex = None


def _build_keyword_index():
    """
    *build a keyword -> emoji lookup from `emoji.EMOJI_DATA`'s CLDR short names*

    Only fully-qualified emoji are indexed (skips skin-tone/component
    modifiers), and the first emoji seen for a given keyword wins, so
    shorter/more canonical entries (which sort first in `EMOJI_DATA`)
    take priority over obscure variants.

    **Return:**

    - ``keywordIndex`` -- a dict mapping lowercase keyword -> emoji character
    """
    keywordIndex = {}
    for character, data in emoji.EMOJI_DATA.items():
        if data.get("status") != emoji.STATUS["fully_qualified"]:
            continue
        names = [data.get("en", "")] + data.get("alias", [])
        for name in names:
            for keyword in name.strip(":").split("_"):
                keyword = keyword.lower()
                if keyword and keyword not in keywordIndex:
                    keywordIndex[keyword] = character
    return keywordIndex


def _get_keyword_index():
    """
    *lazily build and cache the keyword -> emoji index*

    **Return:**

    - ``keywordIndex`` -- the cached keyword -> emoji index
    """
    global _keywordIndex
    if _keywordIndex is None:
        _keywordIndex = _build_keyword_index()
    return _keywordIndex


def _tokenise(text):
    """
    *split free text into lowercase, stopword-free keyword tokens*

    **Key Arguments:**

    - ``text`` -- the free text to tokenise

    **Return:**

    - ``tokens`` -- a list of lowercase keyword tokens
    """
    words = re.findall(r"[A-Za-z]+", text.lower())
    return [word for word in words if word not in _STOPWORDS]


def pick_emoji(title, description=""):
    """
    *pick an appropriate emoji for a folder from its title and description*

    Looks up each word of ``title`` in turn against the `emoji` package's
    keyword index, then falls back to ``description`` if nothing in the
    title matched, and finally to :py:data:`FALLBACK_EMOJI`.

    **Key Arguments:**

    - ``title`` -- the folder's title
    - ``description`` -- the folder's description. Default `""`.

    **Return:**

    - ``pickedEmoji`` -- the picked emoji character
    """
    keywordIndex = _get_keyword_index()

    for text in (title, description):
        for token in _tokenise(text or ""):
            if token in keywordIndex:
                return keywordIndex[token]

    return FALLBACK_EMOJI

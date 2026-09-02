#!/usr/bin/env python
# encoding: utf-8
"""
*Render an index row as the one-line label the user reads*

A label is `<code> <emoji> <title>`, e.g. `A10-19 🏥 Health`, and is the
display form of an index row - distinct from the row's *folder name*
(`A10_19_health🏥`), which is the on-disk string. Areas and categories own
an emoji and so carry one; IDs and domain headings do not, and so read
`<code> <title>`.

This module exists so the three places that render the same row - the `fd`
tree, the `fd` keyword results and the `open` picker - cannot drift apart.

Author
: David Young
"""

from aardvark_jd import codes, emoji_picker

# ROWS THAT *SHOULD* CARRY AN EMOJI BUT DON'T - LEGACY OR DRIFTED DATA, SINCE
# BOTH COLUMNS ARE `NOT NULL DEFAULT '📁'`. SHOWING THE FALLBACK MARKS THE GAP
# RATHER THAN QUIETLY RENDERING A RAGGED LINE.
FALLBACK_EMOJI = emoji_picker.FALLBACK_EMOJI

# THE ENTITY TYPES `search_index` RECORDS THAT OWN AN EMOJI OF THEIR OWN.
_EMOJI_ENTITY_TYPES = ("area", "category")


def _with_emoji(code, emoji, title):
    """
    *build the label of something that owns an emoji*

    **Key Arguments:**

    - ``code`` -- the Johnny Decimal code, e.g. `"A10-19"`
    - ``emoji`` -- the row's stored emoji, which may be blank
    - ``title`` -- the row's title

    **Return:**

    - ``label`` -- the `<code> <emoji> <title>` display line
    """
    return _join(code, emoji or FALLBACK_EMOJI, title)


def _join(*parts):
    """
    *join the parts of a label with single spaces, dropping any that are empty*

    **Key Arguments:**

    - ``parts`` -- the label's parts, in display order

    **Return:**

    - ``label`` -- the joined display line
    """
    return " ".join(part for part in parts if part)


def area_label(domain, area):
    """
    *the display label for one area*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`
    - ``area`` -- the `areas` row

    **Return:**

    - ``label`` -- the `<code> <emoji> <title>` display line

    **Usage:**

    ```python
    from aardvark_jd import labels
    line = labels.area_label("areas", areaRow)
    ```
    """
    code = codes.format_area_code(domain, area["decade_start"], area["decade_end"])
    return _with_emoji(code, area["emoji"], area["title"])


def category_label(domain, category):
    """
    *the display label for one category*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`
    - ``category`` -- the `categories` row

    **Return:**

    - ``label`` -- the `<code> <emoji> <title>` display line
    """
    code = codes.format_category_code(domain, category["ac_number"])
    return _with_emoji(code, category["emoji"], category["title"])


def id_label(domain, idRow):
    """
    *the display label for one ID*

    IDs carry no `emoji` column and their folders are never emoji-suffixed,
    so the label is the code and the title alone. The fallback used for a
    blank area/category emoji would be a lie here - there is no missing
    emoji to flag.

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`
    - ``idRow`` -- the `ids` row

    **Return:**

    - ``label`` -- the `<code> <title>` display line
    """
    code = codes.format_id_code(domain, idRow["ac_number"], idRow["item_number"])
    return _join(code, idRow["title"])


def domain_label(domain):
    """
    *the display label for one domain heading*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`

    **Return:**

    - ``label`` -- the `<letter> <domain>` display line
    """
    return _join(codes.DOMAIN_LETTER[domain], domain)


def result_label(row):
    """
    *the display label for one search result*

    A search row already carries a formatted `code`, so the label is built
    from that rather than re-derived from the numbers, which the row does
    not hold. Its `emoji` is attached by `search.search.get`; a row without
    one is either an ID (no emoji by design) or an area/category whose
    stored emoji is blank (flagged with the fallback).

    **Key Arguments:**

    - ``row`` -- a search result dict with keys `entity_type`, `code` and `title`, and optionally `emoji`

    **Return:**

    - ``label`` -- the display line, with no trailing path

    **Usage:**

    ```python
    from aardvark_jd import labels
    line = labels.result_label(row)
    ```
    """
    code = row["code"] or ""
    if row.get("entity_type") not in _EMOJI_ENTITY_TYPES:
        return _join(code, row["title"])
    return _with_emoji(code, row.get("emoji"), row["title"])

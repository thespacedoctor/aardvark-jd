#!/usr/bin/env python
# encoding: utf-8
"""
*Johnny Decimal domain/code parsing and formatting helpers*

Author
: David Young
"""

import re

DOMAINS = ("areas", "resources")
DOMAIN_LETTER = {"areas": "A", "resources": "R"}

_AREA_REF_RE = re.compile(r"^(?:[AR]\.)?(\d{2})(?:-(\d{2}))?$")
_CATEGORY_REF_RE = re.compile(r"^(?:[AR]\.)?(\d{2})$")


def validate_domain(domain):
    """
    *check a domain is either `areas` or `resources`, raising a clear error otherwise*

    **Key Arguments:**

    - ``domain`` -- the domain string to validate

    **Return:**

    - ``domain`` -- the validated domain, unchanged
    """
    if domain not in DOMAINS:
        raise ValueError(
            f"'{domain}' is not a valid domain - expected one of {DOMAINS}"
        )
    return domain


def domain_letter(domain):
    """
    *return the single-letter code for a domain (`areas` -> `A`, `resources` -> `R`)*

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`

    **Return:**

    - ``letter`` -- the domain's single-letter code
    """
    validate_domain(domain)
    return DOMAIN_LETTER[domain]


def parse_area_ref(text):
    """
    *parse a user-supplied area reference into its decade-start number*

    Accepts `"10"`, `"10-19"`, `"A.10"` or `"A.10-19"` style input.

    **Key Arguments:**

    - ``text`` -- the raw area reference supplied on the command-line

    **Return:**

    - ``decadeStart`` -- the area's decade-start number, e.g. `10`
    """
    text = str(text).strip()
    match = _AREA_REF_RE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not a valid area reference - expected e.g. '10', '10-19' or 'A.10-19'"
        )
    decadeStart = int(match.group(1))
    if decadeStart % 10 != 0 or decadeStart == 0:
        raise ValueError(
            f"'{text}' is not a valid area reference - decade must be one of 10, 20, ..., 90"
        )
    decadeEndText = match.group(2)
    if decadeEndText is not None and int(decadeEndText) != decadeStart + 9:
        raise ValueError(
            f"'{text}' is not a valid area reference - a decade range must span exactly "
            f"'{decadeStart:02d}-{decadeStart + 9:02d}'"
        )
    return decadeStart


def parse_category_ref(text):
    """
    *parse a user-supplied category reference into its AC number*

    Accepts `"11"` or `"A.11"` style input.

    **Key Arguments:**

    - ``text`` -- the raw category reference supplied on the command-line

    **Return:**

    - ``acNumber`` -- the category's 2-digit AC number, e.g. `11`
    """
    text = str(text).strip()
    match = _CATEGORY_REF_RE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not a valid category reference - expected e.g. '11' or 'A.11'"
        )
    return int(match.group(1))


def format_area_code(domain, decadeStart, decadeEnd):
    """
    *format the display code for a Johnny Decimal area, e.g. `A.10-19`*

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`
    - ``decadeStart`` -- the area's decade-start number
    - ``decadeEnd`` -- the area's decade-end number

    **Return:**

    - ``code`` -- the formatted area code
    """
    return f"{domain_letter(domain)}.{decadeStart:02d}-{decadeEnd:02d}"


def format_category_code(domain, acNumber):
    """
    *format the display code for a Johnny Decimal category, e.g. `A.11`*

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the category's 2-digit AC number

    **Return:**

    - ``code`` -- the formatted category code
    """
    return f"{domain_letter(domain)}.{acNumber:02d}"


def format_id_code(domain, acNumber, itemNumber):
    """
    *format the display code for a Johnny Decimal ID, e.g. `A.11.01`*

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the parent category's 2-digit AC number
    - ``itemNumber`` -- the ID's 2-digit item number

    **Return:**

    - ``code`` -- the formatted ID code
    """
    return f"{domain_letter(domain)}.{acNumber:02d}.{itemNumber:02d}"

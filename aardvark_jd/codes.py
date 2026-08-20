#!/usr/bin/env python
# encoding: utf-8
"""
*Johnny Decimal domain/code parsing and formatting helpers*

Author
: David Young
"""

import re

DOMAINS = ("areas", "resources", "projects")
DOMAIN_LETTER = {"areas": "A", "resources": "R", "projects": "P"}
LETTER_DOMAIN = {letter: domain for domain, letter in DOMAIN_LETTER.items()}

# THE DOMAIN LETTER IS MANDATORY ON EVERY REFERENCE - IT IS THE ONLY THING
# TELLING `A11` FROM `R11` FROM `P11`, NOW THAT COMMANDS NO LONGER TAKE A
# SEPARATE DOMAIN ARGUMENT. THE PERIOD AFTER IT IS THE LEGACY `A.11` FORM,
# STILL ACCEPTED BUT NO LONGER WRITTEN.
_AREA_REF_RE = re.compile(r"^([APR])\.?(\d{2})(?:-(\d{2}))?$", re.IGNORECASE)
_CATEGORY_REF_RE = re.compile(r"^([APR])\.?(\d{2})$", re.IGNORECASE)

LETTER_HINT = "'A' (areas), 'R' (resources) or 'P' (projects)"


def validate_domain(domain):
    """
    *check a domain is one of `areas`, `resources` or `projects`, raising a clear error otherwise*

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
    *return the single-letter code for a domain (`areas` -> `A`, `resources` -> `R`, `projects` -> `P`)*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`

    **Return:**

    - ``letter`` -- the domain's single-letter code
    """
    validate_domain(domain)
    return DOMAIN_LETTER[domain]


def domain_from_letter(text):
    """
    *resolve a single-letter domain code to its domain (`A` -> `areas`, `R` -> `resources`, `P` -> `projects`)*

    The full domain word is accepted too, so anything already holding an
    `"areas"`-style string can be passed straight through.

    **Key Arguments:**

    - ``text`` -- the domain letter supplied on the command-line

    **Return:**

    - ``domain`` -- `areas`, `resources` or `projects`

    **Usage:**

    ```python
    from aardvark_jd import codes
    domain = codes.domain_from_letter("A")
    ```
    """
    text = str(text).strip()
    if text in DOMAINS:
        return text
    letter = text.upper()
    if letter not in LETTER_DOMAIN:
        raise ValueError(
            f"'{text}' is not a valid domain letter - expected {LETTER_HINT}"
        )
    return LETTER_DOMAIN[letter]


def is_jd_ref(text):
    """
    *decide whether a reference is a Johnny Decimal area/category code rather than something else*

    Used to tell an area or category reference (`"A10-19"`, `"R11"`) apart
    from a system folder key (`"root.areas"`), now that neither carries an
    explicit domain argument alongside it.

    **Key Arguments:**

    - ``text`` -- the raw reference supplied on the command-line

    **Return:**

    - ``isJdRef`` -- `True` if the reference is a Johnny Decimal area or category code

    **Usage:**

    ```python
    from aardvark_jd import codes
    isJdRef = codes.is_jd_ref("A10-19")
    ```
    """
    return _AREA_REF_RE.match(str(text).strip()) is not None


def domain_from_ref(text):
    """
    *return the domain a Johnny Decimal reference belongs to, from its letter prefix*

    Only the letter is validated here - the numbers are left to
    `split_area_ref`/`split_category_ref`, so this answers "which domain?"
    for an area ref and a category ref alike.

    **Key Arguments:**

    - ``text`` -- the raw reference supplied on the command-line

    **Return:**

    - ``domain`` -- `areas`, `resources` or `projects`

    **Usage:**

    ```python
    from aardvark_jd import codes
    domain = codes.domain_from_ref("A11")
    ```
    """
    text = str(text).strip()
    match = _AREA_REF_RE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not a valid Johnny Decimal reference - expected a domain letter "
            f"prefix, e.g. 'A10-19', 'R10' or 'P11'"
        )
    return LETTER_DOMAIN[match.group(1).upper()]


def _check_domain_matches(text, letter, domain):
    """
    *check a reference's domain letter agrees with the domain a command is working in*

    **Key Arguments:**

    - ``text`` -- the raw reference, quoted back in the error message
    - ``letter`` -- the reference's upper-cased domain letter
    - ``domain`` -- the domain to check against, or `None` to skip the check

    **Return:**

    - ``domain`` -- the reference's own domain
    """
    refDomain = LETTER_DOMAIN[letter]
    if domain is not None and refDomain != domain:
        raise ValueError(
            f"'{text}' is a '{refDomain}' reference, but this command is working in '{domain}'"
        )
    return refDomain


def split_area_ref(text, domain=None):
    """
    *split a user-supplied area reference into its domain and decade-start number*

    Accepts `"A10"`, `"A10-19"`, `"R10-19"` or `"P10"` style input (the older
    `"A.10"`/`"A.10-19"` form with the period still parses too). The domain
    letter is required.

    **Key Arguments:**

    - ``text`` -- the raw area reference supplied on the command-line
    - ``domain`` -- a domain the reference must belong to, or `None` to take the reference's own. Default `None`.

    **Return:**

    - ``domain`` -- the area's domain, e.g. `areas`
    - ``decadeStart`` -- the area's decade-start number, e.g. `10`

    **Usage:**

    ```python
    from aardvark_jd import codes
    domain, decadeStart = codes.split_area_ref("A10-19")
    ```
    """
    text = str(text).strip()
    match = _AREA_REF_RE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not a valid area reference - expected a domain letter prefix, "
            f"e.g. 'A10-19', 'R10-19' or 'P10-19'"
        )
    refDomain = _check_domain_matches(text, match.group(1).upper(), domain)
    decadeStart = int(match.group(2))
    if decadeStart % 10 != 0 or decadeStart == 0:
        raise ValueError(
            f"'{text}' is not a valid area reference - decade must be one of 10, 20, ..., 90"
        )
    decadeEndText = match.group(3)
    if decadeEndText is not None and int(decadeEndText) != decadeStart + 9:
        raise ValueError(
            f"'{text}' is not a valid area reference - a decade range must span exactly "
            f"'{decadeStart:02d}-{decadeStart + 9:02d}'"
        )
    return refDomain, decadeStart


def split_category_ref(text, domain=None):
    """
    *split a user-supplied category reference into its domain and AC number*

    Accepts `"A11"`, `"R11"` or `"P11"` style input (the older `"A.11"` form
    with the period still parses too). The domain letter is required.

    **Key Arguments:**

    - ``text`` -- the raw category reference supplied on the command-line
    - ``domain`` -- a domain the reference must belong to, or `None` to take the reference's own. Default `None`.

    **Return:**

    - ``domain`` -- the category's domain, e.g. `areas`
    - ``acNumber`` -- the category's 2-digit AC number, e.g. `11`

    **Usage:**

    ```python
    from aardvark_jd import codes
    domain, acNumber = codes.split_category_ref("A11")
    ```
    """
    text = str(text).strip()
    match = _CATEGORY_REF_RE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not a valid category reference - expected a domain letter prefix, "
            f"e.g. 'A11', 'R11' or 'P11'"
        )
    refDomain = _check_domain_matches(text, match.group(1).upper(), domain)
    return refDomain, int(match.group(2))


def parse_area_ref(text, domain=None):
    """
    *parse a user-supplied area reference into its decade-start number*

    **Key Arguments:**

    - ``text`` -- the raw area reference supplied on the command-line
    - ``domain`` -- a domain the reference must belong to, or `None` to accept any. Default `None`.

    **Return:**

    - ``decadeStart`` -- the area's decade-start number, e.g. `10`
    """
    return split_area_ref(text, domain=domain)[1]


def parse_area_ref_is_area(text, domain=None):
    """
    *decide whether a reference points at an area rather than a category*

    Area decades are always multiples of ten (`A10-19`, `A20-29`, ...), and
    the `X0` slot inside each decade is reserved, so category numbers never
    are. That makes a two-digit reference unambiguous.

    **Key Arguments:**

    - ``text`` -- the raw reference supplied on the command-line
    - ``domain`` -- a domain the reference must belong to, or `None` to accept any. Default `None`.

    **Return:**

    - ``isArea`` -- `True` if the reference names an area, `False` if a category

    **Usage:**

    ```python
    from aardvark_jd import codes
    isArea = codes.parse_area_ref_is_area("A10")
    ```
    """
    text = str(text).strip()
    match = _AREA_REF_RE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not a valid area or category reference - expected a domain letter "
            f"prefix, e.g. 'A10-19', 'R10' or 'P11'"
        )
    _check_domain_matches(text, match.group(1).upper(), domain)
    if match.group(3) is not None:
        return True
    return int(match.group(2)) % 10 == 0


def parse_category_ref(text, domain=None):
    """
    *parse a user-supplied category reference into its AC number*

    **Key Arguments:**

    - ``text`` -- the raw category reference supplied on the command-line
    - ``domain`` -- a domain the reference must belong to, or `None` to accept any. Default `None`.

    **Return:**

    - ``acNumber`` -- the category's 2-digit AC number, e.g. `11`
    """
    return split_category_ref(text, domain=domain)[1]


def format_area_code(domain, decadeStart, decadeEnd):
    """
    *format the display code for a Johnny Decimal area, e.g. `A10-19`*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`
    - ``decadeStart`` -- the area's decade-start number
    - ``decadeEnd`` -- the area's decade-end number

    **Return:**

    - ``code`` -- the formatted area code
    """
    return f"{domain_letter(domain)}{decadeStart:02d}-{decadeEnd:02d}"


def format_category_code(domain, acNumber):
    """
    *format the display code for a Johnny Decimal category, e.g. `A11`*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`
    - ``acNumber`` -- the category's 2-digit AC number

    **Return:**

    - ``code`` -- the formatted category code
    """
    return f"{domain_letter(domain)}{acNumber:02d}"


def format_id_code(domain, acNumber, itemNumber):
    """
    *format the display code for a Johnny Decimal ID, e.g. `A11.01`*

    **Key Arguments:**

    - ``domain`` -- `areas`, `resources` or `projects`
    - ``acNumber`` -- the parent category's 2-digit AC number
    - ``itemNumber`` -- the ID's 2-digit item number

    **Return:**

    - ``code`` -- the formatted ID code
    """
    return f"{domain_letter(domain)}{acNumber:02d}.{itemNumber:02d}"

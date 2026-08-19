#!/usr/bin/env python
# encoding: utf-8
"""
*Johnny Decimal numbering, folder-name construction and folder creation*

Author
: David Young
"""

import os
import re

from aardvark_jd import codes, db

MAX_DECADE_START = 90
MAX_ITEM_NUMBER = 99
MIN_ITEM_NUMBER = 10

_WHITESPACE_RE = re.compile(r"\s+")
# THE LEADING `<LETTER><DECADE_START>_<DECADE_END>_` OF AN AREA FOLDER NAME, WHOSE
# FIRST UNDERSCORE IS A RANGE SEPARATOR RATHER THAN A WORD GAP. THE PERIOD AFTER
# THE LETTER IS OPTIONAL SO OLDER `A.10_19_` NAMES STILL RENDER CORRECTLY TOO.
_DECADE_RANGE_RE = re.compile(r"^([A-Z]\.?)?(\d{2})_(\d{2})_")


def slugify(title):
    """
    *lowercase a title and collapse whitespace to underscores, for on-disk names*

    **Key Arguments:**

    - ``title`` -- the title to slugify

    **Return:**

    - ``slug`` -- the lowercased, underscore-joined title
    """
    return _WHITESPACE_RE.sub("_", title.strip().lower())


def display_name(folderName):
    """
    *render an on-disk folder name for display, swapping underscores for spaces*

    Used to mirror the filesystem's folder names into craft.do. The emoji
    suffix is left exactly as-is, so the name carries its own icon - Craft's
    API has no folder icon/emoji field of its own. An area's leading
    `<letter><start>_<end>_` keeps its decade range readable as a hyphen
    (`A10_19_health` -> `A10-19 health`) rather than degrading to an
    ambiguous `A10 19 health`.

    **Key Arguments:**

    - ``folderName`` -- the exact on-disk folder name, e.g. `"A10_19_health🏥"`

    **Return:**

    - ``displayName`` -- the name with underscores rendered as spaces, e.g. `"A10-19 health🏥"`

    **Usage:**

        displayName = folders.display_name("A10_19_health🏥")
    """
    return _DECADE_RANGE_RE.sub(r"\1\2-\3 ", folderName).replace("_", " ")


class DomainExhaustedError(Exception):
    pass


class CategoryExhaustedError(Exception):
    pass


class IdExhaustedError(Exception):
    pass


def next_area_decade(dbConn, domain):
    """
    *work out the next available decade-start number for a new area*

    Decade `00-09` is reserved for the domain's `00_09_system` folder, so
    usable decades run `10-19` through `90-99`.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`

    **Return:**

    - ``decadeStart``, ``decadeEnd`` -- the next available decade's bounds
    """
    existing = [row["decade_start"] for row in db.list_areas(dbConn, domain)]
    candidate = 10 if not existing else max(existing) + 10
    if candidate > MAX_DECADE_START:
        raise DomainExhaustedError(
            f"no more decades available for '{domain}' "
            f"(00-09 reserved for system; max 9 areas: 10-19..90-99)"
        )
    return candidate, candidate + 9


def next_category_number(dbConn, domain, area):
    """
    *work out the next available AC number for a new category within an area*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``area`` -- the parent `areas` row

    **Return:**

    - ``acNumber`` -- the next available category number
    """
    existing = [
        row["ac_number"]
        for row in db.list_categories(dbConn, domain, areaId=area["area_id"])
    ]
    # THE X0 NUMBER IN EACH DECADE IS RESERVED (MIRRORS 00-09 BEING RESERVED
    # FOR THE SYSTEM FOLDER AT THE AREA LEVEL), SO CATEGORIES RUN X1..X9
    candidate = area["decade_start"] + 1 if not existing else max(existing) + 1
    if candidate > area["decade_end"]:
        raise CategoryExhaustedError(
            f"no more category numbers available in area "
            f"{area['decade_start']}-{area['decade_end']} (max 9 categories per area)"
        )
    return candidate


def next_id_number(dbConn, domain, category):
    """
    *work out the next available item number for a new ID within a category*

    Item numbers `00`-`09` are reserved for the category's ten system IDs
    (index, inbox, llm, ...), created alongside the category itself, so
    user-created IDs start at `10`.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``category`` -- the parent `categories` row

    **Return:**

    - ``itemNumber`` -- the next available item number
    """
    existing = [
        row["item_number"]
        for row in db.list_ids(dbConn, domain, category["category_id"])
    ]
    candidate = MIN_ITEM_NUMBER if not existing else max(existing) + 1
    if candidate > MAX_ITEM_NUMBER:
        raise IdExhaustedError(
            f"no more ID numbers available in category {category['ac_number']:02d} "
            f"(max {MAX_ITEM_NUMBER} items per category)"
        )
    return candidate


def area_folder_name(domain, decadeStart, decadeEnd, title, emoji):
    """
    *build an area folder's on-disk name, e.g. `A10_19_health🏥`*

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`
    - ``decadeStart`` -- the area's decade-start number
    - ``decadeEnd`` -- the area's decade-end number
    - ``title`` -- the area's title
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the area folder's on-disk name
    """
    letter = codes.domain_letter(domain)
    return f"{letter}{decadeStart:02d}_{decadeEnd:02d}_{slugify(title)}{emoji}"


def category_folder_name(domain, acNumber, title, emoji):
    """
    *build a category folder's on-disk name, e.g. `A11_doctors🩺`*

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the category's 2-digit AC number
    - ``title`` -- the category's title
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the category folder's on-disk name
    """
    letter = codes.domain_letter(domain)
    return f"{letter}{acNumber:02d}_{slugify(title)}{emoji}"


def id_folder_name(domain, acNumber, itemNumber, title, emoji=""):
    """
    *build an ID folder's on-disk name, e.g. `A11.10_cardiologist`*

    Ordinary IDs are never emoji-suffixed. The ten reserved system IDs
    (`.00`-`.09`) created alongside every category are the one exception,
    and pass their emoji explicitly.

    **Key Arguments:**

    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the parent category's 2-digit AC number
    - ``itemNumber`` -- the ID's 2-digit item number
    - ``title`` -- the ID's title
    - ``emoji`` -- the emoji to append, for reserved system IDs only. Default `""`.

    **Return:**

    - ``folderName`` -- the ID folder's on-disk name
    """
    letter = codes.domain_letter(domain)
    return f"{letter}{acNumber:02d}.{itemNumber:02d}_{slugify(title)}{emoji}"


def project_folder_name(title, emoji):
    """
    *build a project folder's on-disk name (not Johnny-Decimal coded)*

    **Key Arguments:**

    - ``title`` -- the project's title
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the project folder's on-disk name
    """
    return f"{title}{emoji}"


def system_folder_name(baseName, emoji):
    """
    *build a static system-skeleton folder's on-disk name*

    **Key Arguments:**

    - ``baseName`` -- the folder's base name, e.g. `"02_PROJECTS"`
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the system folder's on-disk name
    """
    return f"{baseName}{emoji}"


def make_folder(parentPath, folderName):
    """
    *create a folder on disk, tolerating it already existing*

    **Key Arguments:**

    - ``parentPath`` -- the parent directory's path
    - ``folderName`` -- the folder's name

    **Return:**

    - ``folderPath`` -- the created folder's absolute path
    """
    folderPath = f"{parentPath}/{folderName}"
    os.makedirs(folderPath, exist_ok=True)
    return folderPath


def create_reserved_system_ids(dbConn, domain, acNumber, containingFolderPath):
    """
    *create any of the ten reserved system IDs (`.00`-`.09`) missing inside a category or area-system folder*

    Reuses the same names/emoji as the static `00_09_system` subfolders
    (`paths.SYSTEM_SUBFOLDERS`) - the one exception to ordinary IDs never
    carrying an emoji. Shared by `add_category` (a user category),
    `add_area` (the area's own reserved system folder, whose `acNumber`
    is its decade-start) and `repair_emoji`'s backfill for both - skipping
    any id already recorded makes it safe to call both right after
    creation and again later as a backfill.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the containing category's 2-digit AC number, or an area's decade-start
    - ``containingFolderPath`` -- the containing folder's absolute path
    """
    from aardvark_jd import paths

    for itemNumber, (baseName, title, _description, folderEmoji, _craftKind) in enumerate(paths.SYSTEM_SUBFOLDERS):
        folderKey = f"{domain}.{acNumber}.{baseName}"
        if db.get_system_folder(dbConn, folderKey) is not None:
            continue
        folderName = id_folder_name(domain, acNumber, itemNumber, title, emoji=folderEmoji)
        folderPath = make_folder(containingFolderPath, folderName)
        db.insert_system_folder(dbConn, folderKey, folderName, folderPath)

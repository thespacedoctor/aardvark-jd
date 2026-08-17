#!/usr/bin/env python
# encoding: utf-8
"""
*Johnny Decimal numbering, folder-name construction and folder creation*

Author
: David Young
"""

import os

from aardvark import db

MAX_DECADE_START = 90
MAX_ITEM_NUMBER = 99


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
    candidate = 1 if not existing else max(existing) + 1
    if candidate > MAX_ITEM_NUMBER:
        raise IdExhaustedError(
            f"no more ID numbers available in category {category['ac_number']:02d} "
            f"(max {MAX_ITEM_NUMBER} items per category)"
        )
    return candidate


def area_folder_name(decadeStart, decadeEnd, title, emoji):
    """
    *build an area folder's on-disk name*

    **Key Arguments:**

    - ``decadeStart`` -- the area's decade-start number
    - ``decadeEnd`` -- the area's decade-end number
    - ``title`` -- the area's title
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the area folder's on-disk name
    """
    return f"{decadeStart:02d}-{decadeEnd:02d} {title} {emoji}"


def category_folder_name(acNumber, title, emoji):
    """
    *build a category folder's on-disk name*

    **Key Arguments:**

    - ``acNumber`` -- the category's 2-digit AC number
    - ``title`` -- the category's title
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the category folder's on-disk name
    """
    return f"{acNumber:02d} {title} {emoji}"


def id_folder_name(acNumber, itemNumber, title):
    """
    *build an ID folder's on-disk name (never emoji-suffixed)*

    **Key Arguments:**

    - ``acNumber`` -- the parent category's 2-digit AC number
    - ``itemNumber`` -- the ID's 2-digit item number
    - ``title`` -- the ID's title

    **Return:**

    - ``folderName`` -- the ID folder's on-disk name
    """
    return f"{acNumber:02d}.{itemNumber:02d} {title}"


def project_folder_name(title, emoji):
    """
    *build a project folder's on-disk name (not Johnny-Decimal coded)*

    **Key Arguments:**

    - ``title`` -- the project's title
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the project folder's on-disk name
    """
    return f"{title} {emoji}"


def system_folder_name(baseName, emoji):
    """
    *build a static system-skeleton folder's on-disk name*

    **Key Arguments:**

    - ``baseName`` -- the folder's base name, e.g. `"P.ROJECTS"`
    - ``emoji`` -- the emoji to append

    **Return:**

    - ``folderName`` -- the system folder's on-disk name
    """
    return f"{baseName} {emoji}"


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

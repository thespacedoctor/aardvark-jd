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


def _lowest_free(existing, start, stop, step=1):
    """
    *the lowest unused slot in `range(start, stop + 1, step)`, or `None` if every slot is taken*

    Allocation used to be a high-water mark (`max(existing) + step`), which
    was indistinguishable from this while nothing could ever be removed
    from the index. `archive` changes that: retiring an entity is supposed
    to hand its Johnny Decimal number back, and a high-water mark would
    step straight over the gap it leaves. Scanning for the lowest free slot
    is what actually makes the number reusable.

    **Key Arguments:**

    - ``existing`` -- the numbers already in use
    - ``start`` -- the first allocatable number
    - ``stop`` -- the last allocatable number, inclusive
    - ``step`` -- the gap between allocatable numbers. Default *1*.

    **Return:**

    - ``candidate`` -- the lowest free number, or `None` if the range is exhausted
    """
    taken = set(existing)
    for candidate in range(start, stop + 1, step):
        if candidate not in taken:
            return candidate
    return None


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
    candidate = _lowest_free(existing, 10, MAX_DECADE_START, step=10)
    if candidate is None:
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
    candidate = _lowest_free(existing, area["decade_start"] + 1, area["decade_end"])
    if candidate is None:
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
    candidate = _lowest_free(existing, MIN_ITEM_NUMBER, MAX_ITEM_NUMBER)
    if candidate is None:
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


def move_folder_and_reindex(dbConn, oldFolderPath, newFolderPath, updateRows):
    """
    *move a folder anywhere on disk and repoint the index at it, atomically*

    The general form of `set_emoji.rename_folder_and_reindex`, which can
    only rename a folder in place. Archiving has to move a folder to a
    different parent entirely, so the destination is given outright here
    rather than derived from the source's parent.

    The database write is committed **before** the move, for the reason
    `set_emoji.rename_folder_and_reindex` documents at length: `00_INDEX`
    holds the open SQLite file, and committing after a rename that has
    already moved that directory away fails to unlink the rollback
    journal. If the move then fails, the old values are written back and
    committed again before re-raising, so the index and the filesystem
    never disagree for longer than the compensating write takes.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``oldFolderPath`` -- the folder's current absolute path
    - ``newFolderPath`` -- the folder's new absolute path, parent included
    - ``updateRows`` -- a callable taking `(newFolderName, newFolderPath)` that writes the target row(s), without committing

    **Return:**

    - ``newFolderPath`` -- the folder's new absolute path

    **Usage:**

    ```python
    from aardvark_jd.folders import move_folder_and_reindex
    newPath = move_folder_and_reindex(
        dbConn, oldPath, f"{archiveFolder}/A11.10_cardiologist__archived_20260820",
        lambda name, path: db.update_id_name(dbConn, idId, name, path),
    )
    ```
    """
    import errno
    import shutil

    oldFolderPath = oldFolderPath.rstrip("/")
    newFolderPath = newFolderPath.rstrip("/")
    if newFolderPath == oldFolderPath:
        return newFolderPath

    # ON A CASE-INSENSITIVE FILESYSTEM A PURELY COSMETIC RENAME MAKES
    # `os.path.exists` TRUE AGAINST THE SOURCE ITSELF - `samefile` TELLS
    # THAT APART FROM A GENUINE COLLISION. SEE `rename_folder_and_reindex`.
    if os.path.exists(newFolderPath):
        try:
            isTheSameFolder = os.path.samefile(newFolderPath, oldFolderPath)
        except OSError:
            isTheSameFolder = False
        if not isTheSameFolder:
            raise ValueError(f"'{newFolderPath}' already exists - refusing to overwrite it")
    if not os.path.isdir(oldFolderPath):
        raise ValueError(f"'{oldFolderPath}' is not on disk - the index is out of step with the filesystem")

    oldFolderName = os.path.basename(oldFolderPath)
    newFolderName = os.path.basename(newFolderPath)
    os.makedirs(os.path.dirname(newFolderPath), exist_ok=True)

    try:
        updateRows(newFolderName, newFolderPath)
        db.rewrite_folder_path_prefix(dbConn, oldFolderPath, newFolderPath)
        dbConn.commit()
    except Exception:
        dbConn.rollback()
        raise

    try:
        try:
            os.rename(oldFolderPath, newFolderPath)
        except OSError as error:
            # A MOVE ACROSS FILESYSTEMS CANNOT BE A RENAME - COPY IT INSTEAD.
            if error.errno != errno.EXDEV:
                raise
            shutil.move(oldFolderPath, newFolderPath)
    except Exception:
        updateRows(oldFolderName, oldFolderPath)
        db.rewrite_folder_path_prefix(dbConn, newFolderPath, oldFolderPath)
        dbConn.commit()
        raise

    return newFolderPath

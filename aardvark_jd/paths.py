#!/usr/bin/env python
# encoding: utf-8
"""
*Static folder layout for the aardvark root, and path resolution against `system_folders`*

Author
: David Young
"""

import os

from aardvark_jd import codes, db, folders

DB_BASENAME = "aardvark.db"
_ROOT_INDEX_PREFIX = "00_index"

# THE STATIC SKELETON IS A FIXED, KNOWN LIST, SO ITS EMOJI ARE DECLARED HERE
# RATHER THAN GUESSED - KEYWORD SEARCH GOT 11 OF THESE 14 TITLES WRONG.
# ORDERED DESCRIPTION OF EVERY STATIC FOLDER `init` MUST CREATE.
# EACH ENTRY: (folderKey, parentKey or None, baseName, title, description, emoji)
# ROOT-LEVEL BASE NAMES CARRY A TWO-DIGIT PREFIX, MATCHING THE CONVENTION
# ALREADY USED INSIDE EACH 00_09_system FOLDER BELOW (05-08 RESERVED/UNUSED).
SYSTEM_SKELETON = [
    ("root.index", None, "00_INDEX", "Index", "The aardvark database and system index", "🗂️"),
    ("root.inbox", None, "01_INBOX", "Inbox", "Unsorted items awaiting filing", "📥"),
    ("root.projects", None, "02_PROJECTS", "Projects", "Active and future projects", "🚀"),
    ("root.areas", None, "03_AREAS", "Areas", "Ongoing areas of responsibility", "🧭"),
    ("root.resources", None, "04_RESOURCES", "Resources", "Reference material and resources", "📚"),
    ("root.archive", None, "09_ARCHIVE", "Archive", "Inactive material kept for reference", "🗄️"),
]

# THE CRAFT "KIND" A SYSTEM SUBFOLDER MIRRORS AS - CRAFT HAS NO NOTION OF
# "FOLDER OF LOOSE FILES" VS "SINGLE NOTE", SO THIS IS A CALL ABOUT WHAT
# EACH ONE IS FOR: SOMEWHERE TO FILE THINGS (FOLDER) VS SOMEWHERE TO WRITE
# CONTENT DIRECTLY (DOCUMENT). ONLY USED BY `craft_sync.py`'S MIRROR - THE
# ON-DISK FOLDER IS CREATED THE SAME WAY EITHER WAY.
SYSTEM_SUBFOLDER_KIND_DOCUMENT = "document"
SYSTEM_SUBFOLDER_KIND_FOLDER = "folder"

# THE 10 SYSTEM SUBFOLDERS REPEATED UNDER PROJECTS, AREAS AND RESOURCES, AND
# REUSED VERBATIM (NAMES/EMOJI) FOR THE 10 RESERVED SYSTEM IDS `add_category`
# CREATES ALONGSIDE EVERY NEW CATEGORY (SEE `add_category.py`).
# EACH ENTRY: (baseName, title, description, emoji, craftKind)
SYSTEM_SUBFOLDERS = [
    ("00_index", "Index", "The index for this section", "🗂️", SYSTEM_SUBFOLDER_KIND_DOCUMENT),
    ("01_inbox", "Inbox", "Unsorted items awaiting filing", "📥", SYSTEM_SUBFOLDER_KIND_FOLDER),
    ("02_llm", "LLM", "LLM prompts, context and output", "🤖", SYSTEM_SUBFOLDER_KIND_DOCUMENT),
    ("03_checklists", "Checklists", "Checklists", "☑️", SYSTEM_SUBFOLDER_KIND_FOLDER),
    ("04_templates", "Templates", "Templates", "📐", SYSTEM_SUBFOLDER_KIND_FOLDER),
    ("05_links", "Links", "Links", "🔗", SYSTEM_SUBFOLDER_KIND_DOCUMENT),
    ("06_bin", "Bin", "Scripts and executables for this section", "📜", SYSTEM_SUBFOLDER_KIND_DOCUMENT),
    ("07_settings", "Settings", "Settings", "🎛️", SYSTEM_SUBFOLDER_KIND_DOCUMENT),
    ("08_someday", "Someday", "Someday / maybe items", "💭", SYSTEM_SUBFOLDER_KIND_FOLDER),
    ("09_archive", "Archive", "Inactive material kept for reference", "🗄️", SYSTEM_SUBFOLDER_KIND_FOLDER),
]

SYSTEM_FOLDER_EMOJI = "⚙️"


def _append_system_subfolders(skeleton):
    """
    *append the `00_09_system` folder + its 10 subfolders under each of projects/areas/resources*

    Under `areas`/`resources` this domain-level system folder and its
    subfolders are rendered onto the same `<X>` naming convention as
    Johnny Decimal areas/categories (e.g. `A00_09_system⚙️`,
    `A00_index🗂️`), since they occupy the reserved `00-09` decade/category
    slots exactly as if they were one. Under `projects` - which isn't
    Johnny-Decimal coded - the plain base name is kept as-is. Folder
    *keys* (`f"{sectionKey}.system.{baseName}"`) always use the original,
    un-prefixed `baseName`, regardless of domain, so they stay stable
    across this rendering change and existing `system_folders` rows keep
    resolving.

    **Key Arguments:**

    - ``skeleton`` -- the `SYSTEM_SKELETON` list to append to
    """
    for sectionKey in ("projects", "areas", "resources"):
        domainLetter = codes.DOMAIN_LETTER.get(sectionKey)
        systemKey = f"{sectionKey}.system"
        systemBaseName = f"{domainLetter}00_09_system" if domainLetter else "00_09_system"
        skeleton.append(
            (
                systemKey, f"root.{sectionKey}", systemBaseName, "System",
                "Johnny Decimal system folder (00-09)", SYSTEM_FOLDER_EMOJI,
            )
        )
        for acNumber, (baseName, title, description, folderEmoji, _craftKind) in enumerate(SYSTEM_SUBFOLDERS):
            renderedBaseName = (
                f"{domainLetter}{acNumber:02d}_{folders.slugify(title)}" if domainLetter else baseName
            )
            skeleton.append(
                (f"{sectionKey}.system.{baseName}", systemKey, renderedBaseName, title, description, folderEmoji)
            )


_append_system_subfolders(SYSTEM_SKELETON)


def skeleton_entry(folderKey):
    """
    *look up a static skeleton entry by its logical folder key*

    **Key Arguments:**

    - ``folderKey`` -- the logical folder key, e.g. `"root.areas"`

    **Return:**

    - ``entry`` -- the matching `SYSTEM_SKELETON` tuple

    **Usage:**

    ```python
    from aardvark_jd import paths
    folderKey, parentKey, baseName, title, description, folderEmoji = paths.skeleton_entry("root.areas")
    ```
    """
    for entry in SYSTEM_SKELETON:
        if entry[0] == folderKey:
            return entry
    raise KeyError(f"'{folderKey}' is not a static skeleton folder key")


def get_db_path_in_folder(indexFolderPath):
    """
    *the path to `aardvark.db` inside an already-resolved index folder*

    **Key Arguments:**

    - ``indexFolderPath`` -- the root's `00_INDEX` folder path (emoji-suffixed)

    **Return:**

    - ``pathToDb`` -- the path to `aardvark.db`
    """
    return f"{indexFolderPath}/{DB_BASENAME}"


def find_db_path(rootPath):
    """
    *locate `aardvark.db` under a root whose `00_INDEX` folder name (and emoji) is not yet known*

    The `00_INDEX` folder is the one static folder that must be locatable
    before any database connection exists, so it is found by scanning the
    root for a directory whose name starts with `00_index`, case-insensitive,
    rather than via `system_folders` (which lives inside the database
    itself). Matching case-insensitively - rather than a single literal
    prefix - means this still finds a system created before the folder was
    renumbered to `00_INDEX`, which is exactly the system `repair_emoji`
    needs to be able to open in order to fix.

    **Key Arguments:**

    - ``rootPath`` -- the aardvark system root path

    **Return:**

    - ``pathToDb`` -- the path to `aardvark.db`
    """
    matches = sorted(
        entry.path for entry in os.scandir(rootPath)
        if entry.is_dir() and entry.name.lower().startswith(_ROOT_INDEX_PREFIX)
    )
    if not matches:
        raise FileNotFoundError(f"no '00_INDEX' folder found under '{rootPath}'")
    return get_db_path_in_folder(matches[0])


def resolve(dbConn, folderKey):
    """
    *resolve a logical folder key to its exact on-disk path*

    Reads the `system_folders` table rather than reconstructing
    emoji-suffixed names, so callers never need to guess an emoji.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``folderKey`` -- the logical folder key, e.g. `"projects.system.04_templates"`

    **Return:**

    - ``folderPath`` -- the folder's absolute path
    """
    row = db.get_system_folder(dbConn, folderKey)
    if row is None:
        raise KeyError(f"no system folder is recorded for key '{folderKey}'")
    return row["folder_path"]

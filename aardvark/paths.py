#!/usr/bin/env python
# encoding: utf-8
"""
*Static folder layout for the aardvark root, and path resolution against `system_folders`*

Author
: David Young
"""

from aardvark import db

DB_RELATIVE_PATH = "00_index/aardvark.db"

# ORDERED DESCRIPTION OF EVERY STATIC FOLDER `init` MUST CREATE.
# EACH ENTRY: (folderKey, parentKey or None, baseName, title, description)
SYSTEM_SKELETON = [
    ("root.index", None, "00_index", "Index", "The aardvark database and system index"),
    ("root.inbox", None, "01_inbox", "Inbox", "Unsorted items awaiting filing"),
    ("root.projects", None, "P.ROJECTS", "Projects", "Active and future projects"),
    ("root.areas", None, "A.REAS", "Areas", "Ongoing areas of responsibility"),
    ("root.resources", None, "R.ESOURCES", "Resources", "Reference material and resources"),
    ("root.archive", None, "09_archive", "Archive", "Inactive material kept for reference"),
]

# THE 10 SYSTEM SUBFOLDERS REPEATED UNDER PROJECTS, AREAS AND RESOURCES
_SYSTEM_SUBFOLDERS = [
    ("00_index", "Index", "The index for this section"),
    ("01_inbox", "Inbox", "Unsorted items awaiting filing"),
    ("02_llm", "LLM", "LLM prompts, context and output"),
    ("03_checklists", "Checklists", "Checklists"),
    ("04_templates", "Templates", "Templates"),
    ("05_links", "Links", "Links"),
    ("06_bin", "Bin", "Items pending deletion"),
    ("07_settings", "Settings", "Settings"),
    ("08_someday", "Someday", "Someday / maybe items"),
    ("09_archive", "Archive", "Inactive material kept for reference"),
]

def _append_system_subfolders(skeleton):
    """
    *append the `00_09_system` folder + its 10 subfolders under each of projects/areas/resources*

    **Key Arguments:**

    - ``skeleton`` -- the `SYSTEM_SKELETON` list to append to
    """
    for sectionKey in ("projects", "areas", "resources"):
        systemKey = f"{sectionKey}.system"
        skeleton.append(
            (systemKey, f"root.{sectionKey}", "00_09_system", "System", "Johnny Decimal system folder (00-09)")
        )
        for baseName, title, description in _SYSTEM_SUBFOLDERS:
            skeleton.append((f"{sectionKey}.system.{baseName}", systemKey, baseName, title, description))


_append_system_subfolders(SYSTEM_SKELETON)


def get_db_path(rootPath):
    """
    *the path to `aardvark.db` under a given root*

    **Key Arguments:**

    - ``rootPath`` -- the aardvark system root path

    **Return:**

    - ``pathToDb`` -- the path to `aardvark.db`
    """
    return f"{rootPath}/{DB_RELATIVE_PATH}"


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

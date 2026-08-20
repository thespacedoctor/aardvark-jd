#!/usr/bin/env python
# encoding: utf-8
"""
*Resolve an arbitrary filesystem path back to the aardvark entity that owns it*

The reverse of `paths.resolve` - every `system_folders`/`areas`/
`categories`/`ids` row already stores its absolute `folder_path`, but
nothing previously walked that set backwards from a path. Used by
`open_craft.open_craft` to answer "what am I standing in", and by
`dropbox_client.to_dropbox_path`'s shared prefix-matching logic.

Author
: David Young
"""

import os

from aardvark_jd import db


def _normalise(path):
    """
    *resolve a path to its canonical, symlink-free, case-folded form*

    Case-folding matters here specifically because the live settings file
    on this machine records `/Users/Dave/Dropbox/aardvark` while the shell
    reports `/Users/dave/...` - macOS's default case-insensitive
    filesystem makes both work for file access, but a naive case-sensitive
    string-prefix match between the two would silently never match.

    **Key Arguments:**

    - ``path`` -- the path to normalise

    **Return:**

    - ``normalised`` -- the resolved, lower-cased path
    """
    return os.path.realpath(os.path.expanduser(path)).lower()


def _is_prefix(candidatePath, targetPath):
    """
    *check whether `candidatePath` contains `targetPath`, on a path-segment boundary*

    A plain string prefix check would let `.../A11_doctors` match
    `.../A11_doctors_old` - comparing on `os.sep`-bounded segments instead
    means a folder only matches its own subtree.

    **Key Arguments:**

    - ``candidatePath`` -- a normalised candidate folder path
    - ``targetPath`` -- the normalised path being resolved

    **Return:**

    - ``matches`` -- `True` if `targetPath` is `candidatePath` itself or lies under it
    """
    return targetPath == candidatePath or targetPath.startswith(candidatePath + os.sep)


def entity_for_path(dbConn, somePath, rootPath=None):
    """
    *resolve a filesystem path to the deepest aardvark entity that contains it*

    The system root itself carries no `system_folders` row of its own -
    only its six children (`root.inbox`, `root.areas`, ...) do - so
    standing directly in the root would otherwise never resolve. Passing
    `rootPath` (`settings["system"]["root_path"]`) adds it as the
    shallowest possible candidate, resolving to the space-root "00 Index"
    document `craft_sync._refresh_space_index` maintains
    (`craft_links` type `"space:index"`, key `"root"`).

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``somePath`` -- the path to resolve, e.g. the current working directory
    - ``rootPath`` -- the aardvark system root path, if available. Default `None`.

    **Return:**

    - ``entityType`` -- `'id'`, `'category'`, `'area'`, `'system_folder'` or `'space:index'`
    - ``entityKey`` -- the entity's `craft_links.entity_key`
    - ``folderPath`` -- the matched entity's own absolute folder path
    - ``label`` -- the matched entity's title/name, for display

    **Usage:**

    ```python
    from aardvark_jd import locate
    entityType, entityKey, folderPath, label = locate.entity_for_path(dbConn, os.getcwd(), rootPath=rootPath)
    ```
    """
    targetPath = _normalise(somePath)

    candidates = list(db.entity_rows_for_path_prefix(dbConn))
    if rootPath:
        candidates.append(("space:index", "root", rootPath))

    bestMatch = None
    bestDepth = -1
    for entityType, entityKey, folderPath in candidates:
        candidatePath = _normalise(folderPath)
        if not _is_prefix(candidatePath, targetPath):
            continue
        depth = candidatePath.count(os.sep)
        if depth > bestDepth:
            bestDepth = depth
            bestMatch = (entityType, entityKey, folderPath)

    if bestMatch is None:
        raise ValueError(f"'{somePath}' is not inside the aardvark system")

    entityType, entityKey, folderPath = bestMatch
    label = _label_for(dbConn, entityType, entityKey)
    return entityType, entityKey, folderPath, label


def _label_for(dbConn, entityType, entityKey):
    """
    *look up the display title/name for a matched entity*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``entityType`` -- `'id'`, `'category'`, `'area'`, `'system_folder'` or `'space:index'`
    - ``entityKey`` -- the entity's key

    **Return:**

    - ``label`` -- the entity's title (or folder name, for a system folder; or "Index", for the space root)
    """
    if entityType == "space:index":
        return "Index"
    if entityType == "system_folder":
        row = db.get_system_folder(dbConn, entityKey)
        return row["folder_name"] if row else entityKey
    tableName = {"id": "ids", "category": "categories", "area": "areas"}[entityType]
    idColumn = {"id": "id_id", "category": "category_id", "area": "area_id"}[entityType]
    row = dbConn.execute(f"SELECT title FROM {tableName} WHERE {idColumn} = ?", (entityKey,)).fetchone()
    return row["title"] if row else entityKey

#!/usr/bin/env python
# encoding: utf-8
"""
*Change the emoji on an existing area, category, project or system folder*

Author
: David Young
"""

import os

from aardvark_jd import codes, db, emoji_picker, folders, paths

SYSTEM_DOMAIN = "system"
PROJECTS_DOMAIN = "projects"
SET_EMOJI_DOMAINS = codes.DOMAINS + (PROJECTS_DOMAIN, SYSTEM_DOMAIN)


def rename_folder_and_reindex(dbConn, oldFolderPath, newFolderName, updateRow):
    """
    *rename a folder on disk and repoint the index at it, atomically*

    The rename and every database write land together: the folder is moved
    first, and if any of the index work then fails the move is undone before
    the error propagates. Renaming a folder invalidates the stored
    `folder_path` of everything nested inside it, so descendants are
    rewritten in the same transaction as the target row itself.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``oldFolderPath`` -- the folder's current absolute path
    - ``newFolderName`` -- the folder's new on-disk name
    - ``updateRow`` -- a callable taking `(newFolderName, newFolderPath)` that writes the target row, without committing

    **Return:**

    - ``newFolderPath`` -- the folder's new absolute path

    **Usage:**

    ```python
    from aardvark_jd.set_emoji import rename_folder_and_reindex
    newPath = rename_folder_and_reindex(
        dbConn, oldPath, "10-19 Health 🏥",
        lambda name, path: db.update_area_emoji(dbConn, areaId, "🏥", name, path),
    )
    ```
    """
    parentPath = os.path.dirname(oldFolderPath.rstrip("/"))
    newFolderPath = f"{parentPath}/{newFolderName}"

    if newFolderPath == oldFolderPath:
        return newFolderPath

    if os.path.exists(newFolderPath):
        raise ValueError(f"'{newFolderPath}' already exists - refusing to overwrite it")
    if not os.path.isdir(oldFolderPath):
        raise ValueError(f"'{oldFolderPath}' is not on disk - the index is out of step with the filesystem")

    os.rename(oldFolderPath, newFolderPath)
    try:
        updateRow(newFolderName, newFolderPath)
        db.rewrite_folder_path_prefix(dbConn, oldFolderPath, newFolderPath)
        dbConn.commit()
    except Exception:
        dbConn.rollback()
        os.rename(newFolderPath, oldFolderPath)
        raise

    return newFolderPath


class set_emoji(object):
    """
    *change the emoji on an existing area, category, project or static system folder*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas`, `resources`, `projects` or `system`
    - ``ref`` -- an area ref (`"10"`), category ref (`"11"`), project title, or system folder key
    - ``newEmoji`` -- the emoji to use

    **Usage:**

    ```python
    from aardvark_jd.set_emoji import set_emoji
    label, folderPath = set_emoji(
        log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥"
    ).get()
    ```
    """

    def __init__(self, log, dbConn, domain, ref, newEmoji):
        self.log = log
        self.dbConn = dbConn
        self.domain = self._validate_domain(domain)
        self.ref = ref
        self.newEmoji = emoji_picker.validate_chosen_emoji(newEmoji)

    def get(self):
        """
        *rename the target folder to carry the new emoji, and repoint the index*

        **Return:**

        - ``label`` -- a human-readable label for what was retargeted
        - ``folderPath`` -- the target folder's new absolute path
        """
        self.log.debug("starting the ``get`` method")

        if self.domain == SYSTEM_DOMAIN:
            label, folderPath = self._set_system_folder_emoji()
        elif self.domain == PROJECTS_DOMAIN:
            label, folderPath = self._set_project_emoji()
        elif codes.parse_area_ref_is_area(self.ref):
            label, folderPath = self._set_area_emoji()
        else:
            label, folderPath = self._set_category_emoji()

        self.log.debug("completed the ``get`` method")
        return label, folderPath

    def _validate_domain(self, domain):
        """
        *check the domain is one this command understands*

        **Key Arguments:**

        - ``domain`` -- the domain string supplied on the command-line

        **Return:**

        - ``domain`` -- the validated domain, unchanged
        """
        if domain not in SET_EMOJI_DOMAINS:
            raise ValueError(
                f"'{domain}' is not a valid domain for set_emoji - expected one of {SET_EMOJI_DOMAINS}"
            )
        return domain

    def _set_area_emoji(self):
        """
        *retarget an area folder*

        **Return:**

        - ``label`` -- the area's Johnny Decimal code
        - ``folderPath`` -- the area folder's new absolute path
        """
        decadeStart = codes.parse_area_ref(self.ref)
        area = db.get_area(self.dbConn, self.domain, decadeStart)
        if area is None:
            raise ValueError(f"no area '{self.ref}' found in domain '{self.domain}'")

        newFolderName = folders.area_folder_name(
            area["decade_start"], area["decade_end"], area["title"], self.newEmoji
        )
        folderPath = rename_folder_and_reindex(
            self.dbConn, area["folder_path"], newFolderName,
            lambda name, path: db.update_area_emoji(
                self.dbConn, area["area_id"], self.newEmoji, name, path
            ),
        )
        label = codes.format_area_code(self.domain, area["decade_start"], area["decade_end"])
        return label, folderPath

    def _set_category_emoji(self):
        """
        *retarget a category folder*

        **Return:**

        - ``label`` -- the category's Johnny Decimal code
        - ``folderPath`` -- the category folder's new absolute path
        """
        acNumber = codes.parse_category_ref(self.ref)
        category = db.get_category(self.dbConn, self.domain, acNumber)
        if category is None:
            raise ValueError(f"no category '{self.ref}' found in domain '{self.domain}'")

        newFolderName = folders.category_folder_name(
            category["ac_number"], category["title"], self.newEmoji
        )
        folderPath = rename_folder_and_reindex(
            self.dbConn, category["folder_path"], newFolderName,
            lambda name, path: db.update_category_emoji(
                self.dbConn, category["category_id"], self.newEmoji, name, path
            ),
        )
        label = codes.format_category_code(self.domain, category["ac_number"])
        return label, folderPath

    def _set_project_emoji(self):
        """
        *retarget a project folder*

        **Return:**

        - ``label`` -- the project's title
        - ``folderPath`` -- the project folder's new absolute path
        """
        project = db.get_project_by_title(self.dbConn, self.ref)
        if project is None:
            raise ValueError(f"no project titled '{self.ref}' found")

        newFolderName = folders.project_folder_name(project["title"], self.newEmoji)
        folderPath = rename_folder_and_reindex(
            self.dbConn, project["folder_path"], newFolderName,
            lambda name, path: db.update_project_emoji(
                self.dbConn, project["project_id"], self.newEmoji, name, path
            ),
        )
        return project["title"], folderPath

    def _set_system_folder_emoji(self):
        """
        *retarget a static system folder*

        **Return:**

        - ``label`` -- the folder's logical key
        - ``folderPath`` -- the folder's new absolute path
        """
        skeletonEntry = paths.skeleton_entry(self.ref)
        baseName = skeletonEntry[2]

        row = db.get_system_folder(self.dbConn, self.ref)
        if row is None:
            raise KeyError(f"no system folder is recorded for key '{self.ref}'")

        newFolderName = folders.system_folder_name(baseName, self.newEmoji)
        folderPath = rename_folder_and_reindex(
            self.dbConn, row["folder_path"], newFolderName,
            lambda name, path: db.update_system_folder(self.dbConn, self.ref, name, path),
        )
        return self.ref, folderPath

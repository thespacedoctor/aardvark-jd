#!/usr/bin/env python
# encoding: utf-8
"""
*Bring an existing system's folder names, emoji and reserved scaffolding into line with the current convention*

Author
: David Young
"""

from aardvark_jd import codes, db, folders, paths
from aardvark_jd.set_emoji import rename_folder_and_reindex


class repair_emoji(object):
    """
    *bring an existing system's folders into line with the current naming convention*

    Covers four things, each idempotent on its own:

    1. static system folders whose emoji has drifted from the skeleton (the
       original purpose of this command)
    2. areas/categories/ids whose on-disk name doesn't match what the
       current naming convention would produce from their stored
       title/emoji/numbers - e.g. systems created before a naming or emoji
       change
    3. areas/categories missing their reserved system scaffolding (the
       per-area `<X>.<D0>_system` folder, the per-category `.00`-`.09`
       reserved IDs) because they were created before that scaffolding
       existed
    4. (existing) `root.index` last, since it's the folder `self.dbConn`'s
       own SQLite file lives in - see `rename_folder_and_reindex`'s
       docstring

    Deepest folders are renamed first so a parent rename never invalidates
    a path a later step in the same run is still about to use.

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection

    **Usage:**

    ```python
    from aardvark_jd.repair_emoji import repair_emoji
    repaired = repair_emoji(log=log, dbConn=dbConn).get()
    ```
    """

    def __init__(self, log, dbConn):
        self.log = log
        self.dbConn = dbConn

    def get(self):
        """
        *rename every drifted folder, then backfill any missing reserved scaffolding*

        **Return:**

        - ``repaired`` -- a list of `(label, newFolderPath)` for each folder renamed
        """
        self.log.debug("starting the ``get`` method")

        repaired = []
        repaired += self._repair_ids()
        repaired += self._repair_categories()
        repaired += self._repair_areas()
        repaired += self._repair_skeleton()

        self._backfill_reserved_scaffolding()

        self.log.debug("completed the ``get`` method")
        return repaired

    def _repair_ids(self):
        """
        *rename any ID folder whose on-disk name doesn't match its stored title/numbers*

        **Return:**

        - ``repaired`` -- a list of `(label, newFolderPath)` for each ID renamed
        """
        repaired = []
        for domain in codes.DOMAINS:
            for category in db.list_categories(self.dbConn, domain):
                for idRow in db.list_ids(self.dbConn, domain, category["category_id"]):
                    expectedFolderName = folders.id_folder_name(
                        domain, idRow["ac_number"], idRow["item_number"], idRow["title"]
                    )
                    if idRow["folder_name"] == expectedFolderName:
                        continue
                    newFolderPath = rename_folder_and_reindex(
                        self.dbConn, idRow["folder_path"], expectedFolderName,
                        lambda name, path, rowId=idRow["id_id"]: db.update_id_name(self.dbConn, rowId, name, path),
                    )
                    repaired.append((f"id:{idRow['id_id']}", newFolderPath))
        return repaired

    def _repair_categories(self):
        """
        *rename any category folder whose on-disk name doesn't match its stored title/emoji/numbers*

        **Return:**

        - ``repaired`` -- a list of `(label, newFolderPath)` for each category renamed
        """
        repaired = []
        for domain in codes.DOMAINS:
            for category in db.list_categories(self.dbConn, domain):
                expectedFolderName = folders.category_folder_name(
                    domain, category["ac_number"], category["title"], category["emoji"]
                )
                if category["folder_name"] == expectedFolderName:
                    continue
                newFolderPath = rename_folder_and_reindex(
                    self.dbConn, category["folder_path"], expectedFolderName,
                    lambda name, path, catId=category["category_id"], emoji=category["emoji"]: db.update_category_emoji(
                        self.dbConn, catId, emoji, name, path
                    ),
                )
                repaired.append((f"category:{category['category_id']}", newFolderPath))
        return repaired

    def _repair_areas(self):
        """
        *rename any area folder whose on-disk name doesn't match its stored title/emoji/numbers*

        **Return:**

        - ``repaired`` -- a list of `(label, newFolderPath)` for each area renamed
        """
        repaired = []
        for domain in codes.DOMAINS:
            for area in db.list_areas(self.dbConn, domain):
                expectedFolderName = folders.area_folder_name(
                    domain, area["decade_start"], area["decade_end"], area["title"], area["emoji"]
                )
                if area["folder_name"] == expectedFolderName:
                    continue
                newFolderPath = rename_folder_and_reindex(
                    self.dbConn, area["folder_path"], expectedFolderName,
                    lambda name, path, areaId=area["area_id"], emoji=area["emoji"]: db.update_area_emoji(
                        self.dbConn, areaId, emoji, name, path
                    ),
                )
                repaired.append((f"area:{area['area_id']}", newFolderPath))
        return repaired

    def _repair_skeleton(self):
        """
        *rename any static system folder whose emoji/name has drifted from the skeleton*

        **Return:**

        - ``repaired`` -- a list of `(folderKey, newFolderPath)` for each folder renamed
        """
        # DEEPEST FIRST: RENAMING A PARENT REWRITES ITS DESCENDANTS' PATHS, SO
        # HANDLING CHILDREN FIRST KEEPS EVERY PATH THIS LOOP READS CURRENT.
        # `root.index` GOES ABSOLUTE LAST REGARDLESS OF DEPTH: IT'S THE FOLDER
        # `self.dbConn`'s OWN SQLITE FILE LIVES IN, AND ONCE IT'S RENAMED,
        # SQLITE'S CACHED PATH FOR THE MAIN DB FILE IS STALE - ANY *FURTHER*
        # WRITE ON THIS CONNECTION FAILS WITH "ATTEMPT TO WRITE A READONLY
        # DATABASE", EVEN THOUGH THE RENAME ITSELF SUCCEEDED. PROCESSING IT
        # LAST MEANS NOTHING ELSE IN THIS RUN WRITES THROUGH THE CONNECTION
        # AFTERWARDS - THE NEXT COMMAND GETS A FRESH ONE.
        skeletonByDepth = sorted(
            paths.SYSTEM_SKELETON,
            key=lambda entry: (entry[0] == "root.index", -entry[0].count(".")),
        )

        repaired = []
        for folderKey, _parentKey, baseName, _title, _description, folderEmoji in skeletonByDepth:
            row = db.get_system_folder(self.dbConn, folderKey)
            if row is None:
                self.log.warning(f"no system folder recorded for '{folderKey}' - skipping")
                continue

            expectedFolderName = folders.system_folder_name(baseName, folderEmoji)
            if row["folder_name"] == expectedFolderName:
                continue

            newFolderPath = rename_folder_and_reindex(
                self.dbConn, row["folder_path"], expectedFolderName,
                lambda name, path, key=folderKey: db.update_system_folder(self.dbConn, key, name, path),
            )
            repaired.append((folderKey, newFolderPath))
        return repaired

    def _backfill_reserved_scaffolding(self):
        """
        *create any area-level system folder or category-level reserved IDs missing from an existing system*

        Runs after every rename pass above, so it always reads each area's/
        category's current (possibly just-renamed) `folder_path`.
        """
        for domain in codes.DOMAINS:
            for area in db.list_areas(self.dbConn, domain):
                self._backfill_area_system_folder(domain, area)
            for category in db.list_categories(self.dbConn, domain):
                self._backfill_category_reserved_ids(domain, category)

    def _backfill_area_system_folder(self, domain, area):
        """
        *create an area's reserved `<X>.<D0>_system` folder if it doesn't already exist*

        **Key Arguments:**

        - ``domain`` -- `areas` or `resources`
        - ``area`` -- the `areas` row
        """
        folderKey = f"{domain}.{area['decade_start']}.system"
        if db.get_system_folder(self.dbConn, folderKey) is not None:
            return
        folderName = folders.category_folder_name(domain, area["decade_start"], "system", paths.SYSTEM_FOLDER_EMOJI)
        folderPath = folders.make_folder(area["folder_path"], folderName)
        db.insert_system_folder(self.dbConn, folderKey, folderName, folderPath)

    def _backfill_category_reserved_ids(self, domain, category):
        """
        *create any of a category's ten reserved system IDs (`.00`-`.09`) that don't already exist*

        **Key Arguments:**

        - ``domain`` -- `areas` or `resources`
        - ``category`` -- the `categories` row
        """
        for itemNumber, (baseName, title, _description, folderEmoji) in enumerate(paths.SYSTEM_SUBFOLDERS):
            folderKey = f"{domain}.{category['ac_number']}.{baseName}"
            if db.get_system_folder(self.dbConn, folderKey) is not None:
                continue
            folderName = folders.id_folder_name(domain, category["ac_number"], itemNumber, title, emoji=folderEmoji)
            folderPath = folders.make_folder(category["folder_path"], folderName)
            db.insert_system_folder(self.dbConn, folderKey, folderName, folderPath)

#!/usr/bin/env python
# encoding: utf-8
"""
*Reset every static system folder to the emoji declared for it in the skeleton*

Author
: David Young
"""

from aardvark_jd import db, folders, paths
from aardvark_jd.set_emoji import rename_folder_and_reindex


class repair_emoji(object):
    """
    *bring an existing system's static folders into line with their declared emoji*

    Systems created before the skeleton emoji were declared carry whatever
    the keyword picker guessed at the time, which for most of the 14 static
    titles was the generic folder emoji. This walks the recorded system
    folders and renames any whose emoji no longer matches the skeleton.

    Deepest folders are handled first so a parent rename never invalidates a
    path this run is still about to use, and folders are skipped when they
    already carry the right emoji, which makes the command idempotent.

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
        *rename every static folder whose emoji has drifted from the skeleton*

        **Return:**

        - ``repaired`` -- a list of `(folderKey, newFolderPath)` for each folder renamed
        """
        self.log.debug("starting the ``get`` method")

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

        self.log.debug("completed the ``get`` method")
        return repaired

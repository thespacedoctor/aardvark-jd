#!/usr/bin/env python
# encoding: utf-8
"""
*Add a new Johnny Decimal area to the Areas or Resources domain*

Author
: David Young
"""

from aardvark import codes, db, emoji_picker, folders, paths


class add_area(object):
    """
    *create a new Johnny Decimal area, auto-assigning the next available decade*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``title`` -- the area's title
    - ``description`` -- the area's description

    **Usage:**

    ```python
    from aardvark.add_area import add_area
    code, folderPath = add_area(
        log=log, dbConn=dbConn, domain="areas", title="Health", description="..."
    ).get()
    ```
    """

    def __init__(self, log, dbConn, domain, title, description):
        self.log = log
        self.dbConn = dbConn
        self.domain = codes.validate_domain(domain)
        self.title = title
        self.description = description

    def get(self):
        """
        *create the area's folder and index row*

        **Return:**

        - ``code`` -- the new area's Johnny Decimal code, e.g. `A.10-19`
        - ``folderPath`` -- the new area folder's absolute path
        """
        self.log.debug("starting the ``get`` method")

        decadeStart, decadeEnd = folders.next_area_decade(self.dbConn, self.domain)
        pickedEmoji = emoji_picker.pick_emoji(self.title, self.description)
        folderName = folders.area_folder_name(decadeStart, decadeEnd, self.title, pickedEmoji)
        parentPath = paths.resolve(self.dbConn, f"root.{self.domain}")
        folderPath = folders.make_folder(parentPath, folderName)

        db.insert_area(
            self.dbConn, self.domain, decadeStart, decadeEnd, self.title, self.description,
            pickedEmoji, folderName, folderPath,
        )
        code = codes.format_area_code(self.domain, decadeStart, decadeEnd)

        self.log.debug("completed the ``get`` method")
        return code, folderPath

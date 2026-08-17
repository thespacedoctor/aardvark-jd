#!/usr/bin/env python
# encoding: utf-8
"""
*Add a new Johnny Decimal category to an existing area*

Author
: David Young
"""

from aardvark import codes, db, emoji_picker, folders


class add_category(object):
    """
    *create a new Johnny Decimal category within an area, auto-assigning the next available AC number*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``areaRef`` -- the parent area reference, e.g. `"10"` or `"10-19"`
    - ``title`` -- the category's title
    - ``description`` -- the category's description

    **Usage:**

    ```python
    from aardvark.add_category import add_category
    code, folderPath = add_category(
        log=log, dbConn=dbConn, domain="areas", areaRef="10", title="Doctors", description="..."
    ).get()
    ```
    """

    def __init__(self, log, dbConn, domain, areaRef, title, description):
        self.log = log
        self.dbConn = dbConn
        self.domain = codes.validate_domain(domain)
        self.areaRef = areaRef
        self.title = title
        self.description = description

    def get(self):
        """
        *create the category's folder and index row*

        **Return:**

        - ``code`` -- the new category's Johnny Decimal code, e.g. `A.11`
        - ``folderPath`` -- the new category folder's absolute path
        """
        self.log.debug("starting the ``get`` method")

        decadeStart = codes.parse_area_ref(self.areaRef)
        area = db.get_area(self.dbConn, self.domain, decadeStart)
        if area is None:
            raise ValueError(f"no area '{self.areaRef}' found in domain '{self.domain}'")

        acNumber = folders.next_category_number(self.dbConn, self.domain, area)
        pickedEmoji = emoji_picker.pick_emoji(self.title, self.description)
        folderName = folders.category_folder_name(acNumber, self.title, pickedEmoji)
        folderPath = folders.make_folder(area["folder_path"], folderName)

        db.insert_category(
            self.dbConn, area["area_id"], self.domain, acNumber, self.title, self.description,
            pickedEmoji, folderName, folderPath,
        )
        code = codes.format_category_code(self.domain, acNumber)

        self.log.debug("completed the ``get`` method")
        return code, folderPath

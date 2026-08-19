#!/usr/bin/env python
# encoding: utf-8
"""
*Add a new Johnny Decimal category to an existing area*

Author
: David Young
"""

from aardvark_jd import codes, db, emoji_picker, folders


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
    - ``chosenEmoji`` -- an emoji supplied on the command-line, bypassing the suggester. Default `None`.
    - ``settings`` -- the aardvark settings dict. Default `None`.

    **Usage:**

    ```python
    from aardvark_jd.add_category import add_category
    code, folderPath = add_category(
        log=log, dbConn=dbConn, domain="areas", areaRef="10", title="Doctors", description="..."
    ).get()
    ```
    """

    def __init__(self, log, dbConn, domain, areaRef, title, description, chosenEmoji=None, settings=None):
        self.log = log
        self.dbConn = dbConn
        self.domain = codes.validate_domain(domain)
        self.areaRef = areaRef
        self.title = title
        self.description = description
        self.chosenEmoji = chosenEmoji
        self.settings = settings

    def get(self):
        """
        *create the category's folder and index row, plus its ten reserved system IDs*

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
        pickedEmoji = emoji_picker.resolve_emoji(
            self.title, self.description, chosenEmoji=self.chosenEmoji,
            settings=self.settings, log=self.log,
        )
        folderName = folders.category_folder_name(self.domain, acNumber, self.title, pickedEmoji)
        folderPath = folders.make_folder(area["folder_path"], folderName)

        db.insert_category(
            self.dbConn, area["area_id"], self.domain, acNumber, self.title, self.description,
            pickedEmoji, folderName, folderPath,
        )
        code = codes.format_category_code(self.domain, acNumber)

        folders.create_reserved_system_ids(self.dbConn, self.domain, acNumber, folderPath)

        self.log.debug("completed the ``get`` method")
        return code, folderPath

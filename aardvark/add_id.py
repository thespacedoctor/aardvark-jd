#!/usr/bin/env python
# encoding: utf-8
"""
*Add a new Johnny Decimal ID (leaf item) to an existing category*

Author
: David Young
"""

from aardvark import codes, db, folders


class add_id(object):
    """
    *create a new Johnny Decimal ID within a category, auto-assigning the next available item number*

    ID folders are never emoji-suffixed.

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``categoryRef`` -- the parent category reference, e.g. `"11"`
    - ``title`` -- the ID's title
    - ``description`` -- the ID's description

    **Usage:**

    ```python
    from aardvark.add_id import add_id
    code, folderPath = add_id(
        log=log, dbConn=dbConn, domain="areas", categoryRef="11", title="Cardiologist", description="..."
    ).get()
    ```
    """

    def __init__(self, log, dbConn, domain, categoryRef, title, description):
        self.log = log
        self.dbConn = dbConn
        self.domain = codes.validate_domain(domain)
        self.categoryRef = categoryRef
        self.title = title
        self.description = description

    def get(self):
        """
        *create the ID's folder and index row*

        **Return:**

        - ``code`` -- the new ID's Johnny Decimal code, e.g. `A.11.01`
        - ``folderPath`` -- the new ID folder's absolute path
        """
        self.log.debug("starting the ``get`` method")

        acNumber = codes.parse_category_ref(self.categoryRef)
        category = db.get_category(self.dbConn, self.domain, acNumber)
        if category is None:
            raise ValueError(f"no category '{self.categoryRef}' found in domain '{self.domain}'")

        itemNumber = folders.next_id_number(self.dbConn, self.domain, category)
        folderName = folders.id_folder_name(acNumber, itemNumber, self.title)
        folderPath = folders.make_folder(category["folder_path"], folderName)

        db.insert_id(
            self.dbConn, category["category_id"], self.domain, acNumber, itemNumber,
            self.title, self.description, folderName, folderPath,
        )
        code = codes.format_id_code(self.domain, acNumber, itemNumber)

        self.log.debug("completed the ``get`` method")
        return code, folderPath

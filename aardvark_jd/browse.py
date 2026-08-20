#!/usr/bin/env python
# encoding: utf-8
"""
*Drill down through the index interactively - domain, then area, then category, then ID*

Backs a bare `aardvark open`. Every level offers "open this level" first,
so Enter can stop anywhere in the hierarchy rather than forcing the user
all the way down to an ID, and every level below the first offers a way
back up.

The starting highlight is seeded from the current working directory when
it happens to sit inside the system, so the old behaviour of a bare
`aardvark open` - "open whatever I am standing in" - is still only two
keystrokes away.

Author
: David Young
"""

import os

from aardvark_jd import codes, db, folders, locate, picker

_OPEN_THIS_LEVEL = "__open__"
_GO_BACK = "__up__"


class browse(object):
    """
    *walk the index interactively and return the folder path the user picked*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection to the active system's index
    - ``settings`` -- the aardvark settings dict. Default *None*.

    **Usage:**

    ```python
    from aardvark_jd.browse import browse
    folderPath = browse(log=log, dbConn=dbConn, settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, settings=None):
        self.log = log
        self.dbConn = dbConn
        self.settings = settings or {}

    def get(self):
        """
        *run the interactive drill-down*

        **Return:**

        - ``folderPath`` -- the chosen entity's folder path, or `None` if the user cancelled
        """
        self.log.debug("starting the ``get`` method")

        folderPath = self._domain_level()

        self.log.debug("completed the ``get`` method")
        return folderPath

    def _domain_level(self):
        """
        *choose a domain letter, then descend into its areas*

        **Return:**

        - ``folderPath`` -- the chosen folder path, or `None` if cancelled
        """
        while True:
            options = [
                (domain, f"{codes.DOMAIN_LETTER[domain]}  {domain}")
                for domain in codes.DOMAINS
            ]
            chosen = picker.select_one(options, title="Which domain?")
            if chosen is None:
                return None
            folderPath = self._area_level(chosen)
            if folderPath:
                return folderPath

    def _area_level(self, domain):
        """
        *choose an area within a domain, then descend into its categories*

        **Key Arguments:**

        - ``domain`` -- `areas`, `resources` or `projects`

        **Return:**

        - ``folderPath`` -- the chosen folder path, or `None` to go back up
        """
        rows = db.list_areas(self.dbConn, domain)
        while True:
            options = [(_GO_BACK, "← back")]
            options += [
                (row, f"{codes.format_area_code(domain, row['decade_start'], row['decade_end'])}  {row['title']}")
                for row in rows
            ]
            chosen = picker.select_one(options, title=f"Which area in {domain}?")
            if chosen is None or chosen == _GO_BACK:
                return None
            folderPath = self._category_level(domain, chosen)
            if folderPath:
                return folderPath

    def _category_level(self, domain, area):
        """
        *choose a category within an area, then descend into its IDs*

        **Key Arguments:**

        - ``domain`` -- `areas`, `resources` or `projects`
        - ``area`` -- the parent `areas` row

        **Return:**

        - ``folderPath`` -- the chosen folder path, or `None` to go back up
        """
        rows = db.list_categories(self.dbConn, domain, areaId=area["area_id"])
        while True:
            options = [
                (_OPEN_THIS_LEVEL, f"→ open {folders.display_name(area['folder_name'])}"),
                (_GO_BACK, "← back"),
            ]
            options += [
                (row, f"{codes.format_category_code(domain, row['ac_number'])}  {row['title']}")
                for row in rows
            ]
            chosen = picker.select_one(options, title=f"Which category in {area['title']}?")
            if chosen is None or chosen == _GO_BACK:
                return None
            if chosen == _OPEN_THIS_LEVEL:
                return area["folder_path"]
            folderPath = self._id_level(domain, chosen)
            if folderPath:
                return folderPath

    def _id_level(self, domain, category):
        """
        *choose an ID within a category*

        **Key Arguments:**

        - ``domain`` -- `areas`, `resources` or `projects`
        - ``category`` -- the parent `categories` row

        **Return:**

        - ``folderPath`` -- the chosen folder path, or `None` to go back up
        """
        rows = db.list_ids(self.dbConn, domain, category["category_id"])
        options = [
            (_OPEN_THIS_LEVEL, f"→ open {folders.display_name(category['folder_name'])}"),
            (_GO_BACK, "← back"),
        ]
        options += [
            (row, f"{codes.format_id_code(domain, row['ac_number'], row['item_number'])}  {row['title']}")
            for row in rows
        ]
        chosen = picker.select_one(options, title=f"Which ID in {category['title']}?")
        if chosen is None or chosen == _GO_BACK:
            return None
        if chosen == _OPEN_THIS_LEVEL:
            return category["folder_path"]
        return chosen["folder_path"]

#!/usr/bin/env python
# encoding: utf-8
"""
*Open the Craft folder/document and/or Todoist project that mirror a given filesystem path*

Author
: David Young
"""

import os
import subprocess
import sys
import webbrowser

from aardvark_jd import db, locate

# ONLY THESE ENTITY TYPES ARE EVER MIRRORED TO TODOIST (SEE `todoist_sync.py`) -
# A `system_folder` OR `space:index` MATCH NEVER HAS A `todoist_links` ROW TO FIND.
_TODOIST_ENTITY_TYPES = ("area", "category", "id")


class open_craft(object):
    """
    *resolve a filesystem path to its linked Craft/Todoist entities, and open whichever exist*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``path`` -- the filesystem path to resolve. Defaults to the current working directory.
    - ``settings`` -- the aardvark settings dict, used to resolve the system root itself (see `locate.entity_for_path`). Default `None`.

    **Usage:**

    ```python
    from aardvark_jd.open_craft import open_craft
    label, craftUrl, todoistUrl = open_craft(log=log, dbConn=dbConn, settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, path=None, settings=None):
        self.log = log
        self.dbConn = dbConn
        self.path = path or os.getcwd()
        self.rootPath = ((settings or {}).get("system") or {}).get("root_path")

    def get(self):
        """
        *resolve `path` to its linked Craft/Todoist entities and open every one that's synced*

        **Return:**

        - ``label`` -- the matched entity's title/name
        - ``craftUrl`` -- the Craft URL that was opened, or `None` if the entity isn't synced to Craft
        - ``todoistUrl`` -- the Todoist URL that was opened, or `None` if the entity isn't mirrored to Todoist

        **Raises:**

        - ``ValueError`` -- if the entity is synced to neither Craft nor Todoist
        """
        self.log.debug("starting the ``get`` method")

        entityType, entityKey, _folderPath, label = locate.entity_for_path(
            self.dbConn, self.path, rootPath=self.rootPath,
        )
        craftLink = db.get_craft_link(self.dbConn, entityType, entityKey)
        craftUrl = craftLink["craft_url"] if craftLink else None

        todoistUrl = None
        if entityType in _TODOIST_ENTITY_TYPES:
            todoistLink = db.get_todoist_link(self.dbConn, entityType, entityKey)
            todoistUrl = todoistLink["todoist_url"] if todoistLink else None

        if not craftUrl and not todoistUrl:
            raise ValueError(
                f"'{label}' has not been synced to craft or todoist yet - "
                f"run `aardvark craft_sync` and/or `aardvark todoist_sync` first"
            )

        if craftUrl:
            self._open(craftUrl)
        if todoistUrl:
            self._open(todoistUrl)

        self.log.debug("completed the ``get`` method")
        return label, craftUrl, todoistUrl

    def _open(self, url):
        """
        *open a URL in the platform's default handler*

        **Key Arguments:**

        - ``url`` -- the Craft deep link or Todoist URL to open
        """
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False)
        else:
            webbrowser.open(url)

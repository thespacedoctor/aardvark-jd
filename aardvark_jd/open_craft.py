#!/usr/bin/env python
# encoding: utf-8
"""
*Open the Craft folder/document that mirrors a given filesystem path*

Author
: David Young
"""

import os
import subprocess
import sys
import webbrowser

from aardvark_jd import db, locate


class open_craft(object):
    """
    *resolve a filesystem path to its linked Craft entity, and open it*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``path`` -- the filesystem path to resolve. Defaults to the current working directory.
    - ``settings`` -- the aardvark settings dict, used to resolve the system root itself (see `locate.entity_for_path`). Default `None`.

    **Usage:**

    ```python
    from aardvark_jd.open_craft import open_craft
    label, craftUrl = open_craft(log=log, dbConn=dbConn, settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, path=None, settings=None):
        self.log = log
        self.dbConn = dbConn
        self.path = path or os.getcwd()
        self.rootPath = ((settings or {}).get("system") or {}).get("root_path")

    def get(self):
        """
        *resolve `path` to its linked Craft entity and open it in the Craft app/browser*

        **Return:**

        - ``label`` -- the matched entity's title/name
        - ``craftUrl`` -- the Craft URL that was opened
        """
        self.log.debug("starting the ``get`` method")

        entityType, entityKey, _folderPath, label = locate.entity_for_path(
            self.dbConn, self.path, rootPath=self.rootPath,
        )
        link = db.get_craft_link(self.dbConn, entityType, entityKey)
        if link is None or not link["craft_url"]:
            raise ValueError(
                f"'{label}' has not been synced to craft yet - run `aardvark craft_sync` first"
            )

        self._open(link["craft_url"])

        self.log.debug("completed the ``get`` method")
        return label, link["craft_url"]

    def _open(self, url):
        """
        *open a `craftdocs://` URL in the platform's default handler*

        **Key Arguments:**

        - ``url`` -- the Craft deep link to open
        """
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False)
        else:
            webbrowser.open(url)

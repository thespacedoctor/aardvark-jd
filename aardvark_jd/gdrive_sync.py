#!/usr/bin/env python
# encoding: utf-8
"""
*Mirror the aardvark folder tree into Google Drive - folders only, no documents*

Drive is the plain-folder mirror: somewhere to drop files that belongs to
the same Johnny Decimal structure as everything else, without trying to be
a second Craft. Nothing writes a document, an index or a link row *into*
Drive; the Drive URL instead travels outwards, onto the Craft link row and
the Todoist project description (see `doc_links`).

Three deliberate narrowings versus the Craft mirror:

- The whole system lands inside one folder at the Drive root, named after
  the aardvark system.
- `00_INDEX` is not mirrored. It holds `aardvark.db`, which has no business
  being synced into Drive by a tool that is not managing its concurrency.
- Of each system folder's ten reserved `00`-`09` subfolders, only
  `01_inbox`, `04_templates` and `09_archive` are created. The other seven
  are documents or scratch space that only make sense in Craft or on disk.

Adoption is the whole point of `_children`: every folder is matched against
what is already in Drive by `(parent, name)` before anything is created, so
a re-run repairs and re-keys rather than duplicating, and a folder the user
made by hand is taken over rather than shadowed. That is also why the full
`drive` scope is the default - see `connect_gdrive`.

Author
: David Young
"""

from aardvark_jd import codes, db, folders, paths
from aardvark_jd.gdrive_client import GDriveClient

# `root.index` IS DELIBERATELY ABSENT - IT HOLDS `aardvark.db`.
_GDRIVE_ROOT_FOLDER_KEYS = (
    "root.inbox", "root.projects", "root.areas", "root.resources", "root.archive",
)

# THE ONLY RESERVED `00`-`09` SUBFOLDERS WORTH HAVING IN DRIVE.
_GDRIVE_RESERVED_BASENAMES = ("01_inbox", "04_templates", "09_archive")

_DOMAIN_ROOT_KEY = {
    "projects": "root.projects",
    "areas": "root.areas",
    "resources": "root.resources",
}


class gdrive_sync(object):
    """
    *mirror the aardvark folder tree into Google Drive*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection to the active system's index
    - ``settings`` -- the aardvark settings dict

    **Usage:**

    ```python
    from aardvark_jd.gdrive_sync import gdrive_sync
    summary = gdrive_sync(log=log, dbConn=dbConn, settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, settings):
        self.log = log
        self.dbConn = dbConn
        self.settings = settings or {}
        self.foldersCreated = 0
        self.linkRowsWritten = 0
        # LAZY PER-PARENT INDEX OF WHAT IS ALREADY IN DRIVE, KEYED BY PARENT
        # ID. DRIVE HAS NO CHEAP WHOLE-TREE LISTING, SO UNLIKE `craft_sync`
        # THIS IS FILLED ONE PARENT AT A TIME, ONLY FOR PARENTS WE TOUCH.
        self.childIndex = {}

        gdriveSettings = self.settings.get("gdrive") or {}
        if not gdriveSettings.get("enabled"):
            raise ValueError(
                "google drive is not connected - run `aardvark connect_gdrive <clientId> <clientSecret>` first"
            )
        for key in ("client_id", "client_secret", "refresh_token"):
            if not gdriveSettings.get(key):
                raise ValueError(
                    f"google drive settings are incomplete (missing `gdrive.{key}`) - "
                    "re-run `aardvark connect_gdrive <clientId> <clientSecret>`"
                )
        self.client = GDriveClient(
            clientId=gdriveSettings["client_id"],
            clientSecret=gdriveSettings["client_secret"],
            refreshToken=gdriveSettings["refresh_token"],
        )

    def get(self):
        """
        *run the mirror, creating whatever is missing and adopting whatever is not*

        **Return:**

        - ``summary`` -- a dict with keys `folders_created` and `link_rows_written`
        """
        self.log.debug("starting the ``get`` method")

        workspaceId = self._ensure_workspace_root()
        rootFolderIds = self._ensure_root_folders(workspaceId)

        for domain in codes.DOMAINS:
            domainRootId = rootFolderIds.get(_DOMAIN_ROOT_KEY[domain])
            if domainRootId:
                self._sync_domain(domain, domainRootId)

        summary = {
            "folders_created": self.foldersCreated,
            "link_rows_written": self.linkRowsWritten,
        }

        self.log.debug("completed the ``get`` method")
        return summary

    def _ensure_workspace_root(self):
        """
        *adopt or create the single Drive folder that holds the whole aardvark system*

        **Return:**

        - ``folderId`` -- the workspace folder's Drive id
        """
        systemName = (self.settings.get("system") or {}).get("name") or "aardvark"
        folderId, _url = self._ensure_folder("workspace", "root", systemName, "root")
        return folderId

    def _ensure_root_folders(self, workspaceId):
        """
        *mirror the five PARA root folders inside the workspace folder*

        **Key Arguments:**

        - ``workspaceId`` -- the workspace folder's Drive id

        **Return:**

        - ``rootFolderIds`` -- a dict mapping folder key -> Drive folder id
        """
        rootFolderIds = {}
        for folderKey in _GDRIVE_ROOT_FOLDER_KEYS:
            systemFolder = db.get_system_folder(self.dbConn, folderKey)
            if not systemFolder:
                continue
            name = folders.display_name(systemFolder["folder_name"])
            folderId, _url = self._ensure_folder("system_folder", folderKey, name, workspaceId)
            rootFolderIds[folderKey] = folderId
        return rootFolderIds

    def _sync_domain(self, domain, domainRootId):
        """
        *mirror one domain's areas, categories and IDs, plus their reserved scaffolding*

        **Key Arguments:**

        - ``domain`` -- `projects`, `areas` or `resources`
        - ``domainRootId`` -- the domain's root Drive folder id
        """
        for area in db.list_areas(self.dbConn, domain):
            areaName = folders.display_name(area["folder_name"])
            areaFolderId, _url = self._ensure_folder(
                "area", str(area["area_id"]), areaName, domainRootId,
            )

            for category in db.list_categories(self.dbConn, domain, areaId=area["area_id"]):
                categoryName = folders.display_name(category["folder_name"])
                categoryFolderId, _url = self._ensure_folder(
                    "category", str(category["category_id"]), categoryName, areaFolderId,
                )

                for idRow in db.list_ids(self.dbConn, domain, category["category_id"]):
                    idName = folders.display_name(idRow["folder_name"])
                    self._ensure_folder("id", str(idRow["id_id"]), idName, categoryFolderId)

                # A CATEGORY'S TEN RESERVED IDS SIT DIRECTLY INSIDE IT, ALONGSIDE
                # ITS USER-CREATED IDS - IT HAS NO SYSTEM FOLDER OF ITS OWN.
                self._sync_reserved_subfolders(
                    f"{domain}.{category['ac_number']}", categoryFolderId,
                )

            self._sync_system_folder(
                f"{domain}.{area['decade_start']}.system",
                f"{domain}.{area['decade_start']}",
                areaFolderId,
            )

        self._sync_system_folder(f"{domain}.system", f"{domain}.system", domainRootId)

    def _sync_system_folder(self, systemFolderKey, reservedKeyPrefix, parentId):
        """
        *mirror a `00_09_system` folder and its three retained reserved subfolders*

        **Key Arguments:**

        - ``systemFolderKey`` -- the system folder's key in `system_folders`
        - ``reservedKeyPrefix`` -- the key prefix its reserved subfolders share
        - ``parentId`` -- the containing Drive folder's id
        """
        systemFolder = db.get_system_folder(self.dbConn, systemFolderKey)
        if not systemFolder:
            return
        name = folders.display_name(systemFolder["folder_name"])
        folderId, _url = self._ensure_folder("system_folder", systemFolderKey, name, parentId)
        self._sync_reserved_subfolders(reservedKeyPrefix, folderId)

    def _sync_reserved_subfolders(self, keyPrefix, containingId):
        """
        *mirror only the inbox, templates and archive members of a reserved `00`-`09` set*

        **Key Arguments:**

        - ``keyPrefix`` -- the key prefix the reserved subfolders share, e.g. `"areas.11"`
        - ``containingId`` -- the containing Drive folder's id
        """
        for baseName in _GDRIVE_RESERVED_BASENAMES:
            folderKey = f"{keyPrefix}.{baseName}"
            systemFolder = db.get_system_folder(self.dbConn, folderKey)
            if not systemFolder:
                continue
            name = folders.display_name(systemFolder["folder_name"])
            self._ensure_folder("system_folder", folderKey, name, containingId)

    def _children(self, parentId):
        """
        *the folders already inside a Drive folder, as a `{name: (id, url)}` index*

        Cached per parent for the life of the sync, so each parent is
        listed at most once however many children are checked against it.

        **Key Arguments:**

        - ``parentId`` -- the parent folder's Drive id

        **Return:**

        - ``children`` -- a dict mapping child folder name -> `(id, url)`
        """
        if parentId not in self.childIndex:
            self.childIndex[parentId] = {
                child["name"]: (child["id"], child.get("webViewLink") or GDriveClient.folder_url(child["id"]))
                for child in self.client.list_child_folders(parentId)
            }
        return self.childIndex[parentId]

    def _ensure_folder(self, entityType, entityKey, name, parentId):
        """
        *adopt the Drive folder already at `(parentId, name)`, or create it, and record the link*

        Matching on the live listing rather than trusting `gdrive_links`
        makes each sync self-healing: a folder moved or recreated in Drive
        is picked up again, and one the user made by hand is adopted rather
        than shadowed by a duplicate.

        **Key Arguments:**

        - ``entityType`` -- the entity's type, e.g. `"area"`
        - ``entityKey`` -- the entity's key, unique within its type
        - ``name`` -- the folder's name in Drive
        - ``parentId`` -- the containing Drive folder's id

        **Return:**

        - ``folderId``, ``url`` -- the folder's Drive id and web URL
        """
        children = self._children(parentId)
        if name in children:
            folderId, url = children[name]
        else:
            folderId, url = self.client.create_folder(name, parentId=parentId)
            children[name] = (folderId, url)
            self.foldersCreated += 1

        db.upsert_gdrive_link(
            self.dbConn, entityType, entityKey, gdriveFolderId=folderId, gdriveUrl=url,
        )
        self.linkRowsWritten += 1
        return folderId, url

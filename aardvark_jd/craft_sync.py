#!/usr/bin/env python
# encoding: utf-8
"""
*Mirror the aardvark index into a craft.do space as linked folders/documents*

The top-level PARA folders become top-level Craft folders (Craft spaces
cannot be created via API), areas and categories nest as folders below
them, and IDs become Craft documents named with their `X.AC.ID` code. A
"00 Index" document at each level lists the level directly below it, one
level deep, with each child's code+title linking to its Craft folder or
document.

Author
: David Young
"""

from aardvark_jd import db, folders, paths
from aardvark_jd.craft_client import CraftClient

_ROOT_FOLDER_KEYS = ("root.inbox", "root.projects", "root.areas", "root.resources", "root.archive")
_DOMAIN_ROOT_KEY = {"areas": "root.areas", "resources": "root.resources"}
_INDEX_DOC_TITLE = "00 Index"


class craft_sync(object):
    """
    *idempotently mirror the current aardvark index into the connected craft.do space*

    Every folder/document created is recorded in the `craft_links` table
    keyed by aardvark entity, so re-running only creates what's missing and
    otherwise just refreshes "00 Index" document content - safe to call
    after every mutating command, or on demand to backfill/repair.

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``settings`` -- the aardvark settings dict; must have `craft.enabled: true`
      and both `craft.api_url` and `craft.api_token` set

    **Usage:**

    ```python
    from aardvark_jd.craft_sync import craft_sync
    summary = craft_sync(log=log, dbConn=dbConn, settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, settings):
        self.log = log
        self.dbConn = dbConn

        craftSettings = (settings or {}).get("craft") or {}
        if not craftSettings.get("enabled"):
            raise ValueError("craft is not connected - run `aardvark connect_craft <apiUrl> <apiToken>` first")
        apiUrl = craftSettings.get("api_url")
        apiToken = craftSettings.get("api_token")
        if not apiUrl or not apiToken:
            raise ValueError("no craft api_url/api_token configured - run `aardvark connect_craft <apiUrl> <apiToken>` first")

        self.client = CraftClient(apiUrl=apiUrl, apiToken=apiToken)
        self.foldersCreated = 0
        self.documentsCreated = 0
        self.indexesRefreshed = 0
        self.folderIndex = {}

    def get(self):
        """
        *sync every root folder, area, category, id and project into Craft*

        **Return:**

        - ``summary`` -- a dict of counts: `folders_created`, `documents_created`, `indexes_refreshed`
        """
        self.log.debug("starting the ``get`` method")

        self._load_folder_index()
        rootFolderIds = self._ensure_root_folders()

        for domain, rootKey in _DOMAIN_ROOT_KEY.items():
            self._sync_domain(domain, rootKey, rootFolderIds[rootKey])

        self._sync_projects(rootFolderIds["root.projects"])
        self._refresh_space_index(rootFolderIds)

        self.log.debug("completed the ``get`` method")
        return {
            "folders_created": self.foldersCreated,
            "documents_created": self.documentsCreated,
            "indexes_refreshed": self.indexesRefreshed,
        }

    def _load_folder_index(self):
        """
        *index every folder already in the Craft space by parent id and name*

        Craft re-keys a folder to a new permanent id once the app syncs it,
        so a folder id recorded on an earlier run cannot be trusted (see
        `CraftClient.create_folder`). Matching the live space on
        `(parentFolderId, name)` instead makes each sync self-healing: stale
        ids are refreshed, and a folder that already exists is adopted rather
        than duplicated.
        """
        self.folderIndex = {}

        def index_level(items, parentFolderId):
            for item in items:
                self.folderIndex[(parentFolderId, item["name"])] = item["id"]
                index_level(item.get("folders") or [], item["id"])

        index_level(self.client.list_folders(), None)

    def _ensure_root_folders(self):
        """
        *ensure a top-level Craft folder exists for each mirrored PARA root folder*

        **Return:**

        - ``rootFolderIds`` -- a dict mapping folder key -> Craft folder id
        """
        rootFolderIds = {}
        for folderKey in _ROOT_FOLDER_KEYS:
            systemFolder = db.get_system_folder(self.dbConn, folderKey)
            name = folders.display_name(systemFolder["folder_name"])
            folderId, _url = self._ensure_folder("system_folder", folderKey, name)
            rootFolderIds[folderKey] = folderId
        return rootFolderIds

    def _sync_domain(self, domain, domainRootKey, domainRootFolderId):
        """
        *sync one Johnny Decimal domain's areas, categories and ids into Craft*

        **Key Arguments:**

        - ``domain`` -- `areas` or `resources`
        - ``domainRootKey`` -- the domain's root system-folder key, e.g. `"root.areas"`
        - ``domainRootFolderId`` -- the domain's root Craft folder id
        """
        areaChildren = []
        for area in db.list_areas(self.dbConn, domain):
            areaName = folders.display_name(area["folder_name"])
            areaFolderId, areaUrl = self._ensure_folder(
                "area", str(area["area_id"]), areaName, parentFolderId=domainRootFolderId,
            )
            areaChildren.append((None, areaName, area["description"], areaUrl))

            categoryChildren = []
            for category in db.list_categories(self.dbConn, domain, areaId=area["area_id"]):
                categoryName = folders.display_name(category["folder_name"])
                categoryFolderId, categoryUrl = self._ensure_folder(
                    "category", str(category["category_id"]), categoryName, parentFolderId=areaFolderId,
                )
                categoryChildren.append((None, categoryName, category["description"], categoryUrl))

                idChildren = []
                for idRow in db.list_ids(self.dbConn, domain, category["category_id"]):
                    idName = folders.display_name(idRow["folder_name"])
                    _documentId, idUrl = self._ensure_document(
                        "id", str(idRow["id_id"]), idName, categoryFolderId,
                    )
                    idChildren.append((None, idName, idRow["description"], idUrl))

                self._refresh_index("category", str(category["category_id"]), categoryFolderId, idChildren)

            self._refresh_index("area", str(area["area_id"]), areaFolderId, categoryChildren)

        self._refresh_index("system_folder", domainRootKey, domainRootFolderId, areaChildren)

    def _sync_projects(self, projectsRootFolderId):
        """
        *sync every project into Craft as a flat document under the Projects root folder*

        **Key Arguments:**

        - ``projectsRootFolderId`` -- the Projects root Craft folder id
        """
        projectChildren = []
        for project in db.list_projects(self.dbConn):
            projectName = folders.display_name(project["folder_name"])
            _documentId, url = self._ensure_document(
                "project", str(project["project_id"]), projectName, projectsRootFolderId,
            )
            projectChildren.append((None, projectName, project["description"], url))

        self._refresh_index("system_folder", "root.projects", projectsRootFolderId, projectChildren)

    def _refresh_space_index(self, rootFolderIds):
        """
        *(re)write the space-root "00 Index" document, listing the five mirrored PARA root folders*

        **Key Arguments:**

        - ``rootFolderIds`` -- a dict mapping folder key -> Craft folder id, from `_ensure_root_folders`
        """
        children = []
        for folderKey in _ROOT_FOLDER_KEYS:
            if folderKey not in rootFolderIds:
                continue
            _key, _parentKey, _baseName, _title, description, _emoji = paths.skeleton_entry(folderKey)
            systemFolder = db.get_system_folder(self.dbConn, folderKey)
            link = db.get_craft_link(self.dbConn, "system_folder", folderKey)
            url = link["craft_url"] if link else None
            children.append((None, folders.display_name(systemFolder["folder_name"]), description, url))

        self._refresh_index("space", "root", None, children)

    # ------------------------------------------------------------------ #
    # idempotent create-or-reuse helpers, backed by `craft_links`
    # ------------------------------------------------------------------ #

    def _ensure_folder(self, entityType, entityKey, name, parentFolderId=None):
        """
        *adopt the matching folder already in the Craft space, otherwise create it*

        Identity comes from the live space - `(parentFolderId, name)` against
        the index built by `_load_folder_index` - not from `craft_links`,
        because Craft re-keys folder ids behind our back. The link row is
        rewritten every run so both the id and the deep link stay current.

        **Key Arguments:**

        - ``entityType`` -- the entity's type, e.g. `"area"`
        - ``entityKey`` -- the entity's key, unique within its type
        - ``name`` -- the folder's name, mirroring its on-disk folder name
        - ``parentFolderId`` -- the parent folder's id, or `None` for a top-level folder

        **Return:**

        - ``folderId``, ``url`` -- the linked Craft folder's id and deep link
        """
        folderId = self.folderIndex.get((parentFolderId, name))
        if folderId is None:
            folderId = self.client.create_folder(name, parentFolderId=parentFolderId)
            self.folderIndex[(parentFolderId, name)] = folderId
            self.foldersCreated += 1

        url = self.client.folder_deep_link(folderId, name)
        db.upsert_craft_link(self.dbConn, entityType, entityKey, craftFolderId=folderId, craftUrl=url)
        return folderId, url

    def _ensure_document(self, entityType, entityKey, title, folderId=None):
        """
        *reuse an entity's linked Craft document if one is already recorded, otherwise create it*

        **Key Arguments:**

        - ``entityType`` -- the entity's type, e.g. `"id"`
        - ``entityKey`` -- the entity's key, unique within its type
        - ``title`` -- the document's title, used only if it still needs creating
        - ``folderId`` -- the containing folder's id, or `None` to leave it unfiled. Default `None`.

        **Return:**

        - ``documentId``, ``url`` -- the linked Craft document's id and shareable URL
        """
        link = db.get_craft_link(self.dbConn, entityType, entityKey)
        if link and link["craft_document_id"]:
            return link["craft_document_id"], link["craft_url"]

        documentId, url = self.client.create_document(title, folderId=folderId)
        db.upsert_craft_link(self.dbConn, entityType, entityKey, craftDocumentId=documentId, craftUrl=url)
        self.documentsCreated += 1
        return documentId, url

    def _refresh_index(self, entityType, entityKey, folderId, children):
        """
        *(re)write a "00 Index" document listing one level of children*

        The index document itself is created once (linked under
        `f"{entityType}:index"`/`entityKey`), and its single content block is
        added once and thereafter updated in place, so this stays idempotent
        across repeated syncs.

        **Key Arguments:**

        - ``entityType`` -- the parent entity's type, e.g. `"area"`
        - ``entityKey`` -- the parent entity's key
        - ``folderId`` -- the parent folder's Craft id; the index document is filed inside it
        - ``children`` -- a list of `(codeOrNone, title, description, url)` tuples, one per child
        """
        indexEntityType = f"{entityType}:index"
        documentId, _url = self._ensure_document(indexEntityType, entityKey, _INDEX_DOC_TITLE, folderId)

        lines = []
        for codeOrTitle, title, description, url in children:
            linkText = f"{codeOrTitle} {title}" if codeOrTitle else title
            if url:
                lines.append(f"- [{linkText}]({url}) — {description}")
            else:
                lines.append(f"- {linkText} — {description}")
        markdown = "\n".join(lines) if lines else "*(nothing here yet)*"

        link = db.get_craft_link(self.dbConn, indexEntityType, entityKey)
        if link and link["craft_block_id"]:
            self.client.update_block(link["craft_block_id"], markdown)
        else:
            blockId = self.client.add_block(documentId, markdown)
            db.upsert_craft_link(self.dbConn, indexEntityType, entityKey, craftBlockId=blockId)

        self.indexesRefreshed += 1

#!/usr/bin/env python
# encoding: utf-8
"""
*Mirror the aardvark index into a craft.do space as linked folders/documents*

The top-level PARA folders become top-level Craft folders (Craft spaces
cannot be created via API), areas and categories nest as folders below
them, and IDs become Craft documents named with their `X.AC.ID` code.

Every domain root (`projects`, `areas`, `resources`) and every area also
gets its own `<X>_system` folder mirrored alongside its areas/categories,
with the ten reserved subfolders (`.00_index`-`.09_archive`) mirrored
inside it as Craft folders or documents per `paths.SYSTEM_SUBFOLDERS`'s
declared kind; a category has no system folder of its own, so its ten
reserved subfolders sit directly inside the category folder instead. The
reserved `.00_index` document at each of these levels lists the level
directly below it, one level deep, with each child's code+title linking
to its Craft folder or document - this replaces the free-standing "00
Index" document that used to sit at area/category level. The space-root
index is unaffected - there is no system folder above the PARA roots.

Author
: David Young
"""

from aardvark_jd import db, folders, paths
from aardvark_jd.craft_client import CraftClient

_ROOT_FOLDER_KEYS = ("root.inbox", "root.projects", "root.areas", "root.resources", "root.archive")
_DOMAIN_ROOT_KEY = {"projects": "root.projects", "areas": "root.areas", "resources": "root.resources"}
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
            self._sync_domain(domain, rootFolderIds[rootKey])

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

    def _sync_domain(self, domain, domainRootFolderId):
        """
        *sync one Johnny Decimal domain's areas, categories and ids into Craft*

        **Key Arguments:**

        - ``domain`` -- `projects`, `areas` or `resources`
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

                # A CATEGORY HAS NO SEPARATE `<X>_system` FOLDER OF ITS OWN - ITS TEN
                # RESERVED SUBFOLDERS (INCLUDING `.00_index`, THE CATEGORY'S INDEX) SIT
                # DIRECTLY INSIDE THE CATEGORY FOLDER, ALONGSIDE ITS USER-CREATED IDS.
                self._sync_reserved_subfolders(f"{domain}.{category['ac_number']}", categoryFolderId, idChildren)

            self._sync_system_folder(
                f"{domain}.{area['decade_start']}.system", f"{domain}.{area['decade_start']}",
                areaFolderId, categoryChildren,
            )

        self._sync_system_folder(f"{domain}.system", f"{domain}.system", domainRootFolderId, areaChildren)

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
        *ensure a generic "00 Index" document exists, then (re)write its content*

        Used only where there is no reserved `.00_index` scaffolding
        document to reuse instead - the space-root index (see
        `_sync_reserved_subfolders` for everywhere else).

        **Key Arguments:**

        - ``entityType`` -- the parent entity's type, e.g. `"system_folder"`
        - ``entityKey`` -- the parent entity's key
        - ``folderId`` -- the parent folder's Craft id; the index document is filed inside it
        - ``children`` -- a list of `(codeOrNone, title, description, url)` tuples, one per child
        """
        indexEntityType = f"{entityType}:index"
        documentId, _url = self._ensure_document(indexEntityType, entityKey, _INDEX_DOC_TITLE, folderId)
        self._write_index_content(documentId, children)

    def _write_index_content(self, documentId, children):
        """
        *replace an index document's whole content with a fresh listing of the given children*

        Craft has no atomic "replace page content" call, and `POST /blocks`
        splits multi-line markdown into one sibling block per line rather
        than one block for the whole thing (confirmed empirically against a
        real space), so there is no single block id to update in place.
        Instead this reads the document's current top-level content,
        deletes all of it, and inserts the fresh markdown - read, delete,
        insert in place of an update. `craft_block_id` is no longer written
        or read anywhere; the column stays in `craft_links` but unused.

        **Key Arguments:**

        - ``documentId`` -- the index document's Craft id
        - ``children`` -- a list of `(codeOrNone, title, description, url)` tuples, one per child
        """
        lines = []
        for codeOrTitle, title, description, url in children:
            linkText = f"{codeOrTitle} {title}" if codeOrTitle else title
            if url:
                lines.append(f"- [{linkText}]({url}) — {description}")
            else:
                lines.append(f"- {linkText} — {description}")
        markdown = "\n".join(lines) if lines else "*(nothing here yet)*"

        existingBlock = self.client.get_block(documentId)
        existingContentIds = [item["id"] for item in (existingBlock.get("content") or [])]
        self.client.delete_blocks(existingContentIds)
        self.client.add_block(documentId, markdown)

        self.indexesRefreshed += 1

    def _sync_system_folder(self, systemFolderKey, reservedKeyPrefix, parentFolderId, indexChildren):
        """
        *sync a `<X>_system` folder and its ten reserved subfolders into Craft*

        Used at the domain level (`f"{domain}.system"`, nested under the
        domain root, alongside its areas) and at the area level
        (`f"{domain}.{decadeStart}.system"`, nested under the area, alongside
        its categories). Does nothing if the system folder hasn't been
        created on disk yet (a legacy system not yet `repair_emoji`'d) -
        this sync just skips it rather than failing.

        **Key Arguments:**

        - ``systemFolderKey`` -- the system folder's own `system_folders.folder_key`
        - ``reservedKeyPrefix`` -- the key prefix its ten reserved subfolders are stored under (see `folders.create_reserved_system_ids`)
        - ``parentFolderId`` -- the Craft folder to nest the system folder inside
        - ``indexChildren`` -- children for the reserved `.00_index` document inside it
        """
        row = db.get_system_folder(self.dbConn, systemFolderKey)
        if row is None:
            return
        name = folders.display_name(row["folder_name"])
        systemFolderId, _url = self._ensure_folder(
            "system_folder", systemFolderKey, name, parentFolderId=parentFolderId,
        )
        self._sync_reserved_subfolders(reservedKeyPrefix, systemFolderId, indexChildren)

    def _sync_reserved_subfolders(self, keyPrefix, containingFolderId, indexChildren):
        """
        *sync the ten static reserved subfolders (`.00_index`-`.09_archive`) inside a system or category folder*

        Each mirrors as a Craft folder or document per its declared
        `paths.SYSTEM_SUBFOLDERS` kind, except `.00_index`, which is always
        a document and becomes the index for `indexChildren` - replacing
        the old free-standing "00 Index" document at this level. Skips any
        reserved subfolder not yet created on disk, same as
        `_sync_system_folder`.

        **Key Arguments:**

        - ``keyPrefix`` -- the `system_folders.folder_key` prefix the ten reserved subfolders share, e.g. `"areas.11"`
        - ``containingFolderId`` -- the Craft folder the reserved subfolders are filed inside
        - ``indexChildren`` -- children for the reserved `.00_index` document
        """
        for baseName, _title, _description, _folderEmoji, craftKind in paths.SYSTEM_SUBFOLDERS:
            folderKey = f"{keyPrefix}.{baseName}"
            row = db.get_system_folder(self.dbConn, folderKey)
            if row is None:
                continue
            name = folders.display_name(row["folder_name"])

            if baseName == "00_index":
                documentId, _url = self._ensure_document("system_folder", folderKey, name, containingFolderId)
                self._write_index_content(documentId, indexChildren)
            elif craftKind == paths.SYSTEM_SUBFOLDER_KIND_FOLDER:
                self._ensure_folder("system_folder", folderKey, name, parentFolderId=containingFolderId)
            else:
                self._ensure_document("system_folder", folderKey, name, containingFolderId)

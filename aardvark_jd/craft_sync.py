#!/usr/bin/env python
# encoding: utf-8
"""
*Mirror the aardvark index into a craft.do space as linked folders/documents*

The top-level PARA folders become top-level Craft folders (Craft spaces
cannot be created via API), and areas, categories and IDs all nest as
folders below them - an ID's folder carries a single `00 Index` document
inside it, which is where its Finder/Dropbox/Todoist link row lives,
since a bare Craft folder has no body of its own to write it into.

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

from aardvark_jd import db, doc_links, dropbox_client, folders, paths
from aardvark_jd.craft_client import CraftClient
from aardvark_jd.dropbox_client import DropboxClient

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
        self.linkRowsWritten = 0
        self.folderIndex = {}
        # LAZY PER-FOLDER INDEX OF EXISTING DOCUMENT TITLES, FOR ADOPTION.
        self.documentIndex = {}

        self.rootPath = (settings.get("system") or {}).get("root_path")
        self.dropboxClient = None
        self.dropboxRoot = None
        dropboxSettings = (settings or {}).get("dropbox") or {}
        if dropboxSettings.get("enabled") and self.rootPath:
            self.dropboxClient = DropboxClient(
                appKey=dropboxSettings.get("app_key"),
                appSecret=dropboxSettings.get("app_secret"),
                refreshToken=dropboxSettings.get("refresh_token"),
            )
            self.dropboxRoot = dropbox_client.find_containing_root(
                self.rootPath, dropbox_client.local_dropbox_roots(),
            )

    def get(self):
        """
        *sync every root folder, area, category, id and project into Craft*

        **Return:**

        - ``summary`` -- a dict of counts: `folders_created`, `documents_created`, `indexes_refreshed`, `link_rows_written`
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
            "link_rows_written": self.linkRowsWritten,
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
                    idKey = str(idRow["id_id"])
                    idFolderId, idUrl = self._ensure_folder(
                        "id", idKey, idName, parentFolderId=categoryFolderId,
                    )
                    documentId, _docUrl = self._ensure_document("id:index", idKey, idName, idFolderId)
                    self._write_link_row("id:index", idKey, documentId, idRow["folder_path"], todoistEntityType="id")
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

        # NOTHING RECORDED - BUT A DOCUMENT WITH THIS TITLE MAY ALREADY BE
        # SITTING IN THE FOLDER, LEFT BY A REBUILT INDEX, A `_migrate_to_v4`
        # CLEAR-OUT, AN ARCHIVE THAT DROPPED THE LINK ROWS, OR SIMPLY BY
        # HAND. ADOPT IT RATHER THAN CREATING A DUPLICATE ALONGSIDE IT -
        # THE SAME `(parent, name)` MATCHING `_ensure_folder` ALREADY DOES.
        adoptedId = self._adopt_document(folderId, title)
        if adoptedId:
            url = self.client._deep_link(adoptedId)
            db.upsert_craft_link(
                self.dbConn, entityType, entityKey, craftDocumentId=adoptedId, craftUrl=url,
            )
            return adoptedId, url

        documentId, url = self.client.create_document(title, folderId=folderId)
        db.upsert_craft_link(self.dbConn, entityType, entityKey, craftDocumentId=documentId, craftUrl=url)
        self.documentsCreated += 1
        return documentId, url

    def _adopt_document(self, folderId, title):
        """
        *find an existing document with this title in this folder, if the API will tell us*

        Cached per folder for the life of the sync, so a folder is listed
        at most once however many documents are checked against it. An
        unfiled document (`folderId` of `None`) cannot be looked up, and
        `CraftClient.list_documents` returns `[]` when the endpoint is
        unavailable - both cases simply mean "no adoption".

        **Key Arguments:**

        - ``folderId`` -- the containing folder's id, or `None`
        - ``title`` -- the document title to match

        **Return:**

        - ``documentId`` -- the existing document's id, or `None`
        """
        if not folderId:
            return None
        if folderId not in self.documentIndex:
            self.documentIndex[folderId] = {
                document.get("title"): document.get("id")
                for document in self.client.list_documents(folderId)
                if document.get("id")
            }
        return self.documentIndex[folderId].get(title)

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
        rewritten = self._write_index_content(documentId, children)
        if self.rootPath:
            self._write_link_row(indexEntityType, entityKey, documentId, self.rootPath, forceRewrite=rewritten)

    def _write_index_content(self, documentId, children):
        """
        *rewrite an index document's content with a fresh listing of the given children, unless it already says exactly that*

        Craft has no atomic "replace page content" call, and `POST /blocks`
        splits multi-line markdown into one sibling block per line rather
        than one block for the whole thing (confirmed empirically against a
        real space), so there is no single block id to update in place.
        Instead this reads the document's current top-level content,
        deletes all of it, and inserts the fresh markdown - read, delete,
        insert in place of an update. `craft_block_id` is no longer written
        or read anywhere; the column stays in `craft_links` but unused.

        Rewriting unconditionally cost four API calls per index document on
        every run - 112 calls across the 28 index documents even when
        nothing had changed, which is what exhausted Craft's rate limit. So
        the read is now also a comparison: when the document already holds
        exactly the computed listing, this returns without writing, taking
        an unchanged index document to one `GET` and no writes.

        **Key Arguments:**

        - ``documentId`` -- the index document's Craft id
        - ``children`` -- a list of `(codeOrNone, title, description, url)` tuples, one per child

        **Return:**

        - ``rewritten`` -- `True` if the content was actually replaced, `False` if it already matched. The caller must pass this straight through as `_write_link_row`'s `forceRewrite`: the two are coupled, and only a real rewrite invalidates the link row's recorded block id.
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
        existingItems = existingBlock.get("content") or []
        if self._index_content_matches(existingItems, markdown):
            return False

        self.client.delete_blocks([item["id"] for item in existingItems])
        self.client.add_block(documentId, markdown)

        self.indexesRefreshed += 1
        return True

    @staticmethod
    def _index_content_matches(existingItems, markdown):
        """
        *is this document's existing content already exactly the computed index listing?*

        Compares on the **tail** of the document rather than the whole of
        it, because an index document's content is always `[link row] +
        [one block per index line]`: `_write_index_content` appends the
        body at the end, and `_write_link_row` then prepends its row at
        `position="start"`. Matching the tail keeps this method ignorant of
        what a link row looks like, and the "at most one block ahead of the
        body" guard means anything else the document has picked up - a
        stray block, a hand-edited note, a second link row - fails the
        comparison and forces a rewrite, preserving the drift repair a full
        sync is there to do.

        Craft round-trips block markdown verbatim apart from trailing
        whitespace, which it strips (both verified against the live space,
        for the `- [title](url) — description` bullets and the
        `*(nothing here yet)*` placeholder alike), so the comparison is a
        plain string equality per `rstrip`ped line and needs no rendering
        step.

        **Key Arguments:**

        - ``existingItems`` -- the document's current top-level content items, as `get_block` returns them
        - ``markdown`` -- the freshly computed listing, one index line per line

        **Return:**

        - ``matches`` -- `True` if the document already holds exactly this listing
        """
        # COMPARE ON TRAILING-WHITESPACE-STRIPPED LINES: CRAFT STRIPS TRAILING
        # WHITESPACE WHEN IT STORES A BLOCK, SO A CHILD WITH AN EMPTY DESCRIPTION -
        # WHICH RENDERS AS `... — ` - WOULD OTHERWISE NEVER COMPARE EQUAL TO WHAT
        # WAS STORED, AND ITS INDEX DOCUMENT WOULD REWRITE ON EVERY RUN FOREVER.
        lines = [line.rstrip() for line in markdown.split("\n")]
        existingMarkdown = [(item.get("markdown") or "").rstrip() for item in existingItems]
        leadingBlocks = len(existingMarkdown) - len(lines)
        if leadingBlocks not in (0, 1):
            return False
        return existingMarkdown[leadingBlocks:] == lines

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
                rewritten = self._write_index_content(documentId, indexChildren)
                self._write_link_row("system_folder", folderKey, documentId, row["folder_path"], forceRewrite=rewritten)
            elif craftKind == paths.SYSTEM_SUBFOLDER_KIND_FOLDER:
                self._ensure_folder("system_folder", folderKey, name, parentFolderId=containingFolderId)
            else:
                documentId, _url = self._ensure_document("system_folder", folderKey, name, containingFolderId)
                self._write_link_row("system_folder", folderKey, documentId, row["folder_path"])

    # ------------------------------------------------------------------ #
    # Finder/Dropbox link row - see `doc_links.py`
    # ------------------------------------------------------------------ #

    def _write_link_row(self, entityType, entityKey, documentId, folderPath, forceRewrite=False, todoistEntityType=None):
        """
        *(re)write a document's Finder/Dropbox/Todoist link row, skipping the API round-trip when nothing changed*

        Called after a document's own content has been written, never
        before. For an ID's `00 Index` document (whose body `craft_sync`
        never otherwise touches) this is a genuine idempotency check - an
        unchanged row costs zero API calls. For a `.00_index` document,
        `forceRewrite` must be whatever `_write_index_content` just
        returned, and nothing else: when it did rewrite, it deleted the
        document's entire content wholesale immediately before this runs,
        which silently invalidates the link row's previously recorded block
        id even when the row's markdown text is unchanged, so the "skip if
        unchanged" fast path can't be trusted; when it skipped, the prior
        block is still there and the fast path is exactly what's wanted.
        Passing `True` unconditionally - as this did before content
        comparison existed - reintroduces one delete and one insert per
        index document per run, which is most of the cost the comparison
        was added to remove.

        **Key Arguments:**

        - ``entityType`` -- the entity's `craft_links` type
        - ``entityKey`` -- the entity's `craft_links` key
        - ``documentId`` -- the entity's Craft document id
        - ``folderPath`` -- the entity's own absolute folder path, linked to from the row
        - ``forceRewrite`` -- skip the unchanged-markdown fast path, because the document's whole body (and so the row's prior block) was just wiped by `_write_index_content`. Pass that method's return value straight through; the two are coupled in both directions. Default `False`.
        - ``todoistEntityType`` -- the entity's `todoist_links` type (`entityKey` is shared between the two tables), or `None` if this entity is never mirrored to Todoist - only IDs are. Default `None`.
        """
        hookmarkUrl = doc_links.hookmark_url(folderPath)
        dropboxUrl = dropbox_client.url_for_path(
            self.dbConn, self.dropboxClient, self.dropboxRoot, folderPath, self.log,
        )
        todoistUrl = None
        if todoistEntityType:
            todoistLink = db.get_todoist_link(self.dbConn, todoistEntityType, entityKey)
            todoistUrl = todoistLink["todoist_url"] if todoistLink else None
        # THE DRIVE LINK IS KEYED BY THE ENTITY'S OWN TYPE, NOT THE `:index`
        # VARIANT `craft_links` USES FOR AN ID'S INDEX DOCUMENT.
        gdriveLink = db.get_gdrive_link(self.dbConn, entityType.split(":")[0], entityKey)
        gdriveUrl = gdriveLink["gdrive_url"] if gdriveLink else None
        markdown = doc_links.link_row_markdown(hookmarkUrl, dropboxUrl, todoistUrl, driveUrl=gdriveUrl)
        if markdown is None:
            return

        link = db.get_craft_link(self.dbConn, entityType, entityKey)
        existingBlockId = None if forceRewrite else (link["craft_block_id"] if link else None)
        if not forceRewrite and link and link["links_markdown"] == markdown and existingBlockId:
            return

        if existingBlockId:
            self.client.delete_blocks([existingBlockId])

        blockId = self.client.add_block(documentId, markdown, position="start")
        db.upsert_craft_link(self.dbConn, entityType, entityKey, craftBlockId=blockId, linksMarkdown=markdown)
        self.linkRowsWritten += 1

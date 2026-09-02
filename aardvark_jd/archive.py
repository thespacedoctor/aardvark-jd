#!/usr/bin/env python
# encoding: utf-8
"""
*Retire an area, category or ID - move its folder into the nearest archive, and free its number*

Every level of an aardvark system already has a reserved `09_archive🗄️`
folder, created since the beginning and until now never written to. This is
what fills it.

Archiving is deliberately **not** a flag on the live row. An archived
entity leaves `areas`/`categories`/`ids` entirely and is recorded in
`archived_entities` instead, for two reasons. First, the live tables carry
`UNIQUE (domain, ac_number[, item_number])`, so a row cannot both stay put
and surrender its number for reuse. Second, and more important: three sync
engines (`craft_sync`, `todoist_sync`, `gdrive_sync`) all adopt-or-create
*by name*, so a single query that forgot to filter out archived rows would
silently rebuild the archived structure on the next sync. Removing the row
makes that whole class of bug impossible - nothing else in the codebase has
to learn what "archived" means.

Freeing the number needs `folders._lowest_free` as well as the delete: the
allocators used to be high-water marks and would otherwise step straight
over the gap.

The move on disk goes through `folders.move_folder_and_reindex`, which
commits the index before touching the filesystem and compensates if the
move then fails.

**This is one-way.** There is no `unarchive` command. `archived_entities`
keeps everything needed to build one later - including where the folder
came from - but restoring by hand is the only route today, and a freed
number may since have been handed to something else.

Author
: David Young
"""

import os
from datetime import datetime

from aardvark_jd import codes, db, folders, paths, refs


class archive(object):
    """
    *archive an area, category or ID, locally and across every connected mirror*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection to the active system's index
    - ``ref`` -- an area ref (`"A10-19"`), category ref (`"A11"`) or ID ref (`"A11.10"`)
    - ``settings`` -- the aardvark settings dict. Default *None*.

    **Usage:**

    ```python
    from aardvark_jd.archive import archive
    code, archivedPath, warnings = archive(log=log, dbConn=dbConn, ref="A11.10", settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, ref, settings=None):
        self.log = log
        self.dbConn = dbConn
        self.ref = ref
        self.settings = settings or {}
        self.warnings = []

    def get(self):
        """
        *archive the referenced entity*

        **Return:**

        - ``code`` -- the entity's Johnny Decimal code
        - ``archivedPath`` -- where its folder now lives
        - ``warnings`` -- a list of non-fatal problems encountered in the mirrors

        **Raises:**

        - ``ValueError`` -- if the ref does not resolve, or the move would be unsafe
        """
        self.log.debug("starting the ``get`` method")

        entityType, domain, row = self._resolve_target()
        code = self._code_for(entityType, domain, row)
        originalPath = row["folder_path"]

        self._guard(originalPath)

        destinationParent = self._nearest_archive_folder(entityType, domain, row)
        newFolderName = self._archived_folder_name(row)
        archivedPath = f"{destinationParent}/{newFolderName}"

        # CAPTURE THE MIRROR LINKS BEFORE THE DB WRITE DELETES THEM.
        mirrorLinks = self._mirror_links(entityType, row)
        descendants = self._descendants(entityType, domain, row)

        self._move_and_record(
            entityType, domain, row, code, originalPath, archivedPath, newFolderName,
            mirrorLinks, descendants,
        )

        self._archive_in_gdrive(entityType, row, mirrorLinks)
        self._archive_in_todoist(entityType, row, mirrorLinks)
        self._mark_archived_in_craft(entityType, row, mirrorLinks)

        self.log.debug("completed the ``get`` method")
        return code, archivedPath, self.warnings

    def _resolve_target(self):
        """
        *work out what the ref points at*

        **Return:**

        - ``entityType``, ``domain``, ``row`` -- `"area"`/`"category"`/`"id"`, the domain, and the index row

        **Raises:**

        - ``ValueError`` -- if the ref is not a Johnny Decimal ref, or does not resolve
        """
        return refs.resolve_ref(self.dbConn, self.ref, "archive")

    def _code_for(self, entityType, domain, row):
        """
        *the entity's Johnny Decimal code*

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``domain`` -- the entity's domain
        - ``row`` -- the index row

        **Return:**

        - ``code`` -- e.g. `"A11.10"`
        """
        if entityType == "area":
            return codes.format_area_code(domain, row["decade_start"], row["decade_end"])
        if entityType == "category":
            return codes.format_category_code(domain, row["ac_number"])
        return codes.format_id_code(domain, row["ac_number"], row["item_number"])

    def _guard(self, originalPath):
        """
        *refuse to archive anything containing the index database itself*

        `folders.move_folder_and_reindex` commits before it moves precisely
        because `00_INDEX` can be a rename target elsewhere. Archiving must
        never go near it: moving the directory holding the open SQLite file
        mid-transaction is exactly the failure that ordering exists to
        avoid, and no archive target should ever contain it anyway.

        **Key Arguments:**

        - ``originalPath`` -- the folder about to be moved

        **Raises:**

        - ``ValueError`` -- if the index database lives inside the target
        """
        rootPath = (self.settings.get("system") or {}).get("root_path")
        if not rootPath:
            return
        try:
            dbPath = os.path.realpath(paths.find_db_path(rootPath))
        except Exception:
            return
        target = os.path.realpath(originalPath)
        if dbPath == target or dbPath.startswith(target + os.sep):
            raise ValueError(
                f"refusing to archive '{originalPath}' - the aardvark index database lives inside it"
            )

    def _nearest_archive_folder(self, entityType, domain, row):
        """
        *the reserved archive folder closest above the entity being archived*

        An ID goes into its own category's `09_archive`; a category into its
        parent area's system-folder archive; an area into the domain's
        top-level system-folder archive. A system predating that scaffolding
        falls back to the root `09_ARCHIVE`, with a warning to run
        `repair_emoji`.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``domain`` -- the entity's domain
        - ``row`` -- the index row

        **Return:**

        - ``folderPath`` -- the absolute path of the archive folder to move into
        """
        if entityType == "id":
            folderKey = f"{domain}.{row['ac_number']}.09_archive"
        elif entityType == "category":
            area = self.dbConn.execute(
                "SELECT decade_start FROM areas WHERE area_id = ?", (row["area_id"],)
            ).fetchone()
            folderKey = f"{domain}.{area['decade_start']}.09_archive" if area else "root.archive"
        else:
            folderKey = f"{domain}.system.09_archive"

        try:
            return paths.resolve(self.dbConn, folderKey)
        except KeyError:
            self.warnings.append(
                f"no '{folderKey}' folder is recorded - archiving to the root archive instead; "
                "run `aardvark repair_emoji` to backfill the reserved scaffolding"
            )
            return paths.resolve(self.dbConn, "root.archive")

    def _archived_folder_name(self, row):
        """
        *the entity's folder name with an archive datestamp appended*

        The datestamp is load-bearing, not decoration: once a Johnny Decimal
        number is freed and handed to something new, that new entity can
        itself be archived into the same folder later. Without the stamp the
        second move would collide with the first.

        **Key Arguments:**

        - ``row`` -- the index row

        **Return:**

        - ``folderName`` -- e.g. `"A11.10_cardiologist__archived_20260820"`
        """
        stamp = datetime.now().strftime("%Y%m%d")
        return f"{row['folder_name']}__archived_{stamp}"

    def _descendants(self, entityType, domain, row):
        """
        *every index row beneath the entity, so each gets its own archive record*

        SQLite's `ON DELETE CASCADE` would drop these silently, leaving no
        trace of what an archived area actually contained - so they are
        collected first and written to `archived_entities` alongside their
        parent.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``domain`` -- the entity's domain
        - ``row`` -- the index row

        **Return:**

        - ``descendants`` -- a list of `(entityType, row)` pairs
        """
        descendants = []
        if entityType == "area":
            for category in db.list_categories(self.dbConn, domain, areaId=row["area_id"]):
                descendants.append(("category", category))
                for idRow in db.list_ids(self.dbConn, domain, category["category_id"]):
                    descendants.append(("id", idRow))
        elif entityType == "category":
            for idRow in db.list_ids(self.dbConn, domain, row["category_id"]):
                descendants.append(("id", idRow))
        return descendants

    def _mirror_links(self, entityType, row):
        """
        *the entity's last known Craft, Todoist, Drive and Dropbox links*

        Read before the archive transaction deletes them, both to store on
        the archive record and to drive the remote clean-up afterwards.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``row`` -- the index row

        **Return:**

        - ``links`` -- a dict with keys `craft`, `craft_document`, `todoist_id`, `todoist`, `gdrive_id`, `gdrive`, `dropbox`
        """
        entityKey = str(self._entity_key(entityType, row))
        craftLink = db.get_craft_link(self.dbConn, entityType, entityKey)
        craftIndexLink = db.get_craft_link(self.dbConn, f"{entityType}:index", entityKey)
        todoistLink = db.get_todoist_link(self.dbConn, entityType, entityKey)
        gdriveLink = db.get_gdrive_link(self.dbConn, entityType, entityKey)
        dropboxLink = db.get_dropbox_link(self.dbConn, row["folder_path"])
        return {
            "craft": craftLink["craft_url"] if craftLink else None,
            "craft_document": craftIndexLink["craft_document_id"] if craftIndexLink else None,
            "todoist_id": todoistLink["todoist_project_id"] if todoistLink else None,
            "todoist": todoistLink["todoist_url"] if todoistLink else None,
            "gdrive_id": gdriveLink["gdrive_folder_id"] if gdriveLink else None,
            "gdrive": gdriveLink["gdrive_url"] if gdriveLink else None,
            "dropbox": dropboxLink["dropbox_url"] if dropboxLink else None,
        }

    def _entity_key(self, entityType, row):
        """
        *the primary key column for an entity type*

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``row`` -- the index row

        **Return:**

        - ``entityKey`` -- the row's numeric id
        """
        return row[{"area": "area_id", "category": "category_id", "id": "id_id"}[entityType]]

    def _move_and_record(
        self, entityType, domain, row, code, originalPath, archivedPath, newFolderName,
        mirrorLinks, descendants,
    ):
        """
        *move the folder, write the archive records and drop the live rows, as one transaction*

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``domain`` -- the entity's domain
        - ``row`` -- the index row
        - ``code`` -- the entity's Johnny Decimal code
        - ``originalPath`` -- where the folder was
        - ``archivedPath`` -- where the folder is going
        - ``newFolderName`` -- the datestamped folder name
        - ``mirrorLinks`` -- the entity's last known mirror links
        - ``descendants`` -- the `(entityType, row)` pairs beneath it
        """
        updater = self._row_updater(entityType, row)
        folders.move_folder_and_reindex(self.dbConn, originalPath, archivedPath, updater)

        try:
            db.insert_archived_entity(
                self.dbConn,
                entityType=entityType,
                entityKey=self._entity_key(entityType, row),
                domain=domain,
                code=code,
                title=row["title"],
                folderName=row["folder_name"],
                originalPath=originalPath,
                archivedPath=archivedPath,
                decadeStart=row["decade_start"] if entityType == "area" else None,
                acNumber=None if entityType == "area" else row["ac_number"],
                itemNumber=row["item_number"] if entityType == "id" else None,
                description=row["description"],
                emoji=row["emoji"] if entityType != "id" else "",
                craftUrl=mirrorLinks["craft"],
                todoistUrl=mirrorLinks["todoist"],
                gdriveUrl=mirrorLinks["gdrive"],
                dropboxUrl=mirrorLinks["dropbox"],
            )

            for descendantType, descendantRow in descendants:
                descendantCode = self._code_for(descendantType, domain, descendantRow)
                # THE ROWS WERE READ BEFORE THE MOVE, SO THEIR `folder_path` IS
                # STILL THE OLD ONE - SWAP THE MOVED PARENT'S PREFIX FOR ITS NEW
                # LOCATION, EXACTLY AS `db.rewrite_folder_path_prefix` JUST DID
                # TO THE LIVE ROWS.
                descendantOriginalPath = descendantRow["folder_path"]
                descendantArchivedPath = descendantOriginalPath.replace(
                    originalPath, archivedPath, 1,
                )
                db.insert_archived_entity(
                    self.dbConn,
                    entityType=descendantType,
                    entityKey=self._entity_key(descendantType, descendantRow),
                    domain=domain,
                    code=descendantCode,
                    title=descendantRow["title"],
                    folderName=descendantRow["folder_name"],
                    originalPath=descendantOriginalPath,
                    archivedPath=descendantArchivedPath,
                    decadeStart=None,
                    acNumber=descendantRow["ac_number"],
                    itemNumber=descendantRow["item_number"] if descendantType == "id" else None,
                    description=descendantRow["description"],
                    emoji=descendantRow["emoji"] if descendantType != "id" else "",
                )
                db.delete_entity_links(
                    self.dbConn, descendantType, self._entity_key(descendantType, descendantRow),
                )

            self._forget_reserved_scaffolding(entityType, domain, row, descendants)
            db.delete_entity_links(self.dbConn, entityType, self._entity_key(entityType, row))
            db.delete_dropbox_links_with_prefix(self.dbConn, originalPath)

            if entityType == "area":
                db.delete_area(self.dbConn, row["area_id"])
            elif entityType == "category":
                db.delete_category(self.dbConn, row["category_id"])
            else:
                db.delete_id(self.dbConn, row["id_id"])

            self.dbConn.commit()
        except Exception:
            self.dbConn.rollback()
            # PUT THE FOLDER BACK - THE INDEX STILL DESCRIBES IT WHERE IT WAS.
            try:
                os.rename(archivedPath, originalPath)
            except OSError:
                self.warnings.append(
                    f"the index write failed and '{archivedPath}' could not be moved back to "
                    f"'{originalPath}' - move it by hand"
                )
            raise

    def _row_updater(self, entityType, row):
        """
        *the callable `move_folder_and_reindex` uses to repoint the entity's own row*

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``row`` -- the index row

        **Return:**

        - ``updateRows`` -- a callable taking `(newFolderName, newFolderPath)`
        """
        if entityType == "area":
            return lambda name, path: db.update_area_emoji(
                self.dbConn, row["area_id"], row["emoji"], name, path,
            )
        if entityType == "category":
            return lambda name, path: db.update_category_emoji(
                self.dbConn, row["category_id"], row["emoji"], name, path,
            )
        return lambda name, path: db.update_id_name(self.dbConn, row["id_id"], name, path)

    def _forget_reserved_scaffolding(self, entityType, domain, row, descendants):
        """
        *drop the `system_folders` rows for reserved scaffolding travelling into the archive*

        `folders.create_reserved_system_ids` early-returns on an
        already-recorded folder key, so leaving these behind would mean the
        next entity handed the same number silently got no scaffolding of
        its own and inherited paths pointing inside the archive.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``domain`` -- the entity's domain
        - ``row`` -- the index row
        - ``descendants`` -- the `(entityType, row)` pairs beneath it
        """
        if entityType == "id":
            return

        if entityType == "category":
            db.delete_system_folders_with_prefix(self.dbConn, f"{domain}.{row['ac_number']}.")
            return

        # AN AREA TAKES ITS OWN SYSTEM FOLDER AND EVERY CATEGORY'S WITH IT. THE
        # TWO PREFIXES CANNOT COLLIDE: A DECADE START IS ALWAYS A MULTIPLE OF
        # TEN, AND A CATEGORY NUMBER NEVER IS.
        db.delete_system_folders_with_prefix(self.dbConn, f"{domain}.{row['decade_start']}.")
        for descendantType, descendantRow in descendants:
            if descendantType == "category":
                db.delete_system_folders_with_prefix(
                    self.dbConn, f"{domain}.{descendantRow['ac_number']}.",
                )

    def _archive_in_gdrive(self, entityType, row, mirrorLinks):
        """
        *move the mirrored Drive folder into the Drive archive folder*

        Drive models parentage as a list, so this is a genuine move -
        the one mirror that can do it.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``row`` -- the index row
        - ``mirrorLinks`` -- the entity's last known mirror links
        """
        if not (self.settings.get("gdrive") or {}).get("enabled"):
            return
        folderId = mirrorLinks["gdrive_id"]
        if not folderId:
            return
        try:
            from aardvark_jd.gdrive_client import GDriveClient

            gdriveSettings = self.settings["gdrive"]
            client = GDriveClient(
                clientId=gdriveSettings["client_id"],
                clientSecret=gdriveSettings["client_secret"],
                refreshToken=gdriveSettings["refresh_token"],
            )
            archiveLink = db.get_gdrive_link(self.dbConn, "system_folder", "root.archive")
            if not archiveLink or not archiveLink["gdrive_folder_id"]:
                self.warnings.append(
                    "the Google Drive archive folder has not been mirrored yet - "
                    "run `aardvark gdrive_sync` and move the folder by hand"
                )
                return
            parents = self.client_parents(client, folderId)
            client.move_folder(folderId, archiveLink["gdrive_folder_id"], ",".join(parents))
        except Exception as error:
            self.warnings.append(f"google drive archive failed: {error}")

    def client_parents(self, client, folderId):
        """
        *the current parent ids of a Drive folder, needed to detach it on a move*

        **Key Arguments:**

        - ``client`` -- an open `GDriveClient`
        - ``folderId`` -- the folder's Drive id

        **Return:**

        - ``parents`` -- a list of parent folder ids
        """
        payload = client._request("GET", f"/files/{folderId}", params={"fields": "parents"})
        return payload.get("parents") or []

    def _archive_in_todoist(self, entityType, row, mirrorLinks):
        """
        *archive the mirrored Todoist project*

        Archived rather than deleted - a Todoist project carries tasks, and
        deleting it would take them with it irreversibly.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``row`` -- the index row
        - ``mirrorLinks`` -- the entity's last known mirror links
        """
        if not (self.settings.get("todoist") or {}).get("enabled"):
            return
        projectId = mirrorLinks["todoist_id"]
        if not projectId:
            return
        try:
            from aardvark_jd.todoist_client import TodoistClient

            TodoistClient(apiToken=self.settings["todoist"]["api_token"]).archive_project(projectId)
        except Exception as error:
            self.warnings.append(f"todoist archive failed: {error}")

    def _mark_archived_in_craft(self, entityType, row, mirrorLinks):
        """
        *flag the mirrored Craft document as archived, and say what cannot be automated*

        Craft's API has no move and no delete for folders or documents, so
        the mirrored folder cannot follow the filesystem into the archive.
        What is possible is a banner on its index document and a clear note
        to the user - the same honest treatment the orphaned ID documents
        got when IDs changed shape.

        **Key Arguments:**

        - ``entityType`` -- `"area"`, `"category"` or `"id"`
        - ``row`` -- the index row
        - ``mirrorLinks`` -- the entity's last known mirror links
        """
        if not (self.settings.get("craft") or {}).get("enabled"):
            return

        documentId = mirrorLinks["craft_document"]
        if documentId:
            try:
                from aardvark_jd.craft_client import CraftClient

                craftSettings = self.settings["craft"]
                client = CraftClient(
                    apiUrl=craftSettings["api_url"], apiToken=craftSettings["api_token"],
                )
                stamp = datetime.now().strftime("%Y-%m-%d")
                client.add_block(
                    documentId,
                    f"> ⚠️ Archived {stamp} - no longer tracked by aardvark, safe to delete.",
                    position="start",
                )
            except Exception as error:
                self.warnings.append(f"could not add the Craft archive banner: {error}")

        self.warnings.append(
            f"the Craft folder for '{folders.display_name(row['folder_name'])}' cannot be moved or "
            "deleted via the API - delete it by hand in the Craft app"
        )

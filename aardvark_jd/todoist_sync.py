#!/usr/bin/env python
# encoding: utf-8
"""
*Mirror the aardvark index into Todoist as nested projects, with a cross-link back to Craft/Finder/Dropbox*

Todoist has no notion of "Workspaces" on a personal (non-Business) plan,
so the whole mirror lives under one top-level project named after the
aardvark system itself (`settings["system"]["name"]`). Only two of the
five PARA roots are mirrored, each shaped differently:

- `03 AREAS` mirrors areas and their categories, nested two deep. There
  is no ID level in Todoist - individual reference items under an area
  stay in Craft/the filesystem only.
- `02 PROJECTS` mirrors every project ID as a flat child directly under
  it - the intervening project areas/categories are not mirrored, since
  a project ID is the actionable unit and Todoist's own nesting is
  better spent on the project's own sections/tasks than on Johnny
  Decimal structure it doesn't need.

`01 INBOX`, `04 RESOURCES`, `09 ARCHIVE` and every `00-09_system`
scaffolding folder are never mirrored - none of them represent
actionable work.

Each mirrored project's description carries a Finder/Dropbox/Craft link
row back to its sibling objects (see `doc_links.todoist_description_markdown`),
and the reverse link (Todoist -> Craft) is written by `craft_sync`, which
is why `todoist_sync` must run *before* `craft_sync` on every mutating
command - see `cl_utils._maybe_sync_todoist`.

Author
: David Young
"""

from aardvark_jd import db, doc_links, dropbox_client, folders, http_retry
from aardvark_jd.dropbox_client import DropboxClient
from aardvark_jd.todoist_client import TodoistClient

_AREAS_ROOT_KEY = "root.areas"
_PROJECTS_ROOT_KEY = "root.projects"


class todoist_sync(object):
    """
    *idempotently mirror the current aardvark index into a connected Todoist account*

    Every project created is recorded in the new `todoist_links` table
    keyed by aardvark entity, mirroring `craft_links` - re-running only
    creates what's missing and otherwise refreshes an entity's
    description when it's changed. Project identity is resolved by
    `(parentId, name)` against a single `list_projects()` call at the
    start of each sync, the same adopt-or-create idempotency
    `craft_sync._load_folder_index` uses for Craft folders.

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``settings`` -- the aardvark settings dict; must have `todoist.enabled: true` and `todoist.api_token` set

    **Usage:**

    ```python
    from aardvark_jd.todoist_sync import todoist_sync
    summary = todoist_sync(log=log, dbConn=dbConn, settings=settings).get()
    ```
    """

    def __init__(self, log, dbConn, settings):
        self.log = log
        self.dbConn = dbConn

        todoistSettings = (settings or {}).get("todoist") or {}
        if not todoistSettings.get("enabled"):
            raise ValueError("todoist is not connected - run `aardvark connect_todoist <apiToken>` first")
        apiToken = todoistSettings.get("api_token")
        if not apiToken:
            raise ValueError("no todoist api_token configured - run `aardvark connect_todoist <apiToken>` first")

        # ONE BACKOFF BUDGET FOR THE WHOLE RUN (SEE `http_retry.RunBudget`).
        self.retryBudget = http_retry.RunBudget()
        self.client = TodoistClient(apiToken=apiToken, budget=self.retryBudget)
        self.systemName = (settings.get("system") or {}).get("name") or "aardvark"
        self.projectsCreated = 0
        self.descriptionsUpdated = 0
        self.projectIndex = {}

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
        *sync the areas and projects domains into Todoist, under one system-named root project*

        **Return:**

        - ``summary`` -- a dict of counts: `projects_created`, `descriptions_updated`
        """
        self.log.debug("starting the ``get`` method")

        self._load_project_index()
        rootId = self._ensure_project(None, self.systemName)

        areasParentId = self._ensure_project(rootId, self._domain_root_name(_AREAS_ROOT_KEY))
        self._sync_areas_domain(areasParentId)

        projectsParentId = self._ensure_project(rootId, self._domain_root_name(_PROJECTS_ROOT_KEY))
        self._sync_projects_domain(projectsParentId)

        self.log.debug("completed the ``get`` method")
        return {
            "projects_created": self.projectsCreated,
            "descriptions_updated": self.descriptionsUpdated,
        }

    def _domain_root_name(self, systemFolderKey):
        """
        *the display name for a PARA root folder, mirroring `craft_sync`'s own root-folder naming*

        **Key Arguments:**

        - ``systemFolderKey`` -- the root folder's `system_folders.folder_key`, e.g. `"root.areas"`

        **Return:**

        - ``name`` -- the display name, e.g. `"03 AREAS🧭"`
        """
        systemFolder = db.get_system_folder(self.dbConn, systemFolderKey)
        return folders.display_name(systemFolder["folder_name"])

    def _sync_areas_domain(self, areasParentId):
        """
        *mirror the `areas` domain's areas and categories, nested two deep, under `03 AREAS`*

        **Key Arguments:**

        - ``areasParentId`` -- the `03 AREAS` Todoist project's id
        """
        for area in db.list_areas(self.dbConn, "areas"):
            areaName = folders.display_name(area["folder_name"])
            areaProjectId = self._ensure_project(areasParentId, areaName)
            self._sync_entity("area", str(area["area_id"]), areaProjectId, area["folder_path"])

            for category in db.list_categories(self.dbConn, "areas", areaId=area["area_id"]):
                categoryName = folders.display_name(category["folder_name"])
                categoryProjectId = self._ensure_project(areaProjectId, categoryName)
                self._sync_entity("category", str(category["category_id"]), categoryProjectId, category["folder_path"])

    def _sync_projects_domain(self, projectsParentId):
        """
        *mirror the `projects` domain's IDs as a flat list directly under `02 PROJECTS`*

        Project areas and categories exist only to number and template
        IDs on the filesystem - they carry no independent Todoist
        project of their own, so this walks straight to `db.list_ids`
        without mirroring the levels above it.

        **Key Arguments:**

        - ``projectsParentId`` -- the `02 PROJECTS` Todoist project's id
        """
        for area in db.list_areas(self.dbConn, "projects"):
            for category in db.list_categories(self.dbConn, "projects", areaId=area["area_id"]):
                for idRow in db.list_ids(self.dbConn, "projects", category["category_id"]):
                    idName = folders.display_name(idRow["folder_name"])
                    idProjectId = self._ensure_project(projectsParentId, idName)
                    self._sync_entity("id", str(idRow["id_id"]), idProjectId, idRow["folder_path"])

    # ------------------------------------------------------------------ #
    # idempotent create-or-reuse helpers, backed by `todoist_links`
    # ------------------------------------------------------------------ #

    def _load_project_index(self):
        """
        *index every project already in the Todoist account by `(parentId, name)`*

        Unlike Craft, a Todoist project's id is durable across syncs, but
        the same adopt-by-name-and-parent approach is used anyway - it
        makes a sync self-healing if a project was renamed or moved by
        hand, and means `todoist_links` never has to be trusted as the
        sole source of truth for "does this project already exist".
        """
        self.projectIndex = {}
        for project in self.client.list_projects():
            self.projectIndex[(project.get("parent_id"), project["name"])] = project["id"]

    def _ensure_project(self, parentId, name):
        """
        *adopt the matching project already in the account, otherwise create it*

        **Key Arguments:**

        - ``parentId`` -- the parent project's id, or `None` for a top-level project
        - ``name`` -- the project's name, mirroring its on-disk folder name

        **Return:**

        - ``projectId`` -- the adopted or newly-created project's id
        """
        projectId = self.projectIndex.get((parentId, name))
        if projectId is None:
            projectId = self.client.create_project(name, parentId=parentId)
            self.projectIndex[(parentId, name)] = projectId
            self.projectsCreated += 1
        return projectId

    def _sync_entity(self, entityType, entityKey, projectId, folderPath):
        """
        *(re)write a mirrored entity's Finder/Dropbox/Craft description, skipping the API round-trip when nothing changed*

        **Key Arguments:**

        - ``entityType`` -- `'area'`, `'category'` or `'id'`
        - ``entityKey`` -- the entity's `area_id`/`category_id`/`id_id`, cast to text
        - ``projectId`` -- the entity's Todoist project id
        - ``folderPath`` -- the entity's own absolute folder path
        """
        hookmarkUrl = doc_links.hookmark_url(folderPath)
        dropboxUrl = dropbox_client.url_for_path(
            self.dbConn, self.dropboxClient, self.dropboxRoot, folderPath, self.log,
        )
        craftLink = db.get_craft_link(self.dbConn, entityType, entityKey)
        craftUrl = craftLink["craft_url"] if craftLink else None
        gdriveLink = db.get_gdrive_link(self.dbConn, entityType, entityKey)
        gdriveUrl = gdriveLink["gdrive_url"] if gdriveLink else None
        description = doc_links.todoist_description_markdown(
            hookmarkUrl, dropboxUrl, craftUrl, driveUrl=gdriveUrl,
        )

        existing = db.get_todoist_link(self.dbConn, entityType, entityKey)
        todoistUrl = self.client.project_url(projectId)
        if existing and existing["todoist_project_id"] == projectId and existing["description"] == description:
            return

        if description:
            self.client.update_project_description(projectId, description)
            self.descriptionsUpdated += 1

        db.upsert_todoist_link(
            self.dbConn, entityType, entityKey,
            todoistProjectId=projectId, todoistUrl=todoistUrl, description=description,
        )

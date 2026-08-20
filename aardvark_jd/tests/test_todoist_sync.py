import logging
import os

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd import todoist_sync as todoist_sync_module
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser
from aardvark_jd.add_project import add_project
from aardvark_jd.todoist_sync import todoist_sync

log = logging.getLogger("test_todoist_sync")
log.addHandler(logging.NullHandler())


class FakeTodoistClient(object):
    """*records every project created and every description written, without any HTTP calls*"""

    def __init__(self, apiToken):
        self.apiToken = apiToken
        self._counter = 0
        self.projects = []  # (id, name, parentId)
        self.descriptionsSet = []  # (projectId, description)

    def _next_id(self):
        self._counter += 1
        return f"proj-{self._counter}"

    def list_projects(self):
        return [{"id": pid, "name": name, "parent_id": parent} for pid, name, parent in self.projects]

    def create_project(self, name, parentId=None, description=None):
        projectId = self._next_id()
        self.projects.append((projectId, name, parentId))
        if description is not None:
            self.descriptionsSet.append((projectId, description))
        return projectId

    def update_project_description(self, projectId, description):
        self.descriptionsSet.append((projectId, description))

    @staticmethod
    def project_url(projectId):
        return f"https://app.todoist.com/app/project/{projectId}"


@pytest.fixture
def dbConn(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    yield conn
    conn.close()


@pytest.fixture
def todoistSettings(dbConn):
    rootPath = os.path.dirname(db.get_system_folder(dbConn, "root.index")["folder_path"])
    return {
        "todoist": {"enabled": True, "api_token": "fake-token"},
        "system": {"name": "Test", "root_path": rootPath},
    }


@pytest.fixture
def fakeClient(monkeypatch):
    client = FakeTodoistClient(apiToken="fake-token")
    monkeypatch.setattr(todoist_sync_module, "TodoistClient", lambda apiToken: client)
    return client


def test_todoist_sync_requires_enabled(dbConn):
    with pytest.raises(ValueError):
        todoist_sync(log=log, dbConn=dbConn, settings={"todoist": {"enabled": False}}).get()


def test_todoist_sync_requires_api_token(dbConn):
    with pytest.raises(ValueError):
        todoist_sync(log=log, dbConn=dbConn, settings={"todoist": {"enabled": True}}).get()


def test_todoist_sync_mirrors_areas_and_categories_under_the_system_root(dbConn, todoistSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()

    todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()

    byName = {name: (pid, parent) for pid, name, parent in fakeClient.projects}
    rootId, _ = byName["Test"]
    areasRootId, areasRootParent = byName["03 AREAS🧭"]
    assert areasRootParent == rootId

    areaId, areaParent = next((pid, parent) for name, (pid, parent) in byName.items() if name.startswith("A10-19 health"))
    assert areaParent == areasRootId

    categoryId, categoryParent = next((pid, parent) for name, (pid, parent) in byName.items() if name.startswith("A11 doctors"))
    assert categoryParent == areaId

    # no ID level under areas - only areas and categories are mirrored there
    assert not any(name.startswith("A11.") for name in byName)


def test_todoist_sync_mirrors_project_ids_flat_under_the_projects_root(dbConn, todoistSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="projects", title="Launches", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="projects", areaRef="P10", title="Website", description="d2").get()
    add_project(log=log, dbConn=dbConn, categoryRef="P11", projectTitle="Relaunch").get()

    todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()

    byName = {name: (pid, parent) for pid, name, parent in fakeClient.projects}
    projectsRootId, _ = byName["02 PROJECTS🚀"]

    idProjectId, idParent = next((pid, parent) for name, (pid, parent) in byName.items() if name.startswith("P11.10 relaunch"))
    assert idParent == projectsRootId

    # the intervening project area/category are never mirrored to Todoist
    assert not any(name.startswith("P10-19 launches") for name in byName)
    assert not any(name.startswith("P11 website") for name in byName)


def test_todoist_sync_skips_resources_inbox_archive_and_system_folders(dbConn, todoistSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="resources", title="Reading", description="d1").get()

    todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()

    names = {name for _pid, name, _parent in fakeClient.projects}
    assert not any("RESOURCES" in name for name in names)
    assert not any("INBOX" in name for name in names)
    assert not any("ARCHIVE" in name for name in names)
    assert not any("system" in name for name in names)


def test_todoist_sync_description_carries_finder_and_craft_links(dbConn, todoistSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    db.upsert_craft_link(dbConn, "area", "1", craftFolderId="folder-1", craftUrl="craftdocs://openfolder?folderId=folder-1")

    todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()

    byName = {name: pid for pid, name, _parent in fakeClient.projects}
    areaId = next(pid for name, pid in byName.items() if name.startswith("A10-19 health"))
    description = next(desc for pid, desc in fakeClient.descriptionsSet if pid == areaId)
    assert "Craft" in description
    assert "craftdocs://openfolder?folderId=folder-1" in description


def test_todoist_sync_is_idempotent(dbConn, todoistSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()

    todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()
    projectsAfterFirst = len(fakeClient.projects)

    summary = todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()

    assert len(fakeClient.projects) == projectsAfterFirst
    assert summary["projects_created"] == 0
    assert summary["descriptions_updated"] == 0


def test_todoist_sync_adopts_projects_already_in_the_account(dbConn, todoistSettings, fakeClient):
    todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()
    projectsAfterFirst = list(fakeClient.projects)

    summary = todoist_sync(log=log, dbConn=dbConn, settings=todoistSettings).get()

    assert summary["projects_created"] == 0
    assert fakeClient.projects == projectsAfterFirst

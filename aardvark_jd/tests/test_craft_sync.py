import logging

import pytest
import yaml

from aardvark_jd import craft_sync as craft_sync_module
from aardvark_jd import db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.craft_sync import craft_sync
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_craft_sync")
log.addHandler(logging.NullHandler())


class FakeCraftClient(object):
    """*records every folder/document/block created or updated, without any HTTP calls*"""

    def __init__(self, apiUrl, apiToken):
        self.apiUrl = apiUrl
        self.apiToken = apiToken
        self._counter = 0
        self.folders = []
        self.documents = []
        self.blocksAdded = []
        self.blocksUpdated = []
        self.listFolderCalls = 0

    def _next_id(self, prefix):
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def list_folders(self):
        """*rebuild the nested tree the real `GET /folders` returns, from what's been created*"""
        self.listFolderCalls += 1

        def children_of(parentFolderId):
            return [
                {"id": folderId, "name": name, "folders": children_of(folderId)}
                for folderId, name, parent in self.folders if parent == parentFolderId
            ]

        return children_of(None)

    def folder_deep_link(self, folderId, title):
        return f"craftdocs://openfolder?folderId={folderId}&spaceId=space-1&title={title}"

    def create_folder(self, name, parentFolderId=None):
        folderId = self._next_id("folder")
        self.folders.append((folderId, name, parentFolderId))
        return folderId

    def create_document(self, title, folderId=None):
        documentId = self._next_id("doc")
        self.documents.append((documentId, title, folderId))
        return documentId, f"https://craft.example/doc/{documentId}"

    def add_block(self, documentId, markdown, position="end"):
        blockId = self._next_id("block")
        self.blocksAdded.append((documentId, markdown, blockId))
        return blockId

    def update_block(self, blockId, markdown):
        self.blocksUpdated.append((blockId, markdown))

    def index_bodies(self):
        """*every index markdown body ever written, in write order*"""
        return [markdown for _documentId, markdown, _blockId in self.blocksAdded] + \
            [markdown for _blockId, markdown in self.blocksUpdated]


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
def craftSettings():
    return {"craft": {"enabled": True, "api_url": "https://connect.craft.do/links/abc123/api/v1", "api_token": "fake-token"}}


@pytest.fixture
def fakeClient(monkeypatch):
    client = FakeCraftClient(apiUrl="https://connect.craft.do/links/abc123/api/v1", apiToken="fake-token")
    monkeypatch.setattr(craft_sync_module, "CraftClient", lambda apiUrl, apiToken: client)
    return client


def test_craft_sync_requires_enabled(dbConn):
    with pytest.raises(ValueError):
        craft_sync(log=log, dbConn=dbConn, settings={"craft": {"enabled": False}}).get()


def test_craft_sync_requires_api_url_and_token(dbConn):
    with pytest.raises(ValueError):
        craft_sync(log=log, dbConn=dbConn, settings={"craft": {"enabled": True}}).get()
    with pytest.raises(ValueError):
        craft_sync(log=log, dbConn=dbConn, settings={"craft": {"enabled": True, "api_url": "https://x"}}).get()
    with pytest.raises(ValueError):
        craft_sync(log=log, dbConn=dbConn, settings={"craft": {"enabled": True, "api_token": "tok"}}).get()


def test_craft_sync_mirrors_root_folders(dbConn, craftSettings, fakeClient):
    summary = craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    # craft folder names mirror the on-disk names, underscores rendered as spaces
    # and the emoji carried in the name itself (craft has no folder icon field)
    folderNames = {name for _id, name, _parent in fakeClient.folders}
    assert {"01 INBOX📥", "02 PROJECTS🚀", "03 AREAS🧭", "04 RESOURCES📚", "09 ARCHIVE🗄️"} <= folderNames
    assert summary["folders_created"] >= 5

    # the space-root index should link out to all five, and only those five -
    # it's written last, so it's the final block added
    spaceIndexBody = fakeClient.blocksAdded[-1][1]
    for title in ("01 INBOX📥", "02 PROJECTS🚀", "03 AREAS🧭", "04 RESOURCES📚", "09 ARCHIVE🗄️"):
        assert title in spaceIndexBody

    # folders are linked with a craftdocs://openfolder deep link, not left as plain text
    assert "[01 INBOX📥](craftdocs://openfolder?folderId=" in spaceIndexBody


def test_craft_sync_mirrors_area_category_id_nesting(dbConn, craftSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="11", title="Cardiologist", description="d3").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    # the decade range keeps its hyphen; everything else mirrors the (lowercased) disk
    # name. the trailing emoji is auto-picked, so match on the prefix only
    folderTitles = {name for _id, name, _parent in fakeClient.folders}
    assert any(name.startswith("A10-19 health") for name in folderTitles)
    assert any(name.startswith("A11 doctors") for name in folderTitles)

    documentTitles = {title for _id, title, _folder in fakeClient.documents}
    assert any(title.startswith("A11.10 cardiologist") for title in documentTitles)

    # the category's own "00 Index" should list the new ID one level down
    assert any("A11.10 cardiologist" in body and "d3" in body for body in fakeClient.index_bodies())


def test_craft_sync_nests_areas_under_their_domain_root(dbConn, craftSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    byName = {name: (folderId, parent) for folderId, name, parent in fakeClient.folders}
    areasRootId, _ = byName["03 AREAS🧭"]
    areaParents = [parent for name, (_id, parent) in byName.items() if name.startswith("A10-19 health")]
    assert areaParents == [areasRootId]


def test_craft_sync_adopts_folders_already_in_the_space(dbConn, craftSettings, fakeClient):
    """*a folder matching by name+parent is reused, not duplicated - craft re-keys folder ids*"""
    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()
    foldersAfterFirst = list(fakeClient.folders)

    # craft re-keys every folder id behind our back, exactly as the live API does
    fakeClient.folders = [(f"rekeyed-{folderId}", name, parent) for folderId, name, parent in foldersAfterFirst]

    summary = craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    assert summary["folders_created"] == 0
    assert len(fakeClient.folders) == len(foldersAfterFirst)
    # the link table should have been refreshed onto the new ids
    link = db.get_craft_link(dbConn, "system_folder", "root.areas")
    assert link["craft_folder_id"].startswith("rekeyed-")
    assert "rekeyed-" in link["craft_url"]


def test_craft_sync_is_idempotent(dbConn, craftSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="11", title="Cardiologist", description="d3").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()
    foldersAfterFirst = len(fakeClient.folders)
    documentsAfterFirst = len(fakeClient.documents)
    blocksAddedAfterFirst = len(fakeClient.blocksAdded)

    summary = craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    assert len(fakeClient.folders) == foldersAfterFirst
    assert len(fakeClient.documents) == documentsAfterFirst
    assert len(fakeClient.blocksAdded) == blocksAddedAfterFirst
    assert summary["folders_created"] == 0
    assert summary["documents_created"] == 0
    assert summary["indexes_refreshed"] > 0
    # every index refresh on the second run updates its existing block in place
    assert len(fakeClient.blocksUpdated) == summary["indexes_refreshed"]


def test_craft_sync_mirrors_projects_as_flat_documents(dbConn, craftSettings, fakeClient):
    from aardvark_jd.new_project import new_project

    new_project(log=log, dbConn=dbConn, templateName="blank", projectTitle="Website Relaunch").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    documentTitles = {title for _id, title, _folder in fakeClient.documents}
    assert "Website Relaunch📁" in documentTitles

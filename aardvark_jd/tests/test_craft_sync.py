import logging
import os

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
    """*records every folder/document/block created or deleted, without any HTTP calls*

    Models the real API's read-delete-insert index refresh: `add_block`
    appends to a per-document content list (each call its own block id,
    same as a real multi-line `POST /blocks` splitting into siblings would
    look from the caller's side), `get_block` reads that list back, and
    `delete_blocks` removes matching ids from it - mirroring the empirical
    probe against a real space.
    """

    def __init__(self, apiUrl, apiToken):
        self.apiUrl = apiUrl
        self.apiToken = apiToken
        self._counter = 0
        self.folders = []
        self.documents = []
        self.blocksAdded = []
        self.blocksDeleted = []
        self._documentContent = {}
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
        self._documentContent[documentId] = []
        return documentId, f"https://craft.example/doc/{documentId}"

    def add_block(self, documentId, markdown, position="end"):
        blockId = self._next_id("block")
        self.blocksAdded.append((documentId, markdown, blockId))
        self._documentContent.setdefault(documentId, []).append((blockId, markdown))
        return blockId

    def get_block(self, blockId):
        content = self._documentContent.get(blockId, [])
        return {"id": blockId, "content": [{"id": bId, "markdown": md} for bId, md in content]}

    def delete_blocks(self, blockIds):
        self.blocksDeleted.extend(blockIds)
        blockIdSet = set(blockIds)
        for documentId, items in self._documentContent.items():
            self._documentContent[documentId] = [(bId, md) for bId, md in items if bId not in blockIdSet]

    def index_bodies(self):
        """*every index markdown body ever added, in write order - includes content later replaced*"""
        return [markdown for _documentId, markdown, _blockId in self.blocksAdded]


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
def craftSettings(dbConn):
    # `system.root_path` is always populated by the time real code ever
    # constructs `craft_sync` - `cl_utils.main` refuses to proceed without
    # it - so this fixture derives the real root from `dbConn` rather than
    # leaving it unset, matching what every caller actually sees.
    rootPath = os.path.dirname(db.get_system_folder(dbConn, "root.index")["folder_path"])
    return {
        "craft": {"enabled": True, "api_url": "https://connect.craft.do/links/abc123/api/v1", "api_token": "fake-token"},
        "system": {"root_path": rootPath},
    }


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
    # it's written last, immediately followed by its own Finder/Dropbox link
    # row (see `_refresh_index`), so it's the second-to-last block added
    spaceIndexBody = fakeClient.blocksAdded[-2][1]
    for title in ("01 INBOX📥", "02 PROJECTS🚀", "03 AREAS🧭", "04 RESOURCES📚", "09 ARCHIVE🗄️"):
        assert title in spaceIndexBody

    # folders are linked with a craftdocs://openfolder deep link, not left as plain text
    assert "[01 INBOX📥](craftdocs://openfolder?folderId=" in spaceIndexBody


def test_craft_sync_mirrors_area_category_id_nesting(dbConn, craftSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="A11", title="Cardiologist", description="d3").get()

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


def test_craft_sync_mirrors_the_three_level_system_scaffolding(dbConn, craftSettings, fakeClient):
    """*domain- and area-level system folders, and their reserved subfolders, mirror three levels deep*"""
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    byName = {name: (folderId, parent) for folderId, name, parent in fakeClient.folders}
    documentTitles = {title for _id, title, _folder in fakeClient.documents}

    # the domain's own system folder nests under the domain root, alongside its areas
    areasRootId, _ = byName["03 AREAS🧭"]
    domainSystemFolderId, domainSystemParent = byName["A00-09 system⚙️"]
    assert domainSystemParent == areasRootId

    # the area's own system folder nests under the area, alongside its categories
    areaFolderId = next(fid for name, (fid, _p) in byName.items() if name.startswith("A10-19 health"))
    areaSystemFolderId, areaSystemParent = byName["A10 system⚙️"]
    assert areaSystemParent == areaFolderId

    # a folder-kind reserved subfolder mirrors as a Craft folder, nested inside the system folder
    _inboxFolderId, inboxParent = byName["A10.01 inbox📥"]
    assert inboxParent == areaSystemFolderId

    # a document-kind reserved subfolder mirrors as a Craft document, not a folder
    assert "A10.02 llm🤖" not in byName
    assert any(title.startswith("A10.02 llm") for title in documentTitles)

    # the area's reserved `.00_index` document is now ITS index, listing the area's
    # categories - there's no more free-standing "00 Index" document at area level
    assert any("A11 doctors" in body and "d2" in body for body in fakeClient.index_bodies())

    # a category has no system folder of its own - its reserved subfolders sit directly
    # inside the category folder, alongside its user-created ids
    categoryFolderId = next(fid for name, (fid, _p) in byName.items() if name.startswith("A11 doctors"))
    _catInboxId, catInboxParent = byName["A11.01 inbox📥"]
    assert catInboxParent == categoryFolderId

    # the domain-root system folder's own index lists this domain's areas - also no
    # longer a free-standing "00 Index" document directly under the domain root
    assert any("A10-19 health" in body and "d1" in body for body in fakeClient.index_bodies())


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

    # craft re-keys every folder id behind our back, exactly as the live API does - the
    # nesting itself is untouched, so parent references are rekeyed the same way
    def rekey(folderId):
        return f"rekeyed-{folderId}" if folderId is not None else None

    fakeClient.folders = [
        (rekey(folderId), name, rekey(parent)) for folderId, name, parent in foldersAfterFirst
    ]

    summary = craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    assert summary["folders_created"] == 0
    assert len(fakeClient.folders) == len(foldersAfterFirst)
    # the link table should have been refreshed onto the new ids
    link = db.get_craft_link(dbConn, "system_folder", "root.areas")
    assert link["craft_folder_id"].startswith("rekeyed-")
    assert "rekeyed-" in link["craft_url"]


def test_craft_sync_is_idempotent(dbConn, craftSettings, fakeClient):
    add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="A11", title="Cardiologist", description="d3").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()
    foldersAfterFirst = len(fakeClient.folders)
    documentsAfterFirst = len(fakeClient.documents)
    blocksAddedAfterFirst = len(fakeClient.blocksAdded)

    summary = craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    assert len(fakeClient.folders) == foldersAfterFirst
    assert len(fakeClient.documents) == documentsAfterFirst
    assert summary["folders_created"] == 0
    assert summary["documents_created"] == 0
    assert summary["indexes_refreshed"] > 0
    # every index refresh on the second run deletes its whole prior content and re-inserts
    # fresh content, rather than updating a single block in place (there's no single block
    # to address - see `_refresh_index`) - and since the link row lives in the same
    # document, it's wiped and force-rewritten alongside the index content every time,
    # so each refreshed index document contributes two deletes and two adds (content +
    # link row), not one. The id documents' own link rows are untouched on this run -
    # their folder paths are unchanged, so `_write_link_row` skips them entirely.
    assert len(fakeClient.blocksDeleted) == 2 * summary["indexes_refreshed"]
    assert len(fakeClient.blocksAdded) == blocksAddedAfterFirst + 2 * summary["indexes_refreshed"]
    assert summary["link_rows_written"] == summary["indexes_refreshed"]


def test_craft_sync_mirrors_the_projects_domain_like_areas_and_resources(dbConn, craftSettings, fakeClient):
    from aardvark_jd.new_project import new_project

    add_area(log=log, dbConn=dbConn, domain="projects", title="Launches", description="d1").get()
    add_category(log=log, dbConn=dbConn, domain="projects", areaRef="P10", title="Website", description="d2").get()
    new_project(log=log, dbConn=dbConn, categoryRef="P11", templateName="blank", projectTitle="Relaunch").get()

    craft_sync(log=log, dbConn=dbConn, settings=craftSettings).get()

    byName = {name: (folderId, parent) for folderId, name, parent in fakeClient.folders}
    projectsRootId, _ = byName["02 PROJECTS🚀"]
    areaFolderId, areaParent = next(
        (fid, parent) for name, (fid, parent) in byName.items() if name.startswith("P10-19 launches")
    )
    assert areaParent == projectsRootId
    categoryFolderId, categoryParent = next(
        (fid, parent) for name, (fid, parent) in byName.items() if name.startswith("P11 website")
    )
    assert categoryParent == areaFolderId

    documentTitles = {title for _id, title, _folder in fakeClient.documents}
    assert any(title.startswith("P11.10 relaunch") for title in documentTitles)

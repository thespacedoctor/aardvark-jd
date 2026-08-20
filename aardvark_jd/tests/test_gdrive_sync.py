import logging

import pytest
import yaml

from aardvark_jd import db, gdrive_sync as gdrive_sync_module, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.gdrive_sync import gdrive_sync
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_gdrive_sync")
log.addHandler(logging.NullHandler())


class FakeGDriveClient(object):
    """*an in-memory Drive, recording every folder created without any HTTP calls*"""

    def __init__(self, clientId=None, clientSecret=None, refreshToken=None):
        # folderId -> (name, parentId)
        self.folders = {}
        self.nextId = 1
        self.listCalls = 0
        self.moves = []

    def seed(self, name, parentId):
        """*pretend a folder already exists in Drive, for adoption tests*"""
        folderId = f"seed-{self.nextId}"
        self.nextId += 1
        self.folders[folderId] = (name, parentId)
        return folderId

    def list_child_folders(self, parentId):
        self.listCalls += 1
        return [
            {"id": folderId, "name": name,
             "webViewLink": f"https://drive.google.com/drive/folders/{folderId}"}
            for folderId, (name, parent) in self.folders.items()
            if parent == parentId
        ]

    def create_folder(self, name, parentId=None):
        folderId = f"new-{self.nextId}"
        self.nextId += 1
        self.folders[folderId] = (name, parentId)
        return folderId, f"https://drive.google.com/drive/folders/{folderId}"

    def move_folder(self, folderId, newParentId, oldParentId):
        name, _parent = self.folders[folderId]
        self.folders[folderId] = (name, newParentId)
        self.moves.append((folderId, newParentId))
        return folderId

    @staticmethod
    def folder_url(folderId):
        return f"https://drive.google.com/drive/folders/{folderId}"


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=conn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Cardiologist", description="d3").get()

    client = FakeGDriveClient()
    monkeypatch.setattr(
        gdrive_sync_module, "GDriveClient",
        lambda clientId, clientSecret, refreshToken: client,
    )
    settings = {
        "system": {"name": "Test", "root_path": rootPath},
        "gdrive": {
            "enabled": True, "client_id": "cid",
            "client_secret": "secret", "refresh_token": "refresh",
        },
    }
    yield conn, client, settings
    conn.close()


def _names(client):
    return {name for name, _parent in client.folders.values()}


def test_sync_requires_gdrive_to_be_connected(seeded):
    conn, _client, settings = seeded
    settings["gdrive"]["enabled"] = False
    with pytest.raises(ValueError):
        gdrive_sync(log=log, dbConn=conn, settings=settings)


def test_sync_requires_complete_credentials(seeded):
    conn, _client, settings = seeded
    settings["gdrive"]["refresh_token"] = None
    with pytest.raises(ValueError):
        gdrive_sync(log=log, dbConn=conn, settings=settings)


def test_the_whole_system_lands_under_one_workspace_folder(seeded):
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    workspaceIds = [
        folderId for folderId, (name, parent) in client.folders.items()
        if parent == "root"
    ]
    assert len(workspaceIds) == 1
    assert client.folders[workspaceIds[0]][0] == "Test"


def test_the_index_folder_is_never_mirrored(seeded):
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    assert not any(name.startswith("00 INDEX") for name in _names(client))


def test_the_other_four_root_folders_are_mirrored(seeded):
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    names = _names(client)
    for expected in ("01 INBOX📥", "02 PROJECTS🚀", "03 AREAS🧭", "04 RESOURCES📚", "09 ARCHIVE🗄️"):
        assert expected in names, expected


def test_areas_categories_and_ids_are_mirrored(seeded):
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    names = _names(client)
    assert any(name.startswith("A10-19") for name in names)
    assert any(name.startswith("A11 ") for name in names)
    assert any(name.startswith("A11.10") for name in names)


def test_only_three_reserved_subfolders_are_mirrored(seeded):
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    names = _names(client)
    assert any(name.startswith("A11.01 inbox") for name in names)
    assert any(name.startswith("A11.04 templates") for name in names)
    assert any(name.startswith("A11.09 archive") for name in names)
    # THE OTHER SEVEN ARE DOCUMENTS OR SCRATCH SPACE, AND STAY OUT OF DRIVE
    for excluded in ("A11.00", "A11.02", "A11.03", "A11.05", "A11.06", "A11.07", "A11.08"):
        assert not any(name.startswith(excluded) for name in names), excluded


def test_no_documents_are_ever_created(seeded):
    """the Drive mirror is folders only - the fake has no document API at all"""
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    assert not hasattr(client, "documents")


def test_link_rows_are_written(seeded):
    conn, _client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    area = conn.execute("SELECT area_id FROM areas LIMIT 1").fetchone()
    link = db.get_gdrive_link(conn, "area", str(area["area_id"]))
    assert link is not None
    assert link["gdrive_folder_id"]
    assert link["gdrive_url"].startswith("https://drive.google.com/drive/folders/")


def test_sync_is_idempotent(seeded):
    conn, _client, settings = seeded
    first = gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    second = gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    assert first["folders_created"] > 0
    assert second["folders_created"] == 0


def test_a_folder_already_in_drive_is_adopted_not_duplicated(seeded):
    conn, client, settings = seeded
    workspaceId = client.seed("Test", "root")
    client.seed("03 AREAS🧭", workspaceId)

    gdrive_sync(log=log, dbConn=conn, settings=settings).get()

    areasFolders = [
        folderId for folderId, (name, parent) in client.folders.items()
        if name == "03 AREAS🧭"
    ]
    assert len(areasFolders) == 1
    assert areasFolders[0].startswith("seed-")
    link = db.get_gdrive_link(conn, "system_folder", "root.areas")
    assert link["gdrive_folder_id"] == areasFolders[0]


def test_each_parent_is_listed_at_most_once(seeded):
    conn, client, settings = seeded
    gdrive_sync(log=log, dbConn=conn, settings=settings).get()
    parentsTouched = {parent for _name, parent in client.folders.values()}
    assert client.listCalls <= len(parentsTouched) + 1

import logging
import os
import zipfile

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_initialiser")
log.addHandler(logging.NullHandler())


@pytest.fixture
def settingsFile(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    return settingsPath


def test_init_creates_full_skeleton(tmp_path, settingsFile):
    rootPath = initialiser(
        log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile
    ).get()

    assert rootPath == str(tmp_path / "My Life")
    assert os.path.isdir(rootPath)

    dbPath = paths.find_db_path(rootPath)
    assert os.path.isfile(dbPath)

    dbConn = db.get_connection(dbPath)
    folderKeys = {row["folder_key"] for row in dbConn.execute("SELECT folder_key FROM system_folders").fetchall()}
    expectedKeys = {entry[0] for entry in paths.SYSTEM_SKELETON}
    assert folderKeys == expectedKeys

    for row in dbConn.execute("SELECT folder_name, folder_path FROM system_folders").fetchall():
        assert os.path.isdir(row["folder_path"])
        if row["folder_path"] != rootPath:
            assert row["folder_name"] in row["folder_path"]

    dbConn.close()


def test_init_seeds_blank_template(tmp_path, settingsFile):
    rootPath = initialiser(
        log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile
    ).get()

    dbConn = db.get_connection(paths.find_db_path(rootPath))
    templatesFolder = paths.resolve(dbConn, "projects.system.04_templates")
    dbConn.close()

    zipPath = f"{templatesFolder}/blank_starter.zip"
    assert os.path.isfile(zipPath)
    with zipfile.ZipFile(zipPath) as zipHandle:
        names = set(zipHandle.namelist())
    assert "README.md" in names
    assert "input/.gitkeep" in names
    assert "output/.gitkeep" in names


def test_init_updates_settings_file(tmp_path, settingsFile):
    rootPath = initialiser(
        log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile
    ).get()

    with open(settingsFile) as stream:
        settings = yaml.safe_load(stream)
    assert settings["system"]["name"] == "My Life"
    assert settings["system"]["root_path"] == rootPath


def test_init_is_idempotent(tmp_path, settingsFile):
    args = dict(log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile)
    rootPath1 = initialiser(**args).get()
    dbConn = db.get_connection(paths.find_db_path(rootPath1))
    countBefore = dbConn.execute("SELECT COUNT(*) AS c FROM system_folders").fetchone()["c"]
    dbConn.close()

    rootPath2 = initialiser(**args).get()
    assert rootPath2 == rootPath1

    dbConn = db.get_connection(paths.find_db_path(rootPath2))
    countAfter = dbConn.execute("SELECT COUNT(*) AS c FROM system_folders").fetchone()["c"]
    dbConn.close()

    assert countAfter == countBefore

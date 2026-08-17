import logging
import os

import pytest
import yaml

from aardvark_jd import db, folders, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_add_id")
log.addHandler(logging.NullHandler())


@pytest.fixture
def dbConnWithCategory(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="").get()
    add_category(log=log, dbConn=conn, domain="areas", areaRef="10", title="Doctors", description="").get()
    yield conn
    conn.close()


def test_add_id_happy_path(dbConnWithCategory):
    code, folderPath = add_id(
        log=log, dbConn=dbConnWithCategory, domain="areas", categoryRef="11",
        title="Cardiologist", description="Dr Smith",
    ).get()
    assert code == "A.11.01"
    folderName = os.path.basename(folderPath)
    assert folderName == "11.01 Cardiologist"
    for character in folderName:
        assert ord(character) < 0x1F000
    assert os.path.isdir(folderPath)


def test_add_id_unknown_category_raises_clear_error(dbConnWithCategory):
    with pytest.raises(ValueError):
        add_id(
            log=log, dbConn=dbConnWithCategory, domain="areas", categoryRef="12",
            title="X", description="",
        ).get()


def test_add_id_exhaustion_surfaces_clear_error(dbConnWithCategory):
    for _ in range(99):
        add_id(
            log=log, dbConn=dbConnWithCategory, domain="areas", categoryRef="11",
            title="X", description="",
        ).get()
    with pytest.raises(folders.IdExhaustedError):
        add_id(
            log=log, dbConn=dbConnWithCategory, domain="areas", categoryRef="11",
            title="Overflow", description="",
        ).get()

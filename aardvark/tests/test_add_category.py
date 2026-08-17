import logging
import os

import pytest
import yaml

from aardvark import db, folders, paths
from aardvark.add_area import add_area
from aardvark.add_category import add_category
from aardvark.initialiser import initialiser

log = logging.getLogger("test_add_category")
log.addHandler(logging.NullHandler())


@pytest.fixture
def dbConnWithArea(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="").get()
    yield conn
    conn.close()


def test_add_category_happy_path(dbConnWithArea):
    code, folderPath = add_category(
        log=log, dbConn=dbConnWithArea, domain="areas", areaRef="10", title="Doctors", description="desc"
    ).get()
    assert code == "A.11"
    assert "11 Doctors" in folderPath
    assert os.path.isdir(folderPath)


def test_add_category_accepts_range_ref(dbConnWithArea):
    code, _ = add_category(
        log=log, dbConn=dbConnWithArea, domain="areas", areaRef="10-19", title="Doctors", description=""
    ).get()
    assert code == "A.11"


def test_add_category_unknown_area_raises_clear_error(dbConnWithArea):
    with pytest.raises(ValueError):
        add_category(
            log=log, dbConn=dbConnWithArea, domain="areas", areaRef="20", title="X", description=""
        ).get()


def test_add_category_exhaustion_surfaces_clear_error(dbConnWithArea):
    for _ in range(9):
        add_category(log=log, dbConn=dbConnWithArea, domain="areas", areaRef="10", title="X", description="").get()
    with pytest.raises(folders.CategoryExhaustedError):
        add_category(
            log=log, dbConn=dbConnWithArea, domain="areas", areaRef="10", title="Overflow", description=""
        ).get()

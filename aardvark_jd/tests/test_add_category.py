import logging
import os

import pytest
import yaml

from aardvark_jd import db, folders, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.initialiser import initialiser

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
        log=log, dbConn=dbConnWithArea, domain="areas", areaRef="A10", title="Doctors", description="desc"
    ).get()
    assert code == "A11"
    assert "A11_doctors" in folderPath
    assert os.path.isdir(folderPath)


def test_add_category_happy_path_projects_domain(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="projects", title="Launches", description="").get()

    code, folderPath = add_category(
        log=log, dbConn=conn, domain="projects", areaRef="P10", title="Website", description="desc"
    ).get()
    assert code == "P11"
    assert "P11_website" in folderPath
    assert os.path.isdir(folderPath)
    conn.close()


def test_add_category_accepts_range_ref(dbConnWithArea):
    code, _ = add_category(
        log=log, dbConn=dbConnWithArea, domain="areas", areaRef="A10-19", title="Doctors", description=""
    ).get()
    assert code == "A11"


def test_add_category_unknown_area_raises_clear_error(dbConnWithArea):
    with pytest.raises(ValueError):
        add_category(
            log=log, dbConn=dbConnWithArea, domain="areas", areaRef="A20", title="X", description=""
        ).get()


def test_add_category_exhaustion_surfaces_clear_error(dbConnWithArea):
    for _ in range(9):
        add_category(log=log, dbConn=dbConnWithArea, domain="areas", areaRef="A10", title="X", description="").get()
    with pytest.raises(folders.CategoryExhaustedError):
        add_category(
            log=log, dbConn=dbConnWithArea, domain="areas", areaRef="A10", title="Overflow", description=""
        ).get()


def test_add_category_creates_its_ten_reserved_ids(dbConnWithArea):
    _code, folderPath = add_category(
        log=log, dbConn=dbConnWithArea, domain="areas", areaRef="A10", title="Doctors", description="desc"
    ).get()

    expectedNames = [
        "A11.00_index🗂️", "A11.01_inbox📥", "A11.02_llm🤖", "A11.03_checklists☑️",
        "A11.04_templates📐", "A11.05_links🔗", "A11.06_bin📜", "A11.07_settings🎛️",
        "A11.08_someday💭", "A11.09_archive🗄️",
    ]
    for name in expectedNames:
        assert os.path.isdir(f"{folderPath}/{name}")

    row = db.get_system_folder(dbConnWithArea, "areas.11.04_templates")
    assert row["folder_name"] == "A11.04_templates📐"

import logging
import os

import pytest
import yaml

from aardvark_jd import db, folders, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_add_area")
log.addHandler(logging.NullHandler())


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


@pytest.mark.parametrize("domain", ["areas", "resources"])
def test_add_area_happy_path(dbConn, domain):
    code, folderPath = add_area(log=log, dbConn=dbConn, domain=domain, title="Health", description="desc").get()
    letter = "A" if domain == "areas" else "R"
    assert code == f"{letter}.10-19"
    assert "10-19 Health" in folderPath
    assert os.path.isdir(folderPath)


def test_add_area_domains_are_independent(dbConn):
    codeAreas, _ = add_area(log=log, dbConn=dbConn, domain="areas", title="Health", description="").get()
    codeResources, _ = add_area(log=log, dbConn=dbConn, domain="resources", title="Health", description="").get()
    assert codeAreas == "A.10-19"
    assert codeResources == "R.10-19"


def test_add_area_exhaustion_surfaces_clear_error(dbConn):
    for _ in range(9):
        add_area(log=log, dbConn=dbConn, domain="areas", title="X", description="").get()
    with pytest.raises(folders.DomainExhaustedError):
        add_area(log=log, dbConn=dbConn, domain="areas", title="Overflow", description="").get()


def test_add_area_invalid_domain(dbConn):
    with pytest.raises(ValueError):
        add_area(log=log, dbConn=dbConn, domain="projects", title="X", description="").get()

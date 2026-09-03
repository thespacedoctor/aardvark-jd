import logging

import pytest
import yaml

from aardvark_jd import db, paths, refs
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_refs")
log.addHandler(logging.NullHandler())


@pytest.fixture
def seededConn(tmp_path):
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
    yield conn
    conn.close()


def test_resolve_ref_returns_the_area_row(seededConn):
    entityType, domain, row = refs.resolve_ref(seededConn, "A10-19", "cd")
    assert entityType == "area"
    assert domain == "areas"
    assert row["folder_path"].endswith("_health🏥") or "health" in row["folder_path"].lower()


def test_resolve_ref_returns_the_category_row(seededConn):
    entityType, domain, row = refs.resolve_ref(seededConn, "A11", "cd")
    assert entityType == "category"
    assert domain == "areas"
    assert "folder_path" in row.keys()


def test_resolve_ref_returns_the_id_row(seededConn):
    entityType, domain, row = refs.resolve_ref(seededConn, "A11.10", "cd")
    assert entityType == "id"
    assert domain == "areas"
    assert "folder_path" in row.keys()


def test_resolve_ref_is_case_insensitive_and_strips_whitespace(seededConn):
    entityType, _domain, row = refs.resolve_ref(seededConn, "  a11.10  ", "cd")
    assert entityType == "id"


def test_resolve_ref_raises_for_a_non_reference_string(seededConn):
    with pytest.raises(ValueError, match="not a Johnny Decimal reference"):
        refs.resolve_ref(seededConn, "not a ref", "cd")


def test_resolve_ref_raises_for_a_well_formed_but_absent_id(seededConn):
    with pytest.raises(ValueError, match="no ID 'A99.99' in the index"):
        refs.resolve_ref(seededConn, "A99.99", "cd")


def test_resolve_ref_raises_for_a_well_formed_but_absent_category(seededConn):
    with pytest.raises(ValueError, match="no category 'A99' in the index"):
        refs.resolve_ref(seededConn, "A99", "cd")


def test_resolve_ref_raises_for_a_well_formed_but_absent_area(seededConn):
    with pytest.raises(ValueError, match="no area 'A90-99' in the index"):
        refs.resolve_ref(seededConn, "A90-99", "cd")


def test_resolve_ref_quotes_the_command_hint_in_the_error(seededConn):
    with pytest.raises(ValueError, match="cd takes an area"):
        refs.resolve_ref(seededConn, "not a ref", "cd")

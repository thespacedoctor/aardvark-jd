import logging
import os

import pytest
import yaml

from aardvark_jd import change_dir, db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_change_dir")
log.addHandler(logging.NullHandler())


@pytest.fixture
def seeded(tmp_path):
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
    conn.close()
    yield settingsPath


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


@pytest.mark.parametrize("target", ["A", "A10-19", "A11", "A11.10"])
def test_resolve_path_returns_an_existing_directory(seededConn, target):
    folderPath = change_dir.resolve_path(seededConn, target)
    assert os.path.isdir(folderPath)


def test_target_from_skips_a_value_taking_flag():
    assert change_dir._target_from(["-s", "other.yaml", "A11.10"]) == "A11.10"


def test_target_from_skips_a_bare_flag():
    assert change_dir._target_from(["-y", "A11.10"]) == "A11.10"


def test_target_from_returns_none_when_only_flags_are_given():
    assert change_dir._target_from(["-y", "-s", "other.yaml"]) is None


def test_resolve_path_is_case_insensitive(seededConn):
    upper = change_dir.resolve_path(seededConn, "A11.10")
    lower = change_dir.resolve_path(seededConn, "a11.10")
    assert upper == lower


def test_resolve_path_raises_for_an_unknown_ref(seededConn):
    with pytest.raises(ValueError, match="no ID 'A99.99' in the index"):
        change_dir.resolve_path(seededConn, "A99.99")


def test_resolve_path_raises_when_the_folder_has_been_moved_away(seededConn):
    folderPath = change_dir.resolve_path(seededConn, "A11.10")
    renamedPath = folderPath + "_renamed"
    os.rename(folderPath, renamedPath)
    with pytest.raises(ValueError, match="no longer exists on disk"):
        change_dir.resolve_path(seededConn, "A11.10")


def test_emit_prints_the_resolved_path_and_returns_zero(seeded, capsys):
    exitCode = change_dir.emit(["A11.10", "-s", seeded])
    captured = capsys.readouterr()
    assert exitCode == 0
    assert captured.out.strip().endswith("cardiologist") or "A11" in captured.out


def test_emit_prints_an_error_and_returns_one_for_an_unknown_ref(seeded, capsys):
    exitCode = change_dir.emit(["A99.99", "-s", seeded])
    captured = capsys.readouterr()
    assert exitCode == 1
    assert captured.out == ""
    assert "no ID 'A99.99' in the index" in captured.err


def test_emit_prints_a_usage_error_and_returns_one_for_no_target(seeded, capsys):
    exitCode = change_dir.emit(["-s", seeded])
    captured = capsys.readouterr()
    assert exitCode == 1
    assert captured.err != ""


def test_emit_reports_no_system_found_when_unconfigured(tmp_path, capsys):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    exitCode = change_dir.emit(["A11.10", "-s", settingsPath])
    captured = capsys.readouterr()
    assert exitCode == 1
    assert "no aardvark system found" in captured.err

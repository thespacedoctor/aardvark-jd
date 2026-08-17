import logging
import os

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser
from aardvark_jd.new_project import new_project
from aardvark_jd.repair_emoji import repair_emoji
from aardvark_jd.set_emoji import set_emoji

log = logging.getLogger("test_set_emoji")
log.addHandler(logging.NullHandler())


@pytest.fixture
def settingsFile(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    return settingsPath


@pytest.fixture
def populatedSystem(tmp_path, settingsFile):
    """*an initialised system with an area, two categories and IDs beneath them*"""
    rootPath = initialiser(
        log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile
    ).get()
    dbConn = db.get_connection(paths.find_db_path(rootPath))

    add_area(log=log, dbConn=dbConn, domain="areas", title="Health",
             description="Physical and mental health", chosenEmoji="🩺").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="10", title="Doctors",
                 description="GP and specialists", chosenEmoji="👩‍⚕️").get()
    add_category(log=log, dbConn=dbConn, domain="areas", areaRef="10", title="Dentists",
                 description="Dental care", chosenEmoji="🦷").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="11", title="Cardiologist",
           description="Dr Smith").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="11", title="Optician",
           description="Annual check").get()
    add_id(log=log, dbConn=dbConn, domain="areas", categoryRef="12", title="Hygienist",
           description="Six monthly").get()

    yield rootPath, dbConn
    dbConn.close()


def _all_indexed_paths(dbConn):
    """*every folder_path the index holds, keyed by a readable label*"""
    indexed = {}
    for row in db.list_system_folders(dbConn):
        indexed[f"system:{row['folder_key']}"] = row["folder_path"]
    for table, key in (("areas", "area_id"), ("categories", "category_id"),
                       ("ids", "id_id"), ("projects", "project_id")):
        for row in dbConn.execute(f"SELECT {key}, folder_path FROM {table}").fetchall():
            indexed[f"{table}:{row[key]}"] = row["folder_path"]
    return indexed


def test_every_indexed_path_exists_before_any_rename(populatedSystem):
    _rootPath, dbConn = populatedSystem
    for label, folderPath in _all_indexed_paths(dbConn).items():
        assert os.path.isdir(folderPath), f"{label} is not on disk"


def test_set_area_emoji_cascades_to_categories_and_ids(populatedSystem):
    _rootPath, dbConn = populatedSystem

    label, newFolderPath = set_emoji(
        log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥"
    ).get()

    assert label == "A.10-19"
    assert os.path.basename(newFolderPath) == "10-19 Health 🏥"
    assert os.path.isdir(newFolderPath)

    # THE CASCADE: EVERY DESCENDANT ROW MUST NOW POINT SOMEWHERE REAL
    for descriptor, folderPath in _all_indexed_paths(dbConn).items():
        assert os.path.isdir(folderPath), f"{descriptor} was left pointing at a stale path"

    categories = db.list_categories(dbConn, "areas")
    assert len(categories) == 2
    for category in categories:
        assert category["folder_path"].startswith(newFolderPath + "/")

    for category in categories:
        for row in db.list_ids(dbConn, "areas", category["category_id"]):
            assert row["folder_path"].startswith(category["folder_path"] + "/")


def test_set_category_emoji_cascades_to_its_ids_only(populatedSystem):
    _rootPath, dbConn = populatedSystem
    dentistsBefore = db.get_category(dbConn, "areas", 12)["folder_path"]

    _label, newFolderPath = set_emoji(
        log=log, dbConn=dbConn, domain="areas", ref="11", newEmoji="🩻"
    ).get()

    assert os.path.basename(newFolderPath) == "11 Doctors 🩻"
    for descriptor, folderPath in _all_indexed_paths(dbConn).items():
        assert os.path.isdir(folderPath), f"{descriptor} was left pointing at a stale path"

    doctors = db.get_category(dbConn, "areas", 11)
    for row in db.list_ids(dbConn, "areas", doctors["category_id"]):
        assert row["folder_path"].startswith(newFolderPath + "/")

    # THE SIBLING CATEGORY MUST BE UNTOUCHED
    assert db.get_category(dbConn, "areas", 12)["folder_path"] == dentistsBefore


def test_set_system_folder_emoji_cascades_to_the_whole_domain(populatedSystem):
    _rootPath, dbConn = populatedSystem

    _label, newFolderPath = set_emoji(
        log=log, dbConn=dbConn, domain="system", ref="root.areas", newEmoji="🎯"
    ).get()

    assert os.path.basename(newFolderPath) == "A.REAS 🎯"
    # RENAMING A SECTION FOLDER MOVES EVERY AREA, CATEGORY AND ID BENEATH IT
    for descriptor, folderPath in _all_indexed_paths(dbConn).items():
        assert os.path.isdir(folderPath), f"{descriptor} was left pointing at a stale path"

    area = db.get_area(dbConn, "areas", 10)
    assert area["folder_path"].startswith(newFolderPath + "/")
    for category in db.list_categories(dbConn, "areas"):
        assert category["folder_path"].startswith(newFolderPath + "/")


def test_search_still_resolves_after_a_rename(populatedSystem):
    from aardvark_jd.search import search

    _rootPath, dbConn = populatedSystem
    set_emoji(log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥").get()

    results = search(log=log, dbConn=dbConn, terms=["cardiologist"]).get()
    assert results
    for row in results:
        assert os.path.isdir(row["path"]), "the search index kept a stale path"


def test_set_project_emoji(tmp_path, settingsFile):
    rootPath = initialiser(
        log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile
    ).get()
    dbConn = db.get_connection(paths.find_db_path(rootPath))
    new_project(log=log, dbConn=dbConn, templateName="blank", projectTitle="Website Rebuild",
                chosenEmoji="🚧").get()

    label, newFolderPath = set_emoji(
        log=log, dbConn=dbConn, domain="projects", ref="Website Rebuild", newEmoji="🌐"
    ).get()

    assert label == "Website Rebuild"
    assert os.path.basename(newFolderPath) == "Website Rebuild 🌐"
    assert os.path.isdir(newFolderPath)
    assert os.path.isfile(f"{newFolderPath}/README.md")
    dbConn.close()


def test_set_emoji_is_idempotent(populatedSystem):
    _rootPath, dbConn = populatedSystem
    _label, firstPath = set_emoji(
        log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥"
    ).get()
    before = _all_indexed_paths(dbConn)

    _label, secondPath = set_emoji(
        log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥"
    ).get()

    assert secondPath == firstPath
    assert _all_indexed_paths(dbConn) == before


def test_set_emoji_refuses_to_clobber_an_existing_folder(populatedSystem):
    _rootPath, dbConn = populatedSystem
    area = db.get_area(dbConn, "areas", 10)
    collidingPath = os.path.dirname(area["folder_path"]) + "/10-19 Health 🏥"
    os.makedirs(collidingPath)

    with pytest.raises(ValueError, match="refusing to overwrite"):
        set_emoji(log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥").get()

    # THE ORIGINAL MUST BE LEFT EXACTLY AS IT WAS
    assert db.get_area(dbConn, "areas", 10)["folder_path"] == area["folder_path"]
    assert os.path.isdir(area["folder_path"])


def test_failed_index_write_rolls_back_the_rename(populatedSystem, monkeypatch):
    _rootPath, dbConn = populatedSystem
    area = db.get_area(dbConn, "areas", 10)

    def explode(*args, **kwargs):
        raise RuntimeError("index write failed")

    monkeypatch.setattr(db, "rewrite_folder_path_prefix", explode)

    with pytest.raises(RuntimeError):
        set_emoji(log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="🏥").get()

    # THE FOLDER MUST BE BACK WHERE IT STARTED, AND THE INDEX UNCHANGED
    assert os.path.isdir(area["folder_path"])
    assert db.get_area(dbConn, "areas", 10)["folder_path"] == area["folder_path"]


def test_unknown_refs_raise_clear_errors(populatedSystem):
    _rootPath, dbConn = populatedSystem

    with pytest.raises(ValueError, match="not a valid domain"):
        set_emoji(log=log, dbConn=dbConn, domain="nonsense", ref="10", newEmoji="🏥").get()
    with pytest.raises(ValueError, match="no area"):
        set_emoji(log=log, dbConn=dbConn, domain="areas", ref="90", newEmoji="🏥").get()
    with pytest.raises(ValueError, match="no category"):
        set_emoji(log=log, dbConn=dbConn, domain="areas", ref="19", newEmoji="🏥").get()
    with pytest.raises(ValueError, match="no project"):
        set_emoji(log=log, dbConn=dbConn, domain="projects", ref="Nope", newEmoji="🏥").get()
    with pytest.raises(KeyError):
        set_emoji(log=log, dbConn=dbConn, domain="system", ref="root.nope", newEmoji="🏥").get()


def test_set_emoji_rejects_a_path_breaking_emoji(populatedSystem):
    _rootPath, dbConn = populatedSystem
    with pytest.raises(ValueError, match="cannot be used in a folder name"):
        set_emoji(log=log, dbConn=dbConn, domain="areas", ref="10", newEmoji="a/b").get()


# ----------------------------------------------------------- repair_emoji


def test_repair_emoji_resets_drifted_system_folders(populatedSystem):
    _rootPath, dbConn = populatedSystem

    # DRIFT TWO FOLDERS, ONE OF THEM A PARENT OF THE OTHER
    set_emoji(log=log, dbConn=dbConn, domain="system", ref="root.areas", newEmoji="❓").get()
    set_emoji(log=log, dbConn=dbConn, domain="system", ref="areas.system.02_llm", newEmoji="❓").get()

    repaired = repair_emoji(log=log, dbConn=dbConn).get()
    repairedKeys = {folderKey for folderKey, _path in repaired}
    assert "root.areas" in repairedKeys
    assert "areas.system.02_llm" in repairedKeys

    assert db.get_system_folder(dbConn, "root.areas")["folder_name"] == "A.REAS 🧭"
    assert db.get_system_folder(dbConn, "areas.system.02_llm")["folder_name"] == "02_llm 🤖"

    for descriptor, folderPath in _all_indexed_paths(dbConn).items():
        assert os.path.isdir(folderPath), f"{descriptor} was left pointing at a stale path"


def test_repair_emoji_is_idempotent(populatedSystem):
    _rootPath, dbConn = populatedSystem

    # A FRESHLY INITIALISED SYSTEM ALREADY MATCHES THE SKELETON
    assert repair_emoji(log=log, dbConn=dbConn).get() == []

    set_emoji(log=log, dbConn=dbConn, domain="system", ref="root.areas", newEmoji="❓").get()
    assert len(repair_emoji(log=log, dbConn=dbConn).get()) == 1

    before = _all_indexed_paths(dbConn)
    assert repair_emoji(log=log, dbConn=dbConn).get() == []
    assert _all_indexed_paths(dbConn) == before

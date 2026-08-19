import logging

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser
from aardvark_jd.search import search

log = logging.getLogger("test_search")
log.addHandler(logging.NullHandler())


@pytest.fixture
def dbConnWithIndex(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="").get()
    add_category(
        log=log, dbConn=conn, domain="areas", areaRef="10", title="Doctors",
        description="Doctors, specialists and appointments",
    ).get()
    add_id(
        log=log, dbConn=conn, domain="areas", categoryRef="11", title="Cardiologist",
        description="Dr Smith, cardiology follow-ups",
    ).get()
    yield conn
    conn.close()


def test_prefix_match_hits_id(dbConnWithIndex):
    results = search(log=log, dbConn=dbConnWithIndex, terms=["cardio"]).get()
    codes = [row["code"] for row in results]
    assert "A11.10" in codes


def test_word_match_hits_category_and_id(dbConnWithIndex):
    results = search(log=log, dbConn=dbConnWithIndex, terms=["doctors"]).get()
    codes = [row["code"] for row in results]
    assert "A11" in codes


def test_empty_query_returns_empty_list(dbConnWithIndex):
    assert search(log=log, dbConn=dbConnWithIndex, terms=[]).get() == []
    assert search(log=log, dbConn=dbConnWithIndex, terms=[""]).get() == []


def test_no_match_returns_empty_list(dbConnWithIndex):
    assert search(log=log, dbConn=dbConnWithIndex, terms=["nonexistentxyz"]).get() == []


def test_title_match_ranks_above_description_only_match(dbConnWithIndex):
    add_id(
        log=log, dbConn=dbConnWithIndex, domain="areas", categoryRef="11", title="Nutrition Notes",
        description="not health related at all",
    ).get()
    results = search(log=log, dbConn=dbConnWithIndex, terms=["health"]).get()
    assert results
    assert results[0]["code"] == "A10-19"


def test_like_fallback_equivalence(dbConnWithIndex, monkeypatch):
    monkeypatch.setattr(db, "fts5_enabled", lambda dbConn: False)
    results = search(log=log, dbConn=dbConnWithIndex, terms=["cardio"]).get()
    codes = [row["code"] for row in results]
    assert "A11.10" in codes

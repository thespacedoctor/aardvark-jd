import logging

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser
from aardvark_jd.search import format_result, search

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
    # EXPLICIT EMOJI, SO THE RENDERED LABELS ARE EXACT RATHER THAN WHATEVER THE
    # SUGGESTER HAPPENS TO PICK FOR "HEALTH" ON THE DAY.
    add_area(
        log=log, dbConn=conn, domain="areas", title="Health", description="", chosenEmoji="🏥",
    ).get()
    add_category(
        log=log, dbConn=conn, domain="areas", areaRef="A10", title="Doctors",
        description="Doctors, specialists and appointments", chosenEmoji="🩺",
    ).get()
    add_id(
        log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Cardiologist",
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
        log=log, dbConn=dbConnWithIndex, domain="areas", categoryRef="A11", title="Nutrition Notes",
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


def _result(results, code):
    """*the one result carrying this Johnny Decimal code*"""
    matched = [row for row in results if row["code"] == code]
    assert matched, f"no result for {code} in {[row['code'] for row in results]}"
    return matched[0]


def test_an_area_result_carries_its_emoji(dbConnWithIndex):
    """*`search_index` stores no emoji, so the owning row supplies it at display time*"""
    results = search(log=log, dbConn=dbConnWithIndex, terms=["health"]).get()
    assert _result(results, "A10-19")["emoji"] == "🏥"


def test_a_category_result_carries_its_emoji(dbConnWithIndex):
    results = search(log=log, dbConn=dbConnWithIndex, terms=["doctors"]).get()
    assert _result(results, "A11")["emoji"] == "🩺"


def test_an_id_result_carries_no_emoji(dbConnWithIndex):
    results = search(log=log, dbConn=dbConnWithIndex, terms=["cardio"]).get()
    assert not _result(results, "A11.10").get("emoji")


def test_a_blank_area_emoji_is_left_blank_on_the_row(dbConnWithIndex):
    """*the fallback is a display decision, so it belongs in `labels`, not in the result row*"""
    dbConnWithIndex.execute("UPDATE areas SET emoji = '' WHERE decade_start = 10 AND domain = 'areas'")
    dbConnWithIndex.commit()
    results = search(log=log, dbConn=dbConnWithIndex, terms=["health"]).get()
    assert _result(results, "A10-19")["emoji"] == ""


def test_the_emoji_lookup_survives_a_like_fallback(dbConnWithIndex, monkeypatch):
    monkeypatch.setattr(db, "fts5_enabled", lambda dbConn: False)
    results = search(log=log, dbConn=dbConnWithIndex, terms=["doctors"]).get()
    assert _result(results, "A11")["emoji"] == "🩺"


def test_format_result_puts_the_emoji_between_the_code_and_the_title():
    row = {"entity_type": "category", "code": "A11", "title": "Doctors",
           "emoji": "🩺", "path": "/root/A10_19_health/A11_doctors"}
    assert format_result(row) == "A11 🩺 Doctors  /root/A10_19_health/A11_doctors"


def test_format_result_leaves_an_id_line_without_an_emoji():
    row = {"entity_type": "id", "code": "A11.10", "title": "Cardiologist", "path": "/root/A11.10"}
    assert format_result(row) == "A11.10 Cardiologist  /root/A11.10"


def test_format_result_keeps_a_wide_gutter_before_the_path():
    """*paths contain spaces, so the two-space gutter is what marks where the title ends*"""
    row = {"entity_type": "id", "code": "A11.10", "title": "Cardiologist", "path": "/my folder/A11.10"}
    assert format_result(row).endswith("Cardiologist  /my folder/A11.10")


def test_format_result_falls_back_for_a_blank_area_emoji():
    row = {"entity_type": "area", "code": "A10-19", "title": "Health", "emoji": "", "path": "/root/A10_19"}
    assert format_result(row) == "A10-19 📁 Health  /root/A10_19"

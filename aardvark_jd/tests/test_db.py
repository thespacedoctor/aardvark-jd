import sqlite3

import pytest

from aardvark_jd import db


@pytest.fixture
def dbConn():
    conn = db.get_connection(":memory:")
    db.initialise_schema(conn)
    yield conn
    conn.close()


def test_schema_creates_all_tables(dbConn):
    tables = {
        row["name"]
        for row in dbConn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall()
    }
    for expected in ("meta", "system_folders", "areas", "categories", "ids", "projects", "search_index"):
        assert expected in tables


def test_fts5_enabled_by_default(dbConn):
    assert db.fts5_enabled(dbConn) is True


def test_fts5_fallback(monkeypatch):
    monkeypatch.setattr(db, "_FTS5_SEARCH_INDEX", "CREATE VIRTUAL TABLE search_index USING not_a_real_module();")
    conn = db.get_connection(":memory:")
    db.initialise_schema(conn)
    assert db.fts5_enabled(conn) is False
    # THE FALLBACK PLAIN TABLE SHOULD STILL ACCEPT WRITES VIA THE SHARED TRIGGERS
    areaId = db.insert_area(conn, "areas", 10, 19, "Health", "", "🏥", "10-19 Health 🏥", "/tmp/h")
    rows = conn.execute("SELECT * FROM search_index").fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "Health"
    conn.close()


def test_foreign_key_cascade_delete(dbConn):
    areaId = db.insert_area(dbConn, "areas", 10, 19, "Health", "", "🏥", "10-19 Health 🏥", "/tmp/h")
    catId = db.insert_category(dbConn, areaId, "areas", 11, "Doctors", "", "🩺", "11 Doctors 🩺", "/tmp/h/11")
    db.insert_id(dbConn, catId, "areas", 11, 1, "Cardiologist", "", "11.01 Cardiologist", "/tmp/h/11/1")

    dbConn.execute("DELETE FROM areas WHERE area_id = ?", (areaId,))
    dbConn.commit()

    assert dbConn.execute("SELECT * FROM categories").fetchall() == []
    assert dbConn.execute("SELECT * FROM ids").fetchall() == []
    assert dbConn.execute("SELECT * FROM search_index").fetchall() == []


def test_system_folders_round_trip(dbConn):
    db.insert_system_folder(dbConn, "root.areas", "A.REAS 🗂️", "/tmp/root/A.REAS 🗂️")
    row = db.get_system_folder(dbConn, "root.areas")
    assert row["folder_name"] == "A.REAS 🗂️"
    # RE-INSERTING THE SAME KEY UPDATES RATHER THAN DUPLICATES
    db.insert_system_folder(dbConn, "root.areas", "A.REAS 🌟", "/tmp/root/A.REAS 🌟")
    row = db.get_system_folder(dbConn, "root.areas")
    assert row["folder_name"] == "A.REAS 🌟"
    count = dbConn.execute("SELECT COUNT(*) AS c FROM system_folders").fetchone()["c"]
    assert count == 1

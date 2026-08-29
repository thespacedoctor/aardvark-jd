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
    for expected in ("meta", "system_folders", "areas", "categories", "ids", "craft_links", "todoist_links", "search_index"):
        assert expected in tables
    assert "projects" not in tables


def test_fts5_enabled_by_default(dbConn):
    assert db.fts5_enabled(dbConn) is True


def test_get_connection_sets_a_busy_timeout():
    """*two overlapping `aardvark` commands queue on the write lock instead of one crashing*"""
    conn = db.get_connection(":memory:")
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        conn.close()


def test_get_connection_leaves_journal_mode_at_the_default():
    """*WAL is deliberately not enabled - a `mode=ro` completion reader depends on the default*"""
    conn = db.get_connection(":memory:")
    try:
        # `:memory:` REPORTS `memory`; A FILE DB REPORTS `delete`. EITHER WAY, NOT `wal`.
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] != "wal"
    finally:
        conn.close()


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


def test_migrate_schema_upgrades_a_pre_projects_domain_database(tmp_path):
    """*an old database (CHECK-constrained to ('areas','resources'), with the legacy flat `projects` table) is upgraded in place, preserving existing rows*"""
    dbPath = str(tmp_path / "legacy.db")
    conn = db.get_connection(dbPath)
    conn.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE areas (
            area_id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL CHECK (domain IN ('areas','resources')),
            decade_start INTEGER NOT NULL, decade_end INTEGER NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            emoji TEXT NOT NULL DEFAULT '📁', folder_name TEXT NOT NULL, folder_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            UNIQUE (domain, decade_start)
        );
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL REFERENCES areas(area_id) ON DELETE CASCADE,
            domain TEXT NOT NULL CHECK (domain IN ('areas','resources')),
            ac_number INTEGER NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            emoji TEXT NOT NULL DEFAULT '📁', folder_name TEXT NOT NULL, folder_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            UNIQUE (domain, ac_number)
        );
        CREATE TABLE ids (
            id_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
            domain TEXT NOT NULL CHECK (domain IN ('areas','resources')),
            ac_number INTEGER NOT NULL, item_number INTEGER NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            folder_name TEXT NOT NULL, folder_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            UNIQUE (domain, ac_number, item_number)
        );
        CREATE TABLE projects (
            project_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            emoji TEXT NOT NULL DEFAULT '📁', folder_name TEXT NOT NULL UNIQUE, folder_path TEXT NOT NULL,
            template_used TEXT, status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now'))
        );
    """)
    areaId = conn.execute(
        "INSERT INTO areas(domain, decade_start, decade_end, title, description, emoji, folder_name, folder_path) "
        "VALUES ('areas', 10, 19, 'Health', '', '🏥', '10-19 Health', '/tmp/h')"
    ).lastrowid
    catId = conn.execute(
        "INSERT INTO categories(area_id, domain, ac_number, title, description, emoji, folder_name, folder_path) "
        "VALUES (?, 'areas', 11, 'Doctors', '', '🩺', '11 Doctors', '/tmp/h/11')", (areaId,)
    ).lastrowid
    conn.execute(
        "INSERT INTO ids(category_id, domain, ac_number, item_number, title, description, folder_name, folder_path) "
        "VALUES (?, 'areas', 11, 1, 'Cardiologist', '', '11.01 Cardiologist', '/tmp/h/11/1')", (catId,)
    )
    conn.execute(
        "INSERT INTO projects(title, description, emoji, folder_name, folder_path, template_used) "
        "VALUES ('Old Project', '', '📁', 'Old Project', '/tmp/old', 'blank')"
    )
    conn.commit()
    conn.close()

    upgradedConn = db.get_connection(dbPath)
    db.initialise_schema(upgradedConn)

    tables = {
        row["name"] for row in upgradedConn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert "projects" not in tables

    checkSql = upgradedConn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'areas'"
    ).fetchone()["sql"]
    assert "'projects'" in checkSql

    area = upgradedConn.execute("SELECT * FROM areas WHERE area_id = ?", (areaId,)).fetchone()
    assert area["title"] == "Health"
    category = upgradedConn.execute("SELECT * FROM categories WHERE category_id = ?", (catId,)).fetchone()
    assert category["title"] == "Doctors"
    idRow = upgradedConn.execute("SELECT * FROM ids WHERE category_id = ?", (catId,)).fetchone()
    assert idRow["title"] == "Cardiologist"

    # A NEW `PROJECTS` DOMAIN AREA CAN NOW BE INSERTED AGAINST THE WIDENED CHECK
    db.insert_area(upgradedConn, "projects", 10, 19, "Launches", "", "🚀", "P10_19_launches", "/tmp/p")
    upgradedConn.close()


def test_migrate_schema_clears_stale_id_craft_links(tmp_path):
    """*a v3 database's `craft_links` rows of type 'id' (pointing at the old top-level ID document) are cleared on upgrade to v4, leaving other entity types untouched*"""
    dbPath = str(tmp_path / "v3.db")
    conn = db.get_connection(dbPath)
    db.initialise_schema(conn)

    db.upsert_craft_link(conn, "id", "1", craftDocumentId="old-doc-1", craftUrl="craftdocs://open?blockId=old-doc-1")
    db.upsert_craft_link(conn, "area", "1", craftFolderId="folder-1", craftUrl="craftdocs://openfolder?folderId=folder-1")
    db.set_meta(conn, "schema_version", "3")

    db.initialise_schema(conn)

    assert db.get_craft_link(conn, "id", "1") is None
    area = db.get_craft_link(conn, "area", "1")
    assert area is not None
    assert area["craft_folder_id"] == "folder-1"
    assert db.get_meta(conn, "schema_version") == db._SCHEMA_VERSION
    conn.close()


def test_craft_link_round_trip(dbConn):
    assert db.get_craft_link(dbConn, "area", "1") is None

    db.upsert_craft_link(dbConn, "area", "1", craftFolderId="folder-1", craftUrl="https://craft.example/f/1")
    row = db.get_craft_link(dbConn, "area", "1")
    assert row["craft_folder_id"] == "folder-1"
    assert row["craft_document_id"] is None
    assert row["craft_url"] == "https://craft.example/f/1"

    # re-upserting the same key updates rather than duplicates
    db.upsert_craft_link(dbConn, "area", "1", craftFolderId="folder-1", craftUrl="https://craft.example/f/1-renamed")
    row = db.get_craft_link(dbConn, "area", "1")
    assert row["craft_url"] == "https://craft.example/f/1-renamed"
    count = dbConn.execute("SELECT COUNT(*) AS c FROM craft_links").fetchone()["c"]
    assert count == 1

    # a later upsert that only sets craft_block_id must not clobber the
    # folder id/url recorded above
    db.upsert_craft_link(dbConn, "area", "1", craftBlockId="block-1")
    row = db.get_craft_link(dbConn, "area", "1")
    assert row["craft_block_id"] == "block-1"
    assert row["craft_folder_id"] == "folder-1"
    assert row["craft_url"] == "https://craft.example/f/1-renamed"


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


def test_craft_link_links_markdown_round_trip(dbConn):
    db.upsert_craft_link(dbConn, "id", "1", craftDocumentId="doc-1", craftBlockId="block-1", linksMarkdown="[a](b)")
    row = db.get_craft_link(dbConn, "id", "1")
    assert row["links_markdown"] == "[a](b)"

    # an upsert that only touches craft_document_id must not clobber links_markdown
    db.upsert_craft_link(dbConn, "id", "1", craftDocumentId="doc-1-renamed")
    row = db.get_craft_link(dbConn, "id", "1")
    assert row["links_markdown"] == "[a](b)"
    assert row["craft_block_id"] == "block-1"


def test_craft_link_clear_block_id(dbConn):
    db.upsert_craft_link(dbConn, "id", "1", craftDocumentId="doc-1", craftBlockId="block-1")
    db.upsert_craft_link(dbConn, "id", "1", clearBlockId=True)
    row = db.get_craft_link(dbConn, "id", "1")
    assert row["craft_block_id"] is None
    # the document id, set earlier and untouched by this call, survives
    assert row["craft_document_id"] == "doc-1"


def test_entity_rows_for_path_prefix(dbConn):
    db.insert_system_folder(dbConn, "root.areas", "03_AREAS", "/root/03_AREAS")
    areaId = db.insert_area(dbConn, "areas", 10, 19, "Health", "", "🏥", "A10_19_health🏥", "/root/03_AREAS/A10_19_health")
    categoryId = db.insert_category(dbConn, areaId, "areas", 11, "Doctors", "", "📁", "A11_doctors", "/root/03_AREAS/A10_19_health/A11_doctors")
    db.insert_id(dbConn, categoryId, "areas", 11, 10, "Cardiologist", "", "A11.10_cardiologist", "/root/03_AREAS/A10_19_health/A11_doctors/A11.10_cardiologist")

    rows = db.entity_rows_for_path_prefix(dbConn)
    rowsByType = {(entityType, entityKey): folderPath for entityType, entityKey, folderPath in rows}
    assert rowsByType[("system_folder", "root.areas")] == "/root/03_AREAS"
    assert rowsByType[("area", str(areaId))] == "/root/03_AREAS/A10_19_health"
    assert rowsByType[("category", str(categoryId))] == "/root/03_AREAS/A10_19_health/A11_doctors"
    assert any(entityType == "id" for entityType, _key in rowsByType)


def test_dropbox_link_round_trip(dbConn):
    assert db.get_dropbox_link(dbConn, "/root/03_AREAS") is None

    db.upsert_dropbox_link(dbConn, "/root/03_AREAS", "https://dropbox.example/a")
    row = db.get_dropbox_link(dbConn, "/root/03_AREAS")
    assert row["dropbox_url"] == "https://dropbox.example/a"

    # re-upserting the same path updates rather than duplicates
    db.upsert_dropbox_link(dbConn, "/root/03_AREAS", "https://dropbox.example/a-renamed")
    row = db.get_dropbox_link(dbConn, "/root/03_AREAS")
    assert row["dropbox_url"] == "https://dropbox.example/a-renamed"
    count = dbConn.execute("SELECT COUNT(*) AS c FROM dropbox_links").fetchone()["c"]
    assert count == 1


def test_todoist_link_round_trip(dbConn):
    assert db.get_todoist_link(dbConn, "area", "1") is None

    db.upsert_todoist_link(dbConn, "area", "1", todoistProjectId="proj-1", todoistUrl="https://app.todoist.com/app/project/proj-1")
    row = db.get_todoist_link(dbConn, "area", "1")
    assert row["todoist_project_id"] == "proj-1"
    assert row["todoist_url"] == "https://app.todoist.com/app/project/proj-1"
    assert row["description"] is None

    # re-upserting the same key updates rather than duplicates
    db.upsert_todoist_link(dbConn, "area", "1", description="[📁 Finder](hook://file/abc)")
    row = db.get_todoist_link(dbConn, "area", "1")
    assert row["description"] == "[📁 Finder](hook://file/abc)"
    # untouched fields from the first upsert survive a later upsert that omits them
    assert row["todoist_project_id"] == "proj-1"
    count = dbConn.execute("SELECT COUNT(*) AS c FROM todoist_links").fetchone()["c"]
    assert count == 1


# ---------------------------------------------------------------------- #
# sync drift markers
# ---------------------------------------------------------------------- #

def test_sync_drift_starts_empty(dbConn):
    assert db.drifted_mirrors(dbConn) == []


def test_recording_a_failure_marks_the_mirror_drifted(dbConn):
    db.record_sync_failure(dbConn, "craft", "429 rate limited", "rate-limited")

    drifted = db.drifted_mirrors(dbConn)
    assert [row["mirror"] for row in drifted] == ["craft"]
    assert drifted[0]["last_failure_reason"] == "429 rate limited"
    assert drifted[0]["last_failure_class"] == "rate-limited"


def test_a_success_clears_a_previous_failure(dbConn):
    db.record_sync_failure(dbConn, "craft", "429 rate limited", "rate-limited")
    db.record_sync_success(dbConn, "craft")

    assert db.drifted_mirrors(dbConn) == []
    row = dbConn.execute("SELECT * FROM sync_drift WHERE mirror = 'craft'").fetchone()
    assert row["last_success_at"] is not None
    assert row["last_failure_at"] is None


def test_a_failure_keeps_the_previous_success_timestamp(dbConn):
    db.record_sync_success(dbConn, "gdrive")
    successAt = dbConn.execute("SELECT last_success_at FROM sync_drift WHERE mirror = 'gdrive'").fetchone()[0]

    db.record_sync_failure(dbConn, "gdrive", "network down", "network")

    row = dbConn.execute("SELECT * FROM sync_drift WHERE mirror = 'gdrive'").fetchone()
    assert row["last_success_at"] == successAt
    assert row["last_failure_at"] is not None


def test_drifted_mirrors_are_returned_in_sync_order(dbConn):
    for mirror in ("craft", "gdrive", "todoist"):
        db.record_sync_failure(dbConn, mirror, "boom", "unknown")

    assert [row["mirror"] for row in db.drifted_mirrors(dbConn)] == list(db.MIRRORS)


def test_an_unknown_mirror_name_is_rejected_by_the_schema(dbConn):
    with pytest.raises(sqlite3.IntegrityError):
        db.record_sync_failure(dbConn, "notion", "boom", "unknown")

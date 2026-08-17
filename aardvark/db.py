#!/usr/bin/env python
# encoding: utf-8
"""
*SQLite schema, connection and row-mapping helpers for the aardvark index*

Author
: David Young
"""

import sqlite3

_BASE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_folders (
    folder_key   TEXT PRIMARY KEY,
    folder_name  TEXT NOT NULL,
    folder_path  TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now'))
);

CREATE TABLE IF NOT EXISTS areas (
    area_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    domain        TEXT NOT NULL CHECK (domain IN ('areas','resources')),
    decade_start  INTEGER NOT NULL,
    decade_end    INTEGER NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    emoji         TEXT NOT NULL DEFAULT '📁',
    folder_name   TEXT NOT NULL,
    folder_path   TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    UNIQUE (domain, decade_start)
);

CREATE TABLE IF NOT EXISTS categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id       INTEGER NOT NULL REFERENCES areas(area_id) ON DELETE CASCADE,
    domain        TEXT NOT NULL CHECK (domain IN ('areas','resources')),
    ac_number     INTEGER NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    emoji         TEXT NOT NULL DEFAULT '📁',
    folder_name   TEXT NOT NULL,
    folder_path   TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    UNIQUE (domain, ac_number)
);

CREATE TABLE IF NOT EXISTS ids (
    id_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
    domain        TEXT NOT NULL CHECK (domain IN ('areas','resources')),
    ac_number     INTEGER NOT NULL,
    item_number   INTEGER NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    folder_name   TEXT NOT NULL,
    folder_path   TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    UNIQUE (domain, ac_number, item_number)
);

CREATE TABLE IF NOT EXISTS projects (
    project_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    emoji          TEXT NOT NULL DEFAULT '📁',
    folder_name    TEXT NOT NULL UNIQUE,
    folder_path    TEXT NOT NULL,
    template_used  TEXT,
    status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now'))
);
"""

_SEARCH_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS areas_ai AFTER INSERT ON areas BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        100000000000 + NEW.area_id, 'area',
        (CASE NEW.domain WHEN 'areas' THEN 'A' ELSE 'R' END) || '.' ||
            printf('%02d', NEW.decade_start) || '-' || printf('%02d', NEW.decade_start + 9),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS areas_au AFTER UPDATE ON areas BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        100000000000 + NEW.area_id, 'area',
        (CASE NEW.domain WHEN 'areas' THEN 'A' ELSE 'R' END) || '.' ||
            printf('%02d', NEW.decade_start) || '-' || printf('%02d', NEW.decade_start + 9),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS areas_ad AFTER DELETE ON areas BEGIN
    DELETE FROM search_index WHERE rowid = 100000000000 + OLD.area_id;
END;

CREATE TRIGGER IF NOT EXISTS categories_ai AFTER INSERT ON categories BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        200000000000 + NEW.category_id, 'category',
        (CASE NEW.domain WHEN 'areas' THEN 'A' ELSE 'R' END) || '.' || printf('%02d', NEW.ac_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS categories_au AFTER UPDATE ON categories BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        200000000000 + NEW.category_id, 'category',
        (CASE NEW.domain WHEN 'areas' THEN 'A' ELSE 'R' END) || '.' || printf('%02d', NEW.ac_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS categories_ad AFTER DELETE ON categories BEGIN
    DELETE FROM search_index WHERE rowid = 200000000000 + OLD.category_id;
END;

CREATE TRIGGER IF NOT EXISTS ids_ai AFTER INSERT ON ids BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        300000000000 + NEW.id_id, 'id',
        (CASE NEW.domain WHEN 'areas' THEN 'A' ELSE 'R' END) || '.' ||
            printf('%02d', NEW.ac_number) || '.' || printf('%02d', NEW.item_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS ids_au AFTER UPDATE ON ids BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        300000000000 + NEW.id_id, 'id',
        (CASE NEW.domain WHEN 'areas' THEN 'A' ELSE 'R' END) || '.' ||
            printf('%02d', NEW.ac_number) || '.' || printf('%02d', NEW.item_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS ids_ad AFTER DELETE ON ids BEGIN
    DELETE FROM search_index WHERE rowid = 300000000000 + OLD.id_id;
END;

CREATE TRIGGER IF NOT EXISTS projects_ai AFTER INSERT ON projects BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (400000000000 + NEW.project_id, 'project', 'PRJ', NEW.title, NEW.description, NEW.folder_path);
END;

CREATE TRIGGER IF NOT EXISTS projects_au AFTER UPDATE ON projects BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (400000000000 + NEW.project_id, 'project', 'PRJ', NEW.title, NEW.description, NEW.folder_path);
END;

CREATE TRIGGER IF NOT EXISTS projects_ad AFTER DELETE ON projects BEGIN
    DELETE FROM search_index WHERE rowid = 400000000000 + OLD.project_id;
END;
"""

_FTS5_SEARCH_INDEX = """
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    entity_type UNINDEXED,
    code        UNINDEXED,
    title,
    description,
    path        UNINDEXED,
    tokenize = 'porter unicode61'
);
"""

_FALLBACK_SEARCH_INDEX = """
CREATE TABLE IF NOT EXISTS search_index (
    rowid       INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    code        TEXT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    path        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_search_index_title ON search_index(title);
"""


def get_connection(pathToDb):
    """
    *open a SQLite connection to the aardvark index, with row access by column name*

    **Key Arguments:**

    - ``pathToDb`` -- path to the `aardvark.db` file

    **Return:**

    - ``dbConn`` -- the open SQLite connection
    """
    dbConn = sqlite3.connect(pathToDb)
    dbConn.row_factory = sqlite3.Row
    dbConn.execute("PRAGMA foreign_keys = ON")
    return dbConn


def initialise_schema(dbConn):
    """
    *create the aardvark schema if it does not already exist*

    Probes for FTS5 support once, falling back to a plain indexed table
    for `search_index` if the SQLite build lacks the FTS5 module, and
    records the outcome in `meta['fts5_enabled']`.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    """
    dbConn.executescript(_BASE_SCHEMA)

    fts5Enabled = get_meta(dbConn, "fts5_enabled")
    if fts5Enabled is None:
        try:
            dbConn.executescript(_FTS5_SEARCH_INDEX)
            fts5Enabled = "1"
        except sqlite3.OperationalError:
            dbConn.executescript(_FALLBACK_SEARCH_INDEX)
            fts5Enabled = "0"
        set_meta(dbConn, "fts5_enabled", fts5Enabled)
    elif fts5Enabled == "1":
        dbConn.executescript(_FTS5_SEARCH_INDEX)
    else:
        dbConn.executescript(_FALLBACK_SEARCH_INDEX)

    dbConn.executescript(_SEARCH_TRIGGERS)
    dbConn.commit()


def get_meta(dbConn, key):
    """
    *read a value from the `meta` table*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``key`` -- the meta key to read

    **Return:**

    - ``value`` -- the stored value, or `None` if not set
    """
    row = dbConn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(dbConn, key, value):
    """
    *write a value into the `meta` table*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``key`` -- the meta key to write
    - ``value`` -- the value to store
    """
    dbConn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    dbConn.commit()


def fts5_enabled(dbConn):
    """
    *check whether the FTS5 search index is in use for this database*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection

    **Return:**

    - ``enabled`` -- `True` if FTS5 is in use, `False` if the LIKE fallback is
    """
    return get_meta(dbConn, "fts5_enabled") == "1"


def insert_system_folder(dbConn, folderKey, folderName, folderPath):
    """
    *record the exact name/path of a static scaffold folder*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``folderKey`` -- the logical key for this folder, e.g. `"root.areas"`
    - ``folderName`` -- the folder's exact on-disk name (including emoji)
    - ``folderPath`` -- the folder's absolute path
    """
    dbConn.execute(
        "INSERT INTO system_folders(folder_key, folder_name, folder_path) VALUES (?, ?, ?) "
        "ON CONFLICT(folder_key) DO UPDATE SET folder_name = excluded.folder_name, "
        "folder_path = excluded.folder_path",
        (folderKey, folderName, folderPath),
    )
    dbConn.commit()


def get_system_folder(dbConn, folderKey):
    """
    *look up a static scaffold folder's exact name/path*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``folderKey`` -- the logical key for this folder, e.g. `"root.areas"`

    **Return:**

    - ``row`` -- the `system_folders` row, or `None` if not found
    """
    return dbConn.execute(
        "SELECT * FROM system_folders WHERE folder_key = ?", (folderKey,)
    ).fetchone()


def insert_area(dbConn, domain, decadeStart, decadeEnd, title, description, emoji, folderName, folderPath):
    """
    *insert a new Johnny Decimal area row*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``decadeStart`` -- the area's decade-start number
    - ``decadeEnd`` -- the area's decade-end number
    - ``title`` -- the area's title
    - ``description`` -- the area's description
    - ``emoji`` -- the emoji appended to the area's folder name
    - ``folderName`` -- the area's exact on-disk folder name
    - ``folderPath`` -- the area's absolute folder path

    **Return:**

    - ``areaId`` -- the new row's primary key
    """
    cursor = dbConn.execute(
        "INSERT INTO areas(domain, decade_start, decade_end, title, description, emoji, folder_name, folder_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (domain, decadeStart, decadeEnd, title, description, emoji, folderName, folderPath),
    )
    dbConn.commit()
    return cursor.lastrowid


def get_area(dbConn, domain, decadeStart):
    """
    *look up a Johnny Decimal area by domain and decade-start number*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``decadeStart`` -- the area's decade-start number

    **Return:**

    - ``row`` -- the `areas` row, or `None` if not found
    """
    return dbConn.execute(
        "SELECT * FROM areas WHERE domain = ? AND decade_start = ?", (domain, decadeStart)
    ).fetchone()


def list_areas(dbConn, domain):
    """
    *list all Johnny Decimal areas for a domain, ordered by decade*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`

    **Return:**

    - ``rows`` -- the matching `areas` rows
    """
    return dbConn.execute(
        "SELECT * FROM areas WHERE domain = ? ORDER BY decade_start", (domain,)
    ).fetchall()


def insert_category(dbConn, areaId, domain, acNumber, title, description, emoji, folderName, folderPath):
    """
    *insert a new Johnny Decimal category row*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``areaId`` -- the parent area's primary key
    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the category's 2-digit AC number
    - ``title`` -- the category's title
    - ``description`` -- the category's description
    - ``emoji`` -- the emoji appended to the category's folder name
    - ``folderName`` -- the category's exact on-disk folder name
    - ``folderPath`` -- the category's absolute folder path

    **Return:**

    - ``categoryId`` -- the new row's primary key
    """
    cursor = dbConn.execute(
        "INSERT INTO categories(area_id, domain, ac_number, title, description, emoji, folder_name, folder_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (areaId, domain, acNumber, title, description, emoji, folderName, folderPath),
    )
    dbConn.commit()
    return cursor.lastrowid


def get_category(dbConn, domain, acNumber):
    """
    *look up a Johnny Decimal category by domain and AC number*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the category's 2-digit AC number

    **Return:**

    - ``row`` -- the `categories` row, or `None` if not found
    """
    return dbConn.execute(
        "SELECT * FROM categories WHERE domain = ? AND ac_number = ?", (domain, acNumber)
    ).fetchone()


def list_categories(dbConn, domain, areaId=None):
    """
    *list Johnny Decimal categories for a domain, optionally within one area*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``areaId`` -- restrict to this area's primary key. Default `None`.

    **Return:**

    - ``rows`` -- the matching `categories` rows
    """
    if areaId is None:
        return dbConn.execute(
            "SELECT * FROM categories WHERE domain = ? ORDER BY ac_number", (domain,)
        ).fetchall()
    return dbConn.execute(
        "SELECT * FROM categories WHERE domain = ? AND area_id = ? ORDER BY ac_number",
        (domain, areaId),
    ).fetchall()


def insert_id(dbConn, categoryId, domain, acNumber, itemNumber, title, description, folderName, folderPath):
    """
    *insert a new Johnny Decimal ID row*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``categoryId`` -- the parent category's primary key
    - ``domain`` -- `areas` or `resources`
    - ``acNumber`` -- the parent category's 2-digit AC number
    - ``itemNumber`` -- the ID's 2-digit item number
    - ``title`` -- the ID's title
    - ``description`` -- the ID's description
    - ``folderName`` -- the ID's exact on-disk folder name (no emoji)
    - ``folderPath`` -- the ID's absolute folder path

    **Return:**

    - ``idId`` -- the new row's primary key
    """
    cursor = dbConn.execute(
        "INSERT INTO ids(category_id, domain, ac_number, item_number, title, description, folder_name, folder_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (categoryId, domain, acNumber, itemNumber, title, description, folderName, folderPath),
    )
    dbConn.commit()
    return cursor.lastrowid


def list_ids(dbConn, domain, categoryId):
    """
    *list Johnny Decimal IDs within a category*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``domain`` -- `areas` or `resources`
    - ``categoryId`` -- the parent category's primary key

    **Return:**

    - ``rows`` -- the matching `ids` rows
    """
    return dbConn.execute(
        "SELECT * FROM ids WHERE domain = ? AND category_id = ? ORDER BY item_number",
        (domain, categoryId),
    ).fetchall()


def insert_project(dbConn, title, description, emoji, folderName, folderPath, templateUsed):
    """
    *insert a new project row*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``title`` -- the project's title
    - ``description`` -- the project's description
    - ``emoji`` -- the emoji appended to the project's folder name
    - ``folderName`` -- the project's exact on-disk folder name
    - ``folderPath`` -- the project's absolute folder path
    - ``templateUsed`` -- the template zip's basename, or `"blank"`

    **Return:**

    - ``projectId`` -- the new row's primary key
    """
    cursor = dbConn.execute(
        "INSERT INTO projects(title, description, emoji, folder_name, folder_path, template_used) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, emoji, folderName, folderPath, templateUsed),
    )
    dbConn.commit()
    return cursor.lastrowid

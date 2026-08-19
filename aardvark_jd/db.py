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
    domain        TEXT NOT NULL CHECK (domain IN ('areas','resources','projects')),
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
    domain        TEXT NOT NULL CHECK (domain IN ('areas','resources','projects')),
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
    domain        TEXT NOT NULL CHECK (domain IN ('areas','resources','projects')),
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

CREATE TABLE IF NOT EXISTS craft_links (
    entity_type        TEXT NOT NULL,
    entity_key         TEXT NOT NULL,
    craft_folder_id     TEXT,
    craft_document_id   TEXT,
    craft_block_id       TEXT,
    craft_url           TEXT,
    synced_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
    PRIMARY KEY (entity_type, entity_key)
);
"""

# `CREATE TRIGGER IF NOT EXISTS` NEVER UPDATES AN EXISTING TRIGGER'S BODY, SO
# AN EXISTING DATABASE WOULD SILENTLY KEEP THE OLD CODE-STRING FORMAT FOREVER
# UNLESS EVERY TRIGGER IS EXPLICITLY DROPPED FIRST ON EACH SCHEMA INIT.
_DROP_SEARCH_TRIGGERS = """
DROP TRIGGER IF EXISTS areas_ai;
DROP TRIGGER IF EXISTS areas_au;
DROP TRIGGER IF EXISTS areas_ad;
DROP TRIGGER IF EXISTS categories_ai;
DROP TRIGGER IF EXISTS categories_au;
DROP TRIGGER IF EXISTS categories_ad;
DROP TRIGGER IF EXISTS ids_ai;
DROP TRIGGER IF EXISTS ids_au;
DROP TRIGGER IF EXISTS ids_ad;
"""

_SEARCH_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS areas_ai AFTER INSERT ON areas BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        100000000000 + NEW.area_id, 'area',
        (CASE NEW.domain WHEN 'areas' THEN 'A' WHEN 'projects' THEN 'P' ELSE 'R' END) ||
            printf('%02d', NEW.decade_start) || '-' || printf('%02d', NEW.decade_start + 9),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS areas_au AFTER UPDATE ON areas BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        100000000000 + NEW.area_id, 'area',
        (CASE NEW.domain WHEN 'areas' THEN 'A' WHEN 'projects' THEN 'P' ELSE 'R' END) ||
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
        (CASE NEW.domain WHEN 'areas' THEN 'A' WHEN 'projects' THEN 'P' ELSE 'R' END) || printf('%02d', NEW.ac_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS categories_au AFTER UPDATE ON categories BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        200000000000 + NEW.category_id, 'category',
        (CASE NEW.domain WHEN 'areas' THEN 'A' WHEN 'projects' THEN 'P' ELSE 'R' END) || printf('%02d', NEW.ac_number),
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
        (CASE NEW.domain WHEN 'areas' THEN 'A' WHEN 'projects' THEN 'P' ELSE 'R' END) ||
            printf('%02d', NEW.ac_number) || '.' || printf('%02d', NEW.item_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS ids_au AFTER UPDATE ON ids BEGIN
    INSERT OR REPLACE INTO search_index(rowid, entity_type, code, title, description, path)
    VALUES (
        300000000000 + NEW.id_id, 'id',
        (CASE NEW.domain WHEN 'areas' THEN 'A' WHEN 'projects' THEN 'P' ELSE 'R' END) ||
            printf('%02d', NEW.ac_number) || '.' || printf('%02d', NEW.item_number),
        NEW.title, NEW.description, NEW.folder_path
    );
END;

CREATE TRIGGER IF NOT EXISTS ids_ad AFTER DELETE ON ids BEGIN
    DELETE FROM search_index WHERE rowid = 300000000000 + OLD.id_id;
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

# BUMP WHEN `_BASE_SCHEMA` CHANGES IN A WAY THAT AN ALREADY-INITIALISED
# DATABASE CAN'T PICK UP VIA THE `IF NOT EXISTS` DDL ALONE (E.G. A WIDENED
# `CHECK` CONSTRAINT), AND ADD THE ONE-OFF REBUILD TO `_migrate_schema`.
_SCHEMA_VERSION = "2"


def _migrate_schema(dbConn):
    """
    *rebuild `areas`/`categories`/`ids` onto the current schema and drop the legacy flat `projects` table*

    SQLite cannot alter a `CHECK` constraint in place, so an
    already-initialised database - whose `areas`/`categories`/`ids` tables
    are still `CHECK`-constrained to `('areas','resources')` from before
    Projects became a Johnny Decimal domain - is rebuilt: the three tables
    are renamed aside, recreated via `_BASE_SCHEMA` (which now carries the
    widened `('areas','resources','projects')` constraint), their rows
    copied across, then the renamed-aside tables and the legacy `projects`
    table are dropped. Gated on `meta['schema_version']` so it only runs
    once. A brand-new database (created directly against the current
    `_BASE_SCHEMA`, so already current) just stamps the version.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    """
    if get_meta(dbConn, "schema_version") == _SCHEMA_VERSION:
        return

    areasTableExists = dbConn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'areas'"
    ).fetchone()
    if areasTableExists is None:
        set_meta(dbConn, "schema_version", _SCHEMA_VERSION)
        return

    dbConn.execute("PRAGMA foreign_keys = OFF")
    dbConn.execute("ALTER TABLE areas RENAME TO areas_old")
    dbConn.execute("ALTER TABLE categories RENAME TO categories_old")
    dbConn.execute("ALTER TABLE ids RENAME TO ids_old")
    dbConn.executescript(_BASE_SCHEMA)
    dbConn.execute("INSERT INTO areas SELECT * FROM areas_old")
    dbConn.execute("INSERT INTO categories SELECT * FROM categories_old")
    dbConn.execute("INSERT INTO ids SELECT * FROM ids_old")
    dbConn.execute("DROP TABLE areas_old")
    dbConn.execute("DROP TABLE categories_old")
    dbConn.execute("DROP TABLE ids_old")
    dbConn.execute("DROP TABLE IF EXISTS projects")
    dbConn.execute("PRAGMA foreign_keys = ON")
    dbConn.commit()
    set_meta(dbConn, "schema_version", _SCHEMA_VERSION)


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
    records the outcome in `meta['fts5_enabled']`. The search triggers are
    dropped and recreated on every call, since `CREATE TRIGGER IF NOT
    EXISTS` would otherwise leave an existing database's older trigger
    bodies in place forever. Runs `_migrate_schema` first so an
    already-initialised database is upgraded onto the current schema
    before `_BASE_SCHEMA`'s `IF NOT EXISTS` DDL runs.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    """
    dbConn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    dbConn.commit()
    _migrate_schema(dbConn)

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

    dbConn.executescript(_DROP_SEARCH_TRIGGERS)
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


# EVERY TABLE THAT PERSISTS AN ABSOLUTE `folder_path`, AND SO HAS TO BE
# REWRITTEN WHEN AN ANCESTOR FOLDER IS RENAMED.
_PATH_BEARING_TABLES = ("system_folders", "areas", "categories", "ids")


def rewrite_folder_path_prefix(dbConn, oldPrefix, newPrefix):
    """
    *repoint every descendant row from an old ancestor folder path to a new one*

    Renaming a folder silently invalidates the stored `folder_path` of
    everything nested inside it - categories and IDs under an area, IDs
    under a category, and the whole domain under a section folder - so
    this rewrites all of them in one pass.

    Matching is done with `substr` rather than `LIKE` because aardvark
    folder names are full of underscores (`00_INDEX`), which `LIKE` would
    treat as single-character wildcards.

    Does **not** commit - the caller owns the transaction so the rename and
    the rewrite land together.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``oldPrefix`` -- the ancestor folder's old absolute path
    - ``newPrefix`` -- the ancestor folder's new absolute path

    **Return:**

    - ``rewritten`` -- the total number of descendant rows repointed
    """
    oldParent = oldPrefix.rstrip("/") + "/"
    newParent = newPrefix.rstrip("/") + "/"
    prefixLength = len(oldParent)

    rewritten = 0
    for tableName in _PATH_BEARING_TABLES:
        cursor = dbConn.execute(
            f"UPDATE {tableName} SET folder_path = ? || substr(folder_path, ?) "
            f"WHERE substr(folder_path, 1, ?) = ?",
            (newParent, prefixLength + 1, prefixLength, oldParent),
        )
        rewritten += cursor.rowcount
    return rewritten


def update_area_emoji(dbConn, areaId, emoji, folderName, folderPath):
    """
    *update an area's emoji, folder name and folder path (without committing)*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``areaId`` -- the area's primary key
    - ``emoji`` -- the new emoji
    - ``folderName`` -- the area's new on-disk folder name
    - ``folderPath`` -- the area's new absolute folder path
    """
    dbConn.execute(
        "UPDATE areas SET emoji = ?, folder_name = ?, folder_path = ?, "
        "updated_at = strftime('%Y-%m-%d %H:%M:%S','now') WHERE area_id = ?",
        (emoji, folderName, folderPath, areaId),
    )


def update_category_emoji(dbConn, categoryId, emoji, folderName, folderPath):
    """
    *update a category's emoji, folder name and folder path (without committing)*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``categoryId`` -- the category's primary key
    - ``emoji`` -- the new emoji
    - ``folderName`` -- the category's new on-disk folder name
    - ``folderPath`` -- the category's new absolute folder path
    """
    dbConn.execute(
        "UPDATE categories SET emoji = ?, folder_name = ?, folder_path = ?, "
        "updated_at = strftime('%Y-%m-%d %H:%M:%S','now') WHERE category_id = ?",
        (emoji, folderName, folderPath, categoryId),
    )


def update_id_name(dbConn, idId, folderName, folderPath):
    """
    *update an ID's folder name and folder path (without committing)*

    IDs carry no `emoji` column, unlike areas/categories/projects, so
    there's nothing to pass alongside the name/path.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``idId`` -- the ID's primary key
    - ``folderName`` -- the ID's new on-disk folder name
    - ``folderPath`` -- the ID's new absolute folder path
    """
    dbConn.execute(
        "UPDATE ids SET folder_name = ?, folder_path = ?, "
        "updated_at = strftime('%Y-%m-%d %H:%M:%S','now') WHERE id_id = ?",
        (folderName, folderPath, idId),
    )


def update_system_folder(dbConn, folderKey, folderName, folderPath):
    """
    *update a static system folder's name and path (without committing)*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``folderKey`` -- the logical folder key, e.g. `"root.areas"`
    - ``folderName`` -- the folder's new on-disk name
    - ``folderPath`` -- the folder's new absolute path
    """
    dbConn.execute(
        "UPDATE system_folders SET folder_name = ?, folder_path = ? WHERE folder_key = ?",
        (folderName, folderPath, folderKey),
    )


def list_system_folders(dbConn):
    """
    *list every recorded static system folder*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection

    **Return:**

    - ``rows`` -- the `system_folders` rows
    """
    return dbConn.execute("SELECT * FROM system_folders ORDER BY folder_key").fetchall()


def upsert_craft_link(
    dbConn, entityType, entityKey, craftFolderId=None, craftDocumentId=None, craftBlockId=None, craftUrl=None,
):
    """
    *record or refresh an entity's linked Craft folder/document/block*

    Fields left as `None` keep whatever was already stored, rather than
    being wiped - an index document's `craftBlockId` is only known after a
    later `add_block` call, so it's set in a second upsert that must not
    clobber the `craftDocumentId` written by the first.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``entityType`` -- `'system_folder'`, `'area'`, `'category'` or `'id'`
    - ``entityKey`` -- the entity's key: a `system_folders.folder_key`, or an
      `area_id`/`category_id`/`id_id`/`project_id` cast to text
    - ``craftFolderId`` -- the linked Craft folder's id, if any. Default `None`.
    - ``craftDocumentId`` -- the linked Craft document's id, if any. Default `None`.
    - ``craftBlockId`` -- the linked Craft block's id, if any. Default `None`.
    - ``craftUrl`` -- the linked Craft folder/document's shareable URL, if any. Default `None`.
    """
    dbConn.execute(
        "INSERT INTO craft_links(entity_type, entity_key, craft_folder_id, craft_document_id, craft_block_id, craft_url) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(entity_type, entity_key) DO UPDATE SET "
        "craft_folder_id = COALESCE(excluded.craft_folder_id, craft_links.craft_folder_id), "
        "craft_document_id = COALESCE(excluded.craft_document_id, craft_links.craft_document_id), "
        "craft_block_id = COALESCE(excluded.craft_block_id, craft_links.craft_block_id), "
        "craft_url = COALESCE(excluded.craft_url, craft_links.craft_url), "
        "synced_at = strftime('%Y-%m-%d %H:%M:%S','now')",
        (entityType, entityKey, craftFolderId, craftDocumentId, craftBlockId, craftUrl),
    )
    dbConn.commit()


def get_craft_link(dbConn, entityType, entityKey):
    """
    *look up an entity's linked Craft folder/document, if any*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``entityType`` -- `'system_folder'`, `'area'`, `'category'` or `'id'`
    - ``entityKey`` -- the entity's key, as passed to `upsert_craft_link`

    **Return:**

    - ``row`` -- the `craft_links` row, or `None` if not yet synced
    """
    return dbConn.execute(
        "SELECT * FROM craft_links WHERE entity_type = ? AND entity_key = ?", (entityType, entityKey)
    ).fetchone()

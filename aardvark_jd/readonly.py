#!/usr/bin/env python
# encoding: utf-8
"""
*Open a read-only connection to the active system's index, without ever mutating it*

Shared by `completion.py` (a keystroke must be fast and strictly
read-only) and `change_dir.py` (`av cd` runs on every directory jump, so
the same constraint applies: no settings-file creation, no
`db.initialise_schema` - which drops and recreates nine triggers - and no
Dropbox-ignore re-assert).

Author
: David Young
"""

import os
import sqlite3

from aardvark_jd import paths


def settings_path_from(words):
    """
    *the settings file the command line points at, or the default one*

    A user completing `aardvark add_id -s other.yaml <TAB>` means the
    areas in *that* system, not the one recorded in the default config -
    so the flag is honoured here rather than silently ignored.

    **Key Arguments:**

    - ``words`` -- the full command line as a word list

    **Return:**

    - ``settingsPath`` -- the path to read settings from
    """
    for index, word in enumerate(words):
        if word in ("-s", "--settings") and index + 1 < len(words):
            return os.path.expanduser(words[index + 1])
    return os.path.expanduser("~/.config/aardvark/aardvark.yaml")


def with_connection(fn, words=()):
    """
    *run `fn` against a read-only connection to the active system's index, or return None*

    Read-only (`mode=ro`) is deliberate: the caller must never create,
    migrate or write to the index, and must not fail if the system is
    missing or the settings file is unreadable.

    Only **opening** the connection is swallowed to `None` - a missing
    settings file, an unset `root_path` or a database that will not open
    all mean "no index available", which every caller treats the same
    way. `fn` itself is called *outside* that guard, so a deliberate
    `ValueError` it raises (an unresolvable reference, say) propagates to
    the caller rather than being silently downgraded to `None`.
    `completion.emit` still swallows everything, via its own outer
    `try/except`, so this change is invisible there; `change_dir.emit`
    relies on it to report exactly what went wrong.

    **Key Arguments:**

    - ``fn`` -- a callable taking the open connection
    - ``words`` -- the full command line, so an explicit `-s` is honoured. Default *()*.

    **Return:**

    - ``result`` -- whatever `fn` returns, or `None` if no index could be opened

    **Raises:**

    - whatever `fn` itself raises

    **Usage:**

    ```python
    from aardvark_jd import readonly
    row = readonly.with_connection(lambda dbConn: dbConn.execute("SELECT 1").fetchone())
    ```
    """
    from aardvark_jd import settings_writer

    try:
        settingsPath = settings_path_from(words)
        settings = settings_writer.read_settings(settingsPath) or {}
        rootPath = (settings.get("system") or {}).get("root_path")
        if not rootPath:
            return None
        dbPath = paths.find_db_path(rootPath)
        dbConn = sqlite3.connect(f"file:{dbPath}?mode=ro", uri=True)
        dbConn.row_factory = sqlite3.Row
        # WAIT OUT A CONCURRENT MUTATING COMMAND RATHER THAN RETURNING NO
        # RESULT: A TAB PRESS OR `av cd` CAN LAND DURING A WRITE. SAFE ON
        # `mode=ro`, NOT A PERSISTENT HEADER CHANGE. SEE `db.get_connection`.
        dbConn.execute("PRAGMA busy_timeout = 5000")
    except Exception:
        return None

    try:
        return fn(dbConn)
    finally:
        dbConn.close()

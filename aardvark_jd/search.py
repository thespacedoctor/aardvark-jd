#!/usr/bin/env python
# encoding: utf-8
"""
*Search the aardvark index by keyword or phrase*

Author
: David Young
"""

import sqlite3

from aardvark_jd import db

# FTS5 COLUMN ORDER: entity_type, code, title, description, path - WEIGHT
# TITLE MATCHES ABOVE DESCRIPTION MATCHES, IGNORE THE UNINDEXED COLUMNS
_BM25_WEIGHTS = "0.0, 0.0, 10.0, 1.0, 0.0"


class search(object):
    """
    *search the areas/categories/ids/projects index by keyword or phrase*

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``terms`` -- a list of search words/phrases, e.g. `["cardio"]`

    **Usage:**

    ```python
    from aardvark_jd.search import search
    results = search(log=log, dbConn=dbConn, terms=["cardio"]).get()
    ```
    """

    def __init__(self, log, dbConn, terms):
        self.log = log
        self.dbConn = dbConn
        self.terms = terms

    def get(self):
        """
        *run the search and return ranked results*

        **Return:**

        - ``results`` -- a list of dicts with keys `entity_type`, `code`, `title`, `description`, `path`
        """
        self.log.debug("starting the ``get`` method")

        terms = [term for term in self.terms if term]
        if not terms:
            return []

        if db.fts5_enabled(self.dbConn):
            rows = self._search_fts5(terms)
        else:
            rows = self._search_like(" ".join(terms))

        self.log.debug("completed the ``get`` method")
        return [dict(row) for row in rows]

    def _search_fts5(self, terms):
        """
        *run an FTS5 `MATCH` prefix query, ranked by `bm25()` with title weighted above description*

        Each term is matched as a quoted phrase prefix (`"cardio"*`) and
        terms are ANDed together, so e.g. `"cardio"` matches `"Cardiologist"`.

        **Key Arguments:**

        - ``terms`` -- the search words/phrases

        **Return:**

        - ``rows`` -- the matching `search_index` rows, best match first
        """
        sql = (
            f"SELECT entity_type, code, title, description, path "
            f"FROM search_index WHERE search_index MATCH ? "
            f"ORDER BY bm25(search_index, {_BM25_WEIGHTS}) LIMIT 50"
        )
        ftsQuery = " AND ".join(f'"{term}"*' for term in terms)
        try:
            return self.dbConn.execute(sql, (ftsQuery,)).fetchall()
        except sqlite3.OperationalError:
            # A MALFORMED FTS5 QUERY (E.G. STRAY PUNCTUATION) - FALL BACK TO LIKE
            return self._search_like(" ".join(terms))

    def _search_like(self, query):
        """
        *run a `LIKE`-based search, ranking title matches above description-only matches*

        **Key Arguments:**

        - ``query`` -- the raw search query text

        **Return:**

        - ``rows`` -- the matching `search_index` rows, best match first
        """
        pattern = f"%{query}%"
        sql = (
            "SELECT entity_type, code, title, description, path, "
            "(CASE WHEN title LIKE ? THEN 0 ELSE 1 END) AS rank "
            "FROM search_index WHERE title LIKE ? OR description LIKE ? "
            "ORDER BY rank, title LIMIT 50"
        )
        return self.dbConn.execute(sql, (pattern, pattern, pattern)).fetchall()


def format_result(row):
    """
    *format a single search result row for display*

    **Key Arguments:**

    - ``row`` -- a result dict with keys `code`, `title`, `path`

    **Return:**

    - ``line`` -- the formatted `<code>  <title>  <path>` display line
    """
    code = row["code"] or ""
    return f"{code}  {row['title']}  {row['path']}"

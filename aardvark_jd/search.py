#!/usr/bin/env python
# encoding: utf-8
"""
*Search the aardvark index by keyword or phrase*

Author
: David Young
"""

import sqlite3

from aardvark_jd import codes, db

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


class tree(object):
    """
    *render the whole index, or one Johnny Decimal subtree, as an indented tree*

    Backs a bare `aardvark search` (the whole index) and `aardvark search
    <ref>` (the subtree under a domain letter, area or category). An ID ref
    has no subtree, so the caller prints its path line instead.

    The reserved `.00`-`.09` system IDs never appear: they live in
    `system_folders`, not `ids`, so walking the index tables excludes them
    for free.

    **Key Arguments:**

    - ``log`` -- logger
    - ``dbConn`` -- an open SQLite connection
    - ``ref`` -- a domain letter, area ref or category ref to scope the tree to. Default *None*, meaning the whole index.

    **Usage:**

    ```python
    from aardvark_jd.search import tree
    for line in tree(log=log, dbConn=dbConn, ref="A10-19").get():
        print(line)
    ```
    """

    def __init__(self, log, dbConn, ref=None):
        self.log = log
        self.dbConn = dbConn
        self.ref = ref

    def get(self):
        """
        *build the tree's display lines*

        **Return:**

        - ``lines`` -- a list of ready-to-print strings
        """
        self.log.debug("starting the ``get`` method")

        nodes = self._nodes()
        lines = self._drift_lines() + format_tree(nodes)

        self.log.debug("completed the ``get`` method")
        return lines

    def _drift_lines(self):
        """
        *a header naming any mirror whose last sync failed, or nothing when all are healthy*

        Sync runs in a detached process with no terminal, so this listing -
        the one command a user runs to see the state of their system - is
        where a failure has to be legible rather than merely logged.

        **Return:**

        - ``lines`` -- zero or more ready-to-print strings
        """
        drifted = db.drifted_mirrors(self.dbConn)
        if not drifted:
            return []
        lines = []
        for row in drifted:
            lines.append(
                f"! {row['mirror']} is out of sync ({row['last_failure_class']}, "
                f"last tried {row['last_failure_at']})"
            )
        lines.append("")
        return lines

    def _nodes(self):
        """
        *walk the index into a nested list of display nodes*

        **Return:**

        - ``nodes`` -- a list of dicts with keys `label`, `path` and `children`
        """
        if self.ref is None:
            return [
                node
                for domain in codes.DOMAINS
                for node in self._domain_nodes(domain)
            ]

        domain = codes.domain_from_ref(self.ref) if codes.is_jd_ref(self.ref) else None
        if domain is None:
            domain = codes.domain_from_letter(self.ref)

        # A BARE DOMAIN LETTER HAS NO NUMBERS IN IT, SO IT SCOPES TO THE WHOLE DOMAIN.
        if len(self.ref.strip(".")) == 1:
            return self._domain_nodes(domain)

        if codes.parse_area_ref_is_area(self.ref):
            decadeStart = codes.parse_area_ref(self.ref)
            area = db.get_area(self.dbConn, domain, decadeStart)
            if not area:
                raise ValueError(f"no area '{self.ref}' in the index")
            return [self._area_node(domain, area)]

        acNumber = codes.parse_category_ref(self.ref)
        category = db.get_category(self.dbConn, domain, acNumber)
        if not category:
            raise ValueError(f"no category '{self.ref}' in the index")
        return [self._category_node(domain, category)]

    def _domain_nodes(self, domain):
        """
        *the areas of one domain, as display nodes*

        **Key Arguments:**

        - ``domain`` -- `areas`, `resources` or `projects`

        **Return:**

        - ``nodes`` -- a single-element list holding the domain's node
        """
        children = [self._area_node(domain, area) for area in db.list_areas(self.dbConn, domain)]
        return [{
            "label": f"{codes.DOMAIN_LETTER[domain]}  {domain}",
            "path": None,
            "children": children,
        }]

    def _area_node(self, domain, area):
        """
        *one area and its categories, as a display node*

        **Key Arguments:**

        - ``domain`` -- the area's domain
        - ``area`` -- the `areas` row

        **Return:**

        - ``node`` -- the display node
        """
        code = codes.format_area_code(domain, area["decade_start"], area["decade_end"])
        children = [
            self._category_node(domain, category)
            for category in db.list_categories(self.dbConn, domain, areaId=area["area_id"])
        ]
        return {"label": f"{code}  {area['title']}", "path": area["folder_path"], "children": children}

    def _category_node(self, domain, category):
        """
        *one category and its IDs, as a display node*

        **Key Arguments:**

        - ``domain`` -- the category's domain
        - ``category`` -- the `categories` row

        **Return:**

        - ``node`` -- the display node
        """
        code = codes.format_category_code(domain, category["ac_number"])
        children = [
            {
                "label": f"{codes.format_id_code(domain, row['ac_number'], row['item_number'])}  {row['title']}",
                "path": row["folder_path"],
                "children": [],
            }
            for row in db.list_ids(self.dbConn, domain, category["category_id"])
        ]
        return {
            "label": f"{code}  {category['title']}",
            "path": category["folder_path"],
            "children": children,
        }


def format_tree(nodes, prefix=""):
    """
    *render nested display nodes as box-drawing tree lines*

    **Key Arguments:**

    - ``nodes`` -- a list of dicts with keys `label`, `path` and `children`
    - ``prefix`` -- the indent carried down from the parent level. Default *""*.

    **Return:**

    - ``lines`` -- a list of ready-to-print strings

    **Usage:**

    ```python
    from aardvark_jd.search import format_tree
    lines = format_tree(nodes)
    ```
    """
    lines = []
    for index, node in enumerate(nodes):
        isLast = index == len(nodes) - 1
        if prefix == "" and node["path"] is None:
            # A DOMAIN HEADING SITS FLUSH LEFT WITH NO CONNECTOR ABOVE IT
            lines.append(node["label"])
            lines.extend(format_tree(node["children"], ""))
            continue
        connector = "└── " if isLast else "├── "
        lines.append(f"{prefix}{connector}{node['label']}")
        childPrefix = prefix + ("    " if isLast else "│   ")
        lines.extend(format_tree(node["children"], childPrefix))
    return lines

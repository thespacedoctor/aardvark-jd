#!/usr/bin/env python
# encoding: utf-8
"""
*Resolve a Johnny Decimal reference to the index row it names*

Shared by `archive.archive` and `change_dir.resolve_path` - both need the
same "what does this ref point at" ladder (ID first, then area, then
category), and both want the same clear `ValueError` when it does not
resolve.

Author
: David Young
"""

from aardvark_jd import codes, db


def resolve_ref(dbConn, ref, commandHint):
    """
    *resolve a Johnny Decimal reference to the entity it names*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``ref`` -- the reference as typed, e.g. `"A10-19"`, `"A11"` or `"A11.10"`
    - ``commandHint`` -- the command name to quote in the "not a reference" error, e.g. `"archive"`

    **Return:**

    - ``entityType`` -- `"area"`, `"category"` or `"id"`
    - ``domain`` -- the entity's domain
    - ``row`` -- the index row, carrying `folder_path`

    **Raises:**

    - ``ValueError`` -- if the ref is not a Johnny Decimal reference, or does not resolve

    **Usage:**

    ```python
    from aardvark_jd import refs
    entityType, domain, row = refs.resolve_ref(dbConn, "A11.10", "cd")
    ```
    """
    ref = (ref or "").strip().upper()
    if not (codes.is_jd_ref(ref) or codes.is_id_ref(ref)):
        raise ValueError(
            f"'{ref}' is not a Johnny Decimal reference - {commandHint} takes an area "
            "(\"A10-19\"), a category (\"A11\") or an ID (\"A11.10\")"
        )

    # RESOLVE AN ID FIRST - `domain_from_ref` ONLY UNDERSTANDS AREA AND
    # CATEGORY SHAPES, AND WOULD REJECT AN ID REF OUTRIGHT.
    if codes.is_id_ref(ref):
        domain, acNumber, itemNumber = codes.split_id_ref(ref)
        row = db.get_id(dbConn, domain, acNumber, itemNumber)
        if not row:
            raise ValueError(f"no ID '{ref}' in the index")
        return "id", domain, row

    domain = codes.domain_from_ref(ref)

    if codes.parse_area_ref_is_area(ref):
        decadeStart = codes.parse_area_ref(ref)
        row = db.get_area(dbConn, domain, decadeStart)
        if not row:
            raise ValueError(f"no area '{ref}' in the index")
        return "area", domain, row

    acNumber = codes.parse_category_ref(ref)
    row = db.get_category(dbConn, domain, acNumber)
    if not row:
        raise ValueError(f"no category '{ref}' in the index")
    return "category", domain, row

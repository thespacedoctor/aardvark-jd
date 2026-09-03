#!/usr/bin/env python
"""PROTOTYPE - wayfinder ticket 06. THROWAWAY.

Step 1 of the two-step `add_id` entry flow: emit the throwaway system's
categories as Alfred Script Filter items. Alfred does the matching
(`alfredfiltersresults` is on), so every invocation returns the whole list and
the query argument is ignored here.

Runs under the aardvark env interpreter, so it imports the package directly
rather than reimplementing the index read - it is throwaway and drift does not
matter.
"""
import json
import os
import sys

from aardvark_jd import codes, db, labels, paths

ROOT = os.environ["AARDVARK_ROOT"]


def main():
    conn = db.get_connection(paths.find_db_path(ROOT))
    items = []
    for domain in ("areas", "resources", "projects"):
        for row in db.list_categories(conn, domain):
            code = codes.format_category_code(domain, row["ac_number"])
            label = labels.category_label(domain, row)
            items.append(
                {
                    "uid": f"{domain}:{code}",
                    "title": label,
                    "subtitle": f"add a new ID into {code}  ·  {row['folder_path']}",
                    "arg": code,
                    "match": f"{code} {row['title']}",
                    "variables": {"CATEGORY_CODE": code, "CATEGORY_LABEL": label},
                    "icon": {"type": "fileicon", "path": row["folder_path"]},
                }
            )
    if not items:
        items = [
            {
                "title": "No categories in the throwaway system",
                "subtitle": "run ./setup.sh in the prototype directory first",
                "valid": False,
            }
        ]
    json.dump({"skipknowledge": True, "items": items}, sys.stdout)


if __name__ == "__main__":
    main()

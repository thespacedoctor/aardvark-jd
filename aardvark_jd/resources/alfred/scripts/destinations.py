#!/usr/bin/env python
# encoding: utf-8
"""
*Render the four mirror destinations for one entity as Alfred items*

Deliberately a stub. The rows are built by
`aardvark_jd.alfred.items.destination_items`, where pytest reaches them.
"""

import json
import os
import sys

from aardvark_jd.alfred import items


def main():
    urls = json.loads(os.environ.get("urls") or "{}")
    json.dump(
        {"items": items.destination_items(urls, entityTitle=os.environ.get("entity_title") or "")},
        sys.stdout,
    )


if __name__ == "__main__":
    main()

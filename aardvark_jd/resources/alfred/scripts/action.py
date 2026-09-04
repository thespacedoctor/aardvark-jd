#!/usr/bin/env python
# encoding: utf-8
"""
*Open every mirror an entity is synced to, and say what was opened*

Deliberately a stub. The decision of what to open lives in
`aardvark_jd.alfred.items`, where pytest reaches it; this file only reads
the item variables Alfred exported and calls `open`.
"""

import json
import os
import subprocess
import sys

from aardvark_jd.alfred import items


def main():
    urls = json.loads(os.environ.get("urls") or "{}")
    openable = items.mirror_urls_to_open(urls)

    if not openable:
        print("not synced to any mirror yet - run a sync first")
        return 1

    for _label, url in openable:
        subprocess.run(["open", url], check=False)

    print("opened " + ", ".join(label for label, _url in openable))
    return 0


if __name__ == "__main__":
    sys.exit(main())

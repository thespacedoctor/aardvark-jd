#!/usr/bin/env python
# encoding: utf-8
"""
*Render `aardvark fd --json` on stdin as the `av` Script Filter's items*

Deliberately a stub. Every decision lives in `aardvark_jd.alfred.items`,
where pytest reaches it; this file only moves bytes. It is invoked by
`index.sh` with the interpreter taken from the `aardvark` console script's
shebang, which is the one interpreter that can import `aardvark_jd`.
"""

import json
import os
import sys

from aardvark_jd.alfred import items


def main():
    payload = items.script_filter_payload(
        json.load(sys.stdin),
        workflowVersion=os.environ.get("alfred_workflow_version"),
    )
    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    main()

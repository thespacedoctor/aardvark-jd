#!/usr/bin/env python
# encoding: utf-8
"""
*Sort the Alfred workflow's `info.plist` objects, so Alfred's churn stops being diff noise*

`info.plist` is committed and Alfred's visual editor is the tool that edits
it. What Alfred rewrites on an edit is narrow: the `objects` array's order,
and `uidata`'s canvas coordinates. Neither is semantic, and both otherwise
show up as noise in every diff.

The two are contained asymmetrically. `uidata` is **left exactly as Alfred
wrote it** - stripping it would make Alfred re-lay out the canvas and
destroy the editor this whole approach is keeping. The `objects` array is
sorted by `uid`, which is stable: Alfred mints an object's `uid` once and
`connections` and `uidata` reference it forever.

Run by hand as `make alfred-normalise`, never as a git hook: this repo's
hooks live unversioned in `.git/hooks/` and are invisible to anyone else,
and an automatic rewrite firing while Alfred holds the workflow open is a
way to lose an edit.

**The sort rests on one inference: that `objects` order is non-semantic.**
It is consistent with everything observed, and it is what makes the diff
readable - but if a shuffled array ever turns out to break the workflow,
drop the sort and fall back to the documented reviewer's rule, "ignore
`uidata` and `objects` order when reading this diff".

Author
: David Young
"""

import plistlib
import sys
from pathlib import Path


def normalise_plist(plist):
    """
    *return a copy of a parsed `info.plist` with its `objects` array sorted by `uid`*

    **Key Arguments:**

    - ``plist`` -- the parsed `info.plist`

    **Return:**

    - ``normalised`` -- a new dict, with `objects` sorted and everything else untouched

    **Usage:**

    ```python
    from aardvark_jd.alfred import normalise
    normalised = normalise.normalise_plist(plistlib.loads(data))
    ```
    """
    if "objects" not in plist:
        return dict(plist)
    return dict(plist, objects=sorted(plist["objects"], key=lambda entry: entry.get("uid", "")))


def normalise_file(plistPath):
    """
    *sort one `info.plist` in place, and say whether anything moved*

    **Key Arguments:**

    - ``plistPath`` -- the `info.plist` to normalise

    **Return:**

    - ``changed`` -- `True` if the file was rewritten, `False` if it was already sorted
    """
    plistPath = Path(plistPath)
    original = plistPath.read_bytes()
    normalised = plistlib.dumps(normalise_plist(plistlib.loads(original)))

    if normalised == original:
        return False

    plistPath.write_bytes(normalised)
    return True


def main(argv=None):
    """
    *the `make alfred-normalise` entry point*

    **Key Arguments:**

    - ``argv`` -- the argument list. Default `None`, meaning `sys.argv[1:]`.

    **Return:**

    - ``exitCode`` -- `0` once every named file is sorted, `1` if no path was given
    """
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        print("usage: python -m aardvark_jd.alfred.normalise <path to info.plist>")
        return 1

    for plistPath in arguments:
        if normalise_file(plistPath):
            print(f"sorted the `objects` array in {plistPath}")
        else:
            print(f"{plistPath} was already sorted")
    return 0


if __name__ == "__main__":
    sys.exit(main())

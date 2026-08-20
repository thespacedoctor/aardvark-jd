#!/usr/bin/env python
# encoding: utf-8
"""
*Build the "open this folder elsewhere" link row appended to synced Craft documents*

A single inline markdown line - `[Finder link](hook://file/...)  ·
[Dropbox link](https://...)` - written just below a document's title by
`craft_sync._write_link_row`. Either link is dropped when it isn't
available (no Hookmark link off Darwin, no Dropbox link when the system
root isn't inside a Dropbox-synced folder).

Author
: David Young
"""

import base64
import os
import sys

FINDER_LABEL = "📁 Finder"
DROPBOX_LABEL = "🔗 Dropbox"

# ANY STRING WORKS HERE - HOOKMARK ONLY USES THE ID TO LOOK UP TRACKING DATA
# IN ITS OWN LOCAL DATABASE, WHICH AN AARDVARK-BUILT LINK NEVER APPEARS IN.
# ON A MISS IT FALLS BACK TO DECODING `p=`/`n=` AND LOCATING THE FILE VIA
# SPOTLIGHT - EXACTLY THE PATH EVERY AARDVARK-GENERATED LINK TAKES. KEEPING
# IT FIXED (RATHER THAN RANDOM) MATTERS FOR `craft_sync`'S IDEMPOTENCY CHECK:
# THE SAME FOLDER PATH MUST ALWAYS PRODUCE THE SAME URL.
_HOOKMARK_PLACEHOLDER_ID = "aardvark"


def hookmark_url(folderPath):
    """
    *build a Hookmark `hook://file/...` URL for a folder, or `None` off Darwin*

    Craft doesn't open `file://` links when clicked, so the folder link
    goes through Hookmark instead - Hookmark's own docs describe this
    exact fallback for a hand-built/shared link: when the id isn't found
    in its local database, it decodes the base64 `p=`/`n=` parameters and
    resolves the file via Spotlight. Hookmark itself is Mac-only, so this
    deliberately only fires on macOS, same as the `file://` link it
    replaces.

    **Key Arguments:**

    - ``folderPath`` -- the folder's absolute path

    **Return:**

    - ``url`` -- the folder's `hook://file/...` URL, or `None` if not on Darwin
    """
    if sys.platform != "darwin":
        return None
    absPath = os.path.realpath(os.path.expanduser(folderPath))
    parentPath, name = os.path.split(absPath)
    # EMBEDDED RAW, NOT PERCENT-ENCODED - MATCHING HOOKMARK'S OWN DOCUMENTED
    # EXAMPLE (`p=Lw==`) EXACTLY. PERCENT-ENCODING THE `=` PADDING TRIPPED
    # HOOKMARK'S OWN `hook://` HANDLER INTO REJECTING THE URL OUTRIGHT
    # ("THE URL IS INVALID") RATHER THAN JUST FAILING TO LOCATE THE FILE -
    # ITS PARSER EVIDENTLY EXPECTS THE LITERAL BASE64 TEXT, UNESCAPED.
    parentB64 = base64.b64encode(parentPath.encode("utf-8")).decode("ascii")
    nameB64 = base64.b64encode(name.encode("utf-8")).decode("ascii")
    return f"hook://file/{_HOOKMARK_PLACEHOLDER_ID}?p={parentB64}&n={nameB64}"


def link_row_markdown(hookmarkUrl, dropboxUrl):
    """
    *render the Finder/Dropbox link row as a single markdown line*

    **Key Arguments:**

    - ``hookmarkUrl`` -- the folder's Hookmark `hook://file/...` URL, or `None` to omit it
    - ``dropboxUrl`` -- the folder's Dropbox share URL, or `None` to omit it

    **Return:**

    - ``markdown`` -- the link row's markdown, or `None` if both URLs are `None`
    """
    links = []
    if hookmarkUrl:
        links.append(f"[{FINDER_LABEL}]({hookmarkUrl})")
    if dropboxUrl:
        links.append(f"[{DROPBOX_LABEL}]({dropboxUrl})")
    if not links:
        return None
    return "  ·  ".join(links)

#!/usr/bin/env python
# encoding: utf-8
"""
*Build the "open this folder elsewhere" link row appended to synced Craft documents*

A single inline markdown line - `[Finder link](file://...)  ·  [Dropbox
link](https://...)` - written just below a document's title by
`craft_sync._write_link_row`. Either link is dropped when it isn't
available (no Finder link off Darwin, no Dropbox link when the system
root isn't inside a Dropbox-synced folder).

Author
: David Young
"""

import os
import sys
from urllib.parse import quote

FINDER_LABEL = "📁 Finder"
DROPBOX_LABEL = "🔗 Dropbox"


def finder_url(folderPath):
    """
    *build a `file://` URL for a folder, or `None` off Darwin*

    A `file://` URL is only meaningful on the machine that generated it,
    so this deliberately only fires on macOS - the platform aardvark
    itself only ever runs on today.

    **Key Arguments:**

    - ``folderPath`` -- the folder's absolute path

    **Return:**

    - ``url`` -- the folder's `file://` URL, or `None` if not on Darwin
    """
    if sys.platform != "darwin":
        return None
    return "file://" + quote(os.path.realpath(os.path.expanduser(folderPath)))


def link_row_markdown(finderUrl, dropboxUrl):
    """
    *render the Finder/Dropbox link row as a single markdown line*

    **Key Arguments:**

    - ``finderUrl`` -- the folder's `file://` URL, or `None` to omit it
    - ``dropboxUrl`` -- the folder's Dropbox share URL, or `None` to omit it

    **Return:**

    - ``markdown`` -- the link row's markdown, or `None` if both URLs are `None`
    """
    links = []
    if finderUrl:
        links.append(f"[{FINDER_LABEL}]({finderUrl})")
    if dropboxUrl:
        links.append(f"[{DROPBOX_LABEL}]({dropboxUrl})")
    if not links:
        return None
    return "  ·  ".join(links)

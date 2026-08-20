#!/usr/bin/env python
# encoding: utf-8
"""
*Build the "open this folder elsewhere" link row appended to synced Craft documents*

A single inline markdown line - `[Finder link](hook://file/...)  ·
[Dropbox link](https://...)  ·  [Todoist link](https://...)` - written
just below a document's title by `craft_sync._write_link_row`. Any of
the three is dropped when it isn't available (no Hookmark link off
Darwin, no Dropbox link when the system root isn't inside a
Dropbox-synced folder, no Todoist link when Todoist isn't connected or
the entity isn't one `todoist_sync` mirrors).

Author
: David Young
"""

import base64
import hashlib
import os
import string
import sys
from pathlib import PurePosixPath

FINDER_LABEL = "📁 Finder"
DROPBOX_LABEL = "🔗 Dropbox"
TODOIST_LABEL = "✅ Todoist"
CRAFT_LABEL = "🗒️ Craft"

# HOOKMARK REJECTS `hook://file/...` URLS OUTRIGHT ("THE URL IS INVALID")
# UNLESS THE ID IS EXACTLY 9 CHARACTERS - CONFIRMED BY DECODING ALL 112
# `hook://file/` BOOKMARKS IN THE LIVE HOOKMARK DATABASE (VIA ITS APPLESCRIPT
# DICTIONARY). THE ID ITSELF NEVER NEEDS TO MATCH A REAL BOOKMARK: ON A
# LOOKUP MISS, HOOKMARK DECODES `p=`/`n=` AND LOCATES THE FILE VIA SPOTLIGHT -
# EXACTLY THE PATH EVERY AARDVARK-GENERATED LINK TAKES. KEEPING THE ID
# DETERMINISTIC (RATHER THAN RANDOM) MATTERS FOR `craft_sync`'S IDEMPOTENCY
# CHECK: THE SAME FOLDER PATH MUST ALWAYS PRODUCE THE SAME URL.
_ID_LENGTH = 9
_BASE62_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase


def _synthetic_id(absPath):
    """
    *derive a deterministic 9-character base62 id from a folder's absolute path*

    **Key Arguments:**

    - ``absPath`` -- the folder's absolute path

    **Return:**

    - ``id`` -- a 9-character base62 token
    """
    digest = hashlib.blake2b(absPath.encode("utf-8"), digest_size=8).digest()
    num = int.from_bytes(digest, "big")
    chars = []
    while len(chars) < _ID_LENGTH:
        num, remainder = divmod(num, 62)
        chars.append(_BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def _percent_encode_name(name):
    """
    *percent-encode a filename the way Hookmark's own `hook://file/...` links do*

    `urllib.parse.quote` leaves `_.-~` unescaped even with `safe=""`
    (Python hardcodes them as always-safe), but Hookmark's own links
    escape everything except alphanumerics (e.g. `Diarly%2Eapp`,
    `%5Farchive%5F`) - confirmed from the live Hookmark database. Over-
    encoding is always valid, so this only needs to match Hookmark's
    own addresses, not its looser scriptable `percent encode` command.

    **Key Arguments:**

    - ``name`` -- the plain filename

    **Return:**

    - ``encoded`` -- the percent-encoded name
    """
    return "".join(
        char if char.isalnum() and char.isascii()
        else "".join(f"%{byte:02X}" for byte in char.encode("utf-8"))
        for char in name
    )


def hookmark_url(folderPath):
    """
    *build a Hookmark `hook://file/...` URL for a folder, or `None` off Darwin*

    Craft doesn't open `file://` links when clicked, so the folder link
    goes through Hookmark instead - Hookmark's own docs describe this
    exact fallback for a hand-built/shared link: when the id isn't found
    in its local database, it decodes the `p=`/`n=` parameters and
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
    # `p=` IS ONLY A SEARCH HINT, NOT A FULL PATH - HOOKMARK'S OWN LINKS
    # ENCODE JUST THE PARENT'S LAST TWO PATH COMPONENTS (E.G. `/Applications`
    # -> `//Applications`, MATCHING PurePosixPath('/Applications').parts ==
    # ('/', 'Applications')), THEN SPOTLIGHT-SEARCHES FOR `n` NEAR THAT HINT.
    parentParts = PurePosixPath(parentPath).parts
    parentHint = "/".join(parentParts[-2:])
    parentB64 = base64.b64encode(parentHint.encode("utf-8")).decode("ascii")
    nameEncoded = _percent_encode_name(name)
    return f"hook://file/{_synthetic_id(absPath)}?p={parentB64}&n={nameEncoded}"


def links_row(labelledUrls):
    """
    *render a set of labelled links as a single markdown line, dropping any that are `None`*

    The shared renderer behind `link_row_markdown` (Craft's Finder/
    Dropbox/Todoist row) and `todoist_sync`'s own Finder/Dropbox/Craft
    project description - each embeds the other two mirrors' links plus
    the local Finder link, in whichever order matters for that surface.

    **Key Arguments:**

    - ``labelledUrls`` -- an ordered list of `(label, url)` pairs; a pair whose `url` is falsy is omitted

    **Return:**

    - ``markdown`` -- the link row's markdown, or `None` if every url was falsy
    """
    links = [f"[{label}]({url})" for label, url in labelledUrls if url]
    if not links:
        return None
    return "  ·  ".join(links)


def link_row_markdown(hookmarkUrl, dropboxUrl, todoistUrl=None):
    """
    *render the Finder/Dropbox/Todoist link row as a single markdown line*

    **Key Arguments:**

    - ``hookmarkUrl`` -- the folder's Hookmark `hook://file/...` URL, or `None` to omit it
    - ``dropboxUrl`` -- the folder's Dropbox share URL, or `None` to omit it
    - ``todoistUrl`` -- the entity's linked Todoist project URL, or `None` to omit it. Default `None`.

    **Return:**

    - ``markdown`` -- the link row's markdown, or `None` if every URL is `None`
    """
    return links_row([
        (FINDER_LABEL, hookmarkUrl),
        (DROPBOX_LABEL, dropboxUrl),
        (TODOIST_LABEL, todoistUrl),
    ])


def todoist_description_markdown(hookmarkUrl, dropboxUrl, craftUrl):
    """
    *render the Finder/Dropbox/Craft description set on a mirrored Todoist project*

    **Key Arguments:**

    - ``hookmarkUrl`` -- the folder's Hookmark `hook://file/...` URL, or `None` to omit it
    - ``dropboxUrl`` -- the folder's Dropbox share URL, or `None` to omit it
    - ``craftUrl`` -- the entity's linked Craft folder/document URL, or `None` to omit it

    **Return:**

    - ``markdown`` -- the description's markdown, or `None` if every URL is `None`
    """
    return links_row([
        (FINDER_LABEL, hookmarkUrl),
        (DROPBOX_LABEL, dropboxUrl),
        (CRAFT_LABEL, craftUrl),
    ])

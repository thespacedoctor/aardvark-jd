#!/usr/bin/env python
# encoding: utf-8
"""
*Keep the aardvark index directory out of Dropbox sync*

The index database lives at `<root>/00_INDEX🗂️/aardvark.db`, inside the
Dropbox-synced tree. Dropbox syncing a SQLite database between machines
risks corruption - and once WAL or a background writer exists, its
`-wal`/`-shm` sidecars are uploaded even when the database itself is
excluded (verified empirically - see the wayfinder tickets). So the whole
`00_INDEX🗂️` directory is excluded, via Dropbox's per-file ignore
extended attribute `com.dropbox.ignored`, applied to the directory.

`CPython` has no `os.setxattr` on macOS, so this calls libc `setxattr` /
`getxattr` through `ctypes` - no new dependency, and no `/usr/bin/xattr`
subprocess on every command. The mechanism is macOS + Dropbox-desktop
only; on any other platform, or when the system root is not inside a
Dropbox tree, `assert_index_ignored` is a no-op (with a logged warning
for the in-a-Dropbox-tree-but-not-macOS case).

Setting the attribute on an already-synced directory makes the Dropbox
client purge the server-side copy on its own, so there is no API delete
step here.

Author
: David Young
"""

import ctypes
import ctypes.util
import os
import sys

_XATTR_NAME = b"com.dropbox.ignored"
_IGNORED_VALUE = b"1"

# macOS `getxattr`/`setxattr` CARRY TWO EXTRA ARGS THE LINUX ONES DO NOT:
# A `position` (ONLY MEANINGFUL FOR THE RESOURCE FORK, ALWAYS 0 HERE) AND
# AN `options` FLAG. WE PASS 0 FOR `options`: FOLLOW SYMLINKS (THE DEFAULT),
# WHICH IS CORRECT HERE - THE INDEX DIRECTORY IS A REAL DIRECTORY.
_XATTR_NO_OPTIONS = 0
_XATTR_POSITION = 0

_libc = None


def _load_libc():
    """*the process's libc, with `errno` capture enabled and the xattr signatures declared*"""
    global _libc
    if _libc is None:
        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        # macOS: ssize_t getxattr(const char *path, const char *name, void *value,
        #                         size_t size, u_int32_t position, int options);
        libc.getxattr.restype = ctypes.c_ssize_t
        libc.getxattr.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
            ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int,
        ]
        # int setxattr(const char *path, const char *name, const void *value,
        #              size_t size, u_int32_t position, int options);
        libc.setxattr.restype = ctypes.c_int
        libc.setxattr.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int,
        ]
        _libc = libc
    return _libc


def is_supported():
    """*is the `com.dropbox.ignored` mechanism available on this platform?*"""
    return sys.platform == "darwin"


def is_ignored(path):
    """
    *does `path` already carry `com.dropbox.ignored=1`?*

    Returns `False` for a missing attribute, an unreadable path, or an
    unsupported platform - anything other than the attribute being
    present and set to `1`.

    **Key Arguments:**

    - ``path`` -- the directory (or file) to check

    **Return:**

    - ``ignored`` -- `True` only if the attribute is present and equal to `1`
    """
    if not is_supported():
        return False
    libc = _load_libc()
    buffer = ctypes.create_string_buffer(16)
    read = libc.getxattr(
        os.fsencode(path), _XATTR_NAME, buffer, len(buffer), _XATTR_POSITION, _XATTR_NO_OPTIONS,
    )
    if read < 0:
        return False
    return buffer.raw[:read] == _IGNORED_VALUE


def set_ignored(path):
    """
    *set `com.dropbox.ignored=1` on `path`*

    The caller must gate on `is_supported()` first - the libc signature
    used here is the macOS six-argument one. `assert_index_ignored` does
    this.

    **Key Arguments:**

    - ``path`` -- the directory to exclude from Dropbox sync

    **Raises:**

    - ``OSError`` -- if the syscall fails (permissions, unsupported filesystem)
    """
    libc = _load_libc()
    result = libc.setxattr(
        os.fsencode(path), _XATTR_NAME, _IGNORED_VALUE, len(_IGNORED_VALUE),
        _XATTR_POSITION, _XATTR_NO_OPTIONS,
    )
    if result < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), str(path))


def assert_index_ignored(rootPath, log):
    """
    *idempotently exclude the index directory from Dropbox sync, if it is inside a Dropbox tree*

    A no-op unless the system root sits inside a local Dropbox root. On
    macOS it sets `com.dropbox.ignored` on the `00_INDEX🗂️` directory
    (skipped if already set). On any other platform, inside a Dropbox
    tree, it logs one warning and does nothing. It never raises: a failure
    to assert is logged and a single line is printed to stderr, and the
    calling command carries on.

    Called at `init` and, self-healingly, before every non-completion
    command opens the database - so a second machine that clones the
    Dropbox tree excludes the index on its first `aardvark` run.

    **Key Arguments:**

    - ``rootPath`` -- the aardvark system root
    - ``log`` -- the logger
    """
    from aardvark_jd import dropbox_client, paths

    try:
        dropboxRoot = dropbox_client.find_containing_root(
            rootPath, dropbox_client.local_dropbox_roots(),
        )
    except Exception as exc:  # noqa: BLE001 - never-raise contract: a Dropbox-detection failure must not break the command
        log.warning("could not check whether %s is inside a Dropbox tree: %s", rootPath, exc)
        return

    if not dropboxRoot:
        return

    try:
        indexDir = os.path.dirname(paths.find_db_path(rootPath))
    except OSError as exc:
        # `find_db_path` SCANS FOR THE `00_index` FOLDER; A STALE OR
        # UNREADABLE `root_path` RAISES `FileNotFoundError`/`PermissionError`
        # /`NotADirectoryError` - ALL `OSError`, NONE FATAL HERE.
        log.warning("could not locate the aardvark index directory to exclude from Dropbox: %s", exc)
        return

    if not is_supported():
        log.warning(
            "the aardvark index directory (%s) is inside a Dropbox tree, but excluding it "
            "from sync is only supported on macOS - the index database may sync between "
            "machines and risk corruption",
            indexDir,
        )
        return

    if is_ignored(indexDir):
        return

    try:
        set_ignored(indexDir)
        log.info("excluded the aardvark index directory from Dropbox sync (%s)", indexDir)
    except OSError as exc:
        log.warning("could not exclude the aardvark index directory from Dropbox sync (%s): %s", indexDir, exc)
        print(
            f"warning: could not exclude the aardvark index from Dropbox sync ({exc}) - "
            "the index database may be synced and risk corruption",
            file=sys.stderr,
        )

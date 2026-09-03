#!/usr/bin/env python
# encoding: utf-8
"""
*Resolve a Johnny Decimal reference to its on-disk folder, for `av cd` to jump into*

A subprocess cannot change its parent shell's working directory, so `av
cd <target>` does not `cd` at all - it resolves `<target>` and prints the
absolute path to stdout, nothing else. The shell function `av
shell_init <shell>` emits (`completion.shell_init_script`) is what turns
that path into an actual `cd`, by wrapping `aardvark`/`av` and calling
`builtin cd` on the printed line. Run without that wrapper, `av cd` is
still useful as `cd "$(av cd A11.10)"`.

Intercepted in `cl_utils.main` before docopt and before
`fundamentals.tools`, exactly like `completion.emit` - `av cd` runs on
every directory jump, so it has to be fast and strictly read-only: no
settings-file creation, no `db.initialise_schema`, no Dropbox-ignore
re-assert. Unlike `completion.emit`, failures are **not** swallowed - a
silent `cd` failure would strand the user with no explanation.

Author
: David Young
"""

import os
import sys

from aardvark_jd import codes, paths, readonly, refs


def resolve_path(dbConn, target):
    """
    *resolve a domain letter or Johnny Decimal reference to its absolute on-disk folder*

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``target`` -- a domain letter (`"A"`), area (`"A10-19"`), category (`"A11"`) or ID (`"A11.10"`)

    **Return:**

    - ``folderPath`` -- the target's absolute folder path

    **Raises:**

    - ``ValueError`` -- if `target` does not resolve, or resolves to a folder no longer on disk

    **Usage:**

    ```python
    from aardvark_jd import change_dir
    folderPath = change_dir.resolve_path(dbConn, "A11.10")
    ```
    """
    normalised = (target or "").strip().upper()
    if normalised in codes.LETTER_DOMAIN:
        domain = codes.LETTER_DOMAIN[normalised]
        folderPath = paths.resolve(dbConn, f"root.{domain}")
    else:
        _entityType, _domain, row = refs.resolve_ref(dbConn, normalised, "cd")
        folderPath = row["folder_path"]

    if not os.path.isdir(folderPath):
        raise ValueError(f"'{normalised}' resolves to '{folderPath}', which no longer exists on disk")
    return folderPath


def _target_from(words):
    """
    *the target reference from `av cd`'s arguments, skipping flags and their values*

    **Key Arguments:**

    - ``words`` -- the arguments after `cd`, e.g. `["A11.10", "-s", "other.yaml"]`

    **Return:**

    - ``target`` -- the first positional word, or `None` if there isn't one
    """
    index = 0
    while index < len(words):
        word = words[index]
        if word in ("-s", "--settings"):
            index += 2
            continue
        if word.startswith("-"):
            index += 1
            continue
        return word
    return None


def emit(argv):
    """
    *print the absolute folder path `av cd <target>` should move into, or an error*

    **Key Arguments:**

    - ``argv`` -- the `cd` arguments, e.g. `["A11.10"]` or `["A11.10", "-s", "other.yaml"]`

    **Return:**

    - ``exitCode`` -- `0` on success, `1` on any error

    **Usage:**

    ```python
    from aardvark_jd import change_dir
    sys.exit(change_dir.emit(["A11.10"]))
    ```
    """
    target = _target_from(argv)
    if not target:
        print("usage: aardvark cd <target>", file=sys.stderr)
        return 1

    try:
        folderPath = readonly.with_connection(lambda dbConn: resolve_path(dbConn, target), argv)
    except (ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if folderPath is None:
        print(
            "no aardvark system found - run `aardvark init <systemName> <parentPath>` first",
            file=sys.stderr,
        )
        return 1

    print(folderPath)
    return 0

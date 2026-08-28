#!/usr/bin/env python
# encoding: utf-8
"""
*The user's learned vocabulary of words the spell-checker must stop offering to correct*

Measured against a realistic technical vocabulary, the spell-check
configuration flags **18 per cent** of tokens as suspect - `jupyter` to
`jupiter`, `pydantic` to `pedantic`, `postgres` to `postures`. A learned
list of dismissals is therefore part of the feature rather than a
refinement of it: without it the same false positives recur forever and
the prompt becomes noise the user dismisses reflexively.

The store is **`<root>/.aardvark-vocabulary`**: a dotfile at the aardvark
system root, beside `00_INDEX🗂️` but deliberately outside it, so the
wholesale Dropbox ignore on that directory does not catch it and the file
syncs normally. That is the point - the vocabulary records *this user's*
jargon, not any one machine's, so dismissing `pydantic` once on any
machine keeps it dismissed everywhere. It is a conscious departure from
the index database being a per-machine artefact; the index does not need
to follow the user, and the vocabulary does.

It **starts empty and is never seeded** by walking the existing tree.
`aadvark` and `aadvark-jd` are live typos in that tree today, and seeding
would silence exactly the words the feature exists to catch.

Every read and write degrades rather than raising: a spell-check helper
must never be able to break `av add_project`.

Author
: David Young
"""

import os
import tempfile

VOCABULARY_BASENAME = ".aardvark-vocabulary"

_HEADER = (
    "# aardvark: words to skip when spell-checking new folder titles.\n"
    "# one lowercase word per line. safe to edit.\n"
)


def vocabulary_path(rootPath):
    """
    *where this system's learned vocabulary lives*

    **Key Arguments:**

    - ``rootPath`` -- the aardvark system root

    **Return:**

    - ``pathToVocabulary`` -- the dotfile's path
    """
    return os.path.join(rootPath, VOCABULARY_BASENAME)


def load(rootPath, log=None):
    """
    *the set of words the user has told the spell-checker to leave alone*

    A missing file is the normal case on a system where nothing has been
    dismissed yet. An unreadable or malformed one is treated the same way
    - as empty, with a warning - because refusing to create a folder over
    a damaged sidecar file would be absurd.

    **Key Arguments:**

    - ``rootPath`` -- the aardvark system root
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``words`` -- a `frozenset` of lowercase tokens, empty if there are none
    """
    try:
        with open(vocabulary_path(rootPath), encoding="utf-8") as stream:
            lines = stream.readlines()
    except FileNotFoundError:
        return frozenset()
    except (OSError, UnicodeDecodeError) as error:
        if log:
            log.warning("could not read the learned vocabulary: %s", error)
        return frozenset()

    words = set()
    for line in lines:
        token = line.strip().lower()
        # `#` COMMENTS AND BLANK LINES ARE FOR WHOEVER EDITS THIS BY HAND.
        if token and not token.startswith("#"):
            words.add(token)
    return frozenset(words)


def remember(rootPath, word, log=None):
    """
    *record a word the user has declined to correct, so it is never offered again*

    Written immediately rather than batched to the end of the command, and
    written **atomically** - the whole sorted list to a temporary file in
    the same directory, then `os.replace` over the real one - so a crash
    mid-command can neither lose a dismissal nor leave a torn file.

    Keyed on the token alone, never on the token-and-suggestion pair: if
    `pydantic` is a word this user uses, it stays a word whatever a later
    wordlist revision would suggest for it.

    **Key Arguments:**

    - ``rootPath`` -- the aardvark system root
    - ``word`` -- the token to remember, in any case
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``remembered`` -- `True` if the word is now stored, `False` if the write failed
    """
    token = (word or "").strip().lower()
    if not token:
        return False

    words = set(load(rootPath, log=log))
    if token in words:
        return True
    words.add(token)

    body = _HEADER + "".join(f"{entry}\n" for entry in sorted(words))
    pathToVocabulary = vocabulary_path(rootPath)
    try:
        # THE TEMPORARY FILE MUST SHARE A FILESYSTEM WITH THE TARGET FOR
        # `os.replace` TO BE ATOMIC, SO IT GOES IN THE SAME DIRECTORY.
        handle, temporaryPath = tempfile.mkstemp(
            dir=os.path.dirname(pathToVocabulary) or ".",
            prefix=f"{VOCABULARY_BASENAME}.", suffix=".tmp",
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(body)
            os.replace(temporaryPath, pathToVocabulary)
        except BaseException:
            # NEVER LEAVE THE TEMPORARY FILE BEHIND ON A FAILED WRITE.
            try:
                os.unlink(temporaryPath)
            except OSError:
                pass
            raise
    except OSError as error:
        # THE DISMISSAL IS SIMPLY NOT PERSISTED, SO IT IS OFFERED AGAIN NEXT
        # RUN. THAT IS A FAR BETTER OUTCOME THAN FAILING THE COMMAND.
        if log:
            log.warning("could not record '%s' in the learned vocabulary: %s", token, error)
        return False

    return True

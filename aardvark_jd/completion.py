#!/usr/bin/env python
# encoding: utf-8
"""
*Tab-completion candidates for the shell, and the bash/zsh scripts that ask for them*

The shells invoke a hidden `__complete` subcommand, intercepted at the top
of `cl_utils.main` before docopt (which would reject an undeclared command)
and before `fundamentals.tools` (which would create settings files, set up
logging and run a schema migration - none of which may happen on a
keystroke). The wire protocol is:

    av __complete <cword> <word0> <word1> ... <wordN>

where `<cword>` is the zero-based index into the word list of the word
being completed - it may equal `len(words)` when the user has typed a
trailing space and is completing a fresh, empty word. One candidate is
printed per line as `value<TAB>description`; zsh renders the description
alongside the value, bash discards it.

**Every failure is swallowed.** A traceback printed into a shell's
completion buffer is far worse than no completions at all, so `emit`
catches everything and prints nothing. For the same reason the database is
opened read-only and `db.initialise_schema` is never called - it drops and
recreates nine triggers on every invocation, which must not happen each
time the user presses TAB.

Author
: David Young
"""

import os
import sys

from aardvark_jd import codes, commands, readonly

COMPLETION_COMMAND = "__complete"

_SHELLS = ("bash", "zsh")


def emit(argv):
    """
    *print the completion candidates for a partially-typed command line, never raising*

    **Key Arguments:**

    - ``argv`` -- the `__complete` arguments: `[cword, word0, word1, ...]`

    **Usage:**

    ```python
    from aardvark_jd import completion
    completion.emit(["2", "aardvark", "add_category", "A1"])
    ```
    """
    try:
        cword = int(argv[0])
        words = argv[1:]
        for value, description in candidates(words, cword):
            if description:
                sys.stdout.write(f"{value}\t{description}\n")
            else:
                sys.stdout.write(f"{value}\n")
    except Exception:
        # A BROKEN COMPLETION MUST NEVER WEDGE THE USER'S SHELL - STAY SILENT.
        return


def candidates(words, cword):
    """
    *the completion candidates for the word at `cword` in `words`*

    **Key Arguments:**

    - ``words`` -- the full command line as a word list, starting with the program name
    - ``cword`` -- the zero-based index of the word being completed

    **Return:**

    - ``candidates`` -- a list of `(value, description)` pairs, already filtered by the typed prefix

    **Usage:**

    ```python
    from aardvark_jd import completion
    pairs = completion.candidates(["av", "add_category", "A1"], 2)
    ```
    """
    prefix = words[cword] if cword < len(words) else ""

    # POSITION 0 IS THE PROGRAM NAME ITSELF, POSITION 1 THE SUBCOMMAND.
    if cword <= 1:
        return _filter(
            [(name, commands.summary(name)) for name in commands.names()], prefix,
        )

    commandName = words[1]
    spec = commands.spec(commandName)
    if not spec:
        return []
    _name, _group, _summary, completers = spec

    # A FLAG THAT SWALLOWS THE NEXT WORD MEANS WE ARE COMPLETING ITS VALUE,
    # NOT A POSITIONAL.
    previousWord = words[cword - 1] if 0 < cword <= len(words) else ""
    if previousWord in commands.FLAGS_TAKING_A_VALUE:
        if previousWord in ("-t", "--template"):
            return readonly.with_connection(lambda dbConn: _templates(dbConn, words, prefix), words) or []
        # `--settings` AND `--emoji` HAVE NOTHING USEFUL TO SUGGEST; RETURNING
        # NOTHING LETS THE SHELL FALL BACK TO ITS OWN FILENAME COMPLETION.
        return []

    if prefix.startswith("-"):
        return _filter(_flags(commandName), prefix)

    slot = _positional_slot(words, cword)
    if slot is None or slot >= len(completers):
        return []

    completer = completers[slot]
    if completer == commands.COMPLETER_FREE or completer == commands.COMPLETER_PATH:
        return []
    if completer == "domainLetter":
        return _filter(_domain_letters(), prefix)
    if completer == "shell":
        return _filter([(shell, f"the {shell} completion script") for shell in _SHELLS], prefix)

    return readonly.with_connection(lambda dbConn: _from_index(dbConn, completer, prefix), words) or []


def _positional_slot(words, cword):
    """
    *which positional argument the word at `cword` is, ignoring flags and their values*

    **Key Arguments:**

    - ``words`` -- the full command line as a word list
    - ``cword`` -- the zero-based index of the word being completed

    **Return:**

    - ``slot`` -- the zero-based positional index, or `None` if the word is itself a flag
    """
    slot = 0
    index = 2
    while index < cword:
        word = words[index]
        if word in commands.FLAGS_TAKING_A_VALUE:
            index += 2
            continue
        if word.startswith("-"):
            index += 1
            continue
        slot += 1
        index += 1
    return slot


def _flags(commandName):
    """
    *the option flags accepted by a command*

    **Key Arguments:**

    - ``commandName`` -- the subcommand name

    **Return:**

    - ``flags`` -- a list of `(flag, description)` pairs
    """
    flags = [("-s", "the settings file"), ("--settings", "the settings file")]
    if commandName in ("add_area", "add_category"):
        flags += [("-e", "the emoji to use"), ("--emoji", "the emoji to use")]
    if commandName == "add_project":
        flags += [("-t", "the template to use"), ("--template", "the template to use")]
    if commandName == "archive":
        flags += [("-y", "skip the confirmation prompt"), ("--yes", "skip the confirmation prompt")]
    return flags


def _domain_letters():
    """
    *the three Johnny Decimal domain letters, with their domain names*

    **Return:**

    - ``letters`` -- a list of `(letter, description)` pairs
    """
    return [(codes.DOMAIN_LETTER[domain], domain) for domain in codes.DOMAINS]


def _from_index(dbConn, completer, prefix):
    """
    *the live Johnny Decimal references of the requested kind, read from the index*

    **Key Arguments:**

    - ``dbConn`` -- a read-only SQLite connection to the active system's index
    - ``completer`` -- `"area"`, `"category"`, `"projectCategory"`, `"ref"` or `"refOrTerm"`
    - ``prefix`` -- the partially-typed word

    **Return:**

    - ``candidates`` -- a list of `(ref, title)` pairs
    """
    pairs = []
    if completer == "area":
        pairs = _areas(dbConn)
    elif completer == "category":
        pairs = _categories(dbConn)
    elif completer == "projectCategory":
        # `add_project` ALWAYS CREATES IN THE `projects` DOMAIN, SO OFFERING A
        # CATEGORY FROM ANOTHER ONE PROPOSES A COMMAND THAT CANNOT SUCCEED.
        # `add_id` AND `add_category` ARE NOT NARROWED: BOTH TAKE THEIR DOMAIN
        # FROM THE REF THEY ARE GIVEN, SO EVERY DOMAIN IS VALID THERE.
        pairs = _categories(dbConn, domain="projects")
    elif completer == "ref":
        pairs = _areas(dbConn) + _categories(dbConn) + _ids(dbConn)
    elif completer == "refOrTerm":
        # SHARED BY `fd` (WHERE A BARE DOMAIN LETTER BROWSES THE WHOLE
        # DOMAIN) AND `cd` (WHERE IT JUMPS TO THE DOMAIN'S ROOT FOLDER) -
        # BOTH WANT THE SAME CANDIDATE LIST.
        pairs = _domain_letters() + _areas(dbConn) + _categories(dbConn) + _ids(dbConn)
    return _filter(pairs, prefix)


def _labelled(emoji, title):
    """
    *a completion description carrying the entity's emoji, when it has one*

    Only the **description** half of the pair - the value stays the bare
    Johnny Decimal code, because that is what the shell inserts on the
    command line. `ids` has no `emoji` column (an ID's folder name never
    carries one), so IDs are labelled by title alone.

    **Key Arguments:**

    - ``emoji`` -- the entity's emoji, possibly empty
    - ``title`` -- the entity's title

    **Return:**

    - ``label`` -- the description to show beside the code
    """
    return f"{emoji} {title}" if emoji else title


def _areas(dbConn):
    """
    *every live area, as `(code, label)` pairs*

    **Key Arguments:**

    - ``dbConn`` -- a read-only SQLite connection

    **Return:**

    - ``areas`` -- a list of `(code, title)` pairs
    """
    rows = dbConn.execute(
        "SELECT domain, decade_start, decade_end, title, emoji FROM areas ORDER BY domain, decade_start"
    ).fetchall()
    return [
        (
            codes.format_area_code(row["domain"], row["decade_start"], row["decade_end"]),
            _labelled(row["emoji"], row["title"]),
        )
        for row in rows
    ]


def _categories(dbConn, domain=None):
    """
    *every live category, as `(code, title)` pairs, optionally in one domain only*

    **Key Arguments:**

    - ``dbConn`` -- a read-only SQLite connection
    - ``domain`` -- restrict to `areas`, `resources` or `projects`. Default `None`, meaning all three.

    **Return:**

    - ``categories`` -- a list of `(code, title)` pairs
    """
    if domain:
        rows = dbConn.execute(
            "SELECT domain, ac_number, title, emoji FROM categories WHERE domain = ? ORDER BY ac_number",
            (domain,),
        ).fetchall()
    else:
        rows = dbConn.execute(
            "SELECT domain, ac_number, title, emoji FROM categories ORDER BY domain, ac_number"
        ).fetchall()
    return [
        (
            codes.format_category_code(row["domain"], row["ac_number"]),
            _labelled(row["emoji"], row["title"]),
        )
        for row in rows
    ]


def _ids(dbConn):
    """
    *every live ID, as `(code, title)` pairs*

    **Key Arguments:**

    - ``dbConn`` -- a read-only SQLite connection

    **Return:**

    - ``ids`` -- a list of `(code, title)` pairs
    """
    rows = dbConn.execute(
        "SELECT domain, ac_number, item_number, title FROM ids ORDER BY domain, ac_number, item_number"
    ).fetchall()
    return [
        (codes.format_id_code(row["domain"], row["ac_number"], row["item_number"]), row["title"])
        for row in rows
    ]


def _templates(dbConn, words, prefix):
    """
    *the zip templates available to the project category named earlier on the command line*

    **Key Arguments:**

    - ``dbConn`` -- a read-only SQLite connection
    - ``words`` -- the full command line as a word list
    - ``prefix`` -- the partially-typed word

    **Return:**

    - ``templates`` -- a list of `(templateName, description)` pairs, always including "blank"
    """
    import glob

    pairs = [("blank", "a blank project scaffold")]
    categoryRef = next((word for word in words[2:] if codes.is_jd_ref(word)), None)
    if categoryRef:
        try:
            _domain, acNumber = codes.split_category_ref(categoryRef, domain="projects")
            row = dbConn.execute(
                "SELECT folder_path FROM system_folders WHERE folder_key = ?",
                (f"projects.{acNumber}.04_templates",),
            ).fetchone()
            if row:
                pairs += [
                    (os.path.basename(zipPath)[:-4], "a project template")
                    for zipPath in sorted(glob.glob(f"{row['folder_path']}/*.zip"))
                ]
        except Exception:
            pass
    return _filter(pairs, prefix)


def _filter(pairs, prefix):
    """
    *keep only the candidates starting with the typed prefix*

    Filtering here rather than in the shell scripts keeps those scripts
    trivial, and means both shells behave identically.

    **Key Arguments:**

    - ``pairs`` -- a list of `(value, description)` pairs
    - ``prefix`` -- the partially-typed word

    **Return:**

    - ``pairs`` -- the matching pairs
    """
    if not prefix:
        return list(pairs)
    lowered = prefix.lower()
    return [(value, description) for value, description in pairs if value.lower().startswith(lowered)]


def script(shell):
    """
    *the completion script for the named shell, ready to `eval` or write to an fpath file*

    **Key Arguments:**

    - ``shell`` -- `"bash"` or `"zsh"`

    **Return:**

    - ``script`` -- the shell script text

    **Usage:**

    ```python
    from aardvark_jd import completion
    print(completion.script("zsh"))
    ```
    """
    if shell not in _SHELLS:
        raise ValueError(f"unknown shell '{shell}' - choose one of: {', '.join(_SHELLS)}")
    scriptPath = os.path.dirname(__file__) + f"/resources/completions/aardvark.{shell}"
    with open(scriptPath, encoding="utf-8") as scriptFile:
        return scriptFile.read().rstrip("\n")


def shell_init_script(shell):
    """
    *the shell integration script for the named shell, ready to `eval`*

    A subprocess cannot change its parent shell's working directory, so
    `av cd <target>` on its own only prints the resolved path.
    `shell_init_script` is what turns that into an actual `cd`: it wraps
    `aardvark`/`av` in a shell function that intercepts the `cd`
    subcommand and calls `builtin cd` on the printed path, then appends
    `script(shell)` so one `eval` installs both the wrapper and
    completion.

    **Key Arguments:**

    - ``shell`` -- `"bash"` or `"zsh"`

    **Return:**

    - ``script`` -- the wrapper function followed by the completion script

    **Usage:**

    ```python
    from aardvark_jd import completion
    print(completion.shell_init_script("zsh"))
    ```
    """
    if shell not in _SHELLS:
        raise ValueError(f"unknown shell '{shell}' - choose one of: {', '.join(_SHELLS)}")
    scriptPath = os.path.dirname(__file__) + f"/resources/completions/shell_init.{shell}"
    with open(scriptPath, encoding="utf-8") as scriptFile:
        wrapper = scriptFile.read().rstrip("\n")
    return f"{wrapper}\n{script(shell)}"

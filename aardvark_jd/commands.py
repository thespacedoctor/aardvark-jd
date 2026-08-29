#!/usr/bin/env python
# encoding: utf-8
"""
*The canonical table of aardvark subcommands, their help grouping and their completion behaviour*

`cl_utils.__doc__` remains the docopt grammar - docopt derives its parse
from the `Usage:` block and nothing else, so this module deliberately does
**not** try to generate that string. It is instead the single place that
knows two things docopt has no opinion about: which commands are everyday
verbs and which are one-off setup verbs (used by `help_text` to abridge
`--help`), and what each positional argument should tab-complete to (used
by `completion`).

The two representations are kept honest by
`tests/test_commands.py::test_command_table_matches_docopt_usage`, which
extracts every command named in the `Usage:` block and asserts it matches
`names()` exactly - so adding a usage line without adding it here (or vice
versa) fails the suite rather than silently degrading help or completion.

Author
: David Young
"""

COMMON = "common"
ADVANCED = "advanced"

# COMPLETER TOKENS - RESOLVED BY `completion._COMPLETERS`. `free` MEANS
# "NOTHING TO SUGGEST" (A TITLE, A DESCRIPTION, AN API TOKEN), AND `path`
# MEANS "LET THE SHELL FALL BACK TO ITS OWN FILENAME COMPLETION".
COMPLETER_FREE = "free"
COMPLETER_PATH = "path"

# (name, group, summary, positionalCompleters)
COMMANDS = (
    ("init", COMMON, "create a new PARA + Johnny Decimal root and index",
     (COMPLETER_FREE, COMPLETER_PATH)),
    ("add_area", COMMON, "add a new Johnny Decimal area to `areas`, `resources` or `projects`",
     ("domainLetter", COMPLETER_FREE, COMPLETER_FREE)),
    ("add_category", COMMON, "add a new Johnny Decimal category to an existing area",
     ("area", COMPLETER_FREE, COMPLETER_FREE)),
    ("add_id", COMMON, "add a new Johnny Decimal ID to an existing category",
     ("category", COMPLETER_FREE, COMPLETER_FREE)),
    ("add_project", COMMON, "create a new project (a Johnny Decimal ID) in an existing project category, from a template or blank",
     ("projectCategory", COMPLETER_FREE)),
    ("archive", COMMON, "retire an area, category or ID to the nearest archive folder, freeing its number",
     ("ref",)),
    ("fd", COMMON, "browse the index as a tree, or find in it by Johnny Decimal ref, keyword or phrase",
     ("refOrTerm",)),
    ("open", COMMON, "open the mirrored entities for a path, or pick one interactively",
     (COMPLETER_PATH,)),
    ("set_emoji", ADVANCED, "change the emoji on an existing folder, moving it and repointing the index",
     ("ref", COMPLETER_FREE)),
    ("repair_emoji", ADVANCED, "fix drifted folder names/emoji and backfill missing reserved scaffolding",
     ()),
    ("completion", ADVANCED, "print the shell completion script for `bash` or `zsh`",
     ("shell",)),
    ("connect_craft", ADVANCED, "connect a craft.do space and run the initial full mirror",
     (COMPLETER_FREE, COMPLETER_FREE)),
    ("craft_sync", ADVANCED, "re-run the craft.do mirror on demand, to backfill or repair drift",
     ()),
    ("connect_todoist", ADVANCED, "connect a Todoist account and run the initial full mirror",
     (COMPLETER_FREE,)),
    ("todoist_sync", ADVANCED, "re-run the Todoist mirror on demand, to backfill or repair drift",
     ()),
    ("connect_dropbox", ADVANCED, "connect a Dropbox app and start adding Dropbox share links to synced documents",
     (COMPLETER_FREE, COMPLETER_FREE)),
    ("connect_gdrive", ADVANCED, "connect a Google Drive account and run the initial folder mirror",
     (COMPLETER_FREE, COMPLETER_FREE)),
    ("gdrive_sync", ADVANCED, "re-run the Google Drive folder mirror on demand, to backfill or repair drift",
     ()),
)

# FLAGS THAT SWALLOW THE FOLLOWING WORD - COMPLETION HAS TO SKIP BOTH WHEN
# COUNTING POSITIONAL SLOTS, OR `add_id -s foo.yaml <TAB>` WOULD THINK IT
# WAS COMPLETING THE THIRD POSITIONAL RATHER THAN THE FIRST.
FLAGS_TAKING_A_VALUE = frozenset(("-s", "--settings", "-e", "--emoji", "-t", "--template"))

_BY_NAME = {name: (name, group, summary, completers) for name, group, summary, completers in COMMANDS}


def names(group=None):
    """
    *the subcommand names, optionally restricted to one help group*

    **Key Arguments:**

    - ``group`` -- `COMMON`, `ADVANCED`, or `None` for every command. Default *None*.

    **Return:**

    - ``names`` -- a list of subcommand names, in declaration order

    **Usage:**

    ```python
    from aardvark_jd import commands
    everydayVerbs = commands.names(commands.COMMON)
    ```
    """
    return [name for name, commandGroup, _summary, _completers in COMMANDS
            if group is None or commandGroup == group]


def spec(commandName):
    """
    *look up one command's full table entry*

    **Key Arguments:**

    - ``commandName`` -- the subcommand name, e.g. `"add_id"`

    **Return:**

    - ``spec`` -- the `(name, group, summary, positionalCompleters)` tuple, or `None` if unknown
    """
    return _BY_NAME.get(commandName)


def summary(commandName):
    """
    *look up one command's one-line summary*

    **Key Arguments:**

    - ``commandName`` -- the subcommand name, e.g. `"add_id"`

    **Return:**

    - ``summary`` -- the summary string, or `None` if unknown
    """
    entry = _BY_NAME.get(commandName)
    return entry[2] if entry else None

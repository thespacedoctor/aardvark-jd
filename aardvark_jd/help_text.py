#!/usr/bin/env python
# encoding: utf-8
"""
*Abridge the docopt help screen down to the everyday commands, keeping the full grammar intact*

docopt derives its entire grammar from the `Usage:` block, so every
command has to stay in `cl_utils.__doc__` no matter how rarely it is
used - hiding one by deleting its usage line would stop it parsing. What
we can control is what gets *printed*: `cl_utils.main` intercepts `-h`
before handing anything to docopt, and prints `short_help(__doc__)`,
which strips the `ADVANCED` commands from the display copy only.

`Arguments:` entries are pruned to match, so the abridged screen never
explains a placeholder the user can no longer see - but only when no
surviving usage line still mentions them.

Author
: David Young
"""

import re

from aardvark_jd import commands

_SECTION_RE = re.compile(r"^(Usage|Commands|Arguments|Options):\s*$")
_PLACEHOLDER_RE = re.compile(r"<([A-Za-z][A-Za-z0-9]*)>")
_MORE_COMMANDS_HINT = "Run 'aardvark --help-all' for the full command list, including setup and maintenance commands."


def full_help(docString):
    """
    *the complete help screen, every command included*

    **Key Arguments:**

    - ``docString`` -- the raw docopt docstring, i.e. `cl_utils.__doc__`

    **Return:**

    - ``helpText`` -- the docstring unchanged

    **Usage:**

    ```python
    from aardvark_jd import help_text
    print(help_text.full_help(cl_utils.__doc__))
    ```
    """
    return docString


def short_help(docString):
    """
    *the help screen with every `ADVANCED` command's usage, command and orphaned argument lines removed*

    **Key Arguments:**

    - ``docString`` -- the raw docopt docstring, i.e. `cl_utils.__doc__`

    **Return:**

    - ``helpText`` -- the abridged help screen, with a pointer to `--help-all`

    **Usage:**

    ```python
    from aardvark_jd import help_text
    print(help_text.short_help(cl_utils.__doc__))
    ```
    """
    advanced = set(commands.names(commands.ADVANCED))

    # PASS ONE - DROP THE ADVANCED `Usage:`/`Commands:` LINES, REMEMBERING
    # EVERY PLACEHOLDER THE SURVIVING USAGE LINES STILL REFER TO.
    keptLines = []
    survivingPlaceholders = set()
    section = None
    for line in docString.split("\n"):
        stripped = line.strip()
        headerMatch = _SECTION_RE.match(stripped)
        if headerMatch:
            section = headerMatch.group(1)
            keptLines.append(line)
            continue

        if section == "Usage" and stripped:
            tokens = stripped.split()
            # `aardvark <command> ...` - THE COMMAND IS THE SECOND TOKEN
            if len(tokens) > 1 and tokens[1] in advanced:
                continue
            survivingPlaceholders.update(_PLACEHOLDER_RE.findall(stripped))

        if section == "Commands" and stripped and stripped.split()[0] in advanced:
            continue

        keptLines.append(line)

    # PASS TWO - DROP ANY `Arguments:` ENTRY NO SURVIVING USAGE LINE MENTIONS.
    finalLines = []
    section = None
    for line in keptLines:
        stripped = line.strip()
        headerMatch = _SECTION_RE.match(stripped)
        if headerMatch:
            section = headerMatch.group(1)
            finalLines.append(line)
            continue

        if section == "Arguments" and stripped and stripped.split()[0] not in survivingPlaceholders:
            continue

        finalLines.append(line)

    return _collapse_blank_runs("\n".join(finalLines)) + f"\n\n{_MORE_COMMANDS_HINT}\n"


def _collapse_blank_runs(text):
    """
    *squash runs of two or more blank lines left behind by the removals down to one*

    **Key Arguments:**

    - ``text`` -- the abridged help text

    **Return:**

    - ``text`` -- the same text with no run of more than one blank line
    """
    return re.sub(r"\n{3,}", "\n\n", text).rstrip("\n")

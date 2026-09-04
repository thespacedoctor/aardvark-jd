#!/usr/bin/env python
# encoding: utf-8
"""
*Locate the `aardvark` console script the Alfred workflow shells out to*

Alfred runs scripts under `/bin/zsh --no-rcs` with a `PATH` of six
documented system entries, none of which carries a conda, venv, pipx or uv
binary. The workflow therefore cannot find `aardvark` on `PATH` and has to
be told where it is: `aardvark install_alfred` writes a per-machine plain
text pointer file, and this module is the definitive statement of how that
pointer and the workflow's own configuration variable are read.

The workflow's `scripts/_resolve.sh` reimplements the same three steps in
shell. It has to be a replica rather than a call, because resolving the
binary is what lets the workflow run Python at all - it cannot import this
module to find the interpreter it is looking for. Keep the two in step: if
the order changes here, change it there.

`POINTER_PATH` holds the unexpanded literal path and every defaulted call
expands it, so the result follows `HOME` at call time rather than at
import time.

Author
: David Young
"""

import os
from dataclasses import dataclass
from pathlib import Path

# FIXED AND LITERAL. `~/.config/aardvark/` IS CREATED UNCONDITIONALLY ON
# FIRST RUN BY `cl_utils.main` AND SITS OUTSIDE DROPBOX, SO IT INTRODUCES
# NO SECOND DISCOVERY PROBLEM.
POINTER_PATH = Path("~/.config/aardvark/alfred-binary-path")

# THE THREE STATES THE WORKFLOW'S ROWS ARE WRITTEN AGAINST.
OK = "ok"
MISSING = "missing"
DEAD = "dead"


@dataclass(frozen=True)
class binary_resolution:
    """
    *the outcome of resolving the `aardvark` console script*

    **Key Arguments:**

    - ``state`` -- `OK`, `MISSING` or `DEAD`
    - ``path`` -- the candidate considered, or `None` when nothing was recorded
    - ``source`` -- `"config"` or `"pointer"`, or `None` when nothing was recorded
    """

    state: str
    path: str | None
    source: str | None = None


def _pointer_path(pointerPath=None):
    """
    *the pointer file to read or write, defaulting to the per-machine one*

    **Key Arguments:**

    - ``pointerPath`` -- an explicit pointer file. Default `None`, meaning the per-machine path.

    **Return:**

    - ``pointerPath`` -- the pointer file as a `Path`
    """
    return POINTER_PATH.expanduser() if pointerPath is None else Path(pointerPath)


def _resolution_for(candidatePath, source):
    """
    *classify one candidate path as executable or dead*

    **Key Arguments:**

    - ``candidatePath`` -- the path recorded by the configuration variable or the pointer
    - ``source`` -- `"config"` or `"pointer"`

    **Return:**

    - ``resolution`` -- the `binary_resolution` for that candidate
    """
    state = OK if os.access(candidatePath, os.X_OK) else DEAD
    return binary_resolution(state=state, path=candidatePath, source=source)


def console_script_path(executable):
    """
    *derive the `aardvark` console script's path from an interpreter path*

    The pointer holds the console script, never `sys.executable`: there is
    no `__main__.py`, so the interpreter alone cannot launch anything,
    whereas the console script's shebang resolves its own interpreter with
    no environment activation.

    **Key Arguments:**

    - ``executable`` -- an interpreter path, normally `sys.executable`

    **Return:**

    - ``consoleScriptPath`` -- the `aardvark` console script beside that interpreter

    **Usage:**

    ```python
    from aardvark_jd.alfred import binary
    consoleScriptPath = binary.console_script_path(sys.executable)
    ```
    """
    return Path(executable).parent / "aardvark"


def write_pointer(binaryPath, pointerPath=None):
    """
    *record the `aardvark` console script's path for this machine*

    One line of plain text, not a YAML key - reading YAML needs the
    interpreter the file exists to find.

    **Key Arguments:**

    - ``binaryPath`` -- the `aardvark` console script's absolute path
    - ``pointerPath`` -- an explicit pointer file. Default `None`, meaning the per-machine path.

    **Return:**

    - ``pointerPath`` -- the pointer file written
    """
    targetPath = _pointer_path(pointerPath)
    targetPath.parent.mkdir(parents=True, exist_ok=True)
    targetPath.write_text(f"{binaryPath}\n", encoding="utf-8")
    return targetPath


def read_pointer(pointerPath=None):
    """
    *read this machine's recorded `aardvark` console script path*

    **Key Arguments:**

    - ``pointerPath`` -- an explicit pointer file. Default `None`, meaning the per-machine path.

    **Return:**

    - ``binaryPath`` -- the recorded path, or `None` when the file is absent or blank
    """
    try:
        contents = _pointer_path(pointerPath).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return contents.strip() or None


def remove_pointer(pointerPath=None):
    """
    *delete this machine's binary pointer, if it has one*

    Idempotent, because `install_alfred --uninstall` is.

    **Key Arguments:**

    - ``pointerPath`` -- an explicit pointer file. Default `None`, meaning the per-machine path.

    **Return:**

    - ``removed`` -- `True` if a file was removed, `False` if there was none
    """
    try:
        _pointer_path(pointerPath).unlink()
    except FileNotFoundError:
        return False
    return True


def resolve(configVariable=None, pointerPath=None):
    """
    *resolve the `aardvark` console script: configuration variable, then pointer, then failure*

    **Key Arguments:**

    - ``configVariable`` -- the workflow's `AARDVARK_BINARY` value, normally an empty string
    - ``pointerPath`` -- an explicit pointer file. Default `None`, meaning the per-machine path.

    **Return:**

    - ``resolution`` -- the `binary_resolution`, carrying the dead path when there is one

    **Usage:**

    ```python
    from aardvark_jd.alfred import binary
    resolution = binary.resolve(configVariable=os.environ.get("AARDVARK_BINARY"))
    ```
    """
    # A BLANK CONFIGURATION VARIABLE IS THE NORMAL CASE, NOT AN EDGE CASE:
    # ALFRED'S CONFIGURATION VARIABLES DEFAULT TO EMPTY STRINGS. A VARIABLE
    # THAT IS SET BUT DEAD IS REPORTED AS DEAD RATHER THAN FALLING THROUGH,
    # SINCE AN EXPLICIT OVERRIDE THAT IS WRONG MUST NEVER BE SILENTLY
    # BYPASSED.
    if configVariable is not None and configVariable.strip():
        return _resolution_for(configVariable, "config")

    pointerCandidate = read_pointer(pointerPath)
    if pointerCandidate is not None:
        return _resolution_for(pointerCandidate, "pointer")

    # NO `PATH` PROBE AND NO PLAUSIBLE-DEFAULT FALLBACK, DELIBERATELY.
    # ALFRED'S `PATH` CARRIES NO CONDA, VENV, PIPX OR UV BINARY, AND THE
    # RARE SUCCESS IS THE DANGEROUS ONE - SILENTLY RUNNING A DIFFERENT
    # AARDVARK.
    return binary_resolution(state=MISSING, path=None)

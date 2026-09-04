#!/usr/bin/env python
# encoding: utf-8
"""
*Install the aardvark workflow into Alfred, and record where aardvark lives*

Two separable jobs, and separating them is the decision the rest falls out
of:

1. **Write the binary pointer.** Unconditional, every run, every machine -
   including a machine that installed the workflow by double-clicking an
   exported bundle. This is why the command is not author-only.
2. **Deploy the workflow.** Symlink `workflows/aardvark-jd` at the
   packaged `aardvark_jd/resources/alfred`, unless a workflow is already
   installed there by another route.

**Symlink only. There is no `--copy`.** `importlib.resources` points at the
repo working tree for an editable install and at site-packages for a
package user, through one code path with no branch, so the author gets live
editing and a package user gets a workflow that `pip install --upgrade`
refreshes for free. A copy mode would exist only to go stale.

Author
: David Young
"""

import json
import sys
from importlib.resources import files
from pathlib import Path

from aardvark_jd.alfred import binary

# ALFRED'S OWN RECORD OF WHERE ITS PREFERENCES FOLDER IS, WHICH THE USER
# CAN PUT ANYWHERE - DROPBOX, ICLOUD, WHEREVER.
PREFS_JSON = "prefs.json"
WORKFLOW_DIRECTORY_NAME = "aardvark-jd"
ALFRED_SUPPORT_PATH = "~/Library/Application Support/Alfred"


class install_alfred(object):
    """
    *deploy the aardvark workflow into Alfred and record this machine's `aardvark` path*

    **Key Arguments:**

    - ``log`` -- logger
    - ``executable`` -- the interpreter to derive the console script from. Default `None`, meaning `sys.executable`.
    - ``alfredSupportPath`` -- Alfred's application support folder. Default `None`, meaning the real one.
    - ``pointerPath`` -- the binary pointer file. Default `None`, meaning the per-machine one.
    - ``uninstall`` -- remove the symlink and the pointer instead of writing them. Default `False`.

    **Usage:**

    ```python
    from aardvark_jd.install_alfred import install_alfred
    for message in install_alfred(log=log).get():
        print(message)
    ```
    """

    def __init__(self, log, executable=None, alfredSupportPath=None, pointerPath=None, uninstall=False):
        self.log = log
        self.executable = executable or sys.executable
        self.alfredSupportPath = Path(alfredSupportPath or ALFRED_SUPPORT_PATH).expanduser()
        self.pointerPath = pointerPath
        self.uninstall = uninstall

    def get(self):
        """
        *do both jobs, or undo both of them, and say what happened*

        **Return:**

        - ``messages`` -- one line per thing done, for the caller to print

        **Raises:**

        - ``ValueError`` -- if Alfred is absent, or present with an unusable `prefs.json`
        """
        self.log.debug("starting the ``get`` method")

        workflowsPath = self._workflows_path()
        targetPath = workflowsPath / WORKFLOW_DIRECTORY_NAME

        messages = (
            self._uninstall(targetPath) if self.uninstall else self._install(targetPath)
        )

        self.log.debug("completed the ``get`` method")
        return messages

    def _workflows_path(self):
        """
        *find Alfred's `workflows` folder, or fail cleanly*

        **Never falls back to a default path.**
        `~/Library/Application Support/Alfred/Alfred.alfredpreferences`
        exists on some machines but is vestigial, so a fallback would write
        where Alfred never looks and appear to have succeeded.

        **Return:**

        - ``workflowsPath`` -- Alfred's `workflows` folder

        **Raises:**

        - ``ValueError`` -- if Alfred is absent, or its `prefs.json` is missing, unreadable or lacks `current`
        """
        prefsPath = self.alfredSupportPath / PREFS_JSON

        if not self.alfredSupportPath.is_dir():
            raise ValueError(
                "Alfred is not installed - install Alfred 5 first, then re-run "
                "`aardvark install_alfred`"
            )

        try:
            preferences = json.loads(prefsPath.read_text(encoding="utf-8"))
            currentPath = preferences["current"]
        except (OSError, ValueError, KeyError) as error:
            # A PRESENT ALFRED WITH A BROKEN `prefs.json` IS A DIFFERENT
            # PROBLEM FROM AN ABSENT ALFRED, AND IS REPORTED AS ONE.
            raise ValueError(
                f"Alfred is installed but '{prefsPath}' could not be read for its "
                f"`current` preferences folder ({error}) - open Alfred's preferences "
                f"once, then re-run `aardvark install_alfred`"
            ) from error

        workflowsPath = Path(currentPath).expanduser() / "workflows"
        if not workflowsPath.is_dir():
            raise ValueError(
                f"Alfred's preferences folder '{currentPath}' has no `workflows` "
                f"directory - check Alfred's Advanced preferences for its sync folder"
            )
        return workflowsPath

    def _source_path(self):
        """
        *the packaged workflow directory the symlink points at*

        `importlib.resources` resolves to the repo working tree for an
        editable install and to site-packages for a package user, through
        one code path with no branch.

        **Return:**

        - ``sourcePath`` -- the packaged `resources/alfred` directory
        """
        return Path(str(files("aardvark_jd"))) / "resources" / "alfred"

    def _install(self, targetPath):
        """
        *write the pointer, then deploy the workflow unless something else owns it*

        **Key Arguments:**

        - ``targetPath`` -- `workflows/aardvark-jd`, whatever is or is not there

        **Return:**

        - ``messages`` -- one line per thing done
        """
        consoleScriptPath = binary.console_script_path(self.executable)
        pointerPath = binary.write_pointer(consoleScriptPath, self.pointerPath)
        messages = [f"recorded aardvark at {consoleScriptPath} in {pointerPath}"]

        sourcePath = self._source_path()

        # A REAL DIRECTORY IS AN IMPORTED `.alfredworkflow` - THE USER'S OWN
        # COPY, WHICH THIS COMMAND NEVER TOUCHES. THE POINTER ABOVE IS
        # STILL WRITTEN, WHICH IS THE WHOLE REASON THE TWO JOBS ARE
        # SEPARATE.
        if targetPath.is_dir() and not targetPath.is_symlink():
            messages.append(
                f"a copy-installed workflow is already at {targetPath} and was left "
                f"alone - it will not auto-update with the package"
            )
            return messages

        if targetPath.is_symlink():
            if targetPath.readlink() == sourcePath:
                messages.append(f"workflow symlink unchanged at {targetPath}")
                return messages
            # REPLACING A SYMLINK LOSES NOTHING: IT IS A LINK.
            targetPath.unlink()

        targetPath.symlink_to(sourcePath, target_is_directory=True)
        messages.append(f"linked {targetPath} to {sourcePath}")
        return messages

    def _uninstall(self, targetPath):
        """
        *remove the symlink and the pointer, and touch nothing inside the package*

        This is the documented removal route, not because Alfred's own
        Delete Workflow is dangerous - it unlinks, leaving the target's
        inode and contents intact - but because it is the only route that
        also removes the binary pointer.

        **Key Arguments:**

        - ``targetPath`` -- `workflows/aardvark-jd`, whatever is or is not there

        **Return:**

        - ``messages`` -- one line per thing done
        """
        messages = []

        if targetPath.is_symlink():
            targetPath.unlink()
            messages.append(f"removed the workflow symlink at {targetPath}")
        elif targetPath.is_dir():
            # AN IMPORTED WORKFLOW IS THE USER'S OWN COPY. REMOVE IT IN
            # ALFRED, WHICH IS THE ONLY PLACE THAT KNOWS IT IS THERE.
            messages.append(
                f"a copy-installed workflow at {targetPath} was left alone - remove it "
                f"in Alfred if you want it gone"
            )
        else:
            messages.append("no workflow symlink to remove")

        if binary.remove_pointer(self.pointerPath):
            messages.append("removed this machine's aardvark binary pointer")
        else:
            messages.append("no aardvark binary pointer to remove")

        return messages

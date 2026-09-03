# How does the terminal handoff open a tab at the resolved path?

Type: prototype
Status: open
Blocked by: 01

## Question

Settled while charting: Alfred cannot change a shell's working directory, so the `cd` equivalent opens a new tab in the frontmost iTerm window, already at the resolved path. `aardvark cd <target>` already does the hard half — it resolves the reference and prints the absolute path to stdout, nothing else (`change_dir.py`), which is exactly what the shell wrapper consumes today.

Build it and answer:

- **What does the AppleScript actually look like?** A new tab in the frontmost window when iTerm is running, a new window when it is not, and no error when iTerm has a window but no current session. Verify each of those three states rather than only the happy one.
- **How is the path handed over safely?** The tree is full of emoji-suffixed folder names with spaces. Whether the path is quoted into a `cd` command written to the session, or passed some other way, and what happens to a path containing a quote or a backslash.
- **What is the fallback for other people?** The workflow ships to PyPI and conda users who may not have iTerm. Decide the fallback — `Terminal.app` via AppleScript, macOS's `open -a`, or the user's configured terminal as a workflow configuration variable — and whether iTerm is detected or configured.
- **Does the shell land correctly?** The user's shell integration wraps `aardvark`/`av` (`shell_init`). Confirm the new session is a normal login shell with that integration loaded, so the tab is immediately usable rather than a bare shell in the right directory.
- **Is a Finder reveal wanted alongside it?** The charting settled on the terminal as the action, but a modifier that reveals the same path in Finder is nearly free once the path is resolved, and it overlaps with the charting decision that modifiers open one mirror each. Decide whether it belongs here or in ticket 13's inventory.

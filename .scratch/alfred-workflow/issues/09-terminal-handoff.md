# How does the terminal handoff open a tab at the resolved path?

Type: prototype
Status: resolved
Blocked by: 01

## Question

Settled while charting: Alfred cannot change a shell's working directory, so the `cd` equivalent opens a new tab in the frontmost iTerm window, already at the resolved path. `aardvark cd <target>` already does the hard half — it resolves the reference and prints the absolute path to stdout, nothing else (`change_dir.py`), which is exactly what the shell wrapper consumes today.

Build it and answer:

- **What does the AppleScript actually look like?** A new tab in the frontmost window when iTerm is running, a new window when it is not, and no error when iTerm has a window but no current session. Verify each of those three states rather than only the happy one.
- **How is the path handed over safely?** The tree is full of emoji-suffixed folder names with spaces. Whether the path is quoted into a `cd` command written to the session, or passed some other way, and what happens to a path containing a quote or a backslash.
- **What is the fallback for other people?** The workflow ships to PyPI and conda users who may not have iTerm. Decide the fallback — `Terminal.app` via AppleScript, macOS's `open -a`, or the user's configured terminal as a workflow configuration variable — and whether iTerm is detected or configured.
- **Does the shell land correctly?** The user's shell integration wraps `aardvark`/`av` (`shell_init`). Confirm the new session is a normal login shell with that integration loaded, so the tab is immediately usable rather than a bare shell in the right directory.
- **Is a Finder reveal wanted alongside it?** The charting settled on the terminal as the action, but a modifier that reveals the same path in Finder is nearly free once the path is resolved, and it overlaps with the charting decision that modifiers open one mirror each. Decide whether it belongs here or in ticket 13's inventory.

## Answer

**`open -a` is the whole handoff. No AppleScript at all.**

```bash
open -a "${AARDVARK_TERMINAL_APP:-<iTerm if installed, else Terminal>}" "$path"
```

The ticket assumed AppleScript, and both AppleScript handoffs were built and measured before this shape was tried. `open -a` beat them on every axis that matters, so they are recorded as the rejected alternative rather than the answer.

### What was measured

**Path safety is the reason.** AppleScript's handoff is `write text "cd -- " & quoted form of path`, which puts the path through a POSIX shell parse. Passing the path as `argv` to `osascript` removes the AppleScript-level escape, and `quoted form of` handles the shell-level one correctly for every fixture tried — apostrophe (`'\''`), backslash, `$HOME`, backticks, `&&`, `|`, `"`, emoji — verified by the landing directory, not by reading the string. It has exactly one hole: a **newline** in a folder name emits a literal newline inside the quotes and `write text` submits the line early. `open -a` takes the path as an `argv` element and never builds a shell string, so it has no hole at all. macOS permits newlines in filenames, and this tree's names are user-typed.

**`open -a` gives the wanted window behaviour anyway.** Against a running iTerm with a window it opened a **new tab in that window**, which is what the charting decision asked for, and landed on `back\slash` correctly. So the AppleScript bought no behaviour the one-liner did not already give.

**The three states dissolve.** With `open -a`, launch and window creation are macOS's problem: there is no running-with-a-window, running-without-a-window or not-running branch to write, and none to verify. This matters because two of the three were not testable — this map's sessions run inside iTerm (`iTerm2 → login → bash → claude`), so closing every window or quitting iTerm kills the session doing the testing. Choosing `open -a` retires an untestable branch rather than shipping it unverified.

**Detection is not needed, but the trap is worth recording.** `running of application "iTerm"` is safe — it returns `false` without launching the app, unlike almost every other AppleScript property. `pgrep -x iTerm2` is **not** safe: the process is `/Applications/iTerm.app/Contents/MacOS/iTerm2` and `-x` misses it. Nothing in the chosen shape needs either, but ticket 10 and ticket 12 both touch app-presence checks.

**Terminal.app as fallback was measured and works**, cold: `activate` then `do script … in front window` reuses the window the launch opens, leaving no stray empty one, and landed on `dollar $HOME and \`backtick\`` intact. It is not needed under the chosen shape.

### The fallback, and who chooses the terminal

`AARDVARK_TERMINAL_APP` is a workflow configuration variable and wins when set. Unset, the workflow uses **iTerm when `/Applications/iTerm.app` exists, and `Terminal.app` otherwise** — every Mac has Terminal, so the chain always terminates. iTerm is detected, not configured, so the author and anyone else with iTerm gets it without touching configuration, and the variable exists for Ghostty, WezTerm, Kitty, Warp and Alacritty users. `open -a` **exits non-zero when the named app is not installed** and prints `Unable to find application named '…'`, which satisfies the charting decision that errors are results: Alfred shows a row saying the configured terminal was not found, and Enter on it can open the workflow configuration.

### Does the shell land correctly?

**No, and it is not this ticket's fault.** The tab is a genuine login shell (`shopt -q login_shell` → yes), but `declare -f aardvark` reports the shell-integration function **absent**; `aardvark` and `av` are plain aliases to the conda binaries. So `av cd A11.20` typed in the new tab prints a path instead of moving.

This is pre-existing and not Alfred-specific — `/bin/bash -lic` reproduces it. The first cause found was that `~/.bash_profile` never sourced `~/.bashrc`, where `eval "$(aardvark shell_init bash)"` lives at line 242. That has since been fixed manually (`~/.bash_profile:49`), and the function is **still absent**: an explicit `source ~/.bashrc` inside an interactive shell leaves it undefined, while running the same `eval` standalone defines it correctly. So `~/.bashrc` aborts somewhere before its last line under interactive login, and the remaining cause is in the dotfiles rather than in this repo.

Ruled out of the map by the user rather than ticketed. It costs the Alfred flow nothing — the handoff sets the directory itself and never uses the wrapper — so it affects only what the user can type once they are in the tab.

### Finder reveal

**Ticket 13's inventory, not here.** Charting settled that modifiers open one mirror each, and `finder` is one of the five URLs in ticket 03's entity record, so it is a row in the modifier table rather than a terminal-handoff question.

### Notes to ticket 13

- The action is **one line**, so it belongs in the workflow as a Run Script object, not in `aardvark_jd/alfred/`. There is no logic here to unit-test.
- `AARDVARK_TERMINAL_APP` is a new workflow configuration variable: default empty in `info.plist`, user override in `prefs.plist` (ticket 01's two-layer design).
- The `aardvark cd` half is unchanged and needs no `--json`. Ticket 03 already excludes `cd` from the `--json` flag; that exclusion is confirmed correct — the command prints a bare path and that is all the handoff consumes.
- `open -a` failure is one of the error rows in the error-result inventory.

### Prototype

`.scratch/alfred-workflow/prototypes/09-terminal-handoff/`, branch `prototype/ticket-09-terminal-handoff`. `scripts/handoff.sh` is the decided shape; the two `*_handoff.applescript` files and `quote_probe.applescript` are the rejected alternative and the evidence for the quoting claims; `fixtures/` holds the hostile directory names.

# How does the workflow find aardvark on a second machine?

Type: grilling
Status: resolved
Assignee: Dave
Blocked by: 02

## Question

Two facts collide. Alfred's preferences live in Dropbox — `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences` — so a workflow installed on one machine appears on every other machine, configuration included. And the system's folder tree is deliberately shared between machines, so the same entities are reachable from all of them.

But the thing the workflow calls is a conda environment binary at `/Users/dave/anaconda/envs/aardvark-jd/bin/aardvark`, and there is no reason for that path to be identical on the next machine. A path baked in by `install_alfred` on machine A syncs to machine B and is wrong there — silently, because a Script Filter cannot raise.

Decide:

- **Is the binary path per-machine state, and can Alfred hold per-machine state at all?** Ticket 02 establishes what is stored where and what syncs. If everything in the workflow directory syncs, the path cannot live there.
- **Where per-machine configuration goes if not in the workflow.** The user settings file at `~/.config/aardvark/aardvark.yaml` is outside Dropbox and already per-machine, which makes it a candidate — but then the workflow has to find *that*, which is the same problem one level up. A resolution order (workflow variable, then a known config location, then a `PATH` probe, then conda env discovery) is the obvious shape; decide it explicitly rather than letting it accrete.
- **How the workflow behaves when resolution fails.** The charting decision gives errors an actionable row where a fix is obvious. This is the case that most deserves one: "aardvark not found on this machine — Enter to configure". Decide what Enter does.
- **Whether `install_alfred` is re-run per machine.** If it is, most of this resolves itself, and the decision becomes how the workflow detects it is on an unconfigured machine rather than how it guesses the path. Note that this makes `install_alfred` idempotent-on-a-shared-directory, which ticket 10 has to account for.
- **Whether this is a first-class requirement or an accepted limitation.** A defensible answer is that the workflow works on the machine it was installed on and says so clearly elsewhere. Decide deliberately, because the alternative is a silent failure on a machine the user rarely notices.

## Input from research (2026-09-03)

[Ticket 02](02-alfred-deployment-mechanics.md) resolved the storage half of this question, and it is worse than assumed in one place and better in another.

- **The two-layer split is real and supported**: configuration **defaults** live in `info.plist`, **changed values** in `prefs.plist`, which Alfred's own documentation says to gitignore. So `install_alfred` can write a default without fighting a user override, and a user override wins without being clobbered on upgrade.
- **But both files live inside the workflow directory, inside the Dropbox-synced preferences folder.** Neither is per-machine. So the split solves upgrade collisions, not the cross-machine problem this ticket exists for, and the per-machine value still has to come from somewhere outside Alfred entirely.
- **[Ticket 01](01-alfred-workflow-authoring.md) sharpened the failure mode**: Alfred's `PATH` is a documented six entries and a conda, venv, pipx or uv binary is on none of them, so a `PATH` probe is close to worthless as a resolution step on this machine. The resolution order should not lean on it.
- **The vestigial-preferences-folder trap applies here too**: any resolution step that falls back to a plausible default path rather than failing loudly will appear to work and silently do nothing.

## Answer (2026-09-04)

**Cross-machine resolution is first-class, because it turned out to be cheap.** The ticket framed this as a genuine trade-off between a working second machine and a simpler design. It is not one. The resolution is a three-step chain ending in a hard failure, and it costs `install_alfred` a single extra file write plus a documented re-run on each machine.

### The ticket's central worry does not hold

The question suggests that `~/.config/aardvark/aardvark.yaml` is a candidate for per-machine state "but then the workflow has to find *that*, which is the same problem one level up." **This premise is wrong, and it is what made the ticket look hard.**

`~/.config/aardvark/` is a fixed, literal path. `~` is expanded by the shell on whichever machine is running, with no discovery, no probing and no configuration. It is created unconditionally on first run (`cl_utils.py:156`) and is a real directory outside Dropbox, so every machine has its own. There is no recursion to escape.

### The resolution chain

Three steps, in order, decided explicitly rather than accreted:

1. **The workflow configuration variable**, if set. The manual override, and it wins outright. It lives in `prefs.plist` per ticket 02's two-layer split, which means it syncs — so it is the escape hatch for someone who wants one path everywhere, not the normal path.
2. **The per-machine pointer file**, `~/.config/aardvark/alfred-binary-path`. Written by `install_alfred`. Outside Dropbox, so machine B has its own or has none.
3. **Hard failure with an actionable row.** No further steps.

Two candidate steps were considered and **deliberately excluded**:

- **A `PATH` probe.** Ticket 01 established Alfred's `PATH` as six fixed entries, none of which carries a conda, venv, pipx or uv binary. A probe would almost never succeed, and the case where it *did* succeed is the dangerous one: finding a different, older aardvark on the system and using it silently.
- **A plausible-default fallback.** Ticket 02's vestigial-preferences-folder trap in its general form. Anything that guesses a path rather than failing will appear to work.

`/usr/local/bin` is on Alfred's `PATH` and was checked as a possible symlink target. It is `root:wheel 755` — **verified not writable without sudo** — so that escape costs a privilege prompt during install and was dropped.

### What the pointer file holds: the console script, not the interpreter

**This corrects the charting decision.** The map records that `install_alfred` "bakes in the interpreter path it is running from (`sys.executable`)". `sys.executable` alone cannot launch anything here: there is no `aardvark_jd/__main__.py`, so `python -m aardvark_jd` does not work, and the workflow would have to reconstruct a `-c` incantation.

The right target is the console script. `pyproject.toml` declares `aardvark` and `av` under `[project.scripts]`, both pointing at `cl_utils:main`, and the generated shim carries the shebang `#!/Users/dave/anaconda/envs/aardvark-jd/bin/python3.14`. Invoking it therefore resolves its own interpreter with no environment activation, no `PATH` and no shell — which is exactly what Alfred's `/bin/zsh --no-rcs` environment can offer.

`install_alfred` derives it as `Path(sys.executable).parent / "aardvark"`. Console scripts land in the same `bin/` as the interpreter under both conda and venv, verified on this machine. So `sys.executable` remains how the path is *found*; it is not what gets stored.

**Format: one line of plain text, nothing else.** Not a key inside `aardvark.yaml`, because reading YAML requires a parser, which requires the interpreter this file exists to locate. The Alfred script reads it with `cat` and has no dependencies at all.

### Three states, three behaviours

Checked on every script filter invocation with `[ -x "$path" ]`, which is sub-millisecond:

| State | Meaning | Row |
| --- | --- | --- |
| No pointer file | Never installed on this machine | "aardvark is not configured on this Mac" |
| Pointer file present, path missing or not executable | Environment deleted, renamed or rebuilt | "The recorded aardvark path no longer exists", **showing the dead path** |
| Pointer file present, path executable | Proceed | — |

Distinguishing the second state from the first is the point. A recorded-but-dead path is precisely the silent-failure shape the map keeps warning about, and printing the path is what makes it diagnosable in one glance instead of a debugging session.

Deliberately **not** detected here: a path that exists and runs but belongs to an older aardvark install. That is version drift, and it belongs to [What does `aardvark install_alfred` do?](10-install-alfred-command.md).

### What Enter does on a failure row

**Copies `aardvark install_alfred` to the clipboard and posts a notification saying to run it in a terminal.** The same action for both failure states.

The slicker option — open a terminal with the command pre-typed — was rejected because `open -a` cannot pre-type, so it would reintroduce the AppleScript that [ticket 09](09-terminal-handoff.md) deliberately eliminated, for a one-time-per-machine event. Opening the docs was rejected as strictly less useful than the command itself.

There is an irreducible honesty to this: the workflow cannot run a command it cannot find. Handing over the exact string is the most it can do from a standing start.

### Scope note

Dave confirms the second machine is **hypothetical** — there is one Mac today. This does not change the decision, because the chain costs almost nothing to build and the alternative is a failure mode that only ever appears on a machine you are not looking at. It does mean the failure rows are a guard-rail rather than a routine path, so they get no more investment than described above.

### Build notes for ticket 13

- Resolution order: workflow configuration variable, then `~/.config/aardvark/alfred-binary-path`, then hard failure. No `PATH` probe, no default-path fallback.
- The pointer file is one line: the absolute path to the `aardvark` console script. `install_alfred` derives it as `Path(sys.executable).parent / "aardvark"` and writes it during install.
- Resolution logic is pure and lives in `aardvark_jd/alfred/` with unit tests over all three states; the `cat`-and-test glue in the Alfred script stays a few lines and is coverage-excluded.
- The map's charting bullet about baking in `sys.executable` is superseded — store the console-script path.
- Both failure rows copy `aardvark install_alfred` to the clipboard on Enter; the stale-path row also displays the dead path.

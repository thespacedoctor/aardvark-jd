# What does `aardvark install_alfred` do?

Type: grilling
Status: resolved
Assignee: Dave
Blocked by: 02, 04, 14

## Question

Settled while charting: a new CLI command deploys the workflow into Alfred and bakes in the interpreter path it is running from, because the CLI is the only thing that knows where it is installed (`sys.executable`) without guessing. This ticket decides what the command actually does.

Decide:

- **Link or copy?** A link means repo edits take effect immediately, which is the author's workflow; a copy is what a package user needs, and it is what survives the repo directory moving or disappearing. Decide whether the command does both behind a flag, or picks one and lets the other route be the exported `.alfredworkflow`.
- **What it writes, and where.** Whether it creates the `user.workflow.<UUID>` directory itself or drives Alfred's own import, and how it decides the UUID — the answer comes from ticket 02.
- **Idempotency and upgrade.** What happens when the workflow is already installed: replace, refuse, or update in place. What happens after `pip install --upgrade` when the package's workflow has moved on but the installed copy has not, and whether the workflow can detect that itself and say so in a result row.
- **What "baking in the path" means concretely.** Whether the interpreter path is written into `info.plist`, into a workflow configuration variable, or into a small generated file the scripts read — and how that interacts with ticket 04's decision about whether the plist is generated. Note that ticket 12 may constrain this heavily.
- **Uninstall.** Whether there is a matching removal path, or whether deleting the workflow in Alfred's UI is sufficient and safe given what this command wrote.
- **Where it appears in the CLI.** The usage block hides setup and maintenance commands behind `--help-all`. Decide whether `install_alfred` is an everyday command or a hidden one, and note that adding it means the workflow's own scope decision — that setup commands are out of scope for the Alfred surface — now has an exception living in the CLI.
- **What it does when Alfred is not installed.** A clear failure, not a traceback.

## Answer (2026-09-04)

`install_alfred` does **two separable jobs**, and separating them is the decision that makes the rest fall out. It always writes the per-machine binary pointer file, and it deploys the workflow by symlink unless a workflow is already installed by another route. There is no copy mode.

### The workflow directory lives inside the package, not at the repo root

**This corrects the charting decision** that the workflow lives in "a directory such as `alfred/`" shipped with the package. As this repo is packaged, that directory would ship in neither the sdist nor the wheel: `MANIFEST.in` excludes everything outside `aardvark_jd/`, and `[tool.setuptools.package-data]` declares only `aardvark_jd = ["resources/**/*"]`.

The workflow therefore lives at **`aardvark_jd/resources/alfred/`**. It ships free under the existing glob with no packaging changes, and it is located at runtime by `importlib.resources.files("aardvark_jd") / "resources" / "alfred"`, which resolves correctly in a git checkout and in a site-packages install through the same call. It also sits alongside `completions/`, `templates_src/` and `wordlists/`, which are the same category of thing.

A top-level `alfred/` with a widened manifest was rejected: a top-level directory is not importable, so locating it at runtime falls back to `__file__` arithmetic that differs between a checkout and an installed wheel — the guessing this map keeps ruling out.

**Consequences for [ticket 04](04-version-controlling-info-plist.md)**: the committed plist is `aardvark_jd/resources/alfred/info.plist` and the gitignore entry is `aardvark_jd/resources/alfred/prefs.plist`. Nothing else in that ticket changes — external scripts, the `make alfred-normalise` target and the no-round-trip editing loop all hold at the new path.

### Link, never copy — because the install is editable

The package is installed **editable** on the authoring machine (`aardvark_jd.__file__` resolves into the repo via `__editable__.aardvark_jd-*.pth`). So `importlib.resources` points at the repo working tree here and at site-packages for someone who installed from PyPI, through one code path and with no branch.

That collapses the link-or-copy question. A single behaviour — symlink `workflows/aardvark-jd` to the resolved `resources/alfred` — gives the author live editing into the repo, and gives a package user a workflow that `pip install --upgrade` refreshes with no action at all. A copy mode would exist only to go stale, so there is no `--copy` flag.

Per [ticket 02](02-alfred-deployment-mechanics.md), the directory name is arbitrary and referenced by nothing, so `workflows/aardvark-jd` is used for legibility rather than a minted UUID.

### The two jobs, and why they had to be split

Charting split installation two ways: `install_alfred` for the author, an exported `.alfredworkflow` for anyone installing from PyPI or conda. **[Ticket 12](12-cross-machine-binary-resolution.md) breaks that split**, because the per-machine pointer file has to be written on every machine — including the machine of someone who installed by double-clicking the bundle. `install_alfred` cannot be author-only.

So:

1. **Write the pointer file.** Unconditional, every run, every machine. This is the job that makes the command meaningful for the imported-bundle route.
2. **Deploy the workflow.** Create the symlink — unless a workflow is already installed by another route, in which case report it and leave it alone.

### Re-run behaviour, by target state

| State at `workflows/aardvark-jd` | Action |
| --- | --- |
| Nothing | Create the symlink, write the pointer, report both |
| Symlink already correct | Rewrite the pointer anyway; report the symlink unchanged |
| Symlink pointing elsewhere | Replace it — it is a link, nothing is lost |
| A real directory (imported `.alfredworkflow`) | **Do not touch it.** Write the pointer, report that a copy-installed workflow is present and will not auto-update |

The pointer file is rewritten on every run because it is the thing most likely to be wrong and it costs nothing.

### Version drift is detected by the workflow itself

With a symlink, "the installed workflow has moved on from the package" cannot happen — they are the same bytes. The problem exists only for the imported-bundle route.

`info.plist` carries a `version`, and ticket 03's `--json` `system` block carries the package version. The workflow compares them and surfaces a **warning row** on mismatch — never a blocker. One string comparison against data both sides already hold, and it converts "my workflow does something the CLI stopped doing" into a visible message.

### Where it appears in the CLI: `ADVANCED`

`commands.py` is the canonical table, `help_text.short_help` strips `ADVANCED` entries from the `-h` screen, and `--help-all` shows everything. `test_command_table_matches_docopt_usage` enforces that the table and the docopt `Usage:` block agree, so adding the command means a usage line, a `COMMANDS` entry and completers regardless of group.

`install_alfred` is one-time-per-machine setup, so it is `ADVANCED`. The everyday screen is for verbs typed repeatedly.

This creates a tension worth naming rather than hiding: ticket 12's failure row instructs the user to run a command that `-h` does not display. It is acceptable **because that row copies the exact command string to the clipboard**, so discoverability never routes through the help screen. It also formalises the exception the ticket flags — setup commands are out of scope for the *Alfred surface*, and `install_alfred` is a setup command whose purpose is to build that surface. It lives in the CLI's advanced group and the workflow never offers it as a row of its own.

### When Alfred is not installed

Per ticket 02: read `~/Library/Application Support/Alfred/prefs.json` and take the `current` key. **Never fall back to a default path** — the vestigial `Alfred.alfredpreferences` on this machine would swallow the write and appear to succeed.

Two distinguishable failures, both non-zero exit, neither a traceback:

1. **No Alfred at all** — no `Alfred.app`, no `prefs.json`. "Alfred is not installed."
2. **Alfred present, but `prefs.json` is missing, unreadable, or lacks `current`.** A real anomaly, reported differently and naming the file it tried.

Splitting them costs one branch and stops the second case from sending the user to look in the wrong place.

### Uninstall

**`install_alfred --uninstall`** removes the symlink and the pointer file, and touches nothing inside the repo. It is documented as *the* removal route.

This exists partly because of an unverified hazard. Ticket 14 confirmed Alfred writes *through* a symlinked workflow directory into the real target; nobody has tested what Alfred's own **Delete Workflow** does to one. If it deletes through the link rather than unlinking, it destroys the repo copy. Graduated into [Does Alfred's Delete Workflow delete through a symlink?](17-alfred-delete-through-symlink.md), which must be answered before the symlink ever points at real repo content.

### Build notes for ticket 13

- Workflow directory: `aardvark_jd/resources/alfred/`, located via `importlib.resources.files("aardvark_jd")`. No packaging changes needed.
- `install_alfred` always writes the ticket 12 pointer file; workflow deployment is conditional on the four target states above.
- Symlink only. No `--copy`. Target name `workflows/aardvark-jd`.
- Add `install_alfred` to `commands.py` as `ADVANCED`, with a `Usage:` line and completers, or `test_command_table_matches_docopt_usage` fails.
- `--uninstall` removes the symlink and the pointer file only.
- Version-drift warning row: compare `info.plist` `version` against the `--json` `system` package version.
- Two distinct Alfred-absent failures, both hard, no default-path fallback.

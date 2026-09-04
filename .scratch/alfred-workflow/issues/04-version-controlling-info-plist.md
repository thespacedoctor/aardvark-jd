# Is `info.plist` committed, or generated?

Type: grilling
Status: resolved
Assignee: Dave
Blocked by: 01, 02, 14

## Question

The workflow lives in the repo, but Alfred owns `info.plist` and rewrites it whenever the workflow is edited in Alfred's UI. Decide how the repo copy stays authoritative and reviewable.

Decide:

- **Committed, or generated from source?** Either the plist is the source and is edited in Alfred, or a higher-level source (YAML, Python, a small builder) is the source and the plist is a build artefact. The first makes Alfred's visual editor usable and makes every diff unreadable; the second makes diffs meaningful and means the visual editor's output has to be reverse-engineered or discarded.
- **If committed: how are Alfred's rewrites contained?** Whether a normalisation step (`plutil -convert xml1`, key sorting, stripping generated state) runs before commit, and whether that is a git hook, a make target, or a documented manual step.
- **If generated: what does the source look like, and how faithful must the builder be?** The builder only has to emit the objects this workflow uses, not all of Alfred's — but it has to emit them correctly, and it becomes code that needs tests under the charting rule that the real logic lives in the package.
- **Where the scripts live.** Alfred can hold script bodies inline inside `info.plist` or reference external script files in the workflow directory. External files are diffable, testable and importable; inline bodies are what Alfred's editor produces by default. Decide, and decide whether that choice is what makes the first question answerable.
- **The round trip.** Whether editing in Alfred's UI is supported at all after this decision, and if so, what the path back into the repo is. An answer that forbids the visual editor entirely is legitimate, but it should be a chosen constraint rather than an accident.

Ticket 02's findings on what Alfred actually rewrites, and when, are the decisive input here.

## Answer (2026-09-04)

**`info.plist` is committed, it is the source, and Alfred's visual editor is the tool that edits it.** The generated-from-a-higher-level-source option is rejected. Tickets 02 and 14 between them removed every reason to reach for a builder, and ticket 14's symlink finding removed the round trip that made the question hard in the first place.

### Where script bodies live: external files, never inline

Every script object is an Alfred **External Script** (`type: 8`) pointing at a real file in the workflow directory. No script body is ever stored inline as a `<string>` inside `info.plist`. This confirms ticket 01's lean and makes it a decision.

This is what makes the rest of the answer possible. With the bodies out, `info.plist` holds only structure — objects, connections, `userconfigurationconfig`, the configuration schema — so it stays small enough that committing it is genuinely reviewable rather than committing a blob. The scripts themselves become ordinary files: diffable, lintable, and, for the Python ones, importable from `aardvark_jd/alfred/` so the existing pytest setup reaches them. That is the charting rule about where the real logic lives, honoured at the file level rather than merely asserted.

### The plist is committed, not generated

The evidence is one-sided:

- Alfred's own team commits `Workflow/info.plist` verbatim. Two `alfredapp` workflows are byte-for-byte identical to the vendor's committed file after import and use (ticket 02).
- Opening a workflow in Alfred's editor writes nothing at all — the hash is unchanged (ticket 14).
- The import-time configuration sheet writes to `prefs.plist`, not to `info.plist`. Ticket 02's one anomaly is explained and does not stand (ticket 14).
- Edit-time churn is confined to `uidata` canvas coordinates and `objects` array order. There is no formatting noise, no injected absolute path; keys stay alphabetical and indentation stays tabs.

A builder emitting the plist from YAML or Python would buy meaningful diffs at the cost of reverse-engineering Alfred's object schema, discarding the visual editor outright, and adding a tested subsystem to the package whose only job is to emit a file Alfred already emits correctly. That is disproportionate machinery for `uidata` churn.

### Containing the rewrites: sort `objects`, leave `uidata` alone

Alfred's output is already canonical — XML plist, tab-indented, keys strictly alphabetical at every level — so a `plutil -convert xml1` normalisation step would be a no-op. Only two regions move, and neither carries semantics:

- **`uidata`** (canvas coordinates) is left exactly as Alfred writes it. Stripping it would give cleaner diffs but would make Alfred re-lay out the canvas on every open, which throws away the visual editor this decision is keeping.
- **The `objects` array order** is normalised by sorting on `uid`. This is the churn that turns a canvas nudge into a large meaningless diff, and sorting makes it stable permanently.

The normaliser is a small pure function in `aardvark_jd/alfred/`, unit-tested like the rest of the real logic, exposed as a **`make alfred-normalise` target** and run manually before committing a plist change.

It is deliberately not a git hook. This repo's four hooks live unversioned in `.git/hooks/`, so a hook is invisible to anyone else and cannot be relied on; and an automated plist rewrite firing while Alfred has the workflow open is a way to lose an edit. A `make` target is versioned, explicit, and safe to run at a moment of your choosing.

One assumption underpins the sort: that Alfred reshuffles the `objects` array freely and therefore treats its order as non-semantic. Ticket 02's diff strongly implies this — identical contents, different order, workflow still working — but it has not been verified directly. **Verify it before building the normaliser**: shuffle the array by hand and confirm the workflow still runs. If order turns out to matter, drop the sort and fall back to accepting the churn with a documented reviewer's rule ("ignore `uidata` and `objects` order"), which was the standing alternative and costs nothing.

### The round trip: there isn't one

Ticket 14 established that Alfred follows the symlinked workflow directory completely and writes **through** it into the repo. There is therefore no second copy and no path back to design. The loop is:

1. Edit the workflow in Alfred's visual editor.
2. Alfred writes `info.plist` in the repo working tree.
3. Run `make alfred-normalise`, read `git diff`, commit.

Scripts never enter that loop: they are external files edited in a normal editor, and Alfred picks up changes on the next run.

The constraint this accepts, deliberately: the visual editor is available only on the authoring machine, the one where `install_alfred` created the symlink. Anyone installing from PyPI or conda gets a read-only `info.plist` and editable script files. That is consistent with the two-track install settled while charting, and it is a chosen limit rather than an accident.

### Consequences

- `alfred/prefs.plist` is added to `.gitignore`. Local configuration overrides never appear in a diff, which is what Alfred's own documentation advises and what ticket 14 confirmed the file is for.
- Ticket 10, [What does `aardvark install_alfred` do?](10-install-alfred-command.md), is unblocked: 02, 04 and 14 are all resolved.

### Path correction (2026-09-04, by ticket 10)

This answer was written assuming the workflow directory sits at the repo root as `alfred/`. [Ticket 10](10-install-alfred-command.md) found that a top-level directory ships in neither the sdist nor the wheel under this repo's `MANIFEST.in` and `package-data`, and moved it to **`aardvark_jd/resources/alfred/`**. Read every `alfred/…` path below as `aardvark_jd/resources/alfred/…`. Nothing else in this answer changes.

### Build notes for ticket 13

- `info.plist` is committed at `alfred/info.plist`; `alfred/prefs.plist` is gitignored.
- Every script object is `type: 8` (External Script) referencing a file. No inline bodies.
- Add a pure `objects`-sorting normaliser to `aardvark_jd/alfred/` with unit tests, and a `make alfred-normalise` target that calls it.
- Before building that normaliser, verify by hand that `objects` order is non-semantic. If it is not, drop the sort and document the reviewer's rule instead.
- Document the edit-in-Alfred, normalise, diff, commit loop in the contributing notes, along with the fact that the visual editor is authoring-machine-only.

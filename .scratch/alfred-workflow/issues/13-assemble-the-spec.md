# Assemble the build specification

Type: grilling
Status: resolved
Assignee: Dave
Blocked by: 03, 04, 05, 07, 08, 09, 10, 11, 12, 14, 15, 17

## Question

The last ticket on the map. Every decision above is made; this one turns them into the single document a TDD implementation session can be handed.

Produce a spec covering:

- **The command inventory.** Each of the fifteen in-scope commands mapped to its concrete Alfred surface: what the user types, what Alfred shows, what modifiers do, what is invoked, and what is reported back. Any command that turned out not to earn a surface is listed with the reason.
- **The CLI changes.** The `--json` contract from ticket 03 and the `install_alfred` command from ticket 10, written as behaviour to test rather than as code.
- **The workflow's file layout.** What lives in the repo directory, in what form, per ticket 04, and which parts are generated.
- **The module layout inside the package.** Where the testable logic sits under `aardvark_jd/alfred/`, what the Alfred-invoked entry points look like, and what is excluded from coverage.
- **The build order.** What has to exist before what, and which slice is a usable workflow on its own — the smallest thing worth installing, so the rest can be judged against something real.
- **The test plan.** Per the user's global rules: what is tested first, what 80 per cent coverage means for a package half of which is Alfred glue, and what is deliberately untested.
- **The documentation changes.** The README section and docs page from the charting decision, and where the internal-and-unstable status of the JSON contract is stated so a future reader does not mistake it for API.

Before writing it, re-read the map's Not-yet-specified section: some of that fog will have cleared while the tickets were resolved, and anything now sharp either belongs in the spec or belongs in a new ticket rather than being quietly forgotten.

## Resolution (2026-09-04)

**The spec is written, at [`docs/alfred-workflow-spec.md`](../../../docs/alfred-workflow-spec.md).** It lives in `docs/`, not in `.scratch/`, because it is the one artifact on this map that a TDD session is handed, and pointing an implementation session at a scratch directory is how a document gets deleted mid-build. It also sits next to the two ADRs it cites.

Sixteen resolved tickets went in largely unchanged. What follows is only what this ticket decided, corrected, or cleared.

### Two factual corrections against the CLI

**There are thirteen in-scope commands, not fifteen.** This ticket's own body said fifteen; the charting scope bullet lists thirteen, and `commands.py` confirms there is no `dropbox_sync`. The spec says thirteen.

**`add_project` takes no description.** Its docopt line is `add_project <category> <projectTitle> [-t <templateName>]` — one positional after the category. [Ticket 06](06-argument-entry-flow.md) handed it forward as "`title, description` plus a template step", which is wrong against the CLI. Its argument step is a plain title field with no comma split.

### The structural consequence nobody had spelled out

[Ticket 05](05-index-payload-and-filtering.md) locked "Alfred Filters Results" mode, which means the Script Filter **runs once with an empty query** and Alfred filters client-side from then on. There is therefore no branching on what the user typed, and **the command rows and the entity rows have to be emitted together in one list**. The alternatives — a sigil (`av >add id`) or a second keyword — were rejected: the first taxes every mutating command with a keystroke, the second reopens the one-keyword decision the charting settled. Command rows carry `match` strings that are the command's words only, so a single typed word never lifts one above the entities.

`fd`, `open` and `cd` therefore get **no rows of their own**. They are not things the user picks; they are what an entity row's Enter and modifiers already do. That is the "commands that did not earn a surface" list the ticket asked for.

### The modifier map ([ticket 05](05-index-payload-and-filtering.md)'s fork and [ticket 09](09-terminal-handoff.md)'s handoff, both confirmed here)

Enter opens every synced mirror at once, matching the CLI. **⌘ reveals in Finder, ⌥ is the handoff, ⌃ opens a destinations sub-list** of Craft, Todoist, Drive and Dropbox. ⇧ is left alone — Alfred binds it to Quick Look.

The four individual mirrors go to a sub-list rather than to chords (⌘⌥, ⌘⌃) because a sub-list can *show* which mirrors are unsynced: a `null` URL renders as "not synced to Craft" and, on Enter, runs that sync. An unbound chord cannot do that. This also **confirms lean** over fat: the sub-list resolves from `variables.urls` in memory, so it is a cache read rather than a re-shell.

### `repair_emoji` gets a confirmation screen; the three syncs do not

No ticket had decided the surface for the four argument-less commands. A sync is idempotent and repairable; `repair_emoji` renames folders on disk and is the one command here where a mis-fire is expensive. This also keeps the confirmation screen a consistent signal: **it appears exactly when something on disk changes**.

### `suggestions`, the field [ticket 08](08-spell-check-surface.md) left to be named

`"suggestions": [{"token": …, "index": …, "suggested": …}]`, on the mutating result, beside `corrections` and never merged into it — `corrections` reports substitutions **applied**, `suggestions` carries ones **offered and not yet accepted**, which is what the confirmation screen renders. `index` is the token position from `spell_check.tokenise`, so a row substitutes without re-parsing. The spec restates that **`--json` must run detection despite never prompting**, and quotes [ticket 16](16-spell-check-tuning.md)'s **4.3 per cent** fire rate rather than ticket 08's 1.4 per cent.

### Going back to the reference pick is a row, not a key

[Ticket 06](06-argument-entry-flow.md) left the choice open. A **first row** in the argument step, because Alfred's Escape discards the run rather than stepping back, and a chord hint in the subtitle would compete with the `title = «…»` parse the same subtitle is showing. A row is visible without being read and costs nothing when unused.

### Build order, and the smallest installable slice

Slice 0 is the CLI foundation and is invisible. **Slice 1 is the smallest thing worth installing**: `install_alfred`, the binary pointer, and one Script Filter fed by `fd --json` with the full modifier set. It is the whole daily-driver half — the read commands are what gets typed twenty times a day — and it needs none of the confirmation-screen machinery. Everything after is judged against it. Slice 2 is `add_id` and the mutating machinery it carries, slice 3 the rest of the mutating set, slice 4 sync and maintenance.

Two things sit outside that chain. **[Ticket 16](16-spell-check-tuning.md)'s tuning ships before slice 2**, so the correction rows are tuned the first time they are seen rather than retuned under a UI. **[Ticket 04](04-version-controlling-info-plist.md)'s hand-verification that `objects` order is non-semantic happens inside slice 1**, before the normaliser is written.

### The coverage bar is per module

80 per cent applied **per module, not only globally** — `json_output.py` and every module under `aardvark_jd/alfred/` each meet it alone. A global average lets a well-tested `db.py` hide an untested new module, which is what the "real logic lives where pytest reaches it" rule exists to prevent. The repo has no `.coveragerc` and no `--cov` in the `Makefile` today, so the spec names the mechanism: `[tool.coverage.run] omit` in `pyproject.toml` for the script files, `# pragma: no cover` for the `print(json.dumps(...))` glue, and a new `make test-cov` target so the number is reproducible rather than remembered.

Five things are **deliberately untested**, each with its reason recorded: Alfred itself, the shell scripts under `resources/alfred/scripts/`, `info.plist`, the filesystem effects of `install_alfred` (fakes only, never the live preferences folder) and the `open -a` handoff.

### Fog cleared

**"What happens on a fresh machine" is closed, not ticketed.** With [ticket 14](14-verify-alfred-write-behaviour.md) ruling workflow-directory sync out of scope and [ticket 12](12-cross-machine-binary-resolution.md) settling binary resolution, what remained was an ordering note — install the package, run `install_alfred`, point at the tree — and it is now a README paragraph in the spec's documentation section. Removed from the map's **Not yet specified**.

The other two fog patches (a direct-keyword layer, Universal Actions) both explicitly need a week of real usage that does not exist yet, so they stay as fog and are listed in the spec's own "Known open questions" alongside frecency, so the implementation session sees what was left open on purpose.

### No new tickets

The map is complete. The way to the destination is clear, and nothing is left to decide before someone builds it.

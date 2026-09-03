# What is the shape of aardvark's `--json` output?

Type: grilling
Status: resolved
Blocked by: 01

## Question

Settled while charting: the Alfred workflow gets its data from a new machine-readable output mode on the CLI, covering the read commands and the mutating commands' results, documented in the repo but explicitly internal and unstable. This ticket decides its actual shape.

Decide:

- **Which commands emit it and how it is requested.** A global `--json` flag, a per-command flag, or a separate output-format option. Note that the usage block in `cl_utils.py` is a docopt specification, so every flag added there is visible on every command it is attached to.
- **The entity record.** What one area, category or ID looks like as JSON: its Johnny Decimal code, title, description, domain, emoji, folder path, archived state, and its Craft, Todoist and Drive URLs. The mirror URLs matter here — the charting decision that modifiers open one mirror each needs all of them present on every item, where the CLI today only fires them.
- **The envelope.** Whether output is a bare array or an object with metadata (system name, root path, index generation or timestamp), and whether that envelope carries a version field given the contract is internal and expected to move.
- **The result object from a mutating command.** What `add_id`, `add_project`, `add_area`, `add_category`, `archive` and `set_emoji` return: the new code, the folder path, the emoji actually used, whether a background sync was handed off, and — if the spell-check and emoji surfaces end up staying in the CLI for some paths — what was corrected.
- **How errors are expressed in JSON mode.** The charting decision that a script filter returns an error row rather than raising, which means the CLI's failure has to reach the workflow as data. Decide whether `--json` errors go to stdout as a structured object with a non-zero exit, or to stderr as prose with the exit code carrying the signal.
- **What `open --json` means.** The command's whole purpose today is the side effect of opening URLs. Decide whether `--json` suppresses the opening and just reports the links, or reports what it opened.
- **Where this code lives.** Whether serialisation sits in each command module, in `cl_utils.py`, or in a single new module — bearing in mind the charting decision that the real logic lives where pytest can reach it.

Cross-check every field against `db.py`'s actual row shapes and `doc_links.py` before settling: the contract should expose what the index holds, not what would be convenient to invent.

## Input from research (2026-09-03)

[Ticket 01](01-alfred-workflow-authoring.md) settled three things this contract must accommodate:

- **A mod's `variables` replace the item's wholesale.** There is no merge. Anything a modifier action needs must be repeated inside every mod block, which argues for keeping the per-item variable set small and putting the bulk in `arg`.
- **`uid` decides who owns result ordering.** Supplying it hands ordering to Alfred and enables its learning; omitting it keeps the CLI's order with no learning; supplying it with `skipknowledge: true` keeps both. Alfred's knowledge is keyed on the `uid` string, so **this contract has to decide whether an entity has a stable identifier** — one that survives a rename, an emoji change, a re-index, and an archive-and-reuse of the same Johnny Decimal number. If it does not, `skipknowledge` is the safer default while the design moves.
- **One Open URL object can serve all four mirror actions** via the `alfredworkflow` JSON envelope's ability to override a downstream object's config, rather than needing an object per mirror.

## Answer

Decided with Dave on 2026-09-03, grounded against `db.py` (schema), `doc_links.py`, `search.py`, `open_craft.py`, `locate.py` and `cl_utils.py`.

### Naming

This is the **JSON contract**: the machine-readable output the CLI emits under `--json` and the Alfred workflow consumes. It is internal and unstable — the repo documents it, but nothing outside the repo may depend on it, and it may be reshaped without a deprecation cycle. Ticket 11 owns folding the term into `CONTEXT.md`; concrete terms it can adopt from here are the `aardvark_json` envelope, and an entity's `id` (JD-code identity) versus its `row_key` (numeric index key).

### 1. How it is requested, and which commands emit it

A per-command `[--json]` flag, added to the `Usage:` lines of the in-scope commands only:

- Read: `fd`, `open`
- Mutating: `add_area`, `add_category`, `add_id`, `add_project`, `archive`, `set_emoji`, `repair_emoji`
- Sync: `craft_sync`, `todoist_sync`, `gdrive_sync`

Not added to the setup commands, and not to `cd` — `cd` already prints a bare absolute path to stdout and the terminal-handoff (ticket 09) consumes exactly that; a JSON wrapper would add nothing.

A global flag is rejected because `cl_utils.py`'s usage block is a docopt spec — a token is only recognised on the lines it appears on — and a pre-docopt intercept (the `cd`/`completion`/`shell_init` pattern) is rejected because the mutating and sync commands must run the full stack (settings load, `db.initialise_schema`, drift warning, sync handoff) that the fast-path intercept deliberately skips.

`fd --json` with no term returns the whole index (the payload for Alfred's keyword-entry script filter). `fd --json <ref>` returns the subtree under a domain letter, area or category. `fd --json <keyword>...` returns keyword-search results. There is no separate "dump" command.

`--json` implies non-interactivity — it never prompts, matching the charting decision that the CLI runs headless under Alfred. Where a command has a suppressing flag today (`-y`, `-e`, `-t`, `-w`) the workflow still passes it; `--json` does not silently imply `-w` (sync stays backgrounded per charting).

### 2. The envelope

Always a JSON object, never a bare array. Every envelope carries an integer `aardvark_json` version field, bumped on any breaking change. The workflow refuses (with an actionable row) a version it does not recognise and tells the user to re-run `install_alfred` — this is the version-skew signal tickets 10 and 12 need.

Read commands:

```json
{
  "aardvark_json": 1,
  "system": {
    "name": "My Life",
    "root_path": "/Users/Dave/My Life",
    "generated_at": "2026-09-03T12:00:00Z"
  },
  "entities": [ /* entity records, see §4 */ ]
}
```

`system.name` and `root_path` come from settings / the `meta` table. `generated_at` is an ISO-8601 UTC timestamp taken at emit time — there is no index-generation counter in the schema and a timestamp is sufficient for the workflow's cache-freshness needs (ticket 05).

Mutating commands: `{ "aardvark_json": 1, "result": { ... } }` (see §7).

Errors: `{ "aardvark_json": 1, "error": { ... } }` (see §5).

### 3. The stable identifier

Neither available identifier is stable across every operation, so the contract exposes both:

- `id` — the string `"<domain>:<code>"`, e.g. `"areas:A11.10"`. Stable across rename, emoji change and a from-scratch reindex. **Not** stable across archive-and-reuse of the same Johnny Decimal number — but that is correct: a reused number is a genuinely different entity and Alfred's learning for that slot *should* reset. This is the value the workflow uses as the Alfred `uid`.
- `row_key` — the stringified autoincrement primary key (`area_id` / `category_id` / `id_id`), which is `craft_links` / `todoist_links` / `gdrive_links`'s `entity_key`. Stable across rename and emoji change; not across archive-reuse or reindex. Exposed for mirror-link correlation and debugging, not for identity.

The workflow pairs the `uid` with `skipknowledge: true` (ticket 01's guidance) until frecency and recall are designed — see the map's "Not yet specified". At that point the identity question may be reopened, but the `id`/`row_key` split stands regardless.

### 4. The entity record

Every field verified against the live schema:

```json
{
  "id": "areas:A11.10",
  "row_key": "42",
  "type": "id",
  "domain": "areas",
  "code": "A11.10",
  "title": "Cardiologist",
  "description": "",
  "emoji": "🩺",
  "folder_path": "/Users/Dave/My Life/03_AREAS🧭/A10-19_health🏥/A11_doctors🩺/A11.10_cardiologist",
  "archived": false,
  "urls": {
    "finder": "hook://file/…",
    "craft": "https://…",
    "todoist": "https://…",
    "drive": "https://…",
    "dropbox": "https://…"
  }
}
```

- `type` is one of `area`, `category`, `id`. `domain` is one of `areas`, `resources`, `projects`.
- `emoji` is `""` for IDs (the `ids` table has no `emoji` column and ID folders are never emoji-suffixed) and for an area/category whose stored emoji is blank. The contract does **not** substitute `labels.FALLBACK_EMOJI` — that is a display concern for a human-facing renderer, and the workflow decides its own fallback.
- Any absent URL is `null`. `urls.todoist` is only ever populated for `area`/`category`/`id` (the only types `todoist_sync` mirrors). `urls.finder` is `null` off macOS (`doc_links.hookmark_url` returns `None`).
- `urls.finder` is computed at emit time from `folder_path` via `doc_links.hookmark_url`; it is not stored. `urls.dropbox` is looked up from `dropbox_links` by `folder_path`; the other three from their `*_links` tables by `(type, row_key)`.
- `archived` is always `false` for a record in the `entities` array — archived entities leave the live tables entirely. `fd --json --archived` adds a sibling `"archived": [ ... ]` array to the envelope built from `archived_entities` rows, each carrying that table's own stored `craft_url` / `todoist_url` / `gdrive_url` / `dropbox_url` snapshot (no live `finder` link — the folder has moved). Archived entities are absent from the default payload, matching every existing index walk.

**Implementation note for ticket 13:** the mirror URLs must be fetched with a single read-only pass — a new `db.entities_with_links(dbConn)` doing `LEFT JOIN`s across `areas`/`categories`/`ids` and the three `*_links` tables plus `dropbox_links` — not the per-entity `db.get_*_link` calls `open_craft` uses today, which would be N×4 queries per dump.

### 5. Errors in JSON mode

Under `--json`, a `CLEAR_ERRORS` failure (the `ValueError` / `KeyError` / `*Exhausted` set `cl_utils.main` already catches) is written to **stdout** as `{ "aardvark_json": 1, "error": { "kind": "...", "message": "..." } }` and the process exits non-zero. `kind` is a stable machine token — at least `no_system`, `not_found`, `not_synced`, `value_error`, `domain_exhausted`, `category_exhausted`, `id_exhausted` — that the workflow maps to an actionable error row (ticket 12's "aardvark not found", the charting decision's "entity not yet synced → Enter to sync"). `message` is the human string.

Alfred reads stdout regardless of exit code, so the structured object always reaches the workflow; the non-zero exit is a secondary signal for shell use. stderr continues to carry human prose for a terminal user. `cl_utils.main`'s `except CLEAR_ERRORS` branch gets a `--json` fork; the `no aardvark system found` early-exit path (currently a bare `print(..., file=sys.stderr); sys.exit(1)`) also forks.

### 6. `open --json`

`open --json` **suppresses the opening entirely** and returns the resolved entity:

```json
{ "aardvark_json": 1, "result": { "label": "Cardiologist", "entity": { /* §4 record */ } } }
```

The workflow's own Alfred Open URL object does the opening (ticket 01: one object serves all four mirrors via the `alfredworkflow` envelope), choosing the mirror by modifier key from the `entity.urls` block. `open` without `--json` is unchanged — it still resolves, opens every synced mirror, and prints what it opened.

If the path resolves to an entity synced to nothing, that is **not** an error under `--json` (unlike today's `open`, which raises `ValueError`): the record is returned with all `urls` `null` except `finder`, and the workflow offers a "sync now" row.

### 7. The mutating-command result object

One uniform shape across all seven mutating commands:

```json
{
  "aardvark_json": 1,
  "result": {
    "action": "add_id",
    "entity": { /* §4 record for the new or changed entity */ },
    "emoji_source": "claude",
    "corrections": [ { "from": "cardilogist", "to": "cardiologist" } ],
    "sync": "backgrounded",
    "template_used": "blank",
    "warnings": []
  }
}
```

- `action` is the command name.
- `entity` is the full §4 record for the entity created or modified, so the workflow can immediately reveal its folder and offer its mirrors without a second `fd` call. For `archive`, `entity` describes the archived entity with `"archived": true` and its `archived_entities` URL snapshot.
- `emoji_source` is `claude`, `offline` or `explicit` — present only for `add_area`, `add_category`, `set_emoji` (the commands that resolve an emoji). Omitted for `add_id`, `add_project` (IDs carry no emoji), `archive`, `repair_emoji`.
- `corrections` is the list of spell-check substitutions applied to the title, `[]` when none were made or the check was skipped. Present for `add_area`, `add_category`, `add_id`, `add_project`.
- `sync` is `backgrounded` (detached carrier spawned), `waited` (`-w`, ran in the foreground) or `none` (no mirror connected). Present for every command that calls `_hand_off_sync`.
- `template_used` — `add_project` only.
- `warnings` — the human-string warnings the command already surfaces (`archive` returns a list; others print `note:` lines). Always present, `[]` when empty.
- `repair_emoji` returns `"entities": [ /* §4 records */ ]` in place of `entity`, since it repairs many folders at once.

**Implementation note for ticket 13, and input to tickets 07 and 08:** `emoji_source` and `corrections` are information the `add_*` / `set_emoji` worker classes currently compute internally and discard — their `.get()` methods return only `(code, folderPath)` and friends. Delivering this result object requires those methods to return the emoji provenance and the applied corrections (either by widening the return tuple or via an attribute on the worker). Tickets 07 (emoji surface) and 08 (spell-check surface) decide whether those steps stay in the CLI or move to Alfred; whichever way they land, the CLI path still needs to report what it did here.

### 8. Where the code lives

A single new pure module, `aardvark_jd/json_output.py`, beside `doc_links.py` and `labels.py` as another shared renderer. It holds `entity_record(row, links)`, `read_envelope(system, entities, archived=None)`, `result_envelope(action, ...)`, `error_envelope(exc)` and the `kind`-token mapping — all pure functions over dicts and rows, no I/O, fully unit-tested. `cl_utils.main` / `_dispatch` call it and `print(json.dumps(payload, ensure_ascii=False))`.

Not `aardvark_jd/alfred/` — the JSON contract is a CLI feature that the workflow happens to consume; `alfred/` is reserved for ticket 13's workflow-specific logic (item construction, argument parsing, path discovery). The one-line `print(json.dumps(...))` calls in `cl_utils` are the only glue and are the part excluded from coverage; `json_output.py` itself is held to the 80 per cent bar.

### 9. `fd --json` structure and ordering

- **Flat, never nested.** `entities` is a flat array for the whole-index call, a `<ref>` subtree and a keyword search alike — no tree nesting, no box-drawing. Hierarchy is derivable from `code` and `domain`. The workflow filters a flat item list client-side; the tree is a human-only rendering.
- **Ordering.** Whole-index and subtree calls emit in stable index order: domain (`areas`, then `resources`, then `projects`), then Johnny Decimal number ascending, an area immediately before its categories before their IDs — the same depth-first walk `search.tree` does, flattened. Keyword-search calls stay in `bm25` rank order, matching non-JSON `fd`. The workflow relies on this order (with `skipknowledge: true`) until frecency lands.

### 10. Sync-command result

`craft_sync` / `todoist_sync` / `gdrive_sync` under `--json`:

```json
{
  "aardvark_json": 1,
  "result": {
    "action": "craft_sync",
    "summary": { /* the command's existing summary dict, verbatim */ },
    "drift": [
      { "mirror": "craft", "last_failure_class": "...", "last_failure_at": "..." }
    ]
  }
}
```

`summary` is the dict the command's `.get()` already returns (`folders_created`, `documents_created`, `link_rows_written`, …), passed through unchanged. `drift` is `db.drifted_mirrors(dbConn)` rendered so the workflow can report a failed mirror without a second call. A sync failure under `--json` still follows §5 (structured `error` on stdout, non-zero exit).

### Downstream effects

- Ticket 05 (whole-index-at-scale prototype) is now unblocked and has a concrete payload to measure: the §4 record, flat, in index order, with the §4 `urls` block on every item.
- Tickets 07 and 08 inherit the requirement in §7 that the CLI path reports `emoji_source` and `corrections`.
- Ticket 11 has the vocabulary from the "Naming" section above to fold into `CONTEXT.md`.
- Ticket 13 inherits two implementation notes: the `db.entities_with_links` bulk read (§4) and the worker-class return-value widening (§7).

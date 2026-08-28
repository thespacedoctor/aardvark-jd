# Where does the learned per-user vocabulary live?

Type: grilling
Status: resolved
Blocked by: 06

## Question

[Which en_GB wordlist ships with aardvark?](05-research-en-gb-wordlist.md) established that a learned per-user vocabulary is **part of the spell-correction feature, not a refinement of it**: the shipped wordlist produces an 18 per cent false-positive rate on realistic technical vocabulary, so without a record of dismissals the feature nags indefinitely. Where does that record live?

This collides with a premise already settled on this map. The index database is becoming a **per-machine, unsynced derived artefact**, because the Dropbox ignore is applied in place and the attribute does not sync. So:

- **If the vocabulary lives in `aardvark.db`,** it is per-machine. Dismiss `pydantic` on the laptop and the desktop nags again. That may be acceptable, but it is a consequence of the Dropbox decision and should be chosen rather than inherited by accident.
- **If it lives outside the database,** where? The user settings YAML at `~/.config/aardvark/` is also per-machine. A file inside the synced tree would follow the user between machines, but then it is user data living in a folder the system otherwise treats as derived, and it needs a home in the PARA layout.
- **Is per-machine actually wrong?** Consider that the vocabulary is a record of *this user's* jargon, not of *this machine's*, which argues for following the user. Against that, YAGNI: a single-machine user never notices, and cross-machine sync can be added later without redesign if the store is a plain list.

Decide:

- The store's location and format.
- Whether it is per-machine or follows the user, stated as a deliberate choice.
- Whether a dismissal is recorded per token, or per token-plus-suggestion, since the same token could later attract a different suggestion.
- Confirm the constraint from ticket 05 holds in the chosen design: the store must **not** be bulk-seeded from the existing tree, because that would silence `aadvark` on day one, and `aadvark-jd` is a real typo currently in the live tree.

Blocked by [When and how does aardvark offer a spelling correction?](06-spell-correction-interaction.md), which decides whether dismissals are recorded at all and at what granularity.

## Context from ticket 06 (2026-08-28)

[When and how does aardvark offer a spelling correction?](06-spell-correction-interaction.md) is resolved, so this ticket is unblocked. It settled everything about the vocabulary except where it physically lives:

- **A dismissal is recorded on every declined suggestion** (plain `[y/N]`, no explicit `never`). So the store is written on the common path, not a rare one — it will grow steadily.
- **Keyed on the token alone**, not token-plus-suggestion. The store is a flat set of lowercase tokens.
- **One global list** shared across `add_area`, `add_category`, `add_id`, `add_project`. Not scoped per command or per domain.
- **Two readers:** the interactive prompt and the non-TTY stderr note both filter through it.
- **Not bulk-seeded** from the tree — confirmed still required.

What is left for this ticket: the store's location and format, and the per-machine vs follows-the-user call stated as a deliberate choice (the map's premise that `aardvark.db` is now a per-machine unsynced artefact is the live tension).

## Answer

Resolved 2026-08-28. Grilling session, against `db.py`, `paths.py` (`SYSTEM_SKELETON`), `settings_writer.py`, `default_settings.yaml`, `cl_utils.py`.

### Location and format

**`<root>/.aardvark-vocabulary`** — a dotfile at the aardvark system root, beside `00_INDEX🗂️` but **outside** it, so it is not caught by the wholesale Dropbox ignore (ticket 07) and syncs normally.

- UTF-8, newline-delimited, **one lowercase token per line**.
- A two-line header comment for hand-editors; lines starting `#` and blank lines are ignored on read:

```
# aardvark: words to skip when spell-checking new folder titles.
# one lowercase word per line. safe to edit.
pydantic
postgres
soxspipe
```

- **Read:** drop `#` comments and blank lines, lowercase every token defensively, load into a `frozenset`.
- **Write:** the full list, **sorted and de-duplicated**, so on-disk order is stable and Dropbox diffs (and any conflict copies) stay minimal.
- **Created lazily** on the first dismissal — never written by `init`, so an unused system never carries an empty file.
- Not located in a PARA or system folder: it is a sidecar to the tree, like `.gitignore` at a repo root, which keeps it out of "user data living in a system location".

### Per-machine or follows the user

**Follows the user**, deliberately. The aardvark tree is Dropbox-synced precisely so it moves between machines, and the vocabulary is a record of *this user's* jargon, not any one machine's — dismiss `pydantic` once, on any machine, and it stays dismissed everywhere. This is a conscious departure from the map's premise that `aardvark.db` is now a per-machine unsynced artefact (ticket 08): the index does not need to follow the user, but the vocabulary does, and there is no reason to bind the two decisions together.

The alternative — a one-table addition to `aardvark.db`, inheriting per-machine — was rejected as the wrong behaviour for genuinely user-level data, though it would have been less code. The plain-text format is the hedge: if syncing ever proves troublesome the file is trivially portable or reducible to a table without redesign.

### Granularity (carried from ticket 06, confirmed)

- Keyed on the **token alone**, not token-plus-suggestion.
- Appended **on every declined suggestion** (`N` or bare Enter at the `[y/N]` prompt).
- The store **starts empty** and only ever grows by one token per decline. It is **never** seeded by walking the existing tree — `aadvark` and `aadvark-jd`, live typos in the tree today, stay catchable and are silenced only if the user explicitly declines the prompt for them.

### Write semantics

Persist **immediately** on each dismissal, with an **atomic write**: render the full sorted list to a temp file in the same directory, then `os.replace` over `.aardvark-vocabulary`. A mid-command crash then never loses a dismissal or leaves a torn file. No end-of-command batching.

### Failure behaviour

**Degrade, never raise** — the spell-check helper must not be able to break `av add_project`:

- Read failure (missing is normal; unreadable, permission denied, malformed) → treat the vocabulary as empty, log a warning, carry on.
- Write failure (permission denied, disk full) → log a warning; the dismissal is not persisted, so it is offered again next run.

Mirrors `emoji_picker`'s fallback philosophy.

### Non-interactions (confirmed)

- **Not mirrored** to craft / Todoist / Google Drive — all three walk PARA entities from the DB and never touch arbitrary root files (`gdrive_sync` mirrors folders only).
- **No other command** reads or writes it — only the spell-check path, called from `add_area` / `add_category` / `add_id` / `add_project`.
- **Dropbox conflict copies** (two machines dismissing between syncs) get **no automatic handling in v1** — documented behaviour. The sorted plain-text format makes a manual merge trivial and the loss (a few re-offered suggestions) is negligible.

### Consequence for the map

With tickets 05 (wordlist + tokeniser + candidate generator), 06 (interaction, placement, non-TTY contract, learning, toggle) and 10 (storage) all resolved, the **spell-correction half of the destination is fully specified** and ready to hand to TDD implementation. Nothing about it remains undecided.

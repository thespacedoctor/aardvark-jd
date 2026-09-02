# aardvark-jd

`aardvark-jd` is a Python CLI that manages a personal filing system: one folder
tree laid out as PARA + Johnny Decimal, indexed in SQLite, and mirrored out to
craft.do, Todoist, Google Drive and Dropbox. This glossary fixes the vocabulary
those parts share.

## Language

**System**:
One PARA + Johnny Decimal root — the folder tree together with its index. Created
by `aardvark init`. The tree is the source of truth and is shared between
machines (via Dropbox); the index is not.

**Domain**:
One of the three Johnny Decimal-coded trees: `areas`, `resources`, `projects`.
_Avoid_: section, category (a category is a level *within* a domain).

**Area**:
A Johnny Decimal decade (`10-19`) within a domain.

**Category**:
A Johnny Decimal two-digit slot (`11`) within an area.

**ID**:
A Johnny Decimal leaf (`11.01`) within a category. Never emoji-suffixed.
_Avoid_: item, leaf.

**Project**:
An ID inside a `projects`-domain category, optionally scaffolded from a template
zip in that category's `04_templates`.

**Entity**:
An area, category or ID — the things the index rows describe and the mirrors
reproduce. _Avoid_: object, record, node.

**Reserved system folder** / **reserved system ID**:
The fixed `00-09` scaffolding slots (`01_inbox`, `04_templates`, `09_archive`, …)
created automatically alongside every system, domain and category.

**Code**:
The canonical Johnny Decimal identifier of an entity: `A10-19`, `A11`, `A11.10`.
_Avoid_: number, key.

**Ref**:
What the user typed to name an entity on the command line, before it is resolved
— shorter or differently cased than the code it resolves to (`a10` → `A10-19`).
_Avoid_: using "code" for user input; a ref is what was typed, a code is canonical.

**Emoji**:
The single character an area or category owns. Held in the index and repeated at
the end of the folder name. An ID has none — not a blank one, none at all.

**Folder name**:
An entity's exact on-disk name: slugified title, emoji-suffixed for areas and
categories (`A10_19_health🏥`). _Avoid_: path (that is the whole absolute path).

**Label**:
The one line printed to describe an entity — `A10-19 🏥 Health` — built from its
code, emoji and title. Never the same string as the folder name: the label is
title-cased and space-separated, the folder name slugified. Shared by the `fd`
tree, the `fd` search results and the `open` picker.
_Avoid_: name, display name.

**Title**:
The human-readable name the user gave an entity, before slugification.
_Avoid_: name.

**The index**:
`aardvark.db`, the SQLite store inside `00_INDEX🗂️`. Authoritative for entity
descriptions; for everything else a per-machine, unsynced derived artefact.
_Avoid_: database, cache.

**Mirror**:
An external service the tree is reproduced into: craft.do, Todoist, Google Drive
or Dropbox.

**Sync**:
Reconciling a mirror with the tree by re-walking the whole tree. There is only one
kind: syncs differ in whether you wait for them, not in what they touch.
_Avoid_: fast-path sync, incremental sync — no sync is scoped to what changed.

**Background sync**:
A sync a mutating command hands off and does not wait for. The seven mutating
commands work this way, so they return without knowing whether the mirrors were
reached.

**Foreground sync**:
A sync you wait for: an explicit `craft_sync`, `gdrive_sync` or `todoist_sync`, one
of the `connect_*` commands' first backfill, or any command given `--wait`.

**Drift**:
A mirror disagreeing with the tree. Repaired by the next sync, since every sync
re-walks the whole tree and rewrites what no longer matches.

**Drift marker**:
The per-mirror record of when each mirror last synced and last failed. Persistent,
surfaced by the browse command, and the only way a background sync's failure
becomes visible.

**Index document**:
The generated content page a mirror holds for a section or category, rewritten
by sync.

**Closure** (dependency closure):
The set of entities that must re-sync when one entity changes. For creation it is
one level deep — the new entity's parent category's index document.

**Link row**:
The `.00_index` row a sync writes into a mirror's index document, carrying
cross-service links back to an entity.

**Suspect token**:
A word in a new entity title the spell-checker flags: six or more characters, and
a distance-1 dictionary word exists.

**Dismissal**:
A spell-correction suggestion the user declined. Recorded permanently.

**Learned vocabulary**:
The accumulated dismissals, kept in `<root>/.aardvark-vocabulary` and synced so it
follows the user between machines. _Avoid_: whitelist, allowlist, custom
dictionary.

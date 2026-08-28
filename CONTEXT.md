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

**The index**:
`aardvark.db`, the SQLite store inside `00_INDEX🗂️`. Authoritative for entity
descriptions; for everything else a per-machine, unsynced derived artefact.
_Avoid_: database, cache.

**Mirror**:
An external service the tree is reproduced into: craft.do, Todoist, Google Drive
or Dropbox.

**Sync**:
Reconciling a mirror with the tree. A *fast-path* sync follows a single mutating
command and touches only what that command changed; a *repair* sync
(`craft_sync`, `todoist_sync`, `gdrive_sync`) re-walks the whole tree.

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

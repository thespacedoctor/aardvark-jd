# Map: remote sync execution model

Label: `wayfinder:map`

## Destination

A decided execution model for aardvark's remote mirroring (craft.do, Todoist, Google Drive) that returns the CLI promptly and stops the 429 rate-limit failures, plus a decided design for offering spelling corrections on new entity titles. The destination is a set of decisions ready to hand to TDD implementation, not the implementation itself.

## Notes

**Domain.** `aardvark-jd` is a Python CLI (`aardvark` / `av`, same entry point) implementing a PARA + Johnny Decimal filing system over a folder tree, indexed in SQLite, mirrored out to craft.do, Todoist, Google Drive and Dropbox. Repo: `~/git_repos/_packages_/python/aardvark-jd`, branch `develop`.

**Skills every session should consult.** `mattpocock-skills:grilling` and `mattpocock-skills:domain-modeling` for decision tickets; `mattpocock-skills:research` for research tickets. Implementation, when it eventually happens, follows the user's global TDD rules (test-first, 80% coverage) and Gitflow.

**One deliberate exception to plan-don't-do.** [Measure `av add_project` after content comparison lands](issues/09-measure-latency-after-comparison.md) is a task ticket that implements a change and measures it. It earns its place because a scoping decision waits on the number, not because the map has drifted into execution. Everything else on this map remains planning.

**Standing preferences for this effort.** UK English. No mid-sentence line breaks in Markdown. Comments in source are UPPERCASE. Immutability by default. The user prefers a short plan and explicit approval before non-trivial implementation.

### Settled while charting (2026-08-27)

These are foundational choices made during the charting grilling. They are premises for the tickets below, not tickets themselves.

- **Scope split.** Only the remote-sync cluster and spell-correction are on this map. Four unrelated small fixes are listed under Out of scope.
- **429 fix uses both levers.** Incremental sync is the primary fix; retry/backoff is the non-negotiable safety net, because a full backfill can always hit the limit.
- **Incremental strategy.** Fast path passes the changed entity into the sync engine as an explicit scope (the mutating command already knows what it touched). Repair path stays as the whole-tree walk, upgraded with a timestamp skip. No dirty-flag state machine.
- **Backgrounding is not assumed.** Cutting API calls is the cheap way to CLI speed; backgrounding is the expensive way. Backgrounding only reopens if measured latency exceeds the gate.
- **Latency gate.** 500 ms wall-clock for `av add_project`.
- **Dropbox constraint.** The index DB lives inside the Dropbox tree. A symlink out would not help: the classic Dropbox client follows symlinks and uploads the target's contents. The chosen mechanism is Dropbox's per-file ignore extended attribute, applied in place.
- **Assumption, stated not verified.** Choosing ignore-in-place means the index is a per-machine derived artefact and is no longer synced between machines. The user accepted this. If cross-machine index availability is in fact required, WAL and this whole branch must be revisited. Note that the live `aardvark.db` is currently syncing to Dropbox, confirmed server-side, so this is a change to today's behaviour and not merely a constraint on future work.
- **Failure visibility.** Sync failures must be logged, not only printed to stderr, and must leave a persistent drift marker surfaced by the browse command.
- **Spell-correction engine.** A shipped `en_GB` wordlist plus edit-distance, pure Python, no system dependency. Offer-only and trivially dismissible, because technical jargon and proper nouns will false-positive constantly.

## Decisions so far

<!-- one line per closed ticket -->

- [Verify Dropbox ignore stops the index DB syncing](issues/01-verify-dropbox-ignore.md): `com.dropbox.ignored` works and survives in-place writes and `VACUUM`, but must be applied to a **directory**, because SQLite's `-wal` and `-shm` are created with no attributes and were observed being uploaded, including a stale partial WAL.

- [What are the craft.do API's rate limits?](issues/02-research-craft-rate-limits.md): Craft documents none — 28 operations, all declaring only `200`. Backoff constants must therefore be engineered defaults, and the first real 429's headers must be logged to settle it. Batching exists for folders and documents but **cannot** reach the hot path, so it complements incremental sync rather than replacing it.
- [Which entities must re-sync when one entity changes?](issues/03-index-doc-dependency-closure.md): the closure is exactly **one level deep** — creating an ID dirties only its parent category's index. But the 429s are caused by **unconditional rewriting**, not by the walk: 28 index documents are rewritten every run at 4 API calls each, **112 calls even when nothing changed**. Content comparison alone cuts a run from ~114 calls to ~34 from a single-function change, so scoped syncing is now **deferred behind a measurement**.

- [Which en_GB wordlist ships with aardvark?](issues/05-research-en-gb-wordlist.md): ship the **ESDB/SCOWL `en_GB-ise` size-60** list (828 KB, GPL-3.0-compatible, **+12.3 ms**) plus a hand-rolled distance-1 generator, no new dependency. Latency, not licence, was decisive: `spylls` costs 402 ms and `symspellpy` 1,212 ms to load. **Tokenisation dominates the wordlist choice**, and the sample's 0 false positives hides an **18 per cent rate** on real technical vocabulary, which makes a learned dismissal vocabulary part of the feature.

- [Which directory gets the Dropbox ignore, and how does it get set?](issues/07-which-directory-is-ignored.md): ignore `00_INDEX🗂️` **wholesale** at directory level (file-level misses the `-wal`/`-shm` sidecars). Set by `initialiser` at creation, re-asserted idempotently on every non-completion run in `cl_utils.main` via a `ctypes` libc `setxattr` in a new `aardvark_jd/dropbox_ignore.py`, gated on the root being inside a Dropbox tree. Non-macOS: no-op plus a logged warning. Server-side purge of already-synced data is spun off to [Verify ignore-after-sync behaviour and specify server-side purge](issues/11-verify-ignore-after-sync.md). Unblocks WAL (ticket 08).
- [Do we enable WAL, and what is the concurrency contract?](issues/08-wal-and-concurrency-contract.md): **no WAL** — deliberate decision not to change `journal_mode` from the `delete` default, because the only concurrent accessor is completion's `mode=ro` connection and WAL's sidecar requirement would silently break it. Instead set `PRAGMA busy_timeout = 5000` per-connection on both the writer (`db.get_connection`) and the completion reader. Contract: single short-lived process, one best-effort `mode=ro` reader, writes must not hold a transaction across network I/O (constraint on ticket 09). WAL rides along with the backgrounding fog if that ever opens.

- [When and how does aardvark offer a spelling correction?](issues/06-spell-correction-interaction.md): a per-suspect-token `[y/N]` prompt on **titles only**, shown **before** creation — so the corrected title flows to the folder name, the index row and all three mirrors for free, and the post-hoc rename / repoint branch is designed out — and ahead of the emoji prompt. `N` or bare Enter keeps the title **and** permanently records the token in **one global learned vocabulary** keyed on the token alone, so the feature self-silences on recurring jargon. That vocabulary also mutes the non-TTY path, which otherwise creates as typed and prints a per-token note to stderr, never blocking. New `spell_check: enabled` settings toggle (default true); no per-invocation flag; `init` excluded. Vocabulary storage and per-machine-vs-follows-user is [ticket 10](issues/10-learned-vocabulary-storage.md).

- [Where does the learned per-user vocabulary live?](issues/10-learned-vocabulary-storage.md): a dotfile **`<root>/.aardvark-vocabulary`** — sorted, newline-delimited, lowercase tokens with a hand-editable header comment — created lazily on the first dismissal. It sits beside `00_INDEX🗂️` but outside it, so the Dropbox ignore (ticket 07) does not catch it and it **syncs**: the vocabulary **follows the user**, a deliberate departure from the per-machine index premise, because it records the user's jargon not the machine's. Written atomically on every decline; read/write failure degrades to an empty set with a warning, never raises. Not mirrored, no other consumer, no conflict-copy handling in v1. **With tickets 05, 06 and 10 resolved, the spell-correction half of the destination is fully specified and ready for TDD.**

- [Verify ignore-after-sync behaviour and specify server-side purge](issues/11-verify-ignore-after-sync.md): **Dropbox purges the server-side copy when `com.dropbox.ignored=1` is set on an already-synced directory** — promptly, no local content write needed, verified stable and via three API paths (client v268.4.4072). Reversible, and client-driven not API-driven. **Ticket 07 needs no server-side cleanup code**: the `setxattr` on `00_INDEX🗂️` it already specifies purges the live `aardvark.db` on first assertion. Do **not** add a Dropbox API `files/delete` fallback (redundant, and would delete a `00_INDEX` another machine may still sync). New constraint for ticket 07: the `setxattr` must run in `cl_utils.main` **before** `db.get_connection`, so the ignore lands before any `-wal`/`-shm` is created. Second-machine race window is narrowed, not closed — noted on ticket 07.

## Not yet specified

- **Whether backgrounding opens at all.** Hangs on the measured latency once content comparison lands. Note this fog has shrunk considerably: if comparison alone clears the 500 ms gate, backgrounding and the scope interface collapse together and neither is needed. If backgrounding *does* open, enabling WAL and defining a real concurrent-writer contract come with it (ticket 08 deferred WAL to exactly this trigger).
- **Drift-marker surfacing.** Where the unsynced marker is stored and how the browse command renders it. Partly hangs on the sync-scope interface.
- **Todoist and Google Drive parity.** Whether both adopt the same scope interface and backoff as craft, or whether their rate profiles differ enough to diverge.
- **Whole-space document listing.** `GET /documents` unfiltered returns every document, which could collapse per-folder adoption calls into one. Worth taking only if the closure work does not already remove those calls.
- **Archive and rename paths.** Incremental scope for `archive` and `set_emoji` is likely a different closure from creation. Not sharp until the creation closure is known.

## Out of scope

Ruled beyond this destination while charting. These are sharp, one-session changes that need TDD, not wayfinding, and should be done directly in a separate session.

- **`add_project` completion lists non-project categories.** `commands.py:45` gives `add_project` the generic `category` completer and `completion._categories()` selects every category with no domain filter. Same latent bug in `add_category`'s `area` completer. Out of scope: a sharp bug fix, no decision to make.
- **Show the emoji alongside the PAC code in completion.** The `emoji` column already exists on `areas`, `categories` and `ids`. Out of scope: sharp, no decision to make.
- **Rename `search` to `fd`.** Hard rename, no deprecation shim, agreed while charting. Touches the docopt usage block, `commands.py`, `help_text`, both completion scripts, `open_craft.py` and the README. Out of scope: sharp, no decision to make.
- **Blank line between the A, R and P sections of the browse output.** `search.format_tree()` renders domain headings flush left. Out of scope: sharp, no decision to make.

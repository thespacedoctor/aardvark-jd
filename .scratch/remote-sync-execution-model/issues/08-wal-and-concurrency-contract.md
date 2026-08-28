# Do we enable WAL, and what is the concurrency contract?

Type: grilling
Status: resolved
Assignee: dave (claimed 2026-08-28)
Blocked by: none

## Context from ticket 07 (2026-08-28)

[Which directory gets the Dropbox ignore, and how does it get set?](07-which-directory-is-ignored.md) is resolved, so this ticket is unblocked. The decision: `00_INDEX🗂️` is ignored **wholesale** at directory level, set by `initialiser` and re-asserted idempotently on every non-completion run in `cl_utils.main`. So by the time any WAL connection opens, its containing directory is already ignored and the `-wal`/`-shm` sidecars are safe. The Dropbox hazard is closed; WAL is now purely a concurrency question.

## Question

With the Dropbox hazard closed by ticket 07, is WAL worth enabling, and what concurrency does aardvark actually need?

`db.get_connection()` currently opens with `journal_mode = delete` and sets only `PRAGMA foreign_keys = ON`. Ticket 01 confirmed WAL works fine on the database itself and that its sidecars are safe once the containing directory is ignored.

Decide:

- **Whether WAL is needed at all.** It buys concurrent readers alongside a writer. Today aardvark is a single short-lived process, so the honest answer may be that it buys nothing until and unless backgrounding opens, which is itself still fog pending the latency measurement. Enabling it speculatively would violate YAGNI.
- **The completion path's stake in this.** `completion._with_connection()` opens the index read-only on every TAB keystroke, deliberately avoiding `initialise_schema`. That is the one genuine concurrent reader that exists today. Does it currently risk blocking behind a writer, and would WAL fix a real problem there?
- **`busy_timeout`.** Currently unset, so a lock contention fails immediately rather than waiting. This may be worth setting regardless of WAL, and is a smaller change.
- **Where the pragma is applied.** `get_connection` is the obvious place, but `journal_mode = WAL` is persistent, stored in the database header, whereas `busy_timeout` is per-connection. The read-only completion path must not be the thing that sets it.

If the answer is that WAL is not needed, say so and close it. A decision not to change something is a decision.

## Answer

Resolved 2026-08-28 by grilling.

### Decisions

**1. Do not enable WAL. A deliberate decision not to change `journal_mode`.** It stays at SQLite's default (`delete`). Reasoning:
- aardvark is a single, short-lived process. The only concurrent accessor that exists is shell completion, opening `file:{db}?mode=ro` on every TAB.
- WAL would *risk* that reader rather than help it: a `mode=ro` connection to a WAL database fails when the `-wal`/`-shm` sidecars do not already exist, which is the common case when no writer has run recently. `completion._with_connection` swallows every exception into "no suggestions", so this would be a silent regression, worse than today's transient "blocks during a concurrent write".
- WAL's actual payoff (concurrent reader alongside a long-lived writer) only arrives if backgrounding is adopted, which is still fog pending ticket 09's latency measurement.

**2. Set `PRAGMA busy_timeout = 5000` per-connection, on both paths.**
- In `db.get_connection` (the writer): two `aardvark` commands started at once queue instead of one crashing with `SQLITE_BUSY`.
- In `completion._with_connection`, immediately after `sqlite3.connect` (the reader): a TAB press waits out a concurrent write for up to 5 s instead of instantly returning `None` and offering nothing.
- Per-connection pragma, safe on `mode=ro`, no persistent header change, nothing for the read-only path to set wrong. This is the real fix for the only contention that exists today.

### Concurrency contract

- aardvark is **single-process and short-lived**. There are no background or concurrent writers.
- There is **one concurrent reader**: shell completion, `mode=ro`, best-effort, silently degrades to no suggestions on any error.
- A mutating command may overlap with completion TAB presses. Completion must not be blocked longer than `busy_timeout`.
- **A write must not hold a transaction open across network I/O.** The sync engines are handed the shared connection for the whole command, so they must commit local DB work before making HTTP calls, bounding the write-lock window to actual local writes rather than sync duration. This is a constraint on ticket 09's implementation.
- **Revisit trigger:** if backgrounding is ever adopted (ticket 09 fog), both this contract and the WAL decision are reopened and designed against a real concurrent writer.

### Noted, out of scope for this ticket

`initialise_schema` runs on every non-`init` command and always commits (creates `meta`, runs migrations, drops and recreates the search triggers), so even `av search` takes a brief write lock. A schema-version guard could skip the trigger rewrite when the schema is already current. This is a latency/lock-window optimisation, not a concurrency correctness issue, and is left as fog.

# How does `av add_project` return in under 500 ms?

Type: grilling
Status: resolved
Blocked by: none

## Question

The gate is 500 ms. [Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md) measured **30.7 s** with content comparison in place, down from 56.0 s. What closes the remaining sixty-fold gap?

The measurement rules out the cheap answer. Content comparison did what ticket 03 predicted — craft went from 118 calls to 41, and the 429 stopped — and the command is still thirty seconds. Of that, 29.9 s is network:

| service | calls | network time |
|---|---|---|
| Google Drive | 47 | 13.8 s |
| craft.do | 41 | 13.1 s |
| Todoist | 4 | 1.6 s |
| Dropbox | 2 | 1.4 s |

**Taking craft to zero would still leave about 17 seconds.** At roughly 300 ms per round trip, no reduction in call count alone reaches 500 ms while the CLI waits for the network at all. That is the finding that makes this a decision rather than an optimisation.

Decide:

- **Does the CLI stop waiting for sync at all?** The charting session settled that "backgrounding is not assumed" and reopens only if measured latency exceeds the gate. It does, by sixty times. So this is the moment that premise is revisited.
- If the CLI returns before sync completes, **what does the user see** — and what happens when sync then fails, given the effort already settled that failures must be logged and must leave a persistent drift marker surfaced by browse?
- **What carries the work**: a detached child process, a queued job drained by the next invocation, a daemon? The system is a single short-lived CLI process today, and ticket 08's concurrency contract was written for exactly that shape.
- **What this does to ticket 08.** WAL was deliberately declined on the grounds that the only concurrent accessor is completion's `mode=ro` reader. A background writer outliving the foreground process breaks that premise, and ticket 08 explicitly deferred WAL to this trigger.
- **Whether scoping is still needed** once backgrounding lands, or whether it becomes an optimisation with no deadline. This is what [How do the three sync engines accept a scope?](04-sync-scope-interface.md) now waits on.
- Whether 500 ms is still the right gate for a command that does real filesystem scaffolding, or whether the honest target is "returns promptly and tells the truth about what is still happening".

## Why this blocks ticket 04

Ticket 04 designs the scope interface for all three engines. Whether that interface needs to exist, and whether it needs to be fast or merely tidy, depends on whether the CLI is still waiting for it. Deciding the interface first would be designing for a requirement that may not survive this ticket.

## Context from ticket 13 (2026-08-28)

[What are Google Drive's 47 calls per run, and can they be cut?](13-gdrive-call-cost.md) resolved, and it **does not change this ticket's answer, only its arithmetic**.

Drive has no content-comparison win available — it never had that bug, and is already 45 reads and zero writes on an unchanged run. It has a different win: one OR-ed `files.list` per tree level takes it from 45 calls and 13.8 s to about 5 calls and 2.5 s. Applied, `av add_project` goes from 30.7 s to roughly **19.8 s**.

Against a 500 ms gate that is still forty times over, so **backgrounding remains the only mechanism that meets the gate as stated**, and the question below stands unchanged. Two things it does affect:

- **The honest budget.** Even with both craft and Drive optimised as far as anyone has proposed, the floor is set by round trips to four services in sequence, and the sync order is fixed (`gdrive` -> `todoist` -> `craft`, because each embeds the previous one's URL). No call-count work reaches 500 ms while the CLI waits.
- **The value of finishing sooner.** The Drive change is cheap, confined to two functions, and makes whatever runs in the background finish in a third of the time. If the answer here is backgrounding plus a drift marker, the marker's lifetime is what the user actually experiences, and that is the number the Drive change moves.

So the last sub-question below — whether 500 ms is the right gate, or whether the honest target is "returns promptly and tells the truth about what is still happening" — is now the load-bearing one.


## Answer (2026-08-28)

**The CLI stops waiting.** The seven mutating commands do their local work, spawn the existing repair sync detached, and exit. Recorded as [ADR 0001](../../../docs/adr/0001-mutating-commands-hand-sync-to-a-detached-process.md), because it changes what `av add_project` promises and a future reader will otherwise wonder why a mutating command does not sync.

### The gate survives, restated

500 ms stands, but as **local work plus handoff**, not as end-to-end sync. The original reading was never achievable and pretending otherwise made it unfalsifiable: four services in a fixed sequence at roughly 300 ms a round trip is a floor no call-count work approaches. Content comparison (ticket 09) and Drive's OR-ed listing (ticket 13) together take the command to about 19.8 s, and that is the optimised case.

### What was decided

**Carrier.** A detached child running `av craft_sync`, which already runs `gdrive -> todoist -> craft` in the mandated order (`cl_utils.py:197-200`). **One spawn, not three, and no new sync code path.** A launchd agent was rejected as macOS-only and too large a commitment before the drift marker has shown whether unattended retry is needed; it remains the upgrade path. Draining a queue on the next invocation was rejected because it relocates the 20 seconds onto an unrelated later command and leaves mirrors stale for as long as the CLI goes unused.

**Which commands.** Seven background: `add_project`, `add_area`, `add_category`, `add_id`, `set_emoji`, `repair_emoji`, `archive`. Seven foreground: the three explicit `*_sync` commands and the four `connect_*` commands. `init` syncs nothing.

The `connect_*` split is deliberate and is the one that took argument. Those commands run a **first full backfill into an empty mirror** — the largest, slowest sync the system ever performs, and by this map's own premise *"a full backfill can always hit the limit"*. Backgrounding the run most likely to fail, at the exact moment the user is trying to confirm a connection works, is backwards: you would authorise craft, get an instant prompt back, and learn hours later from a drift marker that the backfill died.

**Scripting.** An explicit `--wait`, which skips the spawn and runs in the foreground. **No TTY-sniffing** — that would make the command behave differently under `| tee`, in CI, and in an interactive shell, and it would contradict ticket 06's stated position that a non-TTY changes *prompting* but never *semantics*. With `--wait`, exit non-zero if any mirror failed; without it, exit on local success alone, since the outcome is not known when the process exits. That non-zero needs documenting precisely: it does **not** mean the command failed, because the folder, the index row and the JD code all exist. It means the entity was created and a mirror did not sync.

**Concurrency, and what it does to ticket 08.** At most one sync at a time, on a single lock. A mutation arriving while a sync runs sets a pending flag and exits; the running sync re-checks that flag on completion and goes round again. Not a queue — a whole-tree repair subsumes every mutation made during the previous run, so one pending slot is sufficient and the loop drains as soon as the user stops typing. It cannot outrun a human typist.

**So ticket 08 survives untouched, and WAL stays declined.** That was the live risk going in: ticket 08 declined WAL specifically because "the only concurrent accessor is completion's `mode=ro` reader", and a background writer outliving the foreground process threatened exactly that premise. Serialising restores it. Overlapping writers were rejected as the expensive answer that buys nothing, since the second sync would redo the first's work regardless.

**Lock placement.** A lockfile beside `aardvark.db` inside `00_INDEX🗂️`, carrying pid and start time. That directory is per-system by construction and per-machine for free, because ticket 07 makes it Dropbox-ignored. **This is now a second thing that silently depends on ticket 07 landing** — if the ignore is ever reverted, a lockfile begins syncing between machines, which is a genuinely confusing failure. Noted on ticket 07's dependants rather than left implicit.

A stale lock is the **worst available failure on this map**: it would stop syncing silently and permanently, fixed only by deleting a file the user does not know exists. So a lock is stale when its pid is no longer alive, with an age cutoff as a backstop against pid reuse. The cutoff is a named constant, not a literal. The drift marker is what makes a broken lock visible, so the two mechanisms cover each other.

**Failure visibility.** A per-mirror drift marker in the index: last success and last failure, with reason, for each of the three mirrors. Not per-entity — the carrier is a whole-tree run that either completes or does not, so per-entity markers would be fiction. Not per-system either, because partial failure is real: Drive can succeed while craft 429s, since they run in sequence. Cleared by the next successful run of that mirror.

`browse` renders the detail, and **the next command prints a one-line warning if the last sync failed**. Relying on `browse` alone would leave a failed sync invisible until the user happened to run the one command that shows it.

This is a smaller change than it sounds, and that is worth stating: all three `_maybe_sync_*` helpers **already** downgrade failures to warnings, because "the filesystem + SQLite mutation that triggered it has already succeeded and remains the source of truth". Sync was already best-effort and already fallible. Backgrounding does not introduce a new failure mode; it moves where an existing one is reported, and finally makes it persistent.

### What this closed

**[How do the three sync engines accept a scope?](04-sync-scope-interface.md) is ruled out of scope.** With a whole-tree repair sync doing the work off the critical path, scoping buys only a faster background job — and ticket 13's OR-ed `files.list` buys more of that, more cheaply, from two functions in one module. Backgrounding removed the deadline that made scoping urgent; ticket 13 removed most of the payoff that made it attractive.

**The glossary was describing a design that will now never exist.** `CONTEXT.md` defined a *fast-path* sync as one that "follows a single mutating command and touches only what that command changed". With scoping out of scope, no such thing will ever be built. The entry has been deleted and replaced with the distinction that is actually real — background versus foreground sync — and `drift` and `drift marker`, used throughout this map but absent from the glossary entirely, have been added.

### What is left

One thing: **backoff**, now [Retry and backoff across the three mirrors](14-retry-and-backoff.md). It is the last item the destination explicitly requires that nothing has decided, and backgrounding sharpens it — a retry that nobody is watching is a different proposition from one that happens in front of a user.

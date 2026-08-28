# Measure `av add_project` after content comparison lands

Type: task
Status: claimed
Blocked by: none

## Question

Does index-content comparison alone bring `av add_project` under the 500 ms gate, and is the scoped sync interface therefore unnecessary?

This is the one deliberate piece of execution on this map. Wayfinder plans rather than does, but this task earns its place because a **decision** waits on its result: whether [How do the three sync engines accept a scope?](04-sync-scope-interface.md) survives or is ruled out of scope.

### The work

Implement the three decisions recorded in [Which entities must re-sync when one entity changes?](03-index-doc-dependency-closure.md), following the project's TDD rules, test-first with coverage at or above 80 per cent:

- `_write_index_content()` reads existing content, compares it against the computed markdown, and returns early when identical.
- When the content rewrite is skipped, the `.00_index` link-row rewrite is skipped too, rather than being forced.
- A test pins the coupling between the two, in both directions: skipping content but forcing the link row would silently reintroduce most of the cost, and skipping the link row when content *did* change would corrupt it.

Note that comparison needs a like-for-like form. `_write_index_content` builds markdown, but `get_block` returns structured content items, so the comparison must either render the existing blocks back to markdown or compare on a normalised form. Getting this wrong in the safe direction means never matching, and silently retaining today's cost while appearing to work — so the test must assert the skip actually happens on an unchanged run, not merely that output is correct.

### The measurement

With the change in place, measure on the live system:

- Wall-clock for `av add_project` into an existing project category, warm and cold.
- Actual API call count per run, before and after. The baseline to beat is roughly 114 calls, of which 112 hit `/blocks`.
- Whether any 429s still occur during a normal single-project run.
- Wall-clock for a full `av craft_sync` repair run, since that path also benefits.

### The decision it unblocks

- **Under 500 ms:** close [How do the three sync engines accept a scope?](04-sync-scope-interface.md) and rule it out of scope, and record that the backgrounding fog collapses with it.
- **Over 500 ms:** that ticket becomes live, and the measurement tells us how much further there is to go.

Record the measured numbers in the answer either way. They are the evidence the gate decision rests on, and they will also be the baseline for any later work.


## Constraint from ticket 08 (2026-08-28)

The concurrency contract requires that **a write must not hold a transaction open across network I/O**. The sync engines are handed `cl_utils`'s shared connection for the whole command, so the content-comparison change (and any scoped-sync work downstream) must commit local DB writes before making HTTP calls, keeping the SQLite write-lock window to local work rather than sync duration. `PRAGMA busy_timeout = 5000` is now set on both the writer and the completion reader.

## Claimed for a dedicated implementation session (2026-08-28)

Claimed for a fresh Opus session — this is a test-first code change plus a live
measurement, not wayfinding. Resume by naming this ticket to `/wayfinder`
(claim state is irrelevant when the ticket is named explicitly). Run against the
live craft.do space; the user has approved live-service use.

### Implementation plan (from the charting session)

**Approach**

- `craft_sync._write_index_content()` (`aardvark_jd/craft_sync.py:347`): before the
  delete-and-rewrite, read the existing block via `self.client.get_block`, render it
  to the same normalised form as the computed markdown, and return early when they
  match.
- When the content rewrite is skipped, also skip the forced `_write_link_row`
  rewrite — drop the `forceRewrite=True` on that path. The two are coupled:
  `_write_link_row` (line 446, fast path at line 487) only avoids a rewrite when the
  document body was not wiped.
- Per ticket 08: commit local DB writes before the HTTP calls, keeping the SQLite
  write-lock window to local work.

**Key risk**

`get_block` returns structured content items; `_write_index_content` builds
markdown. The comparison needs a like-for-like form. Getting the normalisation
wrong in the "safe" direction means it never matches — silently retaining today's
cost while looking correct. The test must assert the skip **actually happens** on
an unchanged run (e.g. spy on the client, assert zero write calls), not merely
that output is correct.

**Checklist**

1. RED: unchanged category -> `_write_index_content` issues no write call.
2. RED: the content-skip / link-row-skip coupling, asserted both directions.
3. GREEN: implement the comparison + early return.
4. Refactor; coverage >= 80% on the changed code (`test-runner`).
5. Live measurement, recorded in the answer:
   - `av add_project` into an existing project category — wall-clock warm and cold,
     and API-call count, before and after. Baseline ~114 calls (112 to `/blocks`).
   - Whether any 429s occur on a normal single-project run.
   - Full `av craft_sync` repair-run wall-clock.
6. Resolve, and act on the gate:
   - **Under 500 ms:** close [How do the three sync engines accept a scope?](04-sync-scope-interface.md),
     rule it out of scope, record that the backgrounding fog collapses with it.
   - **Over 500 ms:** ticket 04 goes live; the numbers say how far there is to go.

**Note on the spell-check path.** Tickets 06 and 10 add a wordlist load (+12.3 ms,
ticket 05) and an optional prompt to the `add_*` flow. The prompt is human
think-time and does not count against the gate, but take the `add_project`
measurement with the wordlist-load path present, or explicitly note it was measured
without it.

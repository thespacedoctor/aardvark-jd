# Measure `av add_project` after content comparison lands

Type: task
Status: open
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

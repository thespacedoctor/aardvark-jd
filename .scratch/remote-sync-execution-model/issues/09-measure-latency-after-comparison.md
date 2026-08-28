# Measure `av add_project` after content comparison lands

Type: task
Status: resolved
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


## Answer (2026-08-28)

**The gate is missed by roughly sixty times. [How do the three sync engines accept a scope?](04-sync-scope-interface.md) survives** — but the measurement also shows that scoping craft alone cannot close the gap either, so the strategic question moves ahead of it as [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md).

### The measurement

Taken against the live craft.do space, the live Todoist, Drive and Dropbox connections, and the real 28-index-document system. `av add_project P22 <title>` into an existing projects category, and a full `av craft_sync` repair run. Call counts are HTTP requests observed at the `requests.Session` level, so every service is counted the same way.

| | before | after |
|---|---|---|
| `av add_project` wall-clock | **56.0 s** | **30.7 s** |
| `av add_project` craft calls | **118** | **41** |
| `av add_project` calls, all services | 171 | 94 |
| `av craft_sync` wall-clock | 48.4 s, **then died** | 25.3 - 28.5 s |
| `av craft_sync` craft calls | 101, then `429` | **30, every one a read** |
| 429s on a normal single run | **yes** | **none observed** |

Craft calls on an unchanged repair run are now `GET /folders`, `GET /connection` and 28 `GET /blocks`: **zero writes**, confirmed stable across four consecutive runs. Ticket 03 predicted "roughly 34 calls, of which about 30 are reads". The measured figure is 30, all reads.

### The 429 is real, and the baseline reproduced it

The before-run did not merely look slow, it **failed**: `craft API POST /blocks failed (429): {"error":"Rate limit exceeded"}` after 101 craft calls in 48 seconds. No run since the change has hit the limit. The 429 fix is demonstrated, not merely argued.

Two caveats on that, both honest gaps rather than findings:

- **The 429's headers were not captured.** Ticket 02 asked for them, and this was the opportunity. The counting harness was only taught to record response headers *after* that run, and no later run reproduced the limit. The response body was `{"error":"Rate limit exceeded"}`. The harness now captures headers if it recurs, so the next 429 anywhere will settle ticket 02's engineered defaults.
- **A transient `502` on `GET /folders`** aborted one `add_project` run's craft sync entirely. Backoff therefore has to cover 5xx, not only 429. The next run self-healed the missing folder and document, which is the drift repair working as designed.

### Where the 30.7 seconds actually goes

This is the finding that decides the gate, and it is not about craft:

| service | calls | network time |
|---|---|---|
| Google Drive | 47 | **13.8 s** |
| craft.do | 41 | 13.1 s |
| Todoist | 4 | 1.6 s |
| Dropbox | 2 | 1.4 s |

29.9 of the 30.7 seconds is network. Local work is under a second. **Taking craft to zero would still leave about 17 seconds**, because Google Drive is now the single largest component and this change did not touch it. Scoped syncing of craft alone therefore cannot reach 500 ms; nothing that only reduces call *counts* can, at roughly 300 ms per round trip.

Measured **without** the spell-correction path, which is not implemented yet. Its +12.3 ms wordlist load (ticket 05) is noise at this scale and does not affect the gate decision.

### The change

`craft_sync._write_index_content()` reads the existing block, compares it against the computed listing, and returns `False` without writing when they match. Both call sites pass that return value straight through as `_write_link_row`'s `forceRewrite`, which is the coupling ticket 03 required.

The comparison matches on the **tail** of the document, because an index document's content is always `[link row] + [one block per index line]` — the body is appended at the end and the link row is then prepended at `position="start"`. Matching the tail keeps the comparison ignorant of what a link row looks like, and a guard of "at most one block ahead of the body" means any other stray content fails the comparison and forces a rewrite, preserving the drift repair a full sync exists to do.

Ticket 08's constraint is already satisfied on this path: `db.upsert_craft_link` commits at `db.py:909`, so no SQLite write lock is held across HTTP.

### The normalisation trap the ticket warned about, found live

The ticket predicted that getting the comparison's form wrong would fail silently in the safe direction. It very nearly did, in a narrower form that only measurement could catch.

**Craft strips trailing whitespace when it stores a block.** The listing format is `- [code title](url) — {description}`, so a child with an **empty description** is sent as `... — ` and comes back as `... —`. Those lines never compare equal, so their index documents rewrite on **every single run, forever**. Two of the 28 documents behaved exactly that way after the first fix, and only converged once the comparison normalised with `rstrip` on both sides.

This was not an edge case: **`add_project` always stores an empty description** (`add_project.py`, `db.insert_id(..., title, "", ...)`), so every projects category was affected. Unit tests alone would not have caught it — the fake client had to be taught the real API's behaviour first. `test_an_index_entry_with_no_description_still_converges` now pins it.

Related, and left alone deliberately: a description-less entry renders with a **dangling em-dash**, `- [P22.13 zz latency probe one](url) —`. That is pre-existing cosmetic behaviour, not a comparison problem, and changing the rendered output is a separate decision. Noted under Out of scope on the map.

### Test-infrastructure correction

`FakeCraftClient` was unfaithful to the real API in exactly the dimension this change depends on, which would have made the new tests vacuous. Its docstring claimed it modelled per-line splitting; it did not. Three corrections, all verified against the live space:

- `add_block` now splits multi-line markdown into **one block per line**, as `POST /blocks` does.
- `position="start"` now actually prepends. It was previously ignored, so the fake put link rows **last** — the opposite of the real document shape the comparison relies on.
- Stored markdown is `rstrip`ped, as Craft does.

`test_craft_sync_is_idempotent` previously asserted the *cost of the old behaviour* (two deletes and two adds per index document per run). It now asserts the opposite, which is the point of the change: a repair run over an unchanged tree writes nothing at all.

Full suite: **454 passed**. Coverage on `craft_sync.py`: **96%**. One unrelated pre-existing failure, `test_cl_utils.py::test_main_end_to_end`, fails only under `--cov` and fails identically on a pristine tree.

### New finding: delete-before-insert is not crash-safe

`_write_index_content` deletes a document's whole content before inserting the replacement, so a failure in that window leaves the document **empty**. The baseline 429 landed on the link-row POST rather than the content insert, so nothing was lost — verified by scanning all 28 live index documents afterwards, none empty — but the window is real and a rate limit is exactly the thing that lands in it.

Content comparison narrows the exposure from all 28 documents on every run to only the ones that actually changed, but it does not close it. Recorded as fog on the map rather than a ticket, because the fix is entangled with the backoff design that ticket 02 left as engineered defaults.

### The gate decision

**Over 500 ms, by a factor of about sixty.** Per this ticket's own rule, [How do the three sync engines accept a scope?](04-sync-scope-interface.md) goes live rather than being ruled out of scope, and the backgrounding fog **opens**.

The measurement sharpens both, though, and reorders them. Scoping is no longer sufficient on its own: it addresses craft's 28 reads, worth about 13 seconds, and leaves Drive's 47 calls and 13.8 seconds untouched. So the strategic decision — whether the CLI returns promptly by backgrounding, by scoping every mirror, or by both — comes first, as [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md), which now blocks ticket 04. Google Drive's cost gets its own ticket, [What are Google Drive's 47 calls per run, and can they be cut?](13-gdrive-call-cost.md), since it is now the largest single component.

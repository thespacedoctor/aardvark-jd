# What are Google Drive's 47 calls per run, and can they be cut?

Type: research
Status: resolved
Blocked by: none

## Question

[Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md) found that Google Drive costs **47 HTTP calls and 13.8 s** on every `av add_project` and every `av craft_sync` — now the **largest single component** of the command, ahead of craft's 41 calls and 13.1 s.

The whole effort has been aimed at craft, because craft was the one returning 429s. Drive never failed, so it was never looked at, and it was quietly just as expensive all along. Its 47 calls barely move between a repair run and a create run (46 vs 47), which is the signature of an unconditional whole-tree walk — the same shape ticket 03 found in craft.

### The work

- Instrument `gdrive_sync` the way ticket 09 instrumented craft: what are the 47 calls, by endpoint, and how many are reads against writes?
- Is there an unconditional-rewrite equivalent of the craft index-document problem, where the same content is written back every run?
- What are Drive's documented rate limits, and how close does 47 calls per mutating command sit to them? Craft's limits turned out to be undocumented; Drive's are published, so this should be answerable from primary sources.
- Does Drive support batching, and would it reach the hot path — the question that batching failed on for craft in ticket 02?
- The same two questions for Todoist, which is cheap today at 4 calls and 1.6 s, so that the parity question can be answered on evidence rather than assumed.

### What this feeds

The Todoist and Drive parity fog, and [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md): if Drive turns out to have a content-comparison win as large as craft's, the arithmetic on the gate changes and backgrounding may carry less weight than the measurement currently suggests.


## Answer (2026-08-28)

**There is no unconditional-rewrite bug in Drive.** A steady-state run is **45 `files.list` calls and zero writes** — already the state ticket 09 had to drag craft to, reached for free because `_ensure_folder` has always compared against the live listing before creating. Full findings at [`research/gdrive-call-cost.md`](../research/gdrive-call-cost.md). Code-level claims were reproduced offline against the real `gdrive_sync.get()` before acceptance.

### The headline

The 47 calls are the *other* half of the problem: an **unconditional whole-tree walk at one list call per interior node**. Forty-five interior folders, forty-five calls, every run. Ticket 03 concluded the walk was not what hurt craft; for Drive the walk is the entire cost, and it scales with the shape of the tree rather than with what changed — every new category adds a call to every future run, forever.

**The premise the design rests on is wrong.** `gdrive_client.list_child_folders()`'s docstring says "Drive has no cheap whole-tree listing, so the sync indexes one parent at a time". Drive has no *recursive* query, true, but `files.list`'s `q` accepts `or`, so **a whole tree level lists in one call**. Measured live and read-only: the entire 163-folder aardvark subtree walks in **5 calls and 2.5 s**, against today's 45 calls and 13.8 s. Same information, same adoption semantics.

### The 47, accounted for to the call

| | count |
|---|---|
| OAuth refresh-token exchange | 1 |
| `GET /files` — one listing per interior folder | 45 |
| writes on an unchanged run | **0** |
| repair-run total | **46** |
| `add_project`, plus one `POST /files` for the new ID folder | **47** |

Depth 0 the Drive root, depth 1 the workspace folder, depth 2 the three domain roots, depth 3 sixteen area and domain-system folders, depth 4 twenty-four category and area-system folders. Derived twice independently — by driving the real sync against a fake Drive with **no network and no mutation**, and by arithmetic over the live tree — and both reproduce the measured 46 and 47 exactly.

The only unconditional rewrite is **local**: `db.upsert_gdrive_link` fires 158 times a run, each with its own `commit()`. Not the cost driver, but it is what keeps ticket 08's "no transaction across network I/O" contract satisfied, by accident rather than design. Tidying those into one transaction would silently break it — worth a test.

### Rate limits: not close, and not the argument

Drive's limits **are** published, unlike craft's. Per minute per user per project, **325,000 quota units**; per minute per project, **1,000,000**. A `files.list` costs **100 units**, so a run costs **4,500** — about **1.4 per cent** of the per-user budget, or **72 full syncs a minute** before anything throttles.

**So Drive never returned a 429 because Drive was never going to.** The 47 calls are a latency and tidiness problem, not a rate-limit one, and should not be argued for on rate-limit grounds. Two things do carry over, though. Drive's rate-limit signal is primarily a **`403 userRateLimitExceeded`**, not a 429, so a backoff policy keyed on 429 alone would miss it — and 403 is otherwise a never-retry code. And the May 2026 quota model adds a **daily billing threshold in quota units**, which turns `files.list`'s 100 units against `files.get`'s 5 into a cost that eventually maps to money.

`GDriveClient._request()` has no retry and no backoff, exactly like `CraftClient._request()`. The difference is that **Google publishes the prescribed algorithm**, so unlike ticket 02's craft constants these need not be invented.

### Batching: the mirror image of ticket 02

For craft, batching existed but could **not** reach the hot path. For Drive it is the opposite, and the answer is still no.

Drive's batching is real and current — `/batch/drive/v3`, 100 calls per batch, no deprecation notice, and the 2019 global-endpoint turndown does not touch it. `files.list` is metadata, so the media exclusion does not bite, and the walk is only five levels deep, so **45 calls would collapse to 5 batches**. It reaches the hot path.

It is nonetheless **strictly dominated**, because Google states plainly that *"a set of n requests batched together counts toward your usage limit as n requests, not as one request"*. Five batches of 45 inner calls still cost 4,500 units. The OR-ed query reaches the same five round trips **and** costs 500, because it is genuinely five list operations rather than forty-five in an envelope — and it needs no hand-rolled multipart assembly in a client whose stated reason for existing is that it needs four endpoints and no SDK. **Do not implement Drive HTTP batching.**

### The negative result that kills the obvious alternative

The tempting fix is one query for every folder in the Drive, rebuilding the tree client-side from `parents`. **Measured, and it is no better than today:** the user's Drive holds **2,160 folders**, which paginates into **5 pages and 13.9 s** — the same wall-clock as the current 45 calls, for a payload thirteen times larger than needed. The win comes from **scoping the query to the subtree**, which OR-ed parents does and a global `mimeType` filter cannot.

Two constraints on the recommended approach, stated rather than discovered later: the widest level produced a **5,220-character `q`** and worked, but Drive publishes no explicit URL-length limit for a plain `files.list`, so chunking parents at ~50 per query should be built in from the start; and a level's results must follow `nextPageToken`, as the existing code already does.

### Todoist: cheap for structural reasons, and the reference implementation

Its 4 calls are now accounted for individually — **2** paginated `GET /projects` (measured live: 70 projects, 2 pages, 502 ms), **1** create, **1** description write. It is cheap because it already does both of the things the other two mirrors lack: **one whole-account listing instead of a walk**, and **content comparison before writing**. On an unchanged repair run it issues 2 calls and nothing else; all 40 mirrored entities skip. Its limits are published — **1,000 partial syncs per user per 15 minutes** — and aardvark uses 0.4 per cent of that. Its Sync API batches up to 100 commands and Todoist says a batch "still counts as one", which is better than Drive's quota-neutral batching, but there is no hot path left to reach.

**One real asymmetry, and it is correctness rather than cost.** Todoist compares against the **local** cache, whereas craft's new comparison and Drive's adoption both compare against the **remote**. So Todoist is cheaper *and* weaker: a description edited by hand in Todoist is never repaired, because the local cache still matches what aardvark last wrote. That should be a recorded decision for the parity question, not an artefact.

### What this does to the gate

**Nothing, and the ticket's speculation should be closed off.** There is no content-comparison win available, because Drive never had the bug; the available win is a different one. And it is not large enough: Drive goes from 13.8 s to roughly **2.9 s**, taking `av add_project` from 30.7 s to about **19.8 s** against a 500 ms gate. [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md) is unaffected, and backgrounding remains the only mechanism that meets the gate as stated.

What it does change is the **ordering**. This is a 9x call reduction and an 11-second saving from a change confined to two functions in one module, with no new state, no dependency-closure reasoning and no risk to adoption semantics — markedly cheaper to implement than scoped syncing of craft, and it does not compete with backgrounding. It makes whatever runs in the background finish sooner, which is what a drift marker's lifetime depends on.

### Recommendations

1. **One OR-ed `files.list` per tree level**, chunked at ~50 parents. 45 calls to 5-8, 13.8 s to ~2.5 s, 4,500 quota units to ~800. Correct the `list_child_folders` docstring in the same change.
2. **Do not implement Drive HTTP batching** — real, reaches the hot path, and strictly dominated by (1).
3. **Extend ticket 02's backoff to `GDriveClient._request`, keyed on 403 as well as 429.**
4. **Pin the per-upsert `commit()` with a test**, so ticket 08's contract is not tidied away.
5. **Leave Todoist's cost alone; decide its local-versus-remote comparison deliberately.**
6. **Consider caching the OAuth access token across invocations** — 1 call and ~170 ms of every run — weighing it as a credential-storage decision rather than a free win.

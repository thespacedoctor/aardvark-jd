# What are Google Drive's 47 calls per run, and can they be cut?

Research answer for [issues/13-gdrive-call-cost.md](../issues/13-gdrive-call-cost.md). Researched 2026-08-28.

## Answer

### Summary

**There is no unconditional-rewrite bug in `gdrive_sync`.** A steady-state run issues **45 `files.list` calls and zero writes**, which is exactly the state `craft_sync` was dragged to by ticket 09. Drive got there for free, because `_ensure_folder` has always compared against the live listing before creating. The 47 calls are not craft's problem wearing a different hat.

They are the *other* half of the problem: an **unconditional whole-tree walk that lists one parent per interior node**. Forty-five interior folders, forty-five list calls, every run, regardless of what changed. Ticket 03 concluded the walk was not what was hurting craft. For Drive the walk is the entire cost.

The load-bearing finding is that **the premise the design rests on is wrong**. `gdrive_client.list_child_folders()`'s docstring states "Drive has no cheap whole-tree listing, so the sync indexes one parent at a time". Drive has no *recursive* query, which is true, but `files.list`'s `q` parameter accepts `or`, so **an entire tree level lists in a single call**. Measured live against the real Drive, read-only: the whole 163-folder aardvark subtree walks in **5 HTTP calls and 2.5 s**, against today's 45 calls and 13.8 s. Same information, same adoption semantics, **9x fewer calls, 5.5x less wall-clock, 9x less quota**.

On batching, the answer is the opposite shape to craft's. **Drive's HTTP batching is real, current and would reach the hot path** — `files.list` is batchable and the walk is only five levels deep. But it is the *worse* of the two options, because Google states plainly that a batch of *n* counts as *n* requests against quota, whereas the OR-ed query collapses a whole level into **one** request costing **one** list's quota. Batching buys round trips only. The query language buys round trips and quota both.

None of this closes the 500 ms gate. Drive at ~2.7 s instead of 13.8 s leaves `av add_project` around 19 s. Ticket 09's conclusion stands unchanged.

### Sources consulted

| Source | Type | Verdict |
|---|---|---|
| `https://developers.google.com/workspace/drive/api/guides/limits` | Primary — Google's Drive API usage limits page | **Authoritative.** Quotas, per-method unit costs and the May 2026 transition notice, quoted verbatim below |
| `https://developers.google.com/workspace/drive/api/guides/performance` | Primary — Drive API "Improve performance", which carries the batch-requests section | **Authoritative.** Batching supported, 100 calls per batch, no quota relief |
| `https://developers.google.com/workspace/drive/api/guides/search-files` | Primary — supported `q` query terms | Confirms `mimeType`, `trashed` and `'id' in parents` as standalone terms |
| `https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list` | Primary — method reference | `pageSize` maximum 1,000 |
| `https://developers.google.com/workspace/drive/api/reference/rest/v3/files` | Primary — Files resource | `parents` is a normal readable field, requestable in a fields mask |
| `https://developers.google.com/workspace/drive/api/guides/handle-errors` | Primary — error reference | `userRateLimitExceeded` (403), `rateLimitExceeded` (403 and 429), exponential backoff prescribed |
| `https://developers.google.com/workspace/drive/api/guides/manage-changes` | Primary — changes feed | `changes.getStartPageToken` / `changes.list` delta model |
| `https://developer.todoist.com/api/v1/` | Primary — Todoist API v1 reference, "Request limits" section | **Authoritative.** Todoist's limits *are* published, unlike Craft's |
| `aardvark_jd/gdrive_sync.py`, `gdrive_client.py`, `todoist_sync.py`, `todoist_client.py` | Primary — this repo's source | Read in full |
| The live index DB, `mode=ro`, and three read-only live probes | Primary — measurement | Reproduces the measured 46 and 47 exactly |

Method note. Google's docs pages are JavaScript-heavy, so the quota and batching pages were fetched with `curl` and stripped to text rather than read through a summariser; every figure quoted below is a verbatim string from the page body. The call counts were derived twice and independently: once by driving the real `gdrive_sync.get()` against an in-memory fake Drive and a copy of the live index, with **no network and no mutation**, and once by arithmetic over the live tree shape. Both give 45. The level-wise timings are live but strictly read-only: one `files.list` per level, no `create`, no `update`, no `PATCH`.

---

## 1. What the 47 calls actually are

**DOCUMENTED (verified in code and reproduced offline).**

A steady-state `av gdrive_sync` repair run issues:

| call | count |
|---|---|
| `POST https://oauth2.googleapis.com/token` (refresh-token exchange) | 1 |
| `GET /drive/v3/files` (one listing per interior folder) | 45 |
| writes of any kind | **0** |
| **total at the `requests.Session` level** | **46** |

`av add_project` adds exactly one `POST /files` to create the new ID's folder: **47**. That is the whole of the 46-versus-47 gap ticket 13 flagged, and it is now accounted for to the call.

The 45 listings are `_children(parentId)` (`gdrive_sync.py:229`), which is memoised per parent for the life of the sync, so each interior folder is listed exactly once. The parents are, by depth:

| depth | what is listed | calls |
|---|---|---|
| 0 | My Drive root | 1 |
| 1 | the `aardvark` workspace folder | 1 |
| 2 | `02 PROJECTS🚀`, `03 AREAS🧭`, `04 RESOURCES📚` | 3 |
| 3 | 13 area folders + 3 domain `00-09 system⚙️` folders | 16 |
| 4 | 11 category folders + 13 area `system⚙️` folders | 24 |
| | **total** | **45** |

`01 INBOX` and `09 ARCHIVE` are created but never descended into, ID folders are leaves, and the three retained reserved subfolders (`01_inbox`, `04_templates`, `09_archive`) are leaves. `00_INDEX` is deliberately not mirrored at all.

So the count is **one call per interior node**, and it scales with the *shape* of the tree, not with what changed. Every new category adds one call to every future run, forever. Every new area adds two.

### Reads against writes

**45 reads, 0 writes, on any run where nothing changed.** This is the single most important thing to record, because it is the opposite of what the ticket's framing predicted.

`_ensure_folder` (`gdrive_sync.py:251-283`) reads the parent's listing, and calls `create_folder` **only** when `name not in children`. There is no delete-and-rewrite, no unconditional `PATCH`, no equivalent of `_write_index_content`. Drive is the mirror that was already doing what ticket 09 had to retrofit into craft.

Verified by construction: driving the real `gdrive_sync.get()` twice against a fake Drive gives `folders_created: 158` on the cold run and `folders_created: 0` on the second, with 45 list calls and nothing else.

## 2. Is there an unconditional-rewrite equivalent?

**Not over the network. There is one in the local database, and it is cheap.**

**DOCUMENTED.** `_ensure_folder` calls `db.upsert_gdrive_link` unconditionally for every entity it touches — **158 times per run** — and `upsert_gdrive_link` (`db.py:1106-1133`) ends in its own `dbConn.commit()`. So a run that changes nothing still performs 158 SQLite upserts and 158 commits, refreshing `synced_at` on every row.

Two things follow, and they pull in opposite directions:

- It is **not** the cost driver. Ticket 09 measured local work at under a second for the whole command across all four mirrors. This is local disk, not 300 ms of network, and it is not what the ticket was looking for.
- It **does** satisfy ticket 08's concurrency contract, and does so by accident rather than by design. Because each upsert commits immediately, no SQLite write lock is held across the HTTP calls that surround it. Anything that later batches these writes into one transaction for tidiness would **break** that contract, since the transaction would then span the whole network-bound walk. Worth pinning with a test before anyone tidies it.

**INFERRED:** the `synced_at` churn is harmless today but is a missed opportunity — a stored `synced_at` plus a stored `gdrive_folder_id` is most of what a timestamp-skip repair path would need.

## 3. Drive's documented rate limits, and how close 47 sits to them

**DOCUMENTED, verbatim from Google's usage-limits page.**

> As of May 1, 2026, the usage limits for this API were updated. Google Cloud projects that made any use of this API between November 2025 and April 2026 will continue with their previously set usage quotas. Cloud projects created on or after May 1, 2026 are subject to the new API quotas.

> Limits are defined in terms of quota units, an abstract unit of measurement representing Google Drive resource usage.

| Usage limit type | Limit |
|---|---|
| Per minute per project | 1,000,000 quota units |
| Per minute per user per project | 325,000 quota units |
| Per day per project | 1 TB |

| Threshold limit type | Limit |
|---|---|
| Per day per project (billing) | 400,000,000 quota units |

| Action | Quota units |
|---|---|
| Read items, such as `files.get` | 5 |
| **List items, such as `files.list`** | **100** |
| Download items, such as `files.download` | 200 |
| Edit items, such as `files.update` | 50 |
| Other actions, such as `files.generateIds` | 5 |

> If you exceed a quota, you'll receive a `403: User rate limit exceeded` HTTP status code response. Additional rate limit checks on the Drive backend might also generate a `429: Rate limit exceeded` response. If this happens, you should use an exponential backoff algorithm and try again later.

> Provided you stay within the per-minute quotas, there's no limit to the number of requests you can make per day.

### The arithmetic

A run costs **45 × 100 = 4,500 quota units** (the OAuth token exchange is against `oauth2.googleapis.com`, not the Drive API, and does not consume Drive quota; a `files.create` adds 50).

| | per run | limit | headroom |
|---|---|---|---|
| Per minute per user per project | 4,500 units | 325,000 units | **72 full syncs per minute** |
| Per minute per project | 4,500 units | 1,000,000 units | **222 full syncs per minute** |
| Per day per project, before billing | 4,500 units | 400,000,000 units | **~89,000 syncs per day** |

**Aardvark sits at roughly 1.4 per cent of the per-user per-minute quota per run.** You would have to run `av add_project` about **once every 0.8 seconds, continuously, for a minute** to be limited. This is a single-user CLI invoked by hand.

**Verdict: not remotely close.** Drive never returned a 429 in ticket 09's measurements because Drive was never going to. Unlike craft, the 47 calls are a **latency** problem and a tidiness problem, not a rate-limit problem, and they should not be argued for on rate-limit grounds.

Two honest caveats:

- **INFERRED, not verified:** which quota regime aardvark's Cloud project is actually under. The May 2026 notice grandfathers projects that used the API between November 2025 and April 2026 onto their previous quotas, which were expressed as a plain request count rather than in quota units. The authority is the project's own Quotas page in the Google Cloud console, which was not consulted. It does not change the conclusion: under either model the headroom is three orders of magnitude, and the difference between "1.4 per cent" and some other small percentage is not decision-relevant.
- **DOCUMENTED and newly relevant:** the May 2026 model introduces a **daily billing threshold** measured in quota units. That makes `files.list`'s **100 units against `files.get`'s 5** a cost that eventually maps to money rather than merely to politeness. Cutting 4,500 units per run to 500 is now a small financial argument as well as a latency one. Not urgent at this volume; worth recording because the pricing detail is stated as "shared later in 2026".

### Backoff

**DOCUMENTED.** Drive returns `403 userRateLimitExceeded`, `403 rateLimitExceeded` and `429 rateLimitExceeded`, and Google's own guidance is truncated exponential backoff with jitter, spelled out step by step on the limits page.

`GDriveClient._request()` (`gdrive_client.py:99-122`) has **no retry, no backoff and no rate-limit awareness**, exactly like `CraftClient._request()`. The difference is that ticket 02 had to engineer craft's constants from nothing, whereas **Google publishes both the failure modes and the prescribed remedy**. Whatever backoff work comes out of ticket 02 should cover Drive too, and for Drive it can cite a source rather than a guess. Note that Drive's rate-limit signal is a **403**, not only a 429 — a retry policy keyed on 429 alone would miss Drive's primary signal, and 403 is otherwise a "never retry" code.

## 4. Does Drive support batching, and would it reach the hot path?

**Yes to both — and it is still the wrong answer.** This is the inverse of ticket 02's craft finding, where batching existed but could not reach the hot path.

**DOCUMENTED, verbatim:**

> The Google Drive API supports batching, to allow your client to put several API calls into a single HTTP request.

> You're limited to 100 calls in a single batch request. If you must make more calls than that, use multiple batch requests.

> There's an 8,000 character limit on the length of the URL for each inner request.

> Google Drive doesn't support batch operations for media, either for upload or download, or for exporting files.

> **Note:** A set of n requests batched together counts toward your usage limit as n requests, not as one request. The batch request is separated into a set of requests before processing.

The batch path is `/batch/drive/v3`. The 2019-2020 turndown of Google's *global* batch endpoint (`www.googleapis.com/batch`) does not affect this: homogeneous batching through API-specific endpoints survived, and the Drive page carries no deprecation notice.

**Would it reach the hot path?** Yes. The hot path is 45 `files.list` calls, and `files.list` is metadata, so the media exclusion does not bite. The walk is data-dependent — a category's Drive id is only known once its area has been listed — so it cannot collapse to one batch, but it **can** collapse to one batch per depth. The tree is five levels deep, and the largest level is 24 calls, comfortably under the 100-call cap. So HTTP batching takes **45 calls to 5**.

**Why it is still the wrong instrument.** Batching is explicitly quota-neutral: five batches of 45 inner `files.list` calls still cost 4,500 quota units. The OR-ed query below reaches the same five round trips **and** costs 500 units, because it is genuinely five list operations rather than forty-five wearing one envelope. Batching also needs multipart/mixed request assembly and response parsing hand-rolled on `requests`, against a client module whose whole stated reason for existing (`gdrive_client.py:6-11`) is that it needs four endpoints and no SDK. The OR-ed query needs a longer `q` string.

**Recommendation: do not implement Drive HTTP batching.** It is strictly dominated.

## 5. The finding that actually matters: one query per level

**DOCUMENTED.** `files.list`'s `q` supports `'<id>' in parents`, `mimeType`, `trashed`, and boolean `or`. `parents` is a normal readable field requestable in a fields mask. `pageSize` maxes at 1,000.

So a whole tree level lists in one call:

```
q      = ('<id1>' in parents or '<id2>' in parents or ...) and mimeType = 'application/vnd.google-apps.folder' and trashed = false
fields = nextPageToken,files(id,name,parents,webViewLink)
```

**MEASURED live, read-only, against the real Drive**, walking down from the `aardvark` workspace folder:

| level | parents OR-ed | child folders returned | time | `q` length |
|---|---|---|---|---|
| 0 | 1 | 5 | 422 ms | 120 chars |
| 1 | 5 | 18 | 673 ms | 320 chars |
| 2 | 18 | 36 | 539 ms | 970 chars |
| 3 | 36 | 103 | 497 ms | 1,870 chars |
| 4 | 103 | 0 (all leaves) | 378 ms | 5,220 chars |
| | **5 calls** | **163 folders** | **2,510 ms** | |

163 folders is exactly the live subtree size, cross-checked independently against a whole-Drive folder dump, so the level walk is **complete, not truncated**.

| | calls | Drive quota | wall-clock |
|---|---|---|---|
| today | 45 lists | 4,500 units | 13.8 s |
| one query per level | 5 lists | 500 units | **2.5 s** |

Adding back the OAuth exchange (168 ms measured) and one `files.create` for `add_project`, Drive's share of the command goes from **47 calls / 13.8 s to roughly 7 calls / 2.9 s**.

The change is confined: a new `list_child_folders_of_many(parentIds)` on `GDriveClient`, and `gdrive_sync` filling `self.childIndex` a level at a time instead of a parent at a time. `_ensure_folder`'s adopt-or-create logic, which is the correctness-critical part, does not move.

### The negative result that kills the obvious alternative

The tempting idea is one query for *every* folder in the Drive — `mimeType = folder and trashed = false` with no parent constraint — reassembling the tree client-side from `parents`. **Measured, and it is no better than today**: the user's Drive holds **2,160 folders**, which paginates into **5 pages and 13,891 ms** at `pageSize: 1000`. Same wall-clock as the current 45 calls, for a payload thirteen times larger than needed.

That is worth recording precisely because it looks like the right answer and is not. The win comes from **scoping the query to the subtree**, which OR-ed parents does and a global `mimeType` filter cannot, since Drive has no recursive `under` operator.

### Two constraints on the OR-ed approach, stated honestly

- **Query length grows with the widest level.** 103 parents produced a 5,220-character `q`, which worked. Drive documents an 8,000-character URL limit for *batch inner requests*; it publishes no explicit limit for a plain `files.list` URL, so the practical ceiling here is **unverified**. Mitigation is to chunk parents into fixed-size groups — 50 per query keeps every URL short and still gives roughly 45 calls to 8. This should be built in from the start rather than discovered when the tree grows.
- **A level's result set is capped by `pageSize`.** At 1,000 per page and 103 children at the widest level, there are three orders of magnitude of headroom, and the code must follow `nextPageToken` regardless — as `list_child_folders` already does.

### The docstring that has to change

`gdrive_client.list_child_folders()` says:

> Drive has no cheap whole-tree listing, so the sync indexes one parent at a time, on demand - see `gdrive_sync._children`.

Half right, and the wrong half is load-bearing. Drive has no *recursive* query, so there is no single call for a subtree. But `q` composes with `or`, so a level costs one call, and the whole tree costs depth-many. The docstring reads as though per-parent listing were forced by the API, and it is not — it is a choice, and a 9x expensive one. Same class of correction as ticket 02's `GET /documents` finding.

### Noted, not recommended: the changes feed

**DOCUMENTED.** Drive publishes `changes.getStartPageToken` and `changes.list`, a proper delta feed: store a token, and a later `changes.list` returns everything that has changed since, in chronological order.

**INFERRED:** it is the wrong tool for this sync. It answers "what changed in Drive", whereas `gdrive_sync` asks "does what I intend to exist already exist" — a question whose answer usually depends on what changed *locally*. It also covers the user's entire Drive by default, and aardvark's mirror is 163 folders of 2,160. It is worth remembering if a drift-detection feature ever appears, and it should not be reached for now.

## 6. The same two questions for Todoist

**Todoist is cheap for structural reasons, not by luck, and it is the design the other mirrors should be measured against.**

**DOCUMENTED (verified in code, and the call count reproduced live).** `av add_project` costs Todoist exactly 4 calls, now accounted for individually:

| call | count |
|---|---|
| `GET /projects` (cursor-paginated; **measured live**: 70 projects over 2 pages, 502 ms) | 2 |
| `POST /projects` (create the new project) | 1 |
| `POST /projects/{id}` (write its description) | 1 |
| **total** | **4** |

Two things make it cheap, and they are precisely the two things Drive and craft lack:

1. **One whole-account listing, not a walk.** `_load_project_index` (`todoist_sync.py:181-193`) calls `list_projects()` once and indexes every project by `(parent_id, name)`. The tree is then walked entirely client-side. This is what section 5 recommends for Drive.
2. **Content comparison before writing.** `_sync_entity` (`todoist_sync.py:238-245`) compares the computed description against the stored one and **returns without an HTTP call** when the project id and description both match. This is ticket 09's craft change, already present in Todoist since it was written.

So: **no unconditional-rewrite bug, and no unconditional walk.** On a repair run over an unchanged tree, Todoist issues 2 calls — the listing — and nothing else. All 40 mirrored entities skip.

**The one real asymmetry, and it is a correctness difference rather than a cost one.** Todoist compares against the **local** cache (`db.get_todoist_link(...)["description"]`), whereas craft's new comparison and Drive's adoption both compare against the **remote**. Todoist is therefore cheaper *and* weaker: a description edited by hand in Todoist will never be repaired, because the local cache still matches what aardvark last wrote. Craft and Drive would repair it. This is a live decision for the parity question — it is a defensible trade, but it should be a choice rather than an accident, because it means the Todoist mirror does not actually self-heal in the way the module's own docstring implies.

### Todoist's rate limits, and its batching

**DOCUMENTED, verbatim from the Todoist API v1 reference, "Request limits":**

> For each user, you can make a maximum of 1000 partial sync requests within a 15 minute period.

> For each user, you can make a maximum of 100 full sync requests within a 15 minute period.

> You can reduce the number of requests you make by batching up to 100 commands in each request and it will still count as one.

> The maximum number of commands is 100 per request.

> There is a 1MiB HTTP request body limit on POST requests.

> Total size of HTTP headers cannot exceed 65 KiB.

> | Type | Limit |
> | Uploads | 5 minutes |
> | Standard Request | 15 seconds |

At 4 calls per command against 1,000 per 15 minutes per user, aardvark uses **0.4 per cent** of the budget. Like Drive, nowhere near.

**Batching: supported, and it would reach the hot path — but there is no hot path left to reach.** Todoist's `/api/v1/sync` endpoint takes a `commands` array of up to 100, including `project_add` and `project_update`, and Todoist states explicitly that a batch **still counts as one** request. That is materially better than Drive's batching, which is quota-neutral. It would matter on a cold backfill, where 40-odd creates and description writes could collapse into one call. On the steady-state path it would save nothing, because content comparison has already reduced the writes to zero.

**Recommendation: leave Todoist alone.** Record it as the reference implementation for the other two mirrors, not as a target for optimisation. The one thing worth revisiting is the local-versus-remote comparison above, and that is a correctness decision, not a cost one.

## 7. What this does and does not do to the 500 ms gate

**It does not close it, and the ticket's speculation that it might should be closed off.**

Ticket 13 asked whether "if Drive turns out to have a content-comparison win as large as craft's, the arithmetic on the gate changes". It does not, for two reasons:

- There is **no content-comparison win available**, because Drive never had the bug. The available win is a different one — collapsing the walk.
- The available win is large but not large enough. Drive goes from 13.8 s to roughly 2.9 s, taking `av add_project` from 30.7 s to about **19.8 s**. The gate is 500 ms.

**INFERRED, and consistent with ticket 09:** at roughly 300 ms per round trip, no call-count reduction reaches 500 ms while the CLI blocks on the network. Even taking all four mirrors to a single call each leaves several seconds. [How does `av add_project` return in under 500 ms?](../issues/12-how-does-the-cli-return-promptly.md) is unaffected by this ticket, and backgrounding remains the only mechanism that can meet the gate as stated.

What this **does** change is the ordering argument. Drive is a 9x call reduction and an 11-second saving from a change confined to two functions in one module, with no new state, no dependency-closure reasoning and no risk to adoption semantics. It is markedly cheaper to implement than scoped syncing of craft, and it does not compete with backgrounding — it makes whatever runs in the background finish sooner, which is exactly what a drift marker's lifetime depends on.

## Recommendations, in priority order

1. **Replace per-parent listing with one OR-ed `files.list` per tree level**, chunking parents at roughly 50 per query. 45 calls to 5-8, 13.8 s to ~2.5 s, 4,500 quota units to ~800. Confined to `GDriveClient` plus `gdrive_sync._children`; `_ensure_folder`'s adopt-or-create logic does not move. Correct the `list_child_folders` docstring in the same change.
2. **Do not implement Drive HTTP batching.** It is real and it would reach the hot path, but it is quota-neutral, costs more to build, and reaches the same round-trip count as (1).
3. **Extend the ticket 02 backoff work to `GDriveClient._request`, keyed on 403 as well as 429.** Drive's rate-limit signal is primarily a `403 userRateLimitExceeded`. A policy that retries only 429 would miss it, and 403 is otherwise a code you must never retry. Google publishes the prescribed algorithm, so unlike craft these constants need not be invented.
4. **Pin the per-upsert commit in `_ensure_folder` with a test.** The 158 commits per run look like something to tidy, and tidying them into one transaction would silently violate ticket 08's "no transaction across network I/O" contract.
5. **Leave Todoist's cost alone; decide its comparison semantics deliberately.** Local-cache comparison makes it the cheapest mirror and the only one that cannot repair remote drift. That should be a recorded decision, not an artefact.
6. **Consider caching the OAuth access token across CLI invocations** — one call and ~170 ms of every run, and every run is a fresh process. Small, and it is a credential-storage decision rather than a free win, since it puts a bearer token on disk. The refresh token already sits in plaintext in `aardvark.yaml`, so it is not a new exposure class, but it should be weighed rather than assumed.

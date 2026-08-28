# What are the craft.do API's rate limits?

Research answer for [issues/02-research-craft-rate-limits.md](../issues/02-research-craft-rate-limits.md). Researched 2026-08-27.

## Answer

### Summary

**Craft publishes nothing about rate limiting.** The Space API's OpenAPI document declares exactly one response per operation — `200` — across all 28 operations. There is no `429`, no error schema, no `Retry-After`, no quota language, and no limits section anywhere in Craft's first-party documentation. The 429 the CLI is hitting in production is real but entirely undocumented, so the limit's shape (requests per interval, and what it is keyed on) **cannot be established without live probing**, which this ticket deliberately did not do.

The one genuinely load-bearing finding is on batching, and it is mixed: **folder and document creation are properly batchable and currently are not batched**, but the dominant cost in `craft_sync` — the per-index-document read/delete/insert — **cannot be batched below one request per document**, because `GET /blocks` takes a single id and `POST /blocks` targets a single parent page. Batching therefore helps, but it does not on its own fix the 429. Incremental sync remains the primary lever, exactly as the map already assumes.

### Sources consulted

| Source | Type | Verdict |
|---|---|---|
| `https://connect.craft.do/api-docs/space` | Primary — the live OpenAPI 3.1.1 spec, `"Craft – Full Space API"` v1.0.0 | Authoritative for shapes; **silent** on limits and errors |
| `https://connect.craft.do/api-docs` | Primary — docs index | Nothing on limits |
| `https://support.craft.do/en/integrate/api` | Primary — Craft help centre | Nothing on limits |
| `https://www.craft.do/imagine/guide/api/api` | Primary — Craft's own API guide | Nothing on limits |
| Web search (rate limits, n8n, MCP, community reports) | Secondary | **No public source anywhere reports Craft's limits** |

The spec is served as an embedded OpenAPI payload inside the docs page. It was fetched and grepped directly rather than read through a summariser, so the negative results below are exhaustive over the document, not an impression of it.

Method note: `429`, `500`, `502` and `503` each appear as substrings in the docs HTML, but every occurrence is a `$R[…]` internal reference index in the embedded payload (e.g. `$R[4429]`), not an HTTP status. Searching the spec for `rate limit`, `retry-after`, `throttl`, `too many` and `quota` returns **zero** matches each.

---

### 1. Published request limits

**Not documented.** No requests-per-interval figure, no statement of what the limit is keyed on, and no distinction between read and write endpoints appears in any Craft source.

What can be said with confidence:

- **DOCUMENTED:** The spec declares only `200` responses. Grepping every `responses:` object in the spec yields 28 operations, each with a single `200` key and no other status code. There is no `components.responses` error section and no schema with `error` in its title.
- **DOCUMENTED:** Every API connection is created per-connection in the app's Connections tab and issues its own unique base URL (`https://connect.craft.do/links/<connectionId>/api/v1`) plus its own token, with per-connection scope over which documents are exposed (support.craft.do). The connection is therefore the natural unit for a limiter to key on.
- **INFERRED (not verified):** Because URL and token are minted together per connection, the limit is most likely keyed on the connection/token rather than the account or the space. This is an inference from the credential model, not a statement by Craft. A space with two connections might get two buckets, or might not — unresolved.
- **INFERRED (weak):** Nothing suggests `POST /blocks` is limited more tightly than reads, but nothing rules it out either. The observed production failure happens to be on `POST /blocks`, which is also simply the endpoint `craft_sync` calls most often on a write-heavy run, so the observation does not discriminate between "writes are limited harder" and "writes are merely more numerous". **Unresolved without probing.**

**Verdict: unresolved.** Requests per interval and the limiter's key can only be settled by live observation.

### 2. Does the 429 carry `Retry-After`?

**Not documented, and unresolved.** The spec never mentions the header, because it never mentions the 429 at all.

Two observations that narrow it:

- **DOCUMENTED (observed in this repo):** The production error body is `{"error":"Rate limit exceeded"}` — a JSON object, captured in the ticket from a real failure.
- **DOCUMENTED (measured):** `connect.craft.do` is fronted by Cloudflare (`server: cloudflare`, `cf-ray` present on the docs host response headers).
- **INFERRED:** Cloudflare's own edge rate-limit block returns an HTML challenge/block page, not a compact JSON body. A JSON `{"error":"..."}` body therefore points at Craft's **application/origin** layer as the limiter, not a Cloudflare edge rule. Application-layer limiters vary widely in whether they set `Retry-After`; many do not.

Consequence for the implementation: **the client must not depend on `Retry-After` being present.** Treat it as an optional optimisation — honour it when present, fall back to exponential backoff when absent. If it is present, it may be in either RFC 9110 form (delay-seconds, or an HTTP-date), so parse both rather than assuming integer seconds.

**Actionable and cheap:** the current `_request()` discards the response headers entirely. Logging the full 429 response headers verbatim on first occurrence would settle this question from ordinary production use, with no probing and no extra load. Recommended below.

### 3. Which other status codes are transient?

**Not documented** — Craft declares no non-200 responses at all, so every claim here is inference from the transport, not from Craft.

Given a Cloudflare-fronted origin, the conventionally transient set applies:

| Status | Retry? | Basis |
|---|---|---|
| `429` | Yes | The observed failure. Rejected before the write was applied, so retry is safe for all methods. |
| `500` | Cautiously | Generic origin fault. May be transient; may be a deterministic bad request. |
| `502`, `503`, `504` | Yes | Cloudflare-to-origin faults — classic transient. `503` may carry `Retry-After`. |
| Connection errors, read timeouts | Yes for reads | Network-level. |
| `400`, `401`, `403`, `404`, `409`, `422` | **No** | Deterministic. Retrying a bad token or a missing id just burns budget. |

**A correctness caveat that matters more than the code list.** `POST /blocks`, `POST /documents` and `POST /folders` are **not idempotent** and the API offers no idempotency key (no such parameter or header anywhere in the spec — DOCUMENTED). So:

- Retrying a **429** is safe for every method: a 429 means the request was rejected, not applied.
- Retrying a **5xx or a timeout on a POST** is *not* safe — the write may well have landed before the error, and a retry duplicates it. A duplicated block is user-visible.

`DELETE /blocks` with explicit ids and every `GET` are idempotent and can be retried freely.

The codebase partly absorbs this already: `_ensure_folder` matches on `(parentFolderId, name)` and `_adopt_document` adopts an existing document by title, so duplicate *folders* and *documents* are self-healing on the next run. Duplicate **blocks** are not self-healing in the same way, though `_write_index_content`'s read-delete-insert does rewrite a document's whole content each run, which would clear them on the following sync.

### 4. Is there any batching?

**Yes, and it is documented — but it does not reach the hot path.** This is the most useful finding, so it is worth separating what helps from what does not.

**DOCUMENTED — real batching, currently unused by the client:**

- **`POST /folders`** takes `{"folders": [...]}` where **`parentFolderId` is a per-item property**. The spec ships an explicit `createMultipleFolders` example creating several folders with mixed parents in one request. `craft_client.create_folder()` sends a one-element array. Folder creation across a whole tree can collapse to **one request per tree depth** (a child still needs its parent's id back before it can be created).
- **`POST /documents`** takes `{"documents": [...]}` with a **single top-level `destination`**. So: many documents per request, but all into one folder. One request per destination folder.
- **`DELETE /blocks`** takes `{"blockIds": [...]}`. **Already batched** — `delete_blocks()` passes the whole content-id list. No win available here.
- Also array-shaped in the spec (unused here): `PUT /blocks`, `PUT /blocks/move`, `DELETE /documents`, `PUT /documents/move`, `DELETE /folders`, `PUT /folders/move`, `POST /tasks`, `POST /comments`, and the `/collections/{id}/items` trio.
- **No `maxItems` constraint appears anywhere in the spec**, so no documented cap on batch size. INFERRED: an undocumented practical cap almost certainly exists — chunk batches (e.g. 50–100 items) rather than sending 382 at once.

**DOCUMENTED — where batching does *not* help, which is the important half:**

- **`POST /blocks` cannot span documents.** Its `position` is a single top-level object requiring one `pageId`. One request writes into exactly one parent page. And because `_write_index_content` already sends an entire index document's markdown as **one** `add_block` call, there is **no remaining win** on the insert side.
- **`GET /blocks` is not batchable at all.** Its `id` parameter is a single string, explicitly mutually exclusive with `date`. Reading N index documents costs N requests. This is the hard floor.

**DOCUMENTED — a separate, easy win found while reading the spec:**

- **`GET /documents` exists and is documented**, which resolves a live uncertainty in the code: `craft_client.list_documents()`'s docstring says it is "**Unverified against a live space** … and may simply not exist". It exists.
- Better, it takes **no** required filter: *"Without location or folderIds filters, returns ALL documents"*, and `folderId` *"includes subfolders recursively"*. So the current one-`GET /documents`-per-folder pattern in `_adopt_document` (line 321) can collapse to **a single whole-space call**, cached for the run — mirroring what `_load_folder_index` already does correctly with its single `GET /folders`.

**Where the volume actually is.** Per index document, `_write_index_content` (lines 374–377) issues three calls unconditionally, with no change detection: `GET /blocks` + `DELETE /blocks` + `POST /blocks`. Multiplied across the tree, that is the hundreds of calls. Batching cannot reduce it, because the read is single-id and the write is single-page. **Only skipping unchanged documents can.** Storing a hash of the intended markdown in `craft_links` and comparing before touching the API takes an unchanged document from three calls to **zero** — and that, not batching, is the fix.

**Net:** batching is worth doing for folder and document creation and for the `GET /documents` collapse, but it is a second-order win. It does not displace the incremental-sync work; it complements it.

---

## Recommended backoff policy

Because the limit is undocumented, this policy is built to be **correct without knowing the numbers**, and to *discover* them from production.

**Answer to the map's open question — backoff is per-request *and* per-run.** Per-request retry alone is unsafe here: a whole-tree walk making hundreds of calls, each retrying four times, can stall for many minutes with no ceiling. A per-run budget is what bounds that.

### Per-request

- **Retry on:** `429`, `502`, `503`, `504`, connection errors and read timeouts. Plus `500` for idempotent methods only.
- **Never retry:** `400`, `401`, `403`, `404`, `409`, `422`. Fail immediately — retrying is pure waste.
- **Method-aware, because there is no idempotency key:**
  - `429` → retry **any** method, including POST. The request was rejected, not applied.
  - `5xx` / timeout → retry `GET` and `DELETE` freely; for `POST`, retry **at most once**, then fail the run rather than risk repeated duplicate writes.
- **Attempts:** 5 total (1 initial + 4 retries) for `429`; 3 total for 5xx and timeouts.
- **Delay:** exponential, base 1 s, factor 2 → 1, 2, 4, 8 s.
- **Ceiling:** 30 s on any single computed wait.
- **Jitter:** **full jitter** — `sleep = random.uniform(0, min(30, 1 * 2 ** attempt))`. Cheap, and it stops a retry train from re-synchronising on a fixed-window boundary.
- **`Retry-After` wins when present.** Parse both RFC 9110 forms (delay-seconds *and* HTTP-date). Sleep the value the server asked for, plus a small positive jitter (0–1 s) — never jitter *below* it, and never let the exponential schedule undercut it. Cap an absurd value at 120 s and fail the run instead of hanging.

### Per-run

- **Cumulative sleep budget: 120 s.** Once total time spent sleeping across the run exceeds this, abort with a clear message rather than sleeping on. This is the guard that keeps the 500 ms latency gate meaningful — a run that has slept two minutes has already failed the user's expectation and should say so.
- **Circuit breaker: 3 consecutive requests that exhaust their retries → abort the run.** Continuing into a limiter that is still closed just deepens the hole.
- **Proactive throttle, not only reactive backoff.** Reactive backoff is the wrong primary tool when you *know* you are about to make hundreds of calls. Add a minimum interval between requests (start at 100 ms, tune once the real limit is known). Combined with incremental sync this should keep the limiter untouched in normal use, leaving backoff as the safety net the map already calls it.
- **Abort must be resumable and visible.** On abort, leave the persistent drift marker the map already requires, and log rather than only printing to stderr.

### Instrumentation (do this in the same change)

`_request()` currently discards response headers. On the **first** `429` of a run, log verbatim:

- the full response header set (specifically any of `retry-after`, `ratelimit-limit`, `ratelimit-remaining`, `ratelimit-reset`, `x-ratelimit-*`, and `cf-ray`),
- the request count and elapsed wall-clock time for the run so far.

That converts every ordinary production 429 into the measurement this ticket could not take without probing, and settles questions 1 and 2 within a few real runs. Revisit the constants above once that data exists — **they are engineered defaults, not Craft's published numbers, because Craft publishes none.**

---

## Documented vs inferred — at a glance

**Documented (verified against Craft's own OpenAPI spec or help centre):**

- The spec declares only `200` responses across all 28 operations; no error schemas, no 429, no `Retry-After`, no rate-limit language anywhere in Craft's first-party docs.
- No idempotency key mechanism exists.
- `POST /folders` batches with **per-item** `parentFolderId`, with a documented multi-parent example.
- `POST /documents` batches, with a **single** top-level `destination`.
- `POST /blocks` batches, but with a **single** top-level `position.pageId` — one parent page per request.
- `GET /blocks` takes a **single** `id` — reads are not batchable.
- `DELETE /blocks` takes an array and is already batched by the client.
- `GET /documents` **exists** (resolving the `list_documents()` docstring's doubt), returns all documents when unfiltered, and `folderId` recurses into subfolders.
- No `maxItems` anywhere in the spec.
- `connect.craft.do` is fronted by Cloudflare.
- Per-connection URL + token credential model.

**Inferred (reasoned, not stated by Craft):**

- The limiter is keyed on the connection/token — from the credential model.
- The limiter sits at Craft's application layer, not Cloudflare's edge — from the JSON error body versus Cloudflare's HTML block page.
- The transient status-code set (`502`/`503`/`504`, cautiously `500`).
- An undocumented practical cap on batch size probably exists.
- Every constant in the backoff policy above.

**Unresolved — settleable only by live probing or by the instrumentation above:**

- Requests per interval, and the interval.
- Whether the limit is per token, per space or per account.
- Whether writes are limited more tightly than reads.
- Whether the 429 carries `Retry-After`, or any `RateLimit-*` headers, and in what units.

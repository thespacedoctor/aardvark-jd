# What are the craft.do API's rate limits?

Type: research
Status: resolved
Blocked by: none

## Question

What does the craft.do Connect API publish about rate limiting, and what does it actually return when limited?

`CraftClient._request()` at `aardvark_jd/craft_client.py:87` has no retry, no backoff and no rate-limit awareness at all: any non-`ok` response is raised immediately as `CraftApiError`, which aborts a sync mid-tree. The observed failure is `craft API POST /blocks failed (429): {"error":"Rate limit exceeded"}`.

Establish, from primary sources and from observation of the live API where the docs are silent:

- The published request limits: requests per interval, whether they are per token, per space or per endpoint, and whether write endpoints such as `POST /blocks` are limited more tightly than reads.
- Whether the 429 response carries a `Retry-After` header, and if so in what units.
- Whether any other status codes are transient and worth retrying, for example 502 or 503.
- Whether the API supports any batching that would let a sync write several blocks in one request, which would reduce call volume independently of the incremental work.

Note that craft.do's API reference has already proven incomplete for this codebase: `craft_client.folder_deep_link()` documents a route read off a copied app link that appears nowhere in the reference. Treat the docs as a starting point, not as authoritative.

The answer feeds the backoff policy, which is currently fog on the map.

## Context pointer

Dispatched to a research subagent on 2026-08-27. Findings will land at `.scratch/remote-sync-execution-model/research/craft-rate-limits.md` and be folded into an `## Answer` section here on completion.

## Answer

Resolved 2026-08-27 by a research subagent. Full findings, including the backoff policy in detail, are at [`research/craft-rate-limits.md`](../research/craft-rate-limits.md). Code-level claims below were independently verified against the source before acceptance.

### The headline

**Craft publishes nothing about rate limiting.** The live OpenAPI 3.1.1 spec embedded at `connect.craft.do/api-docs/space` declares **28 operations, every one of which documents only a `200`**. No error schemas, no 429, no `Retry-After`, no quota language, and nothing in the help centre either. `rate limit`, `retry-after`, `throttl` and `quota` return zero matches. Apparent `429`/`502`/`503` hits in that page are `$R[4429]`-style internal reference indices, not status codes.

Consequently questions 1 and 2 are **unresolved and cannot be settled without live probing**, which was deliberately not done because the account is already being limited.

### The four questions

1. **Published limits: unresolved.** Not documented. Inferred, from the per-connection URL-plus-token model, that the limiter is keyed on the connection. Whether writes are limited harder than reads is undiscriminated by the evidence: `POST /blocks` is both the failing endpoint and simply the most-called one.
2. **`Retry-After`: unresolved; the client must not depend on it.** One useful narrowing: `connect.craft.do` is Cloudflare-fronted, yet the observed 429 body is JSON `{"error":"Rate limit exceeded"}` rather than Cloudflare's HTML block page, so the limiter is Craft's own application layer rather than the edge. Parse both RFC 9110 forms when present, fall back to exponential when absent.
3. **Transient codes: inference only,** since Craft declares no non-200 responses. Retry `429` and `502`/`503`/`504`, cautiously `500`. Never `400`, `401`, `403`, `404`, `409` or `422`.
4. **Batching exists but does not reach the hot path.** This is the most decision-relevant finding, and it is a negative result.

### Batching, honestly split

Real and currently unused: `POST /folders` batches with a **per-item** `parentFolderId`, so whole-tree folder creation could collapse to roughly one request per tree depth. `POST /documents` batches per destination folder. `DELETE /blocks` is already batched.

The hot path is nonetheless immune. `POST /blocks` carries a **single** top-level `position.pageId`, and `_write_index_content` already sends a whole index document as one call, so there is no win left there. `GET /blocks` takes a **single** id, so reads are not batchable at all.

**Verified independently:** `craft_sync._write_index_content()` at `aardvark_jd/craft_sync.py:374-377` issues `get_block` then `delete_blocks` then `add_block` **unconditionally**, with no comparison of the freshly computed markdown against the document's existing content. That is three API calls per index document per run, whether or not anything changed, and it cannot be batched away. Only skipping unchanged documents fixes it.

**This confirms rather than displaces the incremental plan.** Batching is a complement, not the cheap alternative, and should not be framed as one.

### Bonus finding, verified

`GET /documents` **does exist** in the published spec, contradicting `craft_client.list_documents()`'s docstring at `aardvark_jd/craft_client.py:298-305`, which states it is "**Unverified against a live space**" and "may simply not exist". Unfiltered, it returns all documents in the space, so the per-folder call used by document adoption could collapse to a single whole-space call. The docstring should be corrected when that code is next touched.

### Recommended backoff policy: per-request and per-run

Per-request retry alone is unsafe here, because hundreds of calls each retrying several times can stall for minutes without bound.

- **Per-request.** 5 attempts for `429`, 3 for 5xx. Base 1 s, factor 2, **30 s ceiling, full jitter**. A present `Retry-After` overrides the computed delay, jittered upward but never downward.
- **Method-aware,** because the spec exposes no idempotency key on any endpoint. Retry `429` on any method, since it means rejected rather than applied. Retry 5xx and timeouts freely on `GET` and `DELETE`, but **at most once on `POST`**: the write may have landed, and a duplicate block is user-visible.
- **Per-run.** A 120 s cumulative sleep budget, a circuit breaker after 3 consecutive exhaustions, and a **proactive throttle of roughly 100 ms between calls**. Reactive backoff is the wrong primary instrument when the caller already knows hundreds of calls are coming.

### The caveat that matters

**Every constant above is an engineered default, not Craft's number, because Craft publishes none.** The same change must therefore log the first `429`'s response headers verbatim, specifically `retry-after`, `ratelimit-*` and `x-ratelimit-*`. `CraftClient._request()` currently discards them entirely. Capturing them converts every ordinary production 429 into the measurement that could not be taken without probing, and would settle questions 1 and 2 within a few real runs.

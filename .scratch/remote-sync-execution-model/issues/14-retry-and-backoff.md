# Retry and backoff across the three mirrors

Type: grilling
Status: resolved
Blocked by: none

## Question

The map's founding premises call retry and backoff "the non-negotiable safety net, because a full backfill can always hit the limit". Nothing has decided it, and neither `CraftClient._request` nor `GDriveClient._request` has any retry at all today. This is the last thing the destination explicitly requires that remains undecided.

Three tickets have sharpened it since it was first raised:

- **[Ticket 02](02-research-craft-rate-limits.md):** craft documents **no** rate limits — 28 operations, all declaring only `200` — so its constants must be engineered defaults, and the first real 429's headers were to settle them.
- **[Ticket 09](09-measure-latency-after-comparison.md):** the 429 is **real and reproducible**. The pre-change baseline died on `POST /blocks` with `{"error":"Rate limit exceeded"}` after 101 calls in 48 s. Its headers were **not captured** — the harness learned to record them only afterwards — so ticket 02's question is still open. A transient **502** was also observed on `GET /folders`, so this is not only about 429.
- **[Ticket 13](13-gdrive-call-cost.md):** Drive signals throttling as **`403 userRateLimitExceeded`**, not 429, and `403` is otherwise a never-retry code. Drive's quotas are published and it sits at ~1.4 per cent of them, so Drive is not the pressure — but Google **publishes the prescribed algorithm**, so unlike craft's constants Drive's need not be invented.

Decide:

- **What is retried, and on what.** 429 for craft, 403-with-reason for Drive, 5xx for both — and how a retryable 403 is distinguished from a real authorisation failure without swallowing the latter.
- **The policy itself**: exponential backoff with jitter presumably, but how many attempts, what ceiling, and whether it differs per mirror given only craft has ever actually thrown.
- **Where it lives.** Both clients are hand-rolled on `requests` with a near-identical `_request`, and the repetition is now real rather than speculative. One shared helper, or per-client policies?
- **What backoff does to the delete-then-insert window.** `_write_index_content` deletes a document's whole content before inserting the replacement; a failure in that window leaves the document empty, and a rate limit is exactly what lands there. Does retry close this, or does the write need reordering?
- **How a run that exhausts its retries ends.** It now ends in a detached process nobody is watching ([ticket 12](12-how-does-the-cli-return-promptly.md)), so this is the decision that gives the drift marker its content.
- **Whether the 429's headers still need capturing**, or whether engineered defaults are now good enough given the call volume has fallen from 118 to 41 and no 429 has recurred since.

## Why this is the last one

With [ticket 12](12-how-does-the-cli-return-promptly.md) resolved and [ticket 04](04-sync-scope-interface.md) ruled out of scope, the execution model is decided and the spell-correction half has been fully specified since ticket 10. Backoff is the remaining gap between the map and its destination.


## Answer (2026-08-28)

**One shared, hand-rolled retry helper that all three clients call, with a per-run budget rather than only a per-request one.** Two findings from the code reshaped this before any policy was chosen.

### The bug this ticket found

**None of the three mirror clients sets an HTTP timeout.** `requests` with no `timeout` blocks indefinitely, and all three do `self._session.request(...)` bare.

In the foreground that was an annoyance. Under [ticket 12](12-how-does-the-cli-return-promptly.md) it is the worst failure on this map: a hung connection in the detached process **holds the lock forever**, and ticket 12's pid-liveness check cannot break it, because the process is alive and looks healthy. Only the age backstop would, after the cutoff.

So a `(connect, read)` timeout is set once on each `Session` — roughly `(5, 30)` seconds as named constants. The read ceiling matters more than its exact value: it is what guarantees a background sync eventually **ends**, which is what makes ticket 12's lock safe at all. **This is a bug fix that backgrounding promoted into a safety requirement, and it should land regardless of the rest of this ticket.**

### The precedent that does not transfer

`emoji_picker.py:27-28` sets `CLAUDE_TIMEOUT_SECONDS = 15.0` and `CLAUDE_MAX_RETRIES = 0` — retries deliberately disabled with a human waiting. That is the right call there and the wrong one here: the Claude call is an optional nicety with an instant offline fallback, whereas a failed mirror sync is **data drift**.

### What is retryable

`429`; `5xx`; connection errors and timeouts; and `403` **only** when the reason string matches Drive's rate-limit reasons (`userRateLimitExceeded`, `rateLimitExceeded`). Drive's primary throttling signal is a 403, not a 429 ([ticket 13](13-gdrive-call-cost.md)), so a policy keyed on status alone misses it.

The 403 rule must be narrow and commented, because a plain 403 means *your credentials do not permit this*. Retrying it silently converts an auth failure into a long hang followed by a misleading error.

### Where it lives

**One shared hand-rolled helper**, called by each client's `_request`. The three are near-identical (`self._session.request(...)`, then `if not response.ok: raise <Service>ApiError(...)`), so the repetition is real rather than speculative.

`urllib3.Retry` mounted on an `HTTPAdapter` was the obvious alternative and was rejected: it cannot inspect a JSON reason string, so it cannot express the 403 rule above, and half-adopting it — `Retry` for status codes, hand-rolled for 403 — is worse than either. The shared helper is also the one place that can honour `Retry-After`.

### The policy, and the budget that actually controls it

Per request: **5 attempts, jittered exponential backoff, 1 s base, 32 s ceiling** — truncated exponential backoff with jitter, which is what Google prescribes and what craft's undocumented limit will have to tolerate.

Per request that is about 63 s worst case, and **a run makes 30-45 requests**. Multiplied naively, a pathological run backs off for forty-plus minutes. So the real control is a **cumulative per-run backoff budget of 5 minutes**, after which the run abandons and records drift.

**Ticket 12's stale-lock cutoff is derived from that budget, not chosen independently.** The cutoff must exceed the longest legitimate run, or a healthy sync has its lock stolen mid-flight. Two named constants where one is defined in terms of the other, rather than two magic numbers in separate modules that drift apart.

`Retry-After` is honoured when present, **clamped to the per-request ceiling**; if the requested wait exceeds the *remaining run budget*, the run abandons immediately rather than sleeping toward a deadline it already knows it will miss.

### When a mirror gives up

**The run carries on to the next mirror and records drift for the failed one only.** The three mirrors are independent products, and a Drive outage should not leave craft stale when craft is healthy.

The degraded output is safe because of what ticket 09 bought. If Drive exhausts its retries, craft's link row is written without the Drive URL. When Drive later succeeds, the computed link-row markdown gains that URL, differs from the stored `links_markdown`, and is rewritten. **It self-heals through the content comparison rather than needing to be remembered anywhere.**

### The hot loop this ticket had to close

Combining ticket 12 with the run budget produces a failure neither ticket sees alone. Ticket 12: a mutation arriving mid-sync sets a pending flag, and the running sync re-checks it on completion and goes round again. This ticket: a run that blows its budget abandons.

Together: a rate-limited run burns 5 minutes, abandons, sees the pending flag, restarts, hits the same limit, burns another 5 minutes — **forever, in a detached process nobody is watching, hammering an API that has already said stop**.

**Fix: loop only after a run that actually completed. An abandoned run clears the pending flag and exits.** The work is not lost — the next mutating command spawns a fresh sync, and a whole-tree repair picks up everything missed. One rule, no cooldown timer, no extra state, and no way to construct the loop.

### Foreground versus background

**One policy everywhere, differing only in whether retries are announced.** Background retries silently to the log; foreground prints `rate limited, retrying in 16 s` to stderr.

Tiering the *budget* by context was rejected because it gets it backwards: the `connect_*` first backfill is simultaneously the run most likely to be rate-limited and the one the user is most invested in seeing finish, so it would receive the least persistence exactly when it needs the most. The tier that matters is visibility. Someone who can see why they are waiting will wait; someone watching a silent terminal will interrupt at about twenty seconds and conclude the tool is broken.

### The delete-then-insert window

**Reordered to insert-then-delete.** `_write_index_content` currently deletes a document's whole content before inserting the replacement, so a failure in that window leaves it **empty** — and a rate limit is precisely what lands there.

Retry narrows this window but cannot close it: retries are finite, and the run that exhausts them still leaves an empty document. Inserting first means the document briefly holds both old and new content — ugly, self-healing, and visibly wrong — instead of silently empty. This is a real behaviour change to code ticket 09 just touched, so it needs its own test and should land on the same branch.

### Ticket 02's open thread, closed by construction

[Ticket 02](02-research-craft-rate-limits.md) wanted the first real 429's headers to settle craft's engineered constants. Ticket 09 reproduced the 429 and **failed to capture them**.

Rather than mounting another expedition, the shared helper **logs the full response headers at WARNING on any 429 or rate-limit 403**, and honours `Retry-After` when present. Craft's headers will therefore be captured *and acted on* the next time the limit is hit, with nobody needing to remember to look. Ticket 02's question answers itself the first time it recurs.

### The drift marker's content

Per-mirror last-success and last-failure was settled by ticket 12. This ticket adds that the failure carries a **reason class** — rate-limited, auth, network, unknown — not merely a message, because "craft is rate limited" resolves itself and "craft's token expired" never will, and those need opposite responses from the user.

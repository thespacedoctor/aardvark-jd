# Retry and backoff across the three mirrors

Type: grilling
Status: open
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

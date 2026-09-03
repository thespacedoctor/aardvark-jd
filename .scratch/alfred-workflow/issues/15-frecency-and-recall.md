# Should the Alfred surface rank by frecency, and where does that state live?

Type: grilling
Status: open
Blocked by: 05

## Question

Graduated from the map's "Not yet specified" once [ticket 05](05-index-payload-and-filtering.md) settled what Alfred holds: the whole index as a flat entity list, each item keyed by `uid` = `<domain>:<code>`, emitted with `skipknowledge: true` so the CLI's index order is preserved and Alfred does no learning of its own while the design moves.

That was the safe default for a moving design. This ticket decides whether it stays.

Decide:

- **Does the surface rank by frecency at all?** Whether recently-actioned or recently-created entities should sort ahead of plain index order, or whether index order (domain, then Johnny Decimal number) is the right and predictable default for a filing system whose whole point is a fixed structure.
- **If yes: whose knowledge?** Three positions, from [ticket 01](01-alfred-workflow-authoring.md)'s research:
  1. Drop `skipknowledge` and let Alfred learn selection frequency against the `uid` strings. Free, but Alfred's knowledge is opaque, per-Script-Filter-object, and keyed on `uid` — a reused Johnny Decimal number inherits the previous occupant's rank.
  2. Keep `skipknowledge` and rank in the CLI — `fd --json` orders `entities` by a recency signal the index already has (`created_at`, `updated_at`) or a new "last actioned" column the Alfred action path writes back.
  3. A hybrid — Alfred's learning for "actioned from Alfred", the index's timestamps for "recently created anywhere".
- **What is the recency signal?** `areas`/`categories`/`ids` already carry `created_at` and `updated_at`. "Recently created" is free. "Recently used" is not recorded anywhere today and would need the Alfred action path (and arguably `cd`, `open`, `fd`) to write it back — which is a new mutating side effect on read commands.
- **Does "recently created" even need frecency?** A just-created entity is the most likely next target, but the mutating command's own JSON result already returns the new entity's record (ticket 03 §7) — Alfred can surface it directly from that, without it having to win a ranking fight in the next `probe`.
- **Interaction with `uid` stability.** Ticket 03 fixed `uid` = `<domain>:<code>`. If Alfred learns against that, archive-and-reuse of a number hands the new entity the old one's rank. Decide whether that is acceptable (it is a rare event and the rank is roughly "this slot is used often") or whether it forces position 2.

This is a grilling ticket — call the Skill tool for "grilling" and "domain-modeling". A defensible outcome is "index order with `skipknowledge: true` stays, no frecency" — in which case this ticket closes cheaply and confirms ticket 03's default rather than changing it.

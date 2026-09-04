# Should the Alfred surface rank by frecency, and where does that state live?

Type: grilling
Status: resolved
Assignee: Dave
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

## Resolution (2026-09-04)

**No frecency. Index order with `skipknowledge: true` stays, and this ticket confirms ticket 03's default rather than changing it.** The safe default set while the design was moving turns out to be the right permanent answer, for four reasons that only became visible with the surrounding tickets settled.

**"Recently used" does not exist, and creating it costs the read/write split.** Nothing in the index records when an entity was last actioned. Recording it means `fd`, `open`, `cd` and the Alfred action path all writing back on every invocation, which turns the read commands into mutating ones. That is a structural cost paid for a ranking tweak, and it is the wrong trade.

**Any such signal would be per-machine and unrecoverable.** The index is per-machine, unsynced, and has no rebuild-from-tree path — it is only ever built incrementally by the mutating commands. So a frecency column would hold a different value on every machine and be lost outright whenever the index is. A ranking that disagrees between machines is worse than no ranking at all.

**Alfred's own knowledge is actively wrong for this domain, which rules out position 1 on its own merits rather than on caution.** `uid` is `<domain>:<code>` (ticket 03), and `archive` is documented as retiring an entity *"freeing its number"* — code reuse is a designed-in event, not a freak one. A recycled `A11.10` would inherit the rank of its previous occupant and surface that confidently. This is the rare-event-but-silent-failure shape the map has ruled against repeatedly.

**Nothing is being fixed.** Ticket 05 measured the matching at realistic scale: a JD ref, a partial-title prefix and a mid-title word all find the target, and a typed ref is exact. Frecency earns its keep where matching is weak; here it is not. Index order — domain, then Johnny Decimal number — is also the order the user's own filing system trains them to expect, which is the point of a fixed structure.

Two of the ticket's candidate signals died on inspection. **`updated_at` is unusable as a usage signal**: it is written by exactly three functions (`db.update_area_emoji`, `db.update_category_emoji`, `db.update_id_name`), so it fires on an emoji or name change and nothing else. **`created_at` is real and free**, but it is answered better by the recall question below than by ranking.

**Recall of a just-created entity comes from the mutating command's own result, not from ranking.** A newly created entity is genuinely the most likely next target, so after a create the success surface offers its actions directly — reveal, handoff, the mirrors — built from the record ticket 03 §7 already returns. Recency is served at the moment it matters, with no ranking, no new column and no cache dependency. It also covers ticket 05's accepted one-invocation cache lag rather than racing it: the new entity is reachable immediately from the result even though the cached index has not caught up.

Notes to [ticket 13](13-assemble-the-spec.md):

- `skipknowledge: true` is a permanent part of the item contract, not a placeholder. State the reason (recycled `uid`s) beside it, so a future reader does not "fix" it.
- `fd --json` emits `entities` in index order. No ordering parameter, no ranking hook.
- No schema change: no "last actioned" column, and the read commands stay non-mutating.
- The post-create success surface is a required part of every mutating flow's spec, since it is now the whole of the recall story.

This decision rests on there being no usage data yet. If a week of real use shows the surface consistently reaching for the same handful of entities, revisiting it is a fresh effort with evidence, not a resumption of this one.

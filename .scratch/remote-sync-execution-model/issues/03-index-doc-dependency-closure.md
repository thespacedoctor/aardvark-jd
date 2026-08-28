# Which entities must re-sync when one entity changes?

Type: grilling
Status: resolved
Blocked by: none

## Question

When a single entity is created, what is the complete set of craft.do items that must be created or refreshed?

This is the ticket the whole incremental-sync plan rests on. `craft_sync.get()` currently walks every domain, area, category and ID and refreshes every `00 Index` document on every mutating command. The index holds 13 areas, 11 categories and 28 IDs, but `craft_links` holds 382 rows, roughly a sevenfold amplification driven by the reserved `.00_index` to `.09_archive` scaffolding mirrored at every level. That amplification is why one `av add_project` costs hundreds of API calls and trips the rate limit.

The fast path agreed while charting passes the changed entity in as an explicit scope. That only works if the true dependency closure is known, and the closure is wider than the entity itself: per the module docstring, each level's reserved `.00_index` document lists the level directly below it, one level deep, with each child linking to its craft folder or document. So creating an ID dirties its category's index document, and possibly more.

Establish precisely, against the code in `aardvark_jd/craft_sync.py`:

- The exact closure for creating an ID or project: which index documents list it, and whether the space-root index refreshed by `_refresh_space_index()` is in the closure or can be skipped.
- Whether the closure is genuinely one level deep, or whether area and domain-root indexes also change.
- What the closure costs in API calls, so it can be checked against the 500 ms gate.
- Whether the same closure logic holds for Todoist and Google Drive, whose sync engines follow the same adopt-or-create pattern but write different link rows.

Out of scope for this ticket: the closures for `archive` and `set_emoji`. They are almost certainly different and are recorded as fog until the creation closure is settled.

## Answer

Resolved 2026-08-28. All figures below were measured against the live index and traced through `aardvark_jd/craft_sync.py`.

### The closure is exactly one level deep

Each `.00_index` document lists only the level directly below it, so creating an ID or project dirties exactly **one** ancestor index: its parent category's.

| Level | What its index lists | Dirtied by adding an ID? |
|---|---|---|
| Category `.00_index` | its IDs | **yes** |
| Area `.00_index` | its categories | no |
| Domain `.00_index` | its areas | no |
| Space-root index | the five PARA roots | no |

The area, domain and space-root indexes are **not** in the closure for creation, and `_refresh_space_index()` can be skipped entirely. The sibling URLs needed to rebuild the category index are already held in `craft_links.craft_url`, so assembling it costs no extra API calls.

Creating one project therefore needs roughly **8 API calls**: the ID's folder, its `00 Index` document, its link row, and a four-call refresh of the parent category's index.

### The real cause of the 429s is not the walk

This is the finding that reframes the effort. The live system has **27 reserved `.00_index` documents plus the space-root index, 28 in total**, and `_write_index_content()` at `craft_sync.py:374-377` rewrites **every one of them unconditionally**, with no comparison against existing content: `get_block`, then `delete_blocks`, then `add_block`, followed by `_write_link_row(forceRewrite=True)` adding one more `POST`.

That is **4 API calls × 28 = 112 calls on every mutating command, even when nothing has changed**, plus `GET /folders` and `GET /connection`. Every one of the 112 hits `/blocks`, which is precisely the endpoint reported in the 429.

The cost is driven by **unconditional rewriting**, not by the breadth of the walk. That distinction changes the cheapest fix.

### Decisions

**1. Content comparison is the primary fix, and scoped incremental sync is now conditional.** `_write_index_content` will read the existing content, compare it against the computed markdown, and return early when identical. A full whole-tree walk then costs roughly **34 calls, of which about 30 are reads**, against 114 today. This is a single-function change: no scope plumbing, no changes to `cl_utils`, no changes to the three `_maybe_sync_*` helpers, and it **preserves the self-healing drift repair that runs on every sync** — a property scoped syncing actively gives up.

Scoped incremental sync would reach roughly 8 calls, but at the cost of touching every call site and the whole sync-scope interface. It is therefore **deferred behind a measurement** rather than adopted: if comparison alone lands under the 500 ms gate, [How do the three sync engines accept a scope?](04-sync-scope-interface.md) should be **ruled out of scope**, and much of the backgrounding fog along with it.

**2. Folder-id resolution stays as it is.** `_load_folder_index()` keeps its single whole-tree `GET /folders`. Craft re-keys folder ids once the app syncs, verified against a live space, so `craft_links.craft_folder_id` cannot be trusted as the primary source. This is one read call, it is not the problem, and trusting the stored id would trade a real correctness property for a negligible saving.

**3. The link-row rewrite follows the content rewrite.** `.00_index` link rows currently pass `forceRewrite=True` solely because `_write_index_content` wipes the document immediately beforehand, invalidating the recorded block id. When the content rewrite is skipped, that justification no longer holds and the forced rewrite is skipped too, taking an unchanged index document to **one `GET` and zero writes**.

This coupling is subtle and is currently expressed only in a docstring, so it **must be pinned by a test**: skipping the content rewrite while still forcing the link-row rewrite would silently reintroduce most of the cost, and forcing neither when content *did* change would corrupt the link row.

### Out of scope for this ticket

The closures for `archive` and `set_emoji` are different from creation and remain fog. Archive in particular frees a number and moves an entity, so it plausibly dirties more than one ancestor.

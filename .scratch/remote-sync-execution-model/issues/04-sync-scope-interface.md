# How do the three sync engines accept a scope?

Type: grilling
Status: open
Blocked by: 09

## Status note

**This ticket may not survive.** [Which entities must re-sync when one entity changes?](03-index-doc-dependency-closure.md) established that the 429s are caused by unconditional index rewrites rather than by the breadth of the walk, and that content comparison alone cuts a run from ~114 API calls to ~34 without any scope plumbing. If [Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md) comes in under the 500 ms gate, this ticket should be **closed and ruled out of scope** rather than resolved.

## Question

What is the interface by which a mutating command tells `craft_sync`, `todoist_sync` and `gdrive_sync` to sync only what changed?

All three engines are constructed identically today, as `Engine(log=log, dbConn=conn, settings=settings).get()`, and all three are invoked through near-identical `_maybe_sync_*` helpers in `aardvark_jd/cl_utils.py` that swallow failures into a stderr warning. The helpers must run in a fixed order, gdrive then todoist then craft, because each embeds the previous one's URL in its own link row. Any scope interface has to survive that ordering constraint.

Decide:

- The shape of the scope itself. A single entity reference, a list of entity keys, or a richer descriptor that distinguishes "this was created" from "this was renamed"?
- Where the closure computed in ticket 03 is expanded: at the call site, or inside each engine? Putting it inside each engine risks three divergent implementations of the same rule; putting it at the call site leaks mirror-structure knowledge into `cl_utils`.
- Whether the three `_maybe_sync_*` helpers collapse into one parameterised helper, given they now differ only by settings key and engine class. The repetition is real rather than speculative, so DRY applies, but the ordering constraint and the differing summary shapes must survive the extraction.
- What a scoped run returns, given the current summary dicts are whole-run counters, and whether the drift marker is written here.
- How the no-scope case, meaning the manual `av craft_sync` repair path, expresses itself in the same interface.

This is the decision that determines whether items 7 and 8 of the original request are still needed, so it should be resolved before any latency measurement.

# How do the three sync engines accept a scope?

Type: grilling
Status: closed - out of scope
Blocked by: 12

## Ruled out of scope (2026-08-28)

**Closed without being resolved.** [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md) decided that mutating commands hand the existing whole-tree repair sync to a detached process and exit. With sync off the critical path, a scope interface buys only a faster background job — and [ticket 13](13-gdrive-call-cost.md)'s OR-ed `files.list` buys more of that, more cheaply, from two functions in one module.

Backgrounding removed the deadline that made scoping urgent; ticket 13 removed most of the payoff that made it attractive. What remains is a genuine optimisation with no deadline attached, which is past this map's destination. It returns only if the destination is redrawn, and then as a fresh effort.

The interface questions below are left intact rather than deleted, because they are the right questions if anyone ever does pick this up.

## Earlier status note (superseded)

**This ticket survives.** [Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md) came in at **30.7 s** against the 500 ms gate, so scoping was not ruled out of scope.

But the same measurement changed what this ticket is for. Content comparison already took craft from 118 calls to 41 without any scope plumbing, and 29.9 of the 30.7 seconds is network spread across four services — Drive's 47 calls now cost more than craft's 41. **Scoping craft alone cannot reach the gate**: taking craft to zero still leaves about 17 seconds.

So this is no longer the ticket that closes the gap. It is now blocked by [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md), which decides whether the CLI waits for sync at all. If it does not, scoping becomes an optimisation without a deadline, and the interface below should be designed for tidiness rather than for latency. The last line of the Question section, that this should be resolved before any latency measurement, is now spent: the measurement happened first and reframed it.

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

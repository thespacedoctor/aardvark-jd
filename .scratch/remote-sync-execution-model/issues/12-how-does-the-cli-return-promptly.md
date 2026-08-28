# How does `av add_project` return in under 500 ms?

Type: grilling
Status: open
Blocked by: none

## Question

The gate is 500 ms. [Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md) measured **30.7 s** with content comparison in place, down from 56.0 s. What closes the remaining sixty-fold gap?

The measurement rules out the cheap answer. Content comparison did what ticket 03 predicted — craft went from 118 calls to 41, and the 429 stopped — and the command is still thirty seconds. Of that, 29.9 s is network:

| service | calls | network time |
|---|---|---|
| Google Drive | 47 | 13.8 s |
| craft.do | 41 | 13.1 s |
| Todoist | 4 | 1.6 s |
| Dropbox | 2 | 1.4 s |

**Taking craft to zero would still leave about 17 seconds.** At roughly 300 ms per round trip, no reduction in call count alone reaches 500 ms while the CLI waits for the network at all. That is the finding that makes this a decision rather than an optimisation.

Decide:

- **Does the CLI stop waiting for sync at all?** The charting session settled that "backgrounding is not assumed" and reopens only if measured latency exceeds the gate. It does, by sixty times. So this is the moment that premise is revisited.
- If the CLI returns before sync completes, **what does the user see** — and what happens when sync then fails, given the effort already settled that failures must be logged and must leave a persistent drift marker surfaced by browse?
- **What carries the work**: a detached child process, a queued job drained by the next invocation, a daemon? The system is a single short-lived CLI process today, and ticket 08's concurrency contract was written for exactly that shape.
- **What this does to ticket 08.** WAL was deliberately declined on the grounds that the only concurrent accessor is completion's `mode=ro` reader. A background writer outliving the foreground process breaks that premise, and ticket 08 explicitly deferred WAL to this trigger.
- **Whether scoping is still needed** once backgrounding lands, or whether it becomes an optimisation with no deadline. This is what [How do the three sync engines accept a scope?](04-sync-scope-interface.md) now waits on.
- Whether 500 ms is still the right gate for a command that does real filesystem scaffolding, or whether the honest target is "returns promptly and tells the truth about what is still happening".

## Why this blocks ticket 04

Ticket 04 designs the scope interface for all three engines. Whether that interface needs to exist, and whether it needs to be fast or merely tidy, depends on whether the CLI is still waiting for it. Deciding the interface first would be designing for a requirement that may not survive this ticket.

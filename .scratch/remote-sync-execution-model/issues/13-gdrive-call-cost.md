# What are Google Drive's 47 calls per run, and can they be cut?

Type: research
Status: open
Blocked by: none

## Question

[Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md) found that Google Drive costs **47 HTTP calls and 13.8 s** on every `av add_project` and every `av craft_sync` — now the **largest single component** of the command, ahead of craft's 41 calls and 13.1 s.

The whole effort has been aimed at craft, because craft was the one returning 429s. Drive never failed, so it was never looked at, and it was quietly just as expensive all along. Its 47 calls barely move between a repair run and a create run (46 vs 47), which is the signature of an unconditional whole-tree walk — the same shape ticket 03 found in craft.

### The work

- Instrument `gdrive_sync` the way ticket 09 instrumented craft: what are the 47 calls, by endpoint, and how many are reads against writes?
- Is there an unconditional-rewrite equivalent of the craft index-document problem, where the same content is written back every run?
- What are Drive's documented rate limits, and how close does 47 calls per mutating command sit to them? Craft's limits turned out to be undocumented; Drive's are published, so this should be answerable from primary sources.
- Does Drive support batching, and would it reach the hot path — the question that batching failed on for craft in ticket 02?
- The same two questions for Todoist, which is cheap today at 4 calls and 1.6 s, so that the parity question can be answered on evidence rather than assumed.

### What this feeds

The Todoist and Drive parity fog, and [How does `av add_project` return in under 500 ms?](12-how-does-the-cli-return-promptly.md): if Drive turns out to have a content-comparison win as large as craft's, the arithmetic on the gate changes and backgrounding may carry less weight than the measurement currently suggests.

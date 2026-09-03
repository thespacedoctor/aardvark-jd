# Does shipping the whole index to Alfred hold up at realistic scale?

Type: prototype
Status: open
Blocked by: 01, 03

## Question

Settled while charting: Alfred does the filtering, not aardvark. One call on keyword entry fetches the whole index; Alfred's fuzzy matching filters it client-side, which is instant and learns the user's selection order in a way `fd`'s keyword search cannot. That decision rests on an assumption which today's tree is too small to test: that the index stays small enough to ship whole.

Build a throwaway Script Filter that fetches the full index as Alfred JSON and filters client-side, and measure it against a **synthetic tree at realistic scale** — not today's dozen entries. Take a defensible target for a filing system meant to last: a fully-populated Johnny Decimal system is three domains of ten areas of ten categories of up to a hundred IDs, so decide the plausible ceiling and test at it, plus a generous multiple.

Answer:

- **How large is the payload?** Bytes of JSON at the target scale, and how much of it is the mirror URLs that ticket 03's contract puts on every item.
- **Where does it stop feeling instant?** Time from keyword to first results, and Alfred's own filtering latency once the items are in its hands. Find the size at which either becomes noticeable, and compare it to the plausible ceiling.
- **Does Alfred's matching actually find things?** Test the search behaviour that matters: a Johnny Decimal reference (`A11.10`), a partial title, a word from the middle of a title, a word from a description. Whether `match` needs to be populated separately from `title` to make descriptions searchable, and what that does to the payload.
- **What does the fallback look like if it does not scale?** The standing alternative is a hybrid: Alfred filters a cached set, and aardvark's own search runs only on a modifier for a deeper phrase search. Say whether it is needed, and if the answer is "not yet", say at what size it becomes needed and how the workflow would notice.
- **Is there a caching layer worth having?** Whether the whole-index fetch should be cached between invocations, and if so what invalidates it, given the index changes underneath the workflow whenever a mutating command runs.

## Input from research (2026-09-03)

[Ticket 01](01-alfred-workflow-authoring.md) found no documented item-count limit or performance cliff for a Script Filter anywhere in Alfred's material, which is what leaves this prototype as the only way to settle the whole-index assumption.

It also changed two of the questions above:

- **Alfred's matching is word-prefix, not fuzzy subsequence matching**, and `match` **replaces** `title` rather than adding to it. So making descriptions searchable means building a `match` string that still contains the title's words — test what that does to both the payload size and the quality of the results, because a `match` string stuffed with description text will also match things the user did not mean.
- **`cache` with `loosereload` exists** (Alfred 5.5+) and is recommended precisely for the "Alfred Filters Results" mode already chosen. It directly addresses the 240 ms cold `fd`, so the caching question at the end of this ticket now has a first-class mechanism to evaluate rather than a hand-rolled one — including what `loosereload` does about the index changing underneath the cache when a mutating command runs.

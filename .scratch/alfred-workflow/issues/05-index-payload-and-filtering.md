# Does shipping the whole index to Alfred hold up at realistic scale?

Type: prototype
Status: resolved
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

## Answer

Resolved 2026-09-03 by the throwaway prototype at `.scratch/alfred-workflow/prototypes/05-index-payload/` (`generate.py` builds a synthetic Johnny Decimal tree — field lengths modelled on the live `db.py` schema and `doc_links.py` URL forms; `measure.py` runs the headless sweep; `AardvarkPayloadProbe.alfredworkflow` is a throwaway workflow Dave drove by hand in Alfred). Prototype captured on branch `prototype/ticket-05-index-payload`; the verdict and the filled test table live in `probe.md` on that branch.

### Verdict: ship the whole index to Alfred. It holds at the plausible ceiling.

### The plausible ceiling

A fully-packed Johnny Decimal system is 3 domains × ~9 areas × ~9 categories × up to ~99 IDs ≈ 24,000 entities. But one person's PARA + JD filing system, matured over years, realistically fills each category with 15–25 IDs, not 99 — so the **plausible lifetime ceiling is ~5,000 entities**, and ~25,000 is the "generous multiple" (near-full population) the ticket asked to also test.

### 1. Payload size

Minified, seed 42, measured:

| entities | `fd --json` envelope (ticket 03) | Alfred `items` — fat | Alfred `items` — lean | mirror-URL share of fat |
| --- | --- | --- | --- | --- |
| ~1,000 | 0.77 MB | 1.32 MB | 0.87 MB | 24.6% |
| ~5,000 (plausible ceiling) | 3.88 MB | 6.61 MB | 4.37 MB | 24.9% |
| ~15,000 | 11.45 MB | 19.53 MB | 12.94 MB | 24.9% |
| ~25,000 (near-full JD) | 18.99 MB | 32.39 MB | 21.44 MB | 24.8% |

- **Mirror URLs are a flat ~25% of the Alfred payload at every scale.** They are real weight but not the thing that breaks it.
- Folding the description into the Alfred `match` string costs **~7%** on top.
- The payload is highly redundant — gzip ratio ~8.5:1 — but Alfred does not compress Script Filter stdout, so that only matters if a cached file is stored compressed.
- **fat vs lean** is the significant lever: `fat` (every mirror URL in its own `mods` block as `arg`, with the shared discriminator repeated per mod — ticket 01's "mod `variables` replace wholesale, no merge") is ~50% larger than `lean` (one `variables.urls` object per item, downstream resolves the chosen URL). See §6.

### 2. Where it stops feeling instant

Alfred's real parser (`NSJSONSerialization` → `NSDictionary`, via JXA, on this machine):

| scale | script `cat` step | parse to dictionary |
| --- | --- | --- |
| 1,000 | 0.006 s | 0.022 s |
| 5,000 | 0.006 s | 0.067 s |
| 15,000 | 0.009 s | 0.179 s |
| 25,000 | 0.012 s | 0.292 s |

`cat` is free even at 32 MB (page cache). Hands-on in Alfred:

- **Instant, cold, through the plausible ceiling (~5,000).** Filter latency while typing the query stays under 0.5 s.
- **First-results lag first becomes noticeable at ~15,000 entities** — i.e. only in near-full-JD-population territory, which a real one-person system is very unlikely to reach.
- JD ref, partial-title prefix and mid-title-word queries all resolve without perceptible delay.

In "Alfred Filters Results" mode the script runs **once per `probe` invocation**, not per keystroke — so the parse cost is paid once and then Alfred filters in memory. With `cache` + `loosereload` it is paid once per TTL.

### 3. Does Alfred's matching find things

Match mode **"Word matching — Any order"** (`alfredfiltersresultsmatchmode: 2`), with `match` = `"<code> <title> <path segments below root>"`. Confirmed by hand:

- **JD reference** (`A11.10`) — matches (the code is in the `match` string).
- **Partial title** (word prefix, e.g. `veh` → "Vehicles", `annu` → "Annual …") — matches.
- **Word from the middle of a title** — matches (any-order).
- **Word from a description** — does **not** match, because `match` **replaces** `title` (ticket 01) and the default `match` string above does not include the description.

To make descriptions searchable, the description must be appended to the `match` string (+7% payload, §1). The research caveat stands: a `match` string carrying description text will also match entities the user did not mean. Recommendation: **include the description**, appended last, accepting the loosened matching — the payload cost is trivial at this scale and description search is genuinely wanted. Revisit only if false matches prove annoying in use.

### 4. Fallback if it does not scale

**Not needed now.** The standing hybrid (Alfred filters a capped cached set; `aardvark fd` keyword search runs only on a modifier for a deeper phrase search) becomes relevant only past ~15,000 entities. The workflow can notice it has crossed that line by reading the entity count in the payload it just fetched, and switch to the hybrid then. Until a real system approaches that size, ship the whole index unconditionally.

### 5. Caching

**Yes — `cache` with `loosereload`, `{"seconds": 3600, "loosereload": true}`.** Confirmed: the second `probe` invocation is instant regardless of scale. `loosereload` shows the stale cache immediately and refreshes in the background when the payload has moved.

The index changes underneath the cache whenever a mutating command runs. The CLI has no clean scriptable way to flush an Alfred Script Filter's cache (invalidation is: edit the object, debugger Flush, `reload` typed into Alfred, restart Alfred — none CLI-friendly). The accepted behaviour is therefore: **rely on `loosereload`'s background self-heal**, so a folder created by `add_id` shows up in the Alfred surface one invocation late at worst. This is acceptable for a filing system. If tighter freshness is ever wanted, whether touching the Script Filter's script file invalidates the cache needs verifying — handed to ticket 13 as a note, not a blocker.

### 6. The fat/lean payload fork — handed to ticket 13

The Alfred `items` JSON is built by the workflow from the `fd --json` output, so its shape is a workflow-assembly decision, not part of ticket 03's CLI contract. The prototype surfaced two viable shapes:

- **fat** — every mirror URL rides in its own `mods` block as `arg`, with `{entity_id, open: "<service>"}` repeated in each mod's `variables` (no inheritance, per ticket 01). No downstream lookup: the Open URL object gets the URL directly.
- **lean** — one `variables.urls` JSON object per item, no `mods`. ~50% smaller. A modifier's downstream object resolves the chosen URL from that object.

Since the charting decision has Alfred holding the whole index in memory, lean's downstream resolution is a cache read, not a re-invocation of the CLI. **Recommend lean.** Ticket 13 confirms when it specifies what each modifier does.

### Downstream effects

- The map's "Frecency and recall" fog is now specifiable — ticket 05 settles that Alfred holds the whole index as a flat entity list keyed by `<domain>:<code>` with `skipknowledge: true`. Graduated to [Should the Alfred surface rank by frecency, and where does that state live?](15-frecency-and-recall.md).
- Ticket 13 inherits two notes: the fat/lean payload choice (recommend lean), and the cache-invalidation-on-mutation behaviour (rely on `loosereload`).

# Ticket 05 probe — does the whole-index payload hold up at scale?

Throwaway. Two halves: the **payload** half is measured headless by `measure.py`
(results below). The **feel** half needs Alfred on your machine and your hands —
that is what the `.alfredworkflow` is for.

## Build the artifacts

```bash
cd .scratch/alfred-workflow/prototypes/05-index-payload
./regen.sh          # writes workflow/payload-*.json and AardvarkPayloadProbe.alfredworkflow
python measure.py    # prints the payload table
```

`regen.sh` needs only the system Python (`/usr/bin/python3`). Nothing hits a
database or the network. The synthetic tree follows the Johnny Decimal shape
(3 domains → ~9 areas → ~9 categories → IDs) and models field lengths on the
live `db.py` schema and `doc_links.py` URL forms, so the byte counts are real.

## Install the probe (safe — Alfred imports its own copy)

Double-click `AardvarkPayloadProbe.alfredworkflow`. It does **not** touch the
repo copy or any existing workflow. `bundleid` is `dev.thespacedoctor.aardvark.ticket05probe`
— delete it when the ticket closes.

In the workflow's `[𝗑]` configuration set **SCALE** (1000 / 5000 / 15000 / 25000)
and **FORM** (fat / lean). Then in Alfred type `probe` and a query.

- **fat** — every mirror URL rides in its own `mods` block as `arg`, with the
  shared discriminator repeated per mod (ticket 01: mod `variables` replace
  wholesale, no merge). No downstream lookup needed.
- **lean** — one `variables.urls` JSON string per item, no `mods`. Smaller, but
  the downstream object must resolve the chosen URL from the cached payload.

The served payloads have **no `cache` block**, so every `probe` pays the full
parse — worst case. To feel the cached path, edit the Script Filter's script to
read `payload-5000-fat-cached.json` and invoke twice.

## What only you can answer — record answers inline

| Question | SCALE where it first bites | Notes |
|---|---|---|
| Time from `probe␣` to first results (cold, no cache) | 15000 | |
| Filtering latency as you type the query | <0.5s | |
| Does it still feel instant at the plausible ceiling (~5000)? | yes | |
| `A11.10` — does a JD ref match? | yes | match string carries the code |
| partial title (`cardi`) | matches (retested `veh`/`annu`) | `cardi` was a dead test — synthetic vocab has no `cardi*` token; real prefixes match fine |
| word from the middle of a title | yes - matching | "any order" mode |
| word from a **description** — FORM=fat has no description in `match` | not matching| expected: no match |
| regenerate with `generate.py --match-description` and retry the description word | did not test | measures the size cost (below) |
| fat vs lean — any perceptible difference in feel? | did not test | |
| cached path (edit script → `*-cached.json`, invoke ×2) — instant on 2nd? | yes | |

## Payload measurements (headless, `measure.py`, seed 42)

<!-- paste the measure.py table here after running it -->

Read from the first run on this machine (2026-09-03):

```
entities |  cli-json |       fat |  fat+desc |      lean | url %(fat) |  fat gzip |  build s |  parse s
     102 |     0.08M |     0.13M |     0.14M |     0.09M |      24.6% |     0.02M |    ~0.002 |   0.001
    1032 |     0.77M |     1.32M |     1.42M |     0.87M |      24.6% |     0.16M |    ~0.02  |   0.006
    5130 |     3.88M |     6.61M |     7.08M |     4.37M |      24.9% |     0.79M |    ~0.10  |   0.036
   15093 |    11.45M |    19.53M |    20.91M |    12.94M |      24.9% |     2.29M |    ~0.30  |   0.112
   25056 |    18.99M |    32.39M |    34.69M |    21.44M |      24.8% |     3.78M |    ~0.50  |   0.189
```

(`build s` is the CLI's own build+serialise for one payload; `parse s` is a
CPython `json.loads` proxy. Neither includes the SQLite query, which ticket 03's
`db.entities_with_links` still has to be written to measure.)

### Alfred's real parser (NSJSONSerialization via JXA, this machine, 2026-09-03)

```
scale  |  cat (script step)  |  NSJSONSerialization -> NSDictionary
 1000  |      0.006 s         |   0.022 s
 5000  |      0.006 s         |   0.067 s
15000  |      0.009 s         |   0.179 s
25000  |      0.012 s         |   0.292 s
```

`cat` is free even at 32 MB (page cache). Parse-to-dictionary at the plausible
ceiling (~5000) is **67 ms**; at full population (~25000) **292 ms**. This is
parse only — Alfred then converts to its own item model and builds the match
index on top, an unknown multiplier the hands-on filter test has to reveal.

### Reading it

- **Mirror URLs are a flat ~25% of the fat payload at every scale.** They are
  not the thing that breaks it — the per-mod duplication is: **fat is ~50%
  bigger than lean** for the same entities.
- Folding description into `match` costs **~7%** on size.
- At the **plausible ceiling (~5000 entities)**: fat 6.6 MB, lean 4.4 MB,
  cli-json 3.9 MB. Build+serialise ~0.1 s, parse ~0.04 s.
- At **full Johnny Decimal population (~25000)**: fat 32 MB, lean 21 MB. Build
  ~0.5 s, parse ~0.2 s — before Alfred builds 25k item objects and indexes 25k
  match strings, which is the number the probe exists to get.
- In "Alfred Filters Results" mode the script runs **once per `probe`
  invocation**, not per keystroke; with `cache` + `loosereload` (Alfred 5.5+)
  once per TTL. So the parse cost is amortised — the open question is whether
  Alfred's in-memory filter over 25k items stays sub-frame.

## Verdict (2026-09-03)

**Shipping the whole index to Alfred holds at the plausible ceiling. Ship it.**

- At ~5000 entities (the plausible lifetime ceiling for one person's PARA+JD
  system): `probe` feels instant cold, filter latency under 0.5 s, Alfred parse
  67 ms. Lag first becomes noticeable at ~15000 — full-JD-population territory,
  not a real system's size.
- Matching works: JD ref (`A11.10`), partial-title prefix (`veh`, `annu`),
  mid-title word, all in "Word matching — Any order" with `match` = code +
  title + path segments. Description words need description folded into `match`
  (+7% payload).
- `cache` + `loosereload` (Alfred 5.5+, `seconds: 3600`) confirmed: 2nd
  invocation instant regardless of scale. It self-heals a stale cache in the
  background, so a folder created by a mutating command shows up one invocation
  late at worst — acceptable.
- No hybrid fallback needed now. It becomes relevant only past ~15000 entities;
  the workflow can watch the payload's entity count and switch then.
- **fat vs lean**: not felt-tested (indistinguishable in principle — both parse
  once). lean is ~50% smaller for the same entities. Since Alfred holds the
  whole index, a modifier resolving its URL from the cached payload is a memory
  read, not a re-shell — so lean's only cost (downstream lookup) is cheap.
  Recommend **lean**. This is a workflow-assembly call → ticket 13.
- **Cache invalidation on mutation**: rely on `loosereload`'s background
  self-heal; the CLI has no clean scriptable cache-flush. Note the
  one-invocation lag in the docs. → ticket 13.

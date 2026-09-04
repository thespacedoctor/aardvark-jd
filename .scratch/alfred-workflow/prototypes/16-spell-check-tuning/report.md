# Ticket 16 probe: sweeping the spell-checker's floor and tie-break

Run 2026-09-04 against the same corpus and seed as [the ticket 08 probe](../08-spell-check/probe.md), so the numbers are directly comparable with it. Reproduce with `python3 sweep.py`; the captured run is in `results.txt`.

## Method

`sweep.py` reimplements `tokenise` and `suggest` with the length floor and the tie-break rule as parameters, rather than mutating `spell_check`'s module constants, and calls the real `_distance_one_variants` and the real wordlist. The corpus is ticket 08's: unique human-typed folder titles at depth 1 to 3 under the aardvark root, 141 of them.

Recall is measured by injecting one realistic typo (neighbour-key slip, transposition or dropped letter) into a genuine dictionary token, using ticket 08's injector and seed unchanged. The token to corrupt is chosen with the **shipped** floor of 6 in every configuration, so all configurations are scored on the same trials rather than on a trial set the swept floor reshapes.

## Floor against tie-break

Right, wrong and silent are shares of the injected typos. Fires/title is how often the checker speaks on the real, uncorrupted titles.

```
floor tie-break              right   wrong  silent  fires/title  suspects
    4 shortest (shipped)     60.9%   33.7%    5.4%        12.8%         8
    4 longest                87.0%    7.6%    5.4%        12.8%         8
    4 same first letter      85.9%    8.7%    5.4%        12.8%         8
    4 deletion first         87.0%    7.6%    5.4%        12.8%         8
    5 shortest (shipped)     60.9%   33.7%    5.4%         4.3%         6
    5 longest                87.0%    7.6%    5.4%         4.3%         6
    5 same first letter      85.9%    8.7%    5.4%         4.3%         6
    5 deletion first         87.0%    7.6%    5.4%         4.3%         6
    6 shortest (shipped)     57.6%   25.0%   17.4%         1.4%         2
    6 longest                75.0%    7.6%   17.4%         1.4%         2
    6 same first letter      73.9%    8.7%   17.4%         1.4%         2
    6 deletion first         75.0%    7.6%   17.4%         1.4%         2
    7 shortest (shipped)     30.4%   13.0%   56.5%         1.4%         2
    7 deletion first         42.4%    1.1%   56.5%         1.4%         2
```

Two structural facts fall out of the shape of the table.

**The tie-break cannot affect the fire rate.** Every column of fires/title is constant down each floor block, because the tie-break decides *which* candidate is offered, never *whether* one exists. So improving it is free: it trades no false alarms for accuracy.

**"Longest" and "deletion first" are the same rule.** At edit distance 1 a candidate is only ever n−1, n or n+1 characters long, so ranking by descending length *is* ranking a dropped letter first, then a substitution or transposition, then an inserted letter. They score identically at every floor because they are not two rules.

## Why "shortest" is the wrong default

A dropped letter is the commonest real typo and leaves a token shorter than its correction, so preferring the shortest candidate systematically picks against the commonest case. The failures read as broken rather than merely unhelpful, which is what makes them dangerous — a plausible wrong offer invites a wrong acceptance, and that corrupts the folder name, the index row and three mirrors at once.

At floor 6, shipped rule versus deletion-first, on the same typos:

```
  setings  -> stings     becomes  settings
  servies  -> series     becomes  services
  assefs   -> asses      becomes  assess     (wanted assets)
  imagea   -> image      becomes  imaged     (wanted images)
```

By typo kind, floor 6: dropped letters 36.6% → **61.0%**, substitutions 71.4% → **82.1%**, transpositions 78.3% → **91.3%**.

## What the floor actually costs

Moving 6 → 5 adds exactly four suspect tokens across the 141 real titles. All four, in full:

```
  ciara -> clara      lagan -> laban      macos -> macros      silla -> sills
```

Every one is a proper noun or a product name — the population the learned vocabulary exists to retire, one dismissal each. In exchange, dropped-letter recall goes 61.0% → **87.8%** and the silent rate 17.4% → **5.4%**.

Floor 4 is rejected on its own numbers: **identical recall to floor 5**, and 12.8% of titles firing — one in eight. It is the only floor that *sees* the corpus's single real typo, `woth` (for "with"), but it still offers the wrong word, because `with` and `worth` are both distance 1 and `with` loses the tie either way. Floor 4 trades a silent miss for a wrong offer there, which is the worse of the two.

## American spellings

The 1,903 `-ize`, `-ization`, `-izer` and `-yze` twins the `en_GB-ise` list omits were generated from the shipped list and the sweep re-run against the extended wordlist.

```
  shipped en_GB-ise    narrow: 2 titles / 2 tokens    wide: 388 titles / 98 tokens
  with -ize forms      narrow: 2 titles / 2 tokens    wide: 360 titles / 95 tokens
```

No effect at all on the corpus that matters, and three distinct tokens across 11,264 folder names on the wide sweep. Ticket 16's worry — that this class recurs where jargon self-silences — does not survive the measurement: dismissals are keyed per token, so `normalize` is dismissed once and stays dismissed, and the whole population is three tokens.

The generation is deliberately mechanical, and that makes the three-token figure an **over-estimate** rather than an under-estimate: converting every `-ise` ending also admits non-words — `wize`, `promize`, `precize`, `paradize`, `franchize` are all in the extended list, verified. A real `en_GB` list would be curated and would admit fewer forms, so a curated list can only silence the same three tokens or fewer. It would also mask genuine typos that happen to land on one of those non-words, which is a cost the measurement does not charge it.

## Validity checks

The two review subagents dispatched against this script died on a session rate limit, so the checks they were asked for were run directly instead. All four hold:

1. **The suffix chain in `americanised()` does not shadow itself.** `realise`, `realised`, `realises`, `realising`, `organisation`, `analyse`, `analysed` and `optimiser` each produce exactly their own twin — `endswith("ise")` cannot swallow `ised` or `ising`, since those do not end in `ise`.
2. **The generation admits non-words**, as above. Recorded because it biases the `-ize` result towards *more* benefit than a real list would give, and the conclusion is to make no change anyway.
3. **The trial set is identical across floors** — the 92 injected typos compare equal between the floor-5 and floor-6 runs, so every configuration is scored on the same typos and the floor comparison is like-for-like.
4. **"Longest" and "deletion first" are provably the same rule** — the candidate length offsets observed at edit distance 1 are exactly `[-1, 0, +1]`, so descending length *is* deletion-first ordering.

One limitation the checks confirm rather than remove: the injected typos are always made in tokens of six characters or more, because that is how ticket 08 chose them. So the recall figures describe typos in six-plus-character words at each floor. They do not measure typos in five-character words, which floor 5 also begins to check — that population's false alarms are covered by the fires/title column, but its recall is not measured.

## Files

- `sweep.py` — the sweep, parameterised on floor and tie-break.
- `results.txt` — the captured run.

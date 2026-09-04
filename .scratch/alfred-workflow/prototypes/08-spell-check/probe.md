# Probe: the spell-check surface in Alfred (ticket 08)

## What this probe is

Ticket 08 asks what the suspect-token confirmation looks like in Alfred, and whether it earns its place. Two of its five questions are empirical — the false-positive rate on real input, and by extension whether the step is worth having at all — and those two decide the shape of the other three.

So this probe is measurement, not an Alfred workflow. The question "does a step that fires on nearly one title in five belong in a speed surface?" is answered by finding out how often it actually fires, on real titles, rather than by building the step and feeling it. The three scripts here are the primary source for the numbers in the ticket 08 resolution.

## Scripts

Each is standalone and reads the live system. None writes anything.

```bash
python measure_live_index.py   # fire rate over the titles in the SQLite index
python measure_fire_rate.py    # fire rate over unique human-typed folder titles, plus latency
python measure_wide_sweep.py   # the rejected corpus: every folder name at any depth
python measure_recall.py       # recall, against one injected typo per real title
```

All four abort if the wordlist fails to load, because an unreadable wordlist makes every token look clean and a false zero is indistinguishable from a real one. `measure_recall.py` is seeded (`SEED = 20260903`) and draws from a sorted corpus, so the run is reproducible.

### Configuration these numbers depend on

Every figure below moves if any of these changes, so they are recorded alongside the numbers:

| Setting | Value at time of measurement |
| --- | --- |
| Wordlist | `resources/wordlists/en_GB-ise.txt`, SCOWL `en_GB-ise` size 60 |
| Words loaded | 87,851 |
| `MINIMUM_TOKEN_LENGTH` | 6 |
| Edit distance | 1 |
| Tie-break | shortest candidate, then alphabetical |
| Learned vocabulary | `<root>/.aardvark-vocabulary` absent — nothing had ever been dismissed |

The empty learned vocabulary matters: every fire recorded here is a first encounter, with no self-silencing yet applied.

## Corpus

Three corpora were tried, and rejecting the first two is part of the finding.

1. **The live index** (`areas`, `categories`, `ids`): 65 titles. Too small to conclude from, and it fired on none of them.
2. **Every folder name under the aardvark root** (`measure_wide_sweep.py`): 11,102 folders, 11,092 titles, no depth limit and no deduplication. Rejected — dominated by machine-generated instrument data, which nobody types into `add_*`. It fires on 379 titles (3.4%), but those 379 collapse to **98 distinct suspect tokens**, and `xshooter → shooter` alone accounts for 78 of them. Counting the repeats made one false positive look like seventy-eight.

   It is kept and committed for two reasons: rejecting it is part of the finding, and it is the source of the multiple-suspect-token frequency (**2 of 379 firing titles**), which the small corpus cannot supply because it has none.

3. **Unique human-typed folder titles, depth 1–3** (`measure_fire_rate.py`): 141 titles, deduplicated case-insensitively, leading JD code and trailing emoji stripped. This is the corpus the headline numbers come from — it is the population `add_area`, `add_category`, `add_id` and `add_project` actually draw from.

**A caveat on the stripping.** `_CODE` only removes purely numeric prefixes (`02_`, `03.12_`), not the letter-prefixed JD codes the tree also uses (`A11.10_`, `A10-19_`). Those leftovers are harmless in practice because the remaining fragment carries digits and `spell_check.tokenise` drops any token that is not purely alphabetic — but the exclusion is done by the tokeniser, not by the filter, and the distinction would matter to anyone changing either.

## Results

### Fire rate, corpus 3 (141 titles, 132 checkable tokens)

| Measure | Value |
| --- | --- |
| Titles firing | 2 / 141 (1.4%) |
| Tokens flagged | 2 / 132 (1.5%) |
| True positives | 0 |
| False positives | 2 |
| Titles with more than one suspect token | 0 |

The two fires: `spectro → spectra`, `xshooter → shooter`. Both wrong.

**The 18 per cent figure in `spell_check.py`'s docstring is token-level, on a synthetic technical vocabulary.** On this corpus the token-level rate is 1.5 per cent. Ticket 08's premise that the step "fires on nearly one title in five" reads that figure as a per-title rate, and it is not one. The real rate is roughly one title in seventy.

### The miss that matters

The corpus contains exactly one genuine typo:

```
20260701_soxs_spectro_standards_woth_simultaneous_aqc_images
```

`woth` is "with". The checker did not offer it — `woth` is four characters, under `MINIMUM_TOKEN_LENGTH = 6` — and instead flagged `spectro` in the same title. So on the one title in the corpus that a spell-checker existed to catch, it missed the typo and raised a false alarm beside it.

### Recall, one injected typo per title

92 titles that contain a token genuinely present in the dictionary. One neighbour-key substitution, transposition or dropped character injected into one such token per title.

Only real dictionary words are corrupted. A token that passes `suggest()` because it is out-of-vocabulary jargon with no distance-1 neighbour can never be recovered — `suggest()` only ever returns dictionary words — so including those would pad the denominator with unwinnable trials.

| Outcome | Count | Share |
| --- | --- | --- |
| Caught, correct word offered | 53 | 57.6% |
| **Wrong word offered** | **23** | **25.0%** |
| Silent miss, nothing offered | 16 | 17.4% |

By typo kind:

| Kind | Caught |
| --- | --- |
| Transposition | 18 / 23 (78.3%) |
| Substitution | 20 / 28 (71.4%) |
| **Dropped letter** | **15 / 41 (36.6%)** |

Wrong offers include `arhive → arrive` (not "archive"), `servies → series` (not "services"), `setings → stings` (not "settings"), `imates → mates` (not "images"). The tie-break rule — shortest candidate, then alphabetical, no frequency data — is what produces these. **One offer in four is wrong**, which is worse than the docstring's framing of a wrong offer as "one keystroke to decline" implies: a wrong offer that is also plausible is a wrong *acceptance* risk, not just noise.

### Why dropped letters fail

**12 of the 16 silent misses were never checked at all.** Dropping a letter from a six-character word leaves five, and `tokenise` skips anything under `MINIMUM_TOKEN_LENGTH = 6`. So `system → sysem`, `syste`, `sstem`, `sytem` are all invisible, as are `family → famil` and `active → acive`.

The length floor does not merely reduce sensitivity to short words. It makes the single commonest typo class structurally undetectable in exactly the six- and seven-character words that dominate real titles.

### Latency

Warm, over all 141 titles: **min 0.0003 ms, median 0.0006 ms, max 0.0912 ms.** The spread is the interesting part — `suggest` is nearly free on a dictionary hit and pays the edit-distance search only on a miss, so the maximum is a title full of jargon rather than a typical one. Even that worst case is a tenth of a millisecond.

The cost of this feature is keystrokes, never time. That is what makes a zero-keystroke shape worth reaching for instead of dropping the feature.

## Verdict

**Keep it, as alternate rows on the ticket 06 confirmation screen — never as a step.**

The rarity cuts both ways and that is the whole finding. A dedicated step cannot be justified: it would be seen once in seventy creations, in a surface whose point is speed, and it is unreliable when it does appear. But the check costs nothing to run, and rows on a screen that already exists cost nothing to show. So the feature survives in the only shape whose cost matches its value.

**Be careful which unreliability figure gets quoted.** The 25 per cent wrong-offer rate is from the injected-typo test, where a real typo is guaranteed to be present — it describes the checker at its best, with something genuine to find. On real input the checker fired twice and was wrong twice, with no true positives at all; that is the rate describing normal use, and the sample is far too small to put a percentage on. Neither number flatters the feature, but they answer different questions and should not be swapped for one another.

The full decision, including how multiple tokens are handled and how the learned vocabulary is written from Alfred, is in the ticket 08 resolution.

## Corrections made to this probe

The first run of `measure_recall.py` reported 53.5 per cent caught, 28.3 per cent silent and 18.2 per cent wrong. Review found four defects that moved those numbers, and the figures above are from the corrected scripts:

- The candidate pool included out-of-vocabulary tokens, whose injected typos were unwinnable by construction, padding the denominator and depressing the catch rate.
- Typos were spliced in with `str.replace`, which substitutes the first *substring* match and could land the typo inside a longer word, scoring a trial the checker never saw as a miss.
- The `transpose` branch fell through to `drop` whenever the drawn index was the last character, skewing the mix of typo kinds.
- The corpus was in `os.walk` order, so `SEED` did not actually pin the run.

The direction of the correction matters: the catch rate rose slightly, but **the wrong-offer rate rose from 18.2 to 25.0 per cent**, which strengthens rather than weakens the case against a blocking step.

A second review round found that the fix for the second defect had reintroduced a narrower version of it — `spell_check._replace_token` guards its lookarounds against letters but not digits, so it would splice into the `backup` of `backup2024` before reaching a standalone `backup` later in the same title. The injection now uses a digit-aware guard of its own. Re-running produced **identical numbers**: no title in this corpus contains a chosen token inside an earlier digit-adjacent run. The figures above are therefore unaffected, and the fix stands as a guard for anyone re-running against a different tree.

## Snapshot, for re-running later

The corpus is read live from the tree, so it will drift. These are the fires as they stood on 2026-09-03, for anyone re-running and wanting to know whether a difference is a regression or just a changed tree.

Corpus 3, both fires (the complete list):

```
20260701_soxs_spectro_standards_woth_simultaneous_aqc_images    spectro -> spectra
xshooter_qub_demo                                               xshooter -> shooter
```

Corpus 2, the ten commonest of 98 distinct suspect tokens:

```
xshooter -> shooter    (x78)      normalize -> normalise  (x10)
laravel  -> caravel    (x23)      backend   -> backed     (x9)
golang   -> golan      (x19)      optimizer -> optimiser  (x9)
quarkus  -> quarks     (x16)
frontend -> fronted    (x15)
```

Two patterns are visible there and neither is a typo. Most are **technical proper nouns** — framework and instrument names — which is what the learned vocabulary exists to silence, one dismissal each. But `normalize → normalise` and `optimizer → optimiser` are **American spellings**, and those are not typos the user wants corrected one at a time: the wordlist is `en_GB-ise`, so every US spelling in a title is a permanent false positive. That is a systematic class, not a jargon nuisance, and it is worth weighing in ticket 16 alongside the length floor.

## Split off, not fixed here

Two CLI-side defects surfaced here and are not this ticket's to fix, because both change terminal behaviour as well as Alfred's:

- `MINIMUM_TOKEN_LENGTH = 6` hides the commonest typo class, as 12 of 16 silent misses show.
- The tie-break picks badly, producing the 25 per cent wrong-offer rate.

Both are ticketed on the map as [Is the spell-checker's tuning wrong?](../../issues/16-spell-check-tuning.md).

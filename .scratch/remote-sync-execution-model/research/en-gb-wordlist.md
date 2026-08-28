# Which en_GB wordlist ships with aardvark?

Research answer for [issues/05-research-en-gb-wordlist.md](../issues/05-research-en-gb-wordlist.md). Researched 2026-08-28.

## Answer

### Summary

**Ship the ESDB/SCOWL `en_GB-ise` size-60 plain wordlist, normalised to lowercase ASCII, plus a twelve-line hand-rolled Damerau-Levenshtein-1 candidate generator. Take no new dependency.**

The licence question turns out to be easy and the latency question turns out to be decisive. Every serious candidate list is either public domain or under an attribution-only permissive grant that is plainly GPL-3.0-compatible; the only genuine encumbrance found anywhere is the UK Advanced Cryptics Dictionary notice, and it attaches only to SCOWL word lists **larger than size 80**, which is far above anything worth shipping. Meanwhile the three obvious off-the-shelf packages fail hard on import cost: `spylls` takes **402 ms** to load an `en_GB` Hunspell dictionary and `symspellpy` takes **1,212 ms** to build its index, against a 500 ms budget for the whole command. A raw list plus a `frozenset` costs **12.3 ms**.

The most important finding is not about the wordlist at all. **Tokenisation and the suggestion gate dominate the false-positive rate; the choice of wordlist barely moves it.** Across nine SCOWL size variants the false-positive count on the 43-title sample varied from 22 to 15 under a naive tokeniser, and was 0 or 1 for *every one of them* under the right tokeniser and gate. Two rules do all the work: check only tokens of **six characters or more**, and offer a correction only when a **distance-1 dictionary word actually exists**. Together those take the sample from 21 false positives to 0.

`aadvark` **is** caught, and the suggestion is `aardvark`.

The honest caveat, which the 43-title sample alone would have hidden: on a wider realistic technical vocabulary the same configuration produces a **17.4% false-positive rate** (17 of 94 tokens), flagging `jupyter → jupiter`, `pydantic → pedantic`, `postgres → postures` and thirteen others. The supplied sample scores 0 because its jargon happens to sit at distance 2 or more from any English word. A per-user learned vocabulary is therefore not a nicety, it is part of the feature.

### Sources consulted

| Source | Type | Verdict |
|---|---|---|
| `https://github.com/en-wl/wordlist-diff/blob/rel-2026.02.25/Copyright` | Primary — the current ESDB/SCOWL copyright file | **Authoritative and decisive.** Permissive attribution grant; UKACD scoped to lists >80 |
| `https://github.com/en-wl/wordlist/blob/rel-2020.12.07/scowl/Copyright` | Primary — the SCOWL v1 copyright file | Same grant, older phrasing; UKACD enters at level 80 |
| `https://wordlist.aspell.net/dicts/` | Primary — the ESDB dictionaries page | Confirms size 60 = default, size 70 = "large"; documents the `-ise`/`-ize` split and the Pinto lineage |
| `README_en_GB-ise.txt` inside `hunspell-en_GB-ise-2026.02.25.zip` | Primary — shipped with the release | "The English dictionaries come directly from SCOWL and is thus under the same copyright terms as SCOWL" |
| `https://github.com/marcoagpinto/aoo-mozilla-en-dict/blob/master/LICENSE` | Primary — the Pinto `en_GB` upstream licence file | **LGPL-3.0** verbatim |
| `https://github.com/LibreOffice/dictionaries/blob/master/en/README_en_GB.txt` | Primary — LibreOffice's copy | Says "LGPL" with no version |
| `https://github.com/LibreOffice/dictionaries/blob/master/en/license.txt` | Primary — LibreOffice's `en` licence file | **GPL-2.0 verbatim** — contradicts the README next to it |
| `https://packages.debian.org/sid/wbritish` | Primary — Debian package page | `Source: scowl`. `wbritish` **is** SCOWL |
| `https://sources.debian.org/src/scowl/2020.12.07-4/debian/rules/` | Primary — Debian build rules | `wbritish` = size 50, `-large` = 70, `-huge` = 80, `-insane` = 95 |
| `https://sources.debian.org/src/scowl/2020.12.07-4/debian/copyright/` | Primary — Debian's own licence review | Corroborates the SCOWL grant |
| `https://github.com/zverok/spylls/blob/master/LICENSE` | Primary — licence file | **MPL-2.0**, not the MIT its PyPI classifier claims |
| `https://github.com/mammothb/symspellpy/blob/master/LICENSE` | Primary | MIT |
| `https://github.com/barrust/pyspellchecker/blob/master/LICENSE` | Primary | MIT (code). Dictionary data has **no stated licence** |
| `https://github.com/barrust/pyspellchecker` README, "Dictionary Creation" | Primary | Dictionaries derived from the **OpenSubtitles/OPUS** corpus |
| `https://github.com/rspeer/wordfreq#license` | Primary | Code Apache-2.0; **data CC-BY-SA-4.0**, and repackaging as a wordlist is explicitly forbidden |
| Local measurement on this machine | Primary — measured, not estimated | See section 2 |

**Method note.** Every list below was downloaded and built locally, and every timing was taken on this machine (Darwin 25.6.0, Apple Silicon, CPython 3.14.7 in a clean venv). Subprocess figures are the median of 15 to 21 runs of `python -c …`, quoted as a delta against a bare `python -c pass` control measured in the same batch, because the interpreter start dominates everything else at this scale. In-process figures are the median of 20 to 500 iterations. Nothing in section 2 is estimated.

---

### 1. Candidate `en_GB` wordlists and their licences

#### 1.1 SCOWL / ESDB — recommended

SCOWL has been renamed the **English Speller Database (ESDB)** and the current release is **2026.02.25**, not the 2020.12.07 that most write-ups still cite (`https://wordlist.aspell.net/`). The project publishes first-party **plain wordlists** in the companion `wordlist-diff` repository, so no unmunching of a Hunspell `.dic` is required — this is the single most useful practical discovery in the ticket.

The licence, quoted verbatim from `https://github.com/en-wl/wordlist-diff/blob/rel-2026.02.25/Copyright`:

> Copyright 2000-2026 by Kevin Atkinson
>
> Permission to use, copy, modify, distribute, and sell any part of SCOWLv2, or word lists created from it, is hereby granted without fee, provided that the above copyright notice appears in all copies and that both the above copyright notice and this notice appear in supporting documentation.

That is an attribution-only permissive grant in the MIT/X11 family. There is no non-commercial clause, no advertising clause and no share-alike term, so it is **GPL-3.0-compatible** and imposes exactly one obligation: keep the notice with the file.

The same document scopes the two conditional encumbrances precisely:

> If you are using a generated word list larger than 80, the copyright after '=== UKACD' applies.

UKACD is the one term in this whole space with real teeth — it requires that "the copyright notice must be prominently displayed and the text of this document must be included verbatim". **It does not apply at size 60 or 70.** The SCOWL v1 copyright file states the same boundary from the other side: the UKACD list is one of the sources that "the 80 level includes" (`https://github.com/en-wl/wordlist/blob/rel-2020.12.07/scowl/Copyright`). Likewise the Benjamin Titze copyright applies only to Australian English. Neither is triggered by `en_GB-ise` at size 60.

Two provenance notes worth recording rather than glossing:

- The 2026 copyright discloses that **COCA 3-gram data under NDA** was used in building the database: "All data from COCA comes from 3-gram data that is not freely available; however, the usage is within the rights given by the NDA that was signed when purchasing the data." The top-level grant explicitly covers "word lists created from it", so a downstream consumer of the wordlist is inside the grant. The NDA binds Atkinson, not us.
- The carve-out sentence reads "If you are using an official speller dictionary created by SCOWL that is not Australian English, then no additional copyright applies". The `en_GB` dictionaries are described elsewhere on the same site as an "alternative version" rather than the official one. This is a wording mismatch, not a substantive one — the size-based UKACD rule is stated independently, and size 60 is below the threshold either way. **INFERRED, low risk**, but flagged rather than hidden.

**`-ise` versus `-ize` is a real and separate axis, and it matters.** ESDB ships `en_GB-ise` (traditional), `en_GB-ize` (Oxford) and `en_GB-large` (both). Measured against 33 correct British spellings:

| List | Correct British spellings it would wrongly flag |
|---|---|
| `en_GB-ise` | **0 of 33** |
| `en_GB-ize` | 9 of 33 — `organise`, `organised`, `organisation`, `realise`, `recognise`, `apologise`, `specialised`, `prioritise`, `summarise` |
| `en_US` | **28 of 33** — including `colour`, `centre`, `licence`, `defence`, `behaviour`, `programme`, `travelled`, `aluminium` |

That last row is the entire justification for doing `en_GB` at all, and it is worth stating plainly because the 43-title sample does not show it: **the supplied sample cannot discriminate en_GB from en_US** (both score 0 false positives on it), because none of the 43 titles contains a British-spelled word. The discrimination comes from this second test, not from the sample.

#### 1.2 `wbritish` and `words` (Debian) — the same thing as SCOWL

Debian's `wbritish` is not an independent list. `https://packages.debian.org/sid/wbritish` gives `Source: scowl`, and `debian/rules` shows exactly how the sizes map (`https://sources.debian.org/src/scowl/2020.12.07-4/debian/rules/`):

```
SIZE_OPTIONS_small:=-v2 35     -> wbritish-small
SIZE_OPTIONS:=-v2 50           -> wbritish
SIZE_OPTIONS_large:=-v2 70     -> wbritish-large
SIZE_OPTIONS_huge:=-v2 80      -> wbritish-huge     <- UKACD applies from here
SIZE_OPTIONS_insane:=-v3 95    -> wbritish-insane   <- UKACD applies
```

So `wbritish` is SCOWL British at size 50 with variant levels 1 and 2, and its licence is the SCOWL licence, as Debian's own `debian/copyright` confirms. There is nothing to choose here beyond size, and taking it from ESDB upstream is strictly better because upstream is four releases newer and ships a plain list directly. Note that `wbritish-huge` and `wbritish-insane` **do** carry the UKACD obligation.

macOS's `/usr/share/dict/words` is a different artefact again (Webster's 1934, American, archaic) and is not a candidate.

#### 1.3 Hunspell `en_GB` — two distinct lineages, both usable, neither worth it

This is where the licences genuinely differ, and where most secondary write-ups get it wrong.

**Lineage A — Marco A.G. Pinto (the official Hunspell British dictionary).** Forked in 2013 from David Bartlett's abandoned version, itself seeded from Atkinson's Aspell wordlist. `https://wordlist.aspell.net/dicts/` states: "The official British dictionaries are maintained by Marco A.G.Pinto at proofingtoolgui.org. Marco's dictionaries are based on David Bartlett's now abandoned version. They likely have better coverage of British words and fewer Americanisms." The upstream repository's own `LICENSE` file is **GNU LGPL version 3 verbatim** (`https://github.com/marcoagpinto/aoo-mozilla-en-dict/blob/master/LICENSE`). LGPL-3.0 is compatible with GPL-3.0-or-later as a consumer, so this is usable — it is simply a stronger copyleft than needed for a wordlist.

There is a documentation muddle here that anyone reading only LibreOffice's copy would fall into: LibreOffice's `en/README_en_GB.txt` says the dictionary is "covered by his original LGPL licence" **without naming a version**, while the `en/license.txt` sitting in the same directory is **GPL-2.0 verbatim** (`https://github.com/LibreOffice/dictionaries/blob/master/en/license.txt`) — almost certainly because that file covers the whole bundled extension including the Lightproof grammar checker, not the wordlist. GPL-2.0-**only** would be incompatible with GPL-3.0-or-later. Resolve this by citing the upstream Pinto `LICENSE` (LGPL-3.0), not LibreOffice's redistribution.

**Lineage B — SCOWL-derived Hunspell `en_GB`.** ESDB also generates `en_GB-ise` and `en_GB-ize` Hunspell dictionaries. `README_en_GB-ise.txt` in `hunspell-en_GB-ise-2026.02.25.zip` states: "The English dictionaries come directly from SCOWL and is thus under the same copyright terms as SCOWL." Same permissive grant as section 1.1. The README also documents that "the default dictionaries correspond to SCOWL size 60 … The large dictionaries correspond to SCOWL size 70", which independently validates size 60 as upstream's own spell-checking default.

**Both are disqualified on latency, not licence.** A Hunspell dictionary is an affix-compressed `.dic` plus an `.aff` ruleset; using it means running an affix engine, and the only pure-Python one is `spylls`. Measured: **402 ms** to load the LibreOffice/Pinto `en_GB` pair and perform one lookup, against a 500 ms budget for the entire command. See section 3.

#### 1.4 Others considered and rejected

`dwyl/english-words` and similar GitHub scrapes were not pursued: they are American, undated, and their provenance is exactly the "unclear provenance" risk the ticket names. There is no reason to accept that risk when a maintained, first-party, explicitly-licensed British list is available.

---

### 2. Size on disk, import cost and lookup cost — all measured

#### 2.1 Size at each SCOWL cutoff

SCOWL v1 2020.12.07, `mk-list british <size>`, all sub-categories, ISO-8859-1 converted to UTF-8:

| Size | Entries | Plain bytes |
|---:|---:|---:|
| 10 | 4,450 | 35,114 |
| 20 | 12,599 | 106,603 |
| 35 | 50,171 | 459,388 |
| 40 | 57,509 | 533,655 |
| 50 | 101,592 | 959,926 |
| 55 | 108,021 | 1,025,190 |
| **60** | **123,382** | **1,189,464** |
| 70 | 166,522 | 1,622,681 |
| 80 | 343,886 | 3,511,147 |
| 95 | 658,099 | 6,874,128 |

ESDB 2026.02.25 first-party plain wordlists, as shipped and after normalisation (lowercase, NFKD accent-fold, drop anything not pure ASCII letters, deduplicate — this discards possessives, contractions and hyphenated forms, none of which a `snake_case` title can ever produce):

| List | As shipped | Normalised | Normalised bytes | Gzipped |
|---|---:|---:|---:|---:|
| **`en_GB-ise`** | 109,550 | **88,967** | **828,432** | **242,773** |
| `en_GB-ize` | 109,564 | 88,980 | 828,611 | 242,914 |
| `en_GB-large` | 171,326 | 144,891 | 1,411,441 | 392,178 |
| `en_US` | 109,902 | 89,140 | 829,409 | 243,416 |

Normalisation removes 19% of the entries and 20% of the bytes at no cost to behaviour.

#### 2.2 End-to-end cost of the recommended approach

Subprocess wall-clock, median of 21 runs, against a bare-interpreter control measured in the same batch:

| Case | Median | Min | p90 | Delta vs control |
|---|---:|---:|---:|---:|
| bare interpreter (control) | 21.3 ms | 20.6 | 22.6 | — |
| read the list file, build nothing | 21.2 ms | 20.6 | 21.9 | −0.1 ms |
| build `frozenset` (plain, 828 KB) | 31.2 ms | 29.7 | 32.6 | **+9.8 ms** |
| build `frozenset` (gzip, 243 KB) | 34.5 ms | 32.8 | 35.8 | +13.1 ms |
| **full check, typo title `aadvark-jd`** | **33.6 ms** | 30.9 | 35.5 | **+12.3 ms** |
| full check, clean title `small_bodies_and_moons_catalogue` | 33.1 ms | 31.2 | 34.9 | +11.7 ms |
| full check, all-jargon title `soxspipe` | 31.8 ms | 30.8 | 33.7 | +10.5 ms |
| full check, gzip list, `aadvark-jd` | 35.8 ms | 34.8 | 37.0 | +14.5 ms |

**The whole feature costs 12.3 ms of the 500 ms budget, worst case.** Gzipping saves 586 KB in the wheel for 2.2 ms; that trade is available and defensible either way, and the note recommends plain text on KISS grounds.

Splitting the list into per-word-length shards and loading only the three buckets a token can reach was also measured, at +6.0 ms — a 5 ms saving for a materially more complicated resource layout. Not worth it.

In-process, separating load from lookup (median of 20 to 500 iterations):

| Operation | Median | p99 |
|---|---:|---:|
| build the 88,967-word `frozenset` from disk | **5.32 ms** | 5.69 ms (p90) |
| check a clean title (all tokens in the list) | **1.1 µs** | 1.4 µs |
| check `aadvark-jd` (one token misses, 383 candidates generated and intersected) | **31.6 µs** | 37.6 µs |
| check all 43 sample titles | 0.78 ms | — |

Lookup is free. The entire cost is the one-off `frozenset` build, and even that is a third of what the interpreter itself costs to start.

#### 2.3 Edit distance: hand-rolled beats every library

Same control methodology:

| Approach | Median | Delta vs control |
|---|---:|---:|
| bare interpreter | 20.9 ms | — |
| **hand-rolled `edits1`, no import at all** | 28.5 ms | **+7.7 ms** |
| `import difflib` (stdlib) | 27.2 ms | +6.3 ms |
| `from rapidfuzz.distance import Levenshtein` | 33.5 ms | +12.6 ms |
| `import rapidfuzz` | 35.4 ms | +14.5 ms |
| `import textdistance` | 45.1 ms | +24.2 ms |

Importing `rapidfuzz` costs more than the entire hand-rolled solution, and `textdistance` costs three times as much. Both are MIT and both are fine licence-wise; neither earns its place. The classic Norvig deletion/transposition/replacement/insertion generator is twelve lines, has no import cost, and runs in 31.6 µs against an 89k-word set.

Note also that a candidate-generation approach and a distance-scan approach are not equivalent in cost. Generating the ~383 distance-1 strings and intersecting with a `frozenset` is O(1) in the dictionary size; scanning 89k words with `rapidfuzz` is not. The generator is the right shape here regardless of library.

---

### 3. Does an existing pure-Python package already solve this?

**No. Every one of them fails on at least one of: `en_GB` support, import cost, or data provenance.**

| Package | Version | Code licence (from its own LICENSE file) | Bundled `en_GB`? | Measured cost | Verdict |
|---|---|---|---|---|---|
| **`spylls`** | 0.1.7 | **MPL-2.0** (PyPI classifier wrongly says MIT) | **No** — ships `en_US`, `ru`, `sv` only | import 59 ms; **load `en_GB` + 1 lookup 402 ms** | **Disqualified on latency.** MPL-2.0 is GPL-3-compatible, so licence is not the problem — 402 ms of a 500 ms budget is |
| **`symspellpy`** | 6.10.0 | MIT | **No** — bundles `frequency_dictionary_en_82_765.txt`, American | import 44 ms; **load bundled dict at ed=2: 1,212 ms**; load SCOWL br-60 as its dict: **1,234 ms** | **Disqualified.** SymSpell precomputes a deletion index at load; that is the correct design for a long-lived process and exactly wrong for a CLI paying it on every invocation |
| **`pyspellchecker`** | 0.9.0 | MIT (code) | **No** — `en.json.gz` only, no `en_GB` resource exists | import 30.6 ms; construct + one `unknown()` **87 ms** (+66 ms over control) | **Disqualified twice over.** Its `en` is missing **18 of 25** common British spellings including `colour`, `centre`, `behaviour`, `programme`, `aluminium`, `metre`. And its dictionary is derived from the **OpenSubtitles/OPUS** corpus with **no licence stated for the data** — precisely the unclear-provenance risk the ticket flags |
| **`wordfreq`** | 3.1.1 | Apache-2.0 code, **CC-BY-SA-4.0 data** | **No.** `word_frequency(w, 'en-GB')` emits "Using the nearest match, which is 'en'" and returns the identical `en` figure | import **101 ms**; first `word_frequency` call **152 ms** | **Disqualified.** It is a frequency table, not a dictionary, so it cannot answer "is this a word". Its README also explicitly forbids extracting the data to a plain wordlist: "No. The CSV format does not have any space for attribution or license information, and therefore does not follow the CC-By-SA license." CC-BY-SA-4.0 is one-way GPLv3-compatible, but the express prohibition settles it |
| **`autocorrect`** | 2.6.1 | **LGPL-3.0** | **No** — `data/en.tar.gz` only, American | import 59 ms; construct `Speller('en')` **106 ms** | **Disqualified.** No `en_GB`, and adding a language triggers a **runtime download from IPFS gateways** (`autocorrect/constants.py` `ipfs_gateways`, with Dropbox `backup_urls`) — a blocking network call on the CLI path, which is the exact thing this effort exists to remove |
| **`textdistance`** | 4.6.3 | MIT | n/a — algorithms only | import **45.1 ms** (+24.2) | Rejected on import cost; no dictionary anyway |
| **`rapidfuzz`** | 3.14.5 | MIT | n/a — algorithms only | import 35.4 ms (+14.5) | Rejected on import cost. Also a compiled C++ extension rather than pure Python, though it ships wheels so there is no system dependency |
| `Levenshtein` | 0.27.4 | **GPL-2.0-or-later** | n/a | not benchmarked | Would be legally fine (`-or-later` reaches GPL-3), but pointless given the above |

The comparison is not close. Shipping an 828 KB text file and twelve lines of Python is **10× cheaper than the fastest packaged alternative** and is the only option that gets genuine British English.

---

### 4. Tokenisation, and why it matters more than the wordlist

The ticket asked whether tokenisation changes the numbers more than the wordlist choice does. It does, decisively.

#### 4.1 The rule

```
1. Split the title on [_ \- \s .]  (underscore, hyphen, whitespace, full stop)
2. Skip a token unless it is entirely ASCII letters   -> drops digits, emoji, accents
3. Skip a token that is entirely uppercase            -> drops acronyms (NASA, ZTF)
4. Skip a token shorter than 6 characters
5. Lowercase what remains
6. Flag a token only if it is absent from the wordlist AND at least one
   distance-1 word is present in the wordlist
```

Behaviour on awkward inputs, verified:

| Input | Tokens checked |
|---|---|
| `aadvark-jd` | `['aadvark']` — `jd` dropped as too short |
| `10.01_project_alpha` | `['project']` — `10`, `01` dropped, `alpha` too short |
| `🚀_rocket_science` | `['rocket', 'science']` |
| `P31_code⚡️` | `[]` |
| `NASA_archive` | `['archive']` — acronym dropped |
| `atlas_forced_phot_plotting_script` | `['forced', 'plotting', 'script']` — `atlas` and `phot` too short |
| `catalogue2024` | `[]` — a token mixing letters and digits is skipped whole |
| `café_notes` | `[]` — non-ASCII token skipped |
| `CamelCaseTitle` | `['camelcasetitle']` — silent, but see the caveat below |

#### 4.2 The numbers, on the 43-title sample

Sensitivity to the minimum-length threshold, holding wordlist and gate fixed (ESDB `en_GB-ise` 60 normalised, distance-1 gate):

| Minimum token length | Titles flagged | False positives | `aadvark` caught? | The false positives |
|---:|---:|---:|---|---|
| 3 | 9/43 | 8 | yes | `phot`, `repo`, `hmpty`, `lsst`, `neddy`, `soxs`, `rse`, `macos` |
| 4 | 8/43 | 7 | yes | as above minus `rse` |
| 5 | 4/43 | 3 | yes | `hmpty`, `neddy`, `macos` |
| **6** | **1/43** | **0** | **yes** | — |
| 7 | 1/43 | 0 | yes | — |
| 8 | 0/43 | 0 | **no** | — |

Sensitivity to the gate, holding minimum length at 6:

| Gate | Titles flagged | False positives |
|---|---:|---:|
| bare membership (flag anything not in the list) | 13/43 | 12 |
| **+ require a distance-1 word to exist** | **1/43** | **0** |

And sensitivity to the wordlist, holding tokenisation and gate fixed — the point of the exercise:

| Wordlist | False positives | `aadvark` caught? |
|---|---:|---|
| ESDB `en_GB-ise` 60 | 0 | yes |
| ESDB `en_GB-ize` 60 | 0 | yes |
| ESDB `en_GB-large` (70) | 0 | yes |
| ESDB `en_US` 60 | 0 | yes |
| SCOWL v1 british full 50 / 60 / 70 | 0 | yes |
| SCOWL v1 british **words-only** 60 (no proper names) | 1 (`soxs_marshall` → `marshall`) | yes |
| `spylls` + LibreOffice/Pinto `en_GB` Hunspell | 2 (`marshall`, `vscode`) | yes |
| `pyspellchecker` `en` | 0 on this sample, but see §3 | yes |

Under a **naive** tokeniser (split on every non-alpha run, no length floor, bare membership) the same wordlists produce **21 or 22 false positives out of 43**. That is the whole finding in one line: tokenisation and gating move the number by 21; the wordlist moves it by 1.

The one thing the wordlist choice *does* buy is `marshall`. Including SCOWL's `proper-names` and `upper` sub-categories — which the recommended `en_GB-ise` list already does — is what stops `soxs_marshall` being offered a correction. Do not ship a words-only list.

#### 4.3 Recall — does the gate still catch real typos?

Against 34 common English misspellings plus `aadvark`:

| Gate | Sample false positives | Tech-vocabulary false positives | Typo recall | Cost per token |
|---|---:|---:|---:|---:|
| **distance 1** | **0/42** | 17/92 (18%) | **30/34** | **0.03 ms** |
| distance 2 | 6/42 | 45/92 (49%) | 34/34 | 25.67 ms |

Distance 2 buys the last four typos (`maintainance`, `publically`, `reccomend`, `tommorow`) and pays for them with a **49% false-positive rate on technical vocabulary**, six false positives on the sample, and an **850× increase in per-token cost**. Reject it on all three axes. The four misses at distance 1 are the correct trade for an offer-only nicety.

Separately, `wierd` is missed — not by the distance gate but by the length floor, since it is five characters. That is the price of the minimum-length-6 rule and it is worth paying.

#### 4.4 The caveat the sample hides

Running the same configuration over a 94-token vocabulary of realistic Python, astronomy and developer-tool names:

| Outcome | Count | Share |
|---|---:|---:|
| already in the wordlist (silent, correct) | 34 | 36% |
| unknown but silent — no distance-1 word exists | 43 | 46% |
| **false positive — a correction would be offered** | **17** | **18%** |

The seventeen: `jupyter → jupiter`, `uvicorn → unicorn`, `gunicorn → unicorn`, `postgres → postures`, `pydantic → pedantic`, `dagster → dragster`, `topcat → tomcat`, `aladin → aladdin`, `spitzer → spritzer`, `seaborn → seaborne`, `xarray → array`, `polars → polar`, `rustup → dustup`, `openid → opened`, `bcrypt → crypt`, `scrypt → script`, `alerce → amerce`.

The 43-title sample scores 0 because its jargon (`soxspipe`, `panstamps`, `atelparser`, `transientnamer`, `gocart`, `skytag`, `lasair`) sits at distance 2 or more from any English word. That is luck, not a property of the design, and the note would be dishonest to present the 0 without this number beside it.

**Consequence for the implementation.** The feature needs a learned per-user vocabulary, not just a wordlist:

- Record every token the user dismisses a suggestion on, and never offer on it again. This bounds the annoyance at **one offer per novel token, ever**.
- Do **not** bulk-seed that vocabulary from the existing tree. Seeding from the live index would immediately silence `aadvark`, since it is already in the tree — the exact case the feature exists to catch. Learn forward from creations and dismissals only. If the existing tree should be audited for typos, that is a separate one-shot `av` command, not a side effect of seeding.
- Optionally ship a short stop-list of common technology names alongside the wordlist. This is a nicety on top of the learned vocabulary, not a substitute for it — the list can never be complete.

#### 4.5 Two known tokenisation gaps

- **Accented tokens are never checked.** `café` fails the ASCII test and is skipped, so a misspelling of an accented British word is silently missed. The fix, if it ever matters, is to NFKD-fold the token before testing rather than rejecting it, since the shipped list is already folded. **Not implemented in the measured configuration.**
- **CamelCase is not split.** `CamelCaseTitle` becomes one long token, which was verified to be silent against this list but is silent by luck rather than by rule. Either split on case transitions, or skip any token with an internal capital. **Not measured either way** — worth resolving during implementation, not before.

---

## Recommendation

Ship the following inside `aardvark_jd/resources/`. The package already declares `aardvark_jd = ["resources/**/*"]` under `[tool.setuptools.package-data]`, so this is a drop-in with no packaging change.

**Wordlist:** ESDB (SCOWL) `en_GB-ise`, release **2026.02.25**, taken from `https://github.com/en-wl/wordlist-diff/blob/rel-2026.02.25/en_GB-ise.txt`, normalised to lowercase ASCII letters with accents folded and duplicates removed.

**Licence:** the SCOWL/ESDB permissive attribution grant, Copyright 2000-2026 Kevin Atkinson, from `https://github.com/en-wl/wordlist-diff/blob/rel-2026.02.25/Copyright`. **GPL-3.0-compatible.** Size 60 is below the size-80 threshold at which the UKACD notice attaches, and is not Australian, so neither conditional copyright applies. The one obligation is to ship the copyright notice beside the list — put the `Copyright` file in `aardvark_jd/resources/` next to the wordlist and reference it from the project `LICENSE`.

**Measured size:** 88,967 words, **828,432 bytes** plain (242,773 bytes gzipped, from 1,030,707 bytes as shipped upstream). Recommend plain text: gzip saves 586 KB and costs 2.2 ms.

**Measured import cost:** **+12.3 ms** wall-clock over a bare interpreter for the complete check on the worst-case title, subprocess median of 21 runs. In-process that decomposes into a **5.32 ms** one-off `frozenset` build and a **31.6 µs** lookup (**1.1 µs** when nothing is flagged). Against a 500 ms budget this is **2.5%**.

**Measured lookup cost:** 1.1 µs for a clean title, 31.6 µs when a token misses and 383 distance-1 candidates are generated and intersected, 0.78 ms for all 43 sample titles together.

**Edit distance:** hand-rolled Damerau-Levenshtein-1 candidate generation (delete, transpose, replace, insert over `a-z`) intersected with the `frozenset`. **No new dependency.** `rapidfuzz` costs more to import than this costs to run; `textdistance` costs three times as much.

**Tokenisation rule:** split on `[_\-\s.]`; skip any token that is not entirely ASCII letters, that is entirely uppercase, or that is shorter than **6 characters**; lowercase the rest. Offer a correction only when the token is absent from the wordlist **and** at least one distance-1 word is present in it.

**Measured false positives on the supplied 43-title sample: 0.** Exactly one title is flagged — `aadvark-jd` — and the suggestion offered is **`aardvark`**. **Yes, `aadvark` is caught.** All of `soxspipe`, `panstamps`, `atelparser`, `lasair`, `gocart`, `skytag`, `hmpty`, `neddy`, `astrocalc`, `transientnamer`, `dotfile`, `vscode` and `xxxpython_package_templatexxx` stay silent. Typo recall on an independent set of 34 common misspellings is **30/34**; the four misses are all distance-2 errors, and distance 2 is rejected because it costs 49% false positives on technical vocabulary and 850× the runtime.

**Measured false positives on a wider realistic technical vocabulary: 17 of 94 tokens (18%).** This is the real number to design against. Pair the wordlist with a learned per-user vocabulary that records dismissals, so any given token can be offered on at most once. Do not bulk-seed that vocabulary from the existing tree, because doing so would silence `aadvark` on day one.

### Not measured

Stated plainly rather than estimated:

- **The current `av` command's own startup cost.** `av` and `aardvark` are not on `PATH` on this machine, so the baseline the 12.3 ms is being added to was not measured. The 12.3 ms figure is a delta against a bare interpreter and is valid on its own terms, but the headroom against the 500 ms gate is unverified. Measure it before treating the gate as satisfied — that is ticket 09's job.
- **The two tokenisation gaps in §4.5** (accent folding, CamelCase), neither of which is implemented or measured in the recommended configuration.
- **Whether `en_GB-ise` counts as an "official speller dictionary"** for the purposes of the ESDB copyright's carve-out sentence. The size-based UKACD rule makes the question moot at size 60, but the wording mismatch is noted rather than resolved.

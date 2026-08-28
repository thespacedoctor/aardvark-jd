# Which en_GB wordlist ships with aardvark?

Type: research
Status: resolved
Blocked by: none

## Question

What pure-Python, no-system-dependency options exist for checking a title against UK English spelling, and which wordlist can actually be redistributed inside this package?

Agreed while charting: no `pyenchant` or `hunspell`, because a system dependency for a nicety is a bad trade, and no LLM call, because this effort is about removing blocking network calls from the CLI path. That leaves a wordlist shipped in `aardvark_jd/resources/` plus an edit-distance check.

Establish:

- The candidate `en_GB` wordlists, with their licences. Licence is the binding constraint: the package is distributed on PyPI, so the list must be redistributable under a licence compatible with the project's. SCOWL and its derivatives, `wbritish`, and the Hunspell `en_GB` dictionaries all have different terms.
- The size on disk of each candidate at various word-frequency cutoffs, and the resulting import and lookup cost, since this runs on a command that must return in under 500 ms.
- Whether an existing pure-Python package already solves this acceptably, and under what licence, versus shipping a raw list.
- The false-positive rate against a realistic sample: the 52 real titles in the live index, which are heavy with proper nouns and astronomy jargon such as `soxspipe`, `lasair`, `panstamps` and `atelparser`. A candidate that flags most of those is disqualified regardless of licence.

The answer names a recommended wordlist and licence, with the measured size and false-positive figures behind the recommendation.

## Context pointer

Dispatched to a research subagent on 2026-08-27. **The agent was stopped before completing and produced no findings.** It reported that its attempts to read the live system tree were blocked by the permission classifier, and it was falling back to the jargon sample supplied in this ticket when it was halted. No deliverable was written. The ticket is unclaimed and back on the frontier.

Note for whoever retakes it: reading the live tree is **not** required. The jargon sample in point 4 of the question is sufficient for the false-positive measurement, and the repo's own project directory names supply more. A retry should measure against that sample directly and avoid the live system entirely.

## Answer

Resolved 2026-08-28. Full findings, with sources and measurements: [research/en-gb-wordlist.md](../research/en-gb-wordlist.md).

**Ship the ESDB/SCOWL `en_GB-ise` size-60 plain wordlist in `aardvark_jd/resources/`, plus a hand-rolled Damerau-Levenshtein-1 candidate generator. No new dependency.**

- **Licence: settled and easy.** SCOWL/ESDB permissive attribution grant, Copyright 2000-2026 Kevin Atkinson, GPL-3.0-compatible. The only real encumbrance in this space is the UKACD notice, and it attaches only to lists **larger than size 80**, so size 60 is clean. The obligation is to ship the `Copyright` file beside the list and reference it from the project `LICENSE`.
- **Latency, not licence, was the deciding constraint.** `spylls` takes 402 ms to load an `en_GB` Hunspell dictionary and `symspellpy` takes 1,212 ms to build its index, both fatal against the 500 ms gate. `pyspellchecker`, `wordfreq` and `autocorrect` have no `en_GB` at all. The raw list plus a `frozenset` costs **+12.3 ms**, which is 2.5 per cent of the gate.
- **Measured size:** 88,967 words, 828,432 bytes plain. Ship it plain; gzip saves 586 KB and costs 2.2 ms.
- **Tokenisation matters far more than the wordlist does.** Across nine SCOWL size variants the false-positive count on the 43-title sample moved by 1 under the right tokeniser, and by 21 under a naive one. Two rules do all the work: check only tokens of **six characters or more**, and offer only when a **distance-1 dictionary word actually exists**.
- **`aadvark` is caught**, suggesting `aardvark`, with **0 false positives** on the 43-title sample. Typo recall on an independent set is 30/34; the four misses are all distance-2, and distance 2 is rejected at 49 per cent false positives and 850 times the runtime.

**The finding that reshapes the feature.** The 43-title sample scores 0 only because its jargon happens to sit at distance 2 or more from English. On a wider realistic technical vocabulary the same configuration flags **17 of 94 tokens, an 18 per cent false-positive rate**, including `jupyter` to `jupiter`, `pydantic` to `pedantic` and `postgres` to `postures`. A learned per-user vocabulary recording dismissals is therefore **part of the feature, not a refinement of it**, and it must not be bulk-seeded from the existing tree, because that would silence `aadvark` on day one. This surfaced [Where does the learned per-user vocabulary live?](10-learned-vocabulary-storage.md).

**Two corrections to assumptions carried in the question.** `wbritish` is not an independent candidate: Debian builds it from `src:scowl` at size 50. And the LibreOffice `en_GB` licence documentation is genuinely self-contradictory, with `README_en_GB.txt` claiming LGPL while `license.txt` beside it is GPL-2.0 verbatim, which would **not** be GPL-3.0-or-later compatible; do not cite LibreOffice for a licence claim.

**Not measured, stated rather than estimated.** The current `av` startup cost was not measured, because neither `av` nor `aardvark` is on `PATH` on this machine. The 12.3 ms is a delta against a bare interpreter, so headroom against the 500 ms gate remains unverified and belongs to [Measure `av add_project` after content comparison lands](09-measure-latency-after-comparison.md).

# Is the spell-checker's tuning wrong?

Type: grilling
Status: resolved
Assignee: Dave

## Question

Surfaced by [ticket 08](08-spell-check-surface.md)'s measurement, which set out to find the false-positive rate and found two defects in the checker itself instead. Both are CLI-side and change terminal behaviour as well as Alfred's, so neither belonged in ticket 08's answer. Neither blocks [ticket 13](13-assemble-the-spec.md): the Alfred surface is rows on a confirmation screen regardless of which tokens fire.

The measurement is in [the ticket 08 probe](../prototypes/08-spell-check/probe.md), reproducible from the three scripts beside it.

### The evidence

On 141 unique human-typed folder titles, the checker fired twice, and both were false positives. It found no real typos. The corpus contains exactly one genuine typo — `woth` for "with" — which it missed, while flagging `spectro` in that same title. On 92 titles with one realistic typo injected into a genuine dictionary word, it offered the right correction 57.6 per cent of the time, offered a **wrong** word 25.0 per cent of the time, and said nothing 17.4 per cent of the time.

Broken down by typo kind, the failure is not spread evenly: transpositions are caught 78.3 per cent of the time and substitutions 71.4 per cent, but **dropped letters only 36.6 per cent**. The reason is mechanical — **12 of the 16 silent misses were never checked at all**, because dropping a letter from a six-character word leaves five, and `tokenise` skips anything under six. `system → sysem`, `syste`, `sstem`, `sytem`, `family → famil` and `active → acive` are all invisible.

A third pattern showed up in the wide 11,102-folder sweep, which fires on 379 titles that collapse to just 98 distinct suspect tokens. Most are technical proper nouns — `xshooter`, `laravel`, `golang`, `quarkus` — exactly what the learned vocabulary exists to silence, one dismissal each. But `normalize → normalise` and `optimizer → optimiser` are **American spellings**, and the shipped wordlist is `en_GB-ise`. That is a different kind of false positive: it recurs on every new title carrying a US spelling rather than being retired by a single dismissal, and what it offers is not a typo correction but a house-style opinion the checker was never asked for.

Decide:

- **Should American spellings be flagged at all?** The `-ise` wordlist makes every `-ize` form a suspect token. Options: ship the `en_GB` list that accepts both endings, add the common `-ize`/`-or` forms to the shipped vocabulary, or accept the flagging as a deliberate house-style nudge. Note that this class cannot be solved by the learned vocabulary the way jargon can — the user would be dismissing a new word every time rather than teaching a fixed set.

- **Is `MINIMUM_TOKEN_LENGTH = 6` too high?** The threshold exists because short tokens are where false positives live — every three-letter fragment is one edit from a dictionary word — and `spell_check.py` documents that the rule does most of the work of keeping the rate down. But the measurement shows it is not merely blunting sensitivity to short words: it makes the commonest typo class structurally undetectable in the six- and seven-character words that dominate real titles, and it hid the only real typo in the corpus. Decide whether the floor moves, and if so whether it moves for all tokens or only where the typo is a deletion from a longer neighbour — a five-character token with a six-character distance-1 candidate is a different risk from a five-character token in general. The rate at each candidate floor is measurable on the corpus the probe already assembles, so this decision should be made against numbers, not argued.

- **Is the tie-break wrong?** With no frequency data, `suggest` returns the shortest distance-1 candidate, breaking ties alphabetically — deterministic, on the reasoning that a wrong offer costs one keystroke to decline. The measurement says it is wrong 25.0 per cent of the time, and wrong in a way that reads as broken rather than merely unhelpful: `arhive → arrive`, `servies → series`, `setings → stings`, `imates → mates`. Note that "one keystroke to decline" understates the cost — a wrong offer that is *plausible* invites a wrong acceptance, which corrupts the folder name, the index row and all three mirrors at once. Decide whether a frequency-ranked list is worth shipping, whether the existing SCOWL sizes can stand in for frequency (a word in the size-35 list is commoner than one that first appears at size-70), or whether preferring the *longest* candidate, or the one sharing the token's first letter, recovers most of the gap for nothing. Note that "shortest candidate" is precisely the rule that turns a dropped letter into a wrong offer.

- **Does the offer rate justify either change?** The feature fires on 1.4 per cent of titles today. A lower floor raises both the catch rate and the false-alarm rate, and the false alarms are the ones that cost attention. Decide what per-title fire rate is acceptable before deciding the thresholds that produce it.

- **Does any of this change the non-interactive path?** Scripts and Alfred get one stderr note per suspect token instead of a prompt. A noisier checker makes that path noisier too, and nothing reads those notes.

- **Does the docstring's 18 per cent claim need correcting?** It is a token-level rate from a synthetic technical vocabulary, and ticket 08 read it as a per-title rate — the real per-title rate is 1.4 per cent, and the real token-level rate on live titles is 1.5 per cent. Whether or not the tuning changes, the figure in the module docstring invites the same misreading again.

## Resolution (2026-09-04)

**Two changes, both measured: fix the tie-break, and move the floor from 6 to 5. No wordlist change.** The sweep is in [the ticket 16 probe](../prototypes/16-spell-check-tuning/report.md), run against ticket 08's corpus and seed so the numbers compare directly.

### The tie-break is wrong, and fixing it is free

`suggest` prefers the shortest distance-1 candidate. A dropped letter is the commonest real typo and leaves a token *shorter* than its correction, so the shipped rule picks against the commonest case by construction. Replacing `min(len(word), word)` with `min(-len(word), word)` takes right offers from 57.6 to **75.0 per cent** and wrong offers from 25.0 to **7.6 per cent** at the current floor.

It costs nothing. The tie-break decides *which* candidate is offered, never *whether* one exists, so the fire rate is identical either way — verified as a constant column down the whole sweep. The wrong offers that read as broken largely stop: `setings → stings` becomes `settings`, `servies → series` becomes `services`.

Worth recording so it is not re-litigated: **"prefer the longest candidate" and "assume a dropped letter first" are the same rule.** At edit distance 1 a candidate is only ever one shorter, the same length, or one longer — verified, the observed offsets are exactly `[-1, 0, +1]` — so descending length *is* deletion-first ordering. Ship the simpler expression and document the reasoning.

### The floor moves to 5

Dropped-letter recall goes from 61.0 to **87.8 per cent** and the silent rate from 17.4 to **5.4 per cent**. The whole cost is four more suspect tokens across the 141 real titles, and all four are proper nouns or product names — `ciara`, `lagan`, `macos`, `silla` — which is precisely the population the learned vocabulary retires at one dismissal each. Per-title fire rate goes from 1.4 to **4.3 per cent**, one title in twenty-three.

The acceptance criterion, stated before the threshold rather than fitted to it: **at most 5 per cent of titles firing.** Ticket 08 established that the Alfred surface costs no keystrokes for a fired check (the corrections are rows on the confirmation screen), and one prompt in twenty-three is tolerable on the terminal path.

**Floor 4 is rejected on its own numbers**: identical recall to floor 5, and 12.8 per cent of titles firing — one in eight. It is the only floor that sees the corpus's single genuine typo, `woth`, and it still offers the wrong word, because `with` and `worth` are both distance 1 and `with` loses the tie under either rule. That trades a silent miss for a wrong offer, which is the worse failure.

### American spellings: no change, and the ticket's premise was overstated

The 1,903 `-ize`/`-ization`/`-izer`/`-yze` twins the `en_GB-ise` list omits were generated and the sweep re-run against the extended list. On the 141 human-typed titles: **no effect whatsoever**. On the wide 11,264-folder sweep: 98 distinct suspect tokens fall to 95.

The ticket feared this class recurs where jargon self-silences. It does not: dismissals are keyed per token, so `normalize` is dismissed once and stays dismissed, and the entire population is three tokens. The figure is also an over-estimate, since the mechanical generation admits non-words — `wize`, `promize`, `precize`, `paradize` and `franchize` are all in the extended list — so a curated `en_GB` list would silence the same three tokens at most, while masking any genuine typo landing on one of those non-words.

### The docstring is corrected

The module docstring's "18 per cent" is a token-level rate on a synthetic technical vocabulary, and it has already been misread once as a per-title rate. It states both rates with their denominators instead: per-title 1.4 per cent today, 4.3 per cent under the new tuning; token-level 1.5 per cent on live titles. The `MINIMUM_TOKEN_LENGTH` comment is rewritten too — it currently claims the floor "does most of the work", which is true of the false-positive rate but silently omits that the floor is also what made the commonest typo class undetectable.

### Consequences

- **Non-interactive path.** Scripts and Alfred get one stderr note per suspect token, so that path goes from 1.4 to 4.3 per cent of titles carrying a note. Nothing reads them; accepted, no change.
- **This is a CLI change, not an Alfred one.** It alters terminal behaviour too, and it does not block [ticket 13](13-assemble-the-spec.md) — the Alfred surface is rows on a confirmation screen regardless of which tokens fire. It ships as its own test-first slice, independent of the Alfred build.
- One note to ticket 13: the spec's spell-check section should quote **4.3 per cent** as the expected fire rate, not ticket 08's 1.4 per cent, since the confirmation screen will carry correction rows about three times as often as ticket 08 measured.

### Validity

The two review subagents dispatched against the sweep script both failed on a session rate limit, so the checks they were given were run directly: the trial set is identical across floors (92 typos, compared equal), the suffix chain in the `-ize` generator does not shadow itself, and the longest/deletion-first equivalence is confirmed empirically. One limitation stands: because ticket 08's injector corrupts only six-plus-character tokens, the recall figures do not measure typos in five-character words, which floor 5 also begins to check. Their false alarms *are* measured, in the fires/title column.

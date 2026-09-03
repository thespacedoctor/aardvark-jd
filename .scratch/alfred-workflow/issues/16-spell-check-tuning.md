# Is the spell-checker's tuning wrong?

Type: grilling
Status: open

## Question

Surfaced by [ticket 08](08-spell-check-surface.md)'s measurement, which set out to find the false-positive rate and found two defects in the checker itself instead. Both are CLI-side and change terminal behaviour as well as Alfred's, so neither belonged in ticket 08's answer. Neither blocks [ticket 13](13-assemble-the-spec.md): the Alfred surface is rows on a confirmation screen regardless of which tokens fire.

The measurement is in [the ticket 08 probe](../prototypes/08-spell-check/probe.md), reproducible from the three scripts beside it.

### The evidence

On 141 unique human-typed folder titles, the checker fired twice, and both were false positives. It found no real typos. The corpus contains exactly one genuine typo — `woth` for "with" — which it missed, while flagging `spectro` in that same title. On 92 titles with one realistic typo injected into a genuine dictionary word, it offered the right correction 57.6 per cent of the time, offered a **wrong** word 25.0 per cent of the time, and said nothing 17.4 per cent of the time.

Broken down by typo kind, the failure is not spread evenly: transpositions are caught 78.3 per cent of the time and substitutions 71.4 per cent, but **dropped letters only 36.6 per cent**. The reason is mechanical — **12 of the 16 silent misses were never checked at all**, because dropping a letter from a six-character word leaves five, and `tokenise` skips anything under six. `system → sysem`, `syste`, `sstem`, `sytem`, `family → famil` and `active → acive` are all invisible.

Decide:

- **Is `MINIMUM_TOKEN_LENGTH = 6` too high?** The threshold exists because short tokens are where false positives live — every three-letter fragment is one edit from a dictionary word — and `spell_check.py` documents that the rule does most of the work of keeping the rate down. But the measurement shows it is not merely blunting sensitivity to short words: it makes the commonest typo class structurally undetectable in the six- and seven-character words that dominate real titles, and it hid the only real typo in the corpus. Decide whether the floor moves, and if so whether it moves for all tokens or only where the typo is a deletion from a longer neighbour — a five-character token with a six-character distance-1 candidate is a different risk from a five-character token in general. The rate at each candidate floor is measurable on the corpus the probe already assembles, so this decision should be made against numbers, not argued.

- **Is the tie-break wrong?** With no frequency data, `suggest` returns the shortest distance-1 candidate, breaking ties alphabetically — deterministic, on the reasoning that a wrong offer costs one keystroke to decline. The measurement says it is wrong 25.0 per cent of the time, and wrong in a way that reads as broken rather than merely unhelpful: `arhive → arrive`, `servies → series`, `setings → stings`, `imates → mates`. Note that "one keystroke to decline" understates the cost — a wrong offer that is *plausible* invites a wrong acceptance, which corrupts the folder name, the index row and all three mirrors at once. Decide whether a frequency-ranked list is worth shipping, whether the existing SCOWL sizes can stand in for frequency (a word in the size-35 list is commoner than one that first appears at size-70), or whether preferring the *longest* candidate, or the one sharing the token's first letter, recovers most of the gap for nothing. Note that "shortest candidate" is precisely the rule that turns a dropped letter into a wrong offer.

- **Does the offer rate justify either change?** The feature fires on 1.4 per cent of titles today. A lower floor raises both the catch rate and the false-alarm rate, and the false alarms are the ones that cost attention. Decide what per-title fire rate is acceptable before deciding the thresholds that produce it.

- **Does any of this change the non-interactive path?** Scripts and Alfred get one stderr note per suspect token instead of a prompt. A noisier checker makes that path noisier too, and nothing reads those notes.

- **Does the docstring's 18 per cent claim need correcting?** It is a token-level rate from a synthetic technical vocabulary, and ticket 08 read it as a per-title rate — the real per-title rate is 1.4 per cent, and the real token-level rate on live titles is 1.5 per cent. Whether or not the tuning changes, the figure in the module docstring invites the same misreading again.

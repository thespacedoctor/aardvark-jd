# When and how does aardvark offer a spelling correction?

Type: grilling
Status: resolved
Blocked by: 05

## Context from ticket 05 (2026-08-28)

[Which en_GB wordlist ships with aardvark?](05-research-en-gb-wordlist.md) is resolved, so this ticket is unblocked. Two of its findings bear directly on the interaction design:

- **The number to design against is an 18 per cent false-positive rate**, not the 0 per cent measured on the 43 live titles. That sample scores 0 only because its jargon happens to sit at distance 2 or more from English; a wider technical vocabulary flags 17 of 94 tokens.
- **A learned vocabulary of dismissals is part of the feature.** Its storage is [Where does the learned per-user vocabulary live?](10-learned-vocabulary-storage.md), but *when* a dismissal is recorded, and whether it is keyed on the token or the token-plus-suggestion, is this ticket's call and blocks that one.

The mechanism is settled and is not up for rediscussion here: tokens of six characters or more, split on `[_\-\s.]`, offered only when a distance-1 dictionary word exists.

## Question

Given a wordlist that can flag a suspect word in a title, what does the user actually experience?

The request was to "offer to correct my spelling" when creating a new project, area, category or ID. Offer is the operative word: the check must never block or silently rewrite, because the false-positive rate on this user's jargon-heavy titles will be high whatever list ticket 05 lands on.

Decide:

- Which inputs are checked. Titles only, or descriptions too? Descriptions are longer, so they cost more time and produce more false positives, but they are also where prose errors actually live.
- The interaction itself. A prompt per suspect word, a single prompt offering a whole corrected title, or a warning printed after the fact with a suggested follow-up command?
- The non-interactive contract. What happens when stdin is not a TTY, which covers scripted use and the test suite. Silently skipping is the obvious answer but it means the check is invisible in exactly the case where a typo gets committed to a folder name.
- Whether an accepted correction is applied to the folder name on disk as well as the index title, given a rename after creation is a `set_emoji`-shaped operation that also has to repoint every mirror.
- Whether the user can teach it a word, and if so where that personal list is stored. Without this, the same false positives recur forever and the feature becomes noise the user learns to dismiss reflexively.
- Where in the command's flow the check runs, given the 500 ms gate covers the whole command.

The last two points are the ones most likely to decide whether this feature is worth building at all. If it cannot learn, it may not be worth having.

## Answer

Resolved 2026-08-28. Grilling session (`grilling` + `domain-modeling` skills per the map's Notes), against `add_area.py`, `add_category.py`, `add_id.py`, `add_project.py`, `cl_utils.py`, `emoji_picker.py`, `set_emoji.py`, `commands.py`.

### What the user experiences

A per-suspect-word prompt, shown **before** anything is created, in the same `get()` that resolves the emoji and **ahead of** the emoji prompt — accepting a correction changes the title the emoji is derived from.

For each token the checker flags (tokens of six characters or more, split on `[_\-\s.]`, a distance-1 dictionary word exists — mechanism fixed by ticket 05), print one prompt offering the single highest-frequency distance-1 candidate:

```
'aadvark' — did you mean 'aardvark'? [y/N]
```

- **`y`** — substitute that token in the title, preserving the original token's leading case (`Aadvark` → `Aardvark`) and every surrounding separator and other token.
- **`N` / bare Enter** — keep the title as typed **and** record the token in this user's learned vocabulary, permanently. The low-friction answer is the permanent one, so the feature self-silences on recurring jargon as it is used. This is the answer to ticket 06's "is it worth building" question: yes, because it goes quiet on its own.
- Multiple flagged tokens in one title are prompted one at a time, in title order, independently.
- Only the single best candidate is offered; if it is wrong the user declines and re-runs the command.

The resulting title — corrected or unchanged — is the single value everything downstream is built from: the on-disk folder name, the index row, and all three mirrors (craft / Todoist / Google Drive sync afterwards from the DB). There is **no** post-creation title rename and **no** `set_emoji`-shaped mirror repoint: that branch is designed out by checking before the write.

### Scope

- **Titles only.** Descriptions (`add_area`, `add_category`, `add_id` carry one; `add_project` does not) are not checked. Revisit only if a missed description typo proves a real problem in practice.
- **`init <systemName>` is excluded** — a one-time action, a display label rather than a folder-tree title, and outside the original request.
- The learned vocabulary is **one global list** for this user, shared across all four `add_*` commands. It records the user's jargon, not any one command's.

### Non-interactive (non-TTY) contract

stdin not a TTY (scripts, CI, the test suite): create the entity **exactly as typed**, never block, never fail. Print one note per suspect token to **stderr**:

```
note: 'aadvark' in title may be a typo of 'aardvark'
```

This note **also filters through the learned vocabulary** — a token dismissed interactively stays quiet in later scripted runs.

### Learned vocabulary — decided here, located in ticket 10

- **A dismissal is recorded** on every declined suggestion. Plain `[y/N]`, no three-way `never` prompt.
- **Keyed on the token alone**, not token-plus-suggestion: if `pydantic` is a word the user uses, it stays a word regardless of what a later wordlist revision would suggest for it.
- **Not bulk-seeded** from the existing tree (constraint carried from ticket 05 — `aadvark-jd` is a live typo that must stay catchable).
- Consumed by **both** the interactive prompt and the non-TTY stderr note.
- **Where** it is stored, its format, and whether it is per-machine or follows the user between machines are [ticket 10](10-learned-vocabulary-storage.md)'s call, now unblocked.

### Feature toggle

Add `spell_check: enabled` to the settings YAML, default `true`, mirroring the existing `emoji: use_llm` toggle. This is the clean "always off" exit for a user who creates many folders full of fresh proper nouns, where the self-silencing above (which only helps with *recurring* jargon) does not. No per-invocation `--no-spell-check` flag: a single Enter keystroke and the non-TTY skip already cover it.

### Where this lands in code (implementer's note, not a decision)

A new `aardvark_jd/spell_check.py` module parallel to `emoji_picker.py`, exposing a function the four `add_*` classes call from `get()` before `emoji_picker.resolve_emoji(...)`. The 500 ms gate (ticket 09) is unaffected: wordlist load is +12.3 ms (ticket 05) and the prompt itself is human think-time, exactly like today's emoji prompt.

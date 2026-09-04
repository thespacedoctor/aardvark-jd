# What does the suspect-token confirmation look like in Alfred?

Type: prototype
Status: resolved
Blocked by: 06

## Question

The spell-checker offers a correction for each suspect token in a new title — six or more characters with a distance-1 dictionary word — before anything is written, so the corrected title flows to the folder name, the index row and all three mirrors at once. It is `isatty`-guarded (`spell_check.py`), so an Alfred invocation currently skips it silently and creates the folder as typed.

Settled while charting: Alfred replicates it. This ticket decides what that looks like and whether it earns its place.

Build it as a step in the ticket 06 flow and answer:

- **Where does it sit?** In the terminal it runs before the emoji prompt. In Alfred, decide whether it is a step between the title field and the commit, a set of alternate rows on the confirmation, or something shown inline while the title is being typed.
- **What about multiple suspect tokens in one title?** The CLI prompts per token. Decide whether Alfred does the same — which multiplies the steps — or presents them together.
- **How is a dismissal recorded?** Declining a suggestion writes the token permanently to the learned vocabulary at `<root>/.aardvark-vocabulary`, which syncs between machines. Confirm that an Alfred dismissal writes there too, so the feature self-silences on recurring jargon exactly as it does in the terminal, and that it cannot be dismissed accidentally by a stray Enter.
- **What is the false-positive rate on real input?** Earlier research on this codebase found an 18 per cent false-positive rate on genuine technical vocabulary. A step that fires on nearly one title in five, in a surface whose whole point is speed, may not be worth having.
- **Is it worth it at all?** The standing alternative is to accept the current silent skip for Alfred-created entities. Decide, and note that the answer interacts with ticket 07 — if both steps are kept, creating a new category from Alfred is a four-step flow.

## Resolution

**Keep it, but never as a step. It becomes alternate rows on the ticket 06 confirmation screen.**

The measurement is in [the probe](../prototypes/08-spell-check/probe.md), reproducible from the four scripts beside it. It reframed the ticket before answering it.

### The premise was wrong

This ticket asked whether a step firing "on nearly one title in five" earns its place. It does not fire at that rate. The 18 per cent in `spell_check.py`'s docstring is a **token-level** rate from a synthetic technical vocabulary; read as a per-title rate it overstates the problem roughly **fourteenfold** — one title in five against the measured one in seventy.

On 141 unique human-typed folder titles — the population `add_*` actually draws from, with machine-generated instrument filenames excluded — the checker fires on **2 titles (1.4%)**, flags **2 of 132 tokens (1.5%)**, and both fires are false positives. There are **zero** true positives. Roughly one title in seventy.

So the question is not "is this too noisy to bear" but "is something this rare worth building a step for".

### The answer: no step, but do not drop it

The check costs well under a millisecond per title. Its price is measured only in keystrokes. That makes the shape decision, not the keep-or-drop decision, the one that matters — and it points at a shape that costs no keystrokes at all.

Ticket 06 settled that the final Return goes to a confirmation screen rather than committing. That screen already exists on every creation, so putting the corrections on it is free. When a token is suspect, the confirmation carries extra rows above the usual one. On the 98.6 per cent of titles that never fire, nothing changes and nothing is seen.

A dedicated step is ruled out on the numbers: seen once in seventy creations, in a surface whose whole point is speed, and unreliable when it does appear. Both measures of that unreliability point the same way, and neither flatters it. On **real** input the two fires in 141 titles were both false positives — 2 of 2 wrong, on a sample too small to put a rate on. On the **injected-typo** test, where a real typo is guaranteed to be present, it offered a wrong word 25 per cent of the time. The first number is the one that describes normal use; the second is the one that describes it at its best, with a genuine typo to find.

### What the screen does

- **Where it sits.** Alternate rows on the ticket 06 confirmation screen. Not a step, not inline-while-typing.
- **Row order.** "Create as typed" is **first and default**. Correction rows sit above or below it but never take the default position.
- **Multiple suspect tokens.** One row per correction, all shown together, each accepted independently. Measured frequency: **0 of 141** titles in the human-typed corpus, and 2 of 379 firing titles in the wider 11,102-folder sweep (`measure_wide_sweep.py`). The case barely exists, so it does not get to shape the design — but per-token rows keep the CLI's per-token model and cost nothing.
- **Accepting a correction does not commit.** It re-renders the confirmation with that token corrected and that row gone. Commit is always the same explicit "Create" row. Muscle memory from the common no-fire case is therefore unchanged — Return still means create — and the two-token case falls out for free.
- **Teaching the vocabulary needs its own explicit action**, a modifier on the correction row ("Always accept 'xshooter'"). It is **not** implied by creating as typed.

### Why the dismissal rule differs from the terminal's

The terminal records a token to `<root>/.aardvark-vocabulary` on every decline, including a bare Enter, because at a `[y/N]` prompt declining is a deliberate act. Under this shape it is not: "Create as typed" is the default row, so declining becomes the unremarkable path, and carrying the terminal's rule across would mean every reflexive Return silently taught a word. That is exactly the accidental dismissal this ticket asked to rule out.

So the two behaviours diverge deliberately, and the divergence is recorded here rather than treated as an inconsistency to fix later. The self-silencing is still reachable — dropping it would leave `xshooter` firing forever, and it is what makes a checker this unreliable tolerable at all — it just costs one modifier press instead of arriving free with a decline.

### Interaction with ticket 07

The four-step flow this ticket worried about does not happen, but not because both steps vanished. **Ticket 07 kept the emoji step**; what it removed was the Claude API call behind it, leaving a plain offline pick plus manual entry. Only the spell-check step goes.

So the flows are:

- `add_area`, `add_category`: category → `title, description` → **emoji** → confirm → run. Three steps and a confirmation.
- `add_id`: category → `title, description` → confirm → run. Two steps and a confirmation, because IDs carry no emoji.

Neither grows when a token is suspect — that is the point of putting the corrections on the confirmation. The interaction with ticket 07 is therefore that the two tickets between them removed one step from the four this ticket feared, and moved the other off the critical path.

### Handed to ticket 13

- The confirmation screen's row inventory needs the correction rows and the "always accept" modifier written into it.

- **Detection stays in `aardvark_jd/spell_check.py`.** `tokenise` and `suggest` are already pure, already unit-tested and already reachable by pytest, so nothing needs to move. Ticket 03 §8 reserves `aardvark_jd/alfred/` for workflow-specific logic — item construction, argument parsing, path discovery — and detection is not that. What belongs in `alfred/` is only the code that turns a suggestion into rows.

- **Ticket 03's `corrections` field does not carry what this screen needs, and this ticket changes its shape.** Ticket 03 §7 defines `corrections` as the substitutions **applied** to the title, `[]` when none were made *or the check was skipped*. Two things break under this decision:

  1. `--json` implies non-interactivity, and headless `add_*` skips the spell-check entirely. So `corrections` would be `[]` in exactly the case Alfred needs it filled.
  2. The screen needs suggestions that have been **offered and not yet accepted**, so it can render a row per candidate. "Applied substitutions" is a report of something already done — the wrong tense for a confirmation screen whose whole purpose is that nothing has happened yet.

  So `--json` must run suspect-token detection even though it never prompts, and the contract needs a field carrying *offered* suggestions — token, suggested word, and enough position information to substitute it — kept distinct from `corrections`' existing applied-substitutions meaning. Ticket 03 §7 explicitly left this open for tickets 07 and 08 to decide; this is that decision, and it is a change to ticket 03's shape rather than a confirmation of it.

### Split off, not fixed here

Two CLI-side defects surfaced and are **not** this ticket's to fix, because both change terminal behaviour as well as Alfred's: the six-character length floor, which accounts for 12 of 16 silent misses and hid the only real typo in the corpus, and the shortest-candidate tie-break, which produces the 25 per cent wrong-offer rate on the injected-typo test. Both are ticketed on this map as [Is the spell-checker's tuning wrong?](16-spell-check-tuning.md), which does **not** block ticket 13 — the Alfred surface is rows on a confirmation regardless of which tokens fire.

Prototype and measurement scripts on branch `prototype/ticket-08-spell-check-surface`.

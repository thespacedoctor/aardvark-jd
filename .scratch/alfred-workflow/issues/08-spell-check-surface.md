# What does the suspect-token confirmation look like in Alfred?

Type: prototype
Status: open
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

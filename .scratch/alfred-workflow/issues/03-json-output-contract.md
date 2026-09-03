# What is the shape of aardvark's `--json` output?

Type: grilling
Status: open
Blocked by: 01

## Question

Settled while charting: the Alfred workflow gets its data from a new machine-readable output mode on the CLI, covering the read commands and the mutating commands' results, documented in the repo but explicitly internal and unstable. This ticket decides its actual shape.

Decide:

- **Which commands emit it and how it is requested.** A global `--json` flag, a per-command flag, or a separate output-format option. Note that the usage block in `cl_utils.py` is a docopt specification, so every flag added there is visible on every command it is attached to.
- **The entity record.** What one area, category or ID looks like as JSON: its Johnny Decimal code, title, description, domain, emoji, folder path, archived state, and its Craft, Todoist and Drive URLs. The mirror URLs matter here — the charting decision that modifiers open one mirror each needs all of them present on every item, where the CLI today only fires them.
- **The envelope.** Whether output is a bare array or an object with metadata (system name, root path, index generation or timestamp), and whether that envelope carries a version field given the contract is internal and expected to move.
- **The result object from a mutating command.** What `add_id`, `add_project`, `add_area`, `add_category`, `archive` and `set_emoji` return: the new code, the folder path, the emoji actually used, whether a background sync was handed off, and — if the spell-check and emoji surfaces end up staying in the CLI for some paths — what was corrected.
- **How errors are expressed in JSON mode.** The charting decision that a script filter returns an error row rather than raising, which means the CLI's failure has to reach the workflow as data. Decide whether `--json` errors go to stdout as a structured object with a non-zero exit, or to stderr as prose with the exit code carrying the signal.
- **What `open --json` means.** The command's whole purpose today is the side effect of opening URLs. Decide whether `--json` suppresses the opening and just reports the links, or reports what it opened.
- **Where this code lives.** Whether serialisation sits in each command module, in `cl_utils.py`, or in a single new module — bearing in mind the charting decision that the real logic lives where pytest can reach it.

Cross-check every field against `db.py`'s actual row shapes and `doc_links.py` before settling: the contract should expose what the index holds, not what would be convenient to invent.

## Input from research (2026-09-03)

[Ticket 01](01-alfred-workflow-authoring.md) settled three things this contract must accommodate:

- **A mod's `variables` replace the item's wholesale.** There is no merge. Anything a modifier action needs must be repeated inside every mod block, which argues for keeping the per-item variable set small and putting the bulk in `arg`.
- **`uid` decides who owns result ordering.** Supplying it hands ordering to Alfred and enables its learning; omitting it keeps the CLI's order with no learning; supplying it with `skipknowledge: true` keeps both. Alfred's knowledge is keyed on the `uid` string, so **this contract has to decide whether an entity has a stable identifier** — one that survives a rename, an emoji change, a re-index, and an archive-and-reuse of the same Johnny Decimal number. If it does not, `skipknowledge` is the safer default while the design moves.
- **One Open URL object can serve all four mirror actions** via the `alfredworkflow` JSON envelope's ability to override a downstream object's config, rather than needing an object per mirror.

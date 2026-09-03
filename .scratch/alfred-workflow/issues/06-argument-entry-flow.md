# Does the two-step argument entry actually feel right?

Type: prototype
Status: claimed
Blocked by: 01

## Question

Settled while charting: multi-argument commands use a hybrid — Alfred picks the parent from a list, then one free-text field takes `title :: description`. That was chosen on paper against chained filters (too many round trips) and a pure mini-syntax (makes the user remember references Alfred could show). It needs to be felt before the rest of the mutating commands are specified on top of it.

Build a rough working flow for `add_id` — the command with the most arguments and no template step — and use it enough to answer:

- **Does the two-step handoff feel like one action or two?** Specifically, what going back to change the category feels like once the title is half-typed.
- **What is the actual separator?** `::` was a placeholder in the grilling. Test it against alternatives against real titles, and check what happens when the user types a title containing the separator, or omits the description entirely, or types only a description.
- **What does the second step show?** Whether the chosen category stays visible while the title is typed, and how — subtitle, item title, Alfred's own breadcrumb. Losing sight of the target while typing is the most likely way this flow goes wrong.
- **What confirms before it commits?** Whether the final Enter shows a preview row of what is about to be created, and how the flow reads when the emoji step (ticket 07) and the spell-check step (ticket 08) are inserted after it.
- **Does the same flow stretch to the other commands?** `add_project` adds a template choice, `add_area` and `add_category` take an emoji, `set_emoji` takes an existing reference and one emoji, `archive` takes a reference and a confirmation. Say which of those fit this shape unchanged, which need a variant, and whether any of them justifies a different flow entirely.

This is the ticket that decides the mutating half of the workflow's interaction, so its output should be concrete enough for tickets 07 and 08 to slot into.

## Comments

### 2026-09-03 — prototype built, awaiting hands-on run

The throwaway prototype is on branch `prototype/ticket-06-argument-entry` at
`.scratch/alfred-workflow/prototypes/06-argument-entry/`. It is a real Alfred
workflow: `avid` keyword → category Script Filter → keyword-less Script Filter
taking `title <SEP> description` with a live preview → real `aardvark add_id`
into a throwaway system → Finder reveal + notification. `SEP` is a workflow
configuration variable so the separator candidates can be felt without a
rebuild; the seeded titles include hyphens and one ` :: ` as traps.

Decisions taken with Dave before building: the commit really creates (into a
seeded throwaway system, not the live one), and the prototype is handed off
with a written checklist rather than driven live.

`probe.md` holds the run instructions, the test checklist and an empty verdict
table. The ticket stays `claimed` until Dave runs it and fills the verdict, at
which point it resolves and its findings feed tickets 07, 08 and 13.

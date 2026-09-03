# Does the two-step argument entry actually feel right?

Type: prototype
Status: resolved
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

## Answer

A throwaway Alfred workflow for `add_id` was built on branch `prototype/ticket-06-argument-entry` (`.scratch/alfred-workflow/prototypes/06-argument-entry/`, verdict table in `probe.md`) and driven by hand. Decisions taken before building: the commit really creates, into a seeded throwaway system rather than the live one; the prototype was handed off with a written checklist rather than driven live.

**The two-step hybrid holds — build the mutating half on it — with four corrections from the hands-on run.**

**The flow feels fast but reads as two prompts, not one.** Accepted. The speed is the reason Alfred beats the terminal, and no cheaper single-prompt option survived charting. Not worth chasing.

**Separator: `,` (comma).** Chosen over `::`, `/`, `—`, ` - ` and `>` after testing each against the seeded titles. It is natural to type, needs no shift key, and unlike the spaced or unspaced hyphen it does not collide with the hyphens that appear in real titles ("Insurance - buildings and contents"). Split on the **first** comma only: everything after it is the description. A title that itself contains a comma loses the fragment after the first comma to the description — rarer than a hyphenated title, and the confirmation step below catches it before anything is written.

**Step 2 shows the parse and nothing else.** Two lines — `title = «…»` and `description = «…»` — and that is the whole preview. The styled `Create A11.NN <title>` row from the prototype is dropped: putting the JD code next to the title field invites the user to type the code into the title. The folder path is dropped from the subtitle too. KISS.

**An explicit confirmation screen before commit.** The final Return does not create straight away. After step 2 (and the spell-check and emoji steps) there is a confirmation screen showing exactly what will be created; Return there commits, Escape backs out. A preview row is not enough of a confirmation.

**Spell-check (08) and emoji (07) sit after step 2, before the confirmation.** Order: category → `title, description` → spell-check → emoji → confirm → run. `add_id` has no emoji step at all, because IDs are never emoji-suffixed, so for `add_id` specifically it is category → `title, description` → spell-check → confirm → run. The emoji step appears only for `add_area` and `add_category`.

> **Superseded 2026-09-03 by [ticket 08](08-spell-check-surface.md).** There is no spell-check step. Measured at a 1.4 per cent per-title fire rate, the suspect-token correction became alternate rows *on* the confirmation screen rather than a step before it. The order is now category → `title, description` → emoji → confirm → run, and for `add_id` simply category → `title, description` → confirm → run. The confirmation screen carries the correction rows on the rare titles that fire, with "Create as typed" first and default.

**Going back to change the category needs an explicit affordance.** In the prototype there was no way back to the category list from step 2 and no visible key hint. Handed to ticket 13 as a spec requirement: a documented key to return, with a hint shown in the step-2 subtitle, or a first row in step 2 that returns to step 1.

**The shape stretches to every other mutating command** without a structural change: `add_project` inserts a template pick as an extra list step before `title, description`; `add_area` / `add_category` add the emoji step; `set_emoji` and `archive` are a reference pick plus one field or a confirmation. No command justifies a different flow.

### Handoffs

- **Ticket 07 (emoji surface):** the emoji step sits between spell-check and the confirmation screen, and only for `add_area` / `add_category` — never `add_id`. *Resolved: the step is now immediately after `title, description`, since the spell-check step it followed no longer exists.*
- **Ticket 08 (spell-check surface):** the spell-check step sits immediately after `title, description`, before emoji and confirmation. *Resolved the other way: there is no spell-check step. The corrections are rows on the confirmation screen. See the supersession note above.*
- **Ticket 13 (assemble the spec):** separator is `,`, split on the first; step 2 is parse-only with no JD code and no path; a mandatory confirmation screen replaces commit-on-Return; step 2 needs an explicit "back to category" affordance with a visible key hint.

# Ticket 06 probe — does the two-step argument entry feel right?

Throwaway prototype for wayfinder ticket 06. It builds a rough `add_id` flow as
a real Alfred workflow so the interaction can be felt before the rest of the
mutating commands are specified on top of it.

## The question

Settled while charting: multi-argument commands use a hybrid — Alfred picks the
parent category from a list, then one free-text field takes
`title <SEP> description`. This prototype exists to feel that against real
titles and decide the details tickets 07 (emoji) and 08 (spell-check) slot into.

## What was built

- **Step 1** — Script Filter, keyword `avid`. Lists the throwaway system's
  categories; Alfred filters the list. Return descends to step 2 and the chosen
  category is carried forward as `CATEGORY_CODE` / `CATEGORY_LABEL`.
- **Step 2** — a keyword-less Script Filter reached by connection, with
  "Don't close Alfred" set on the connection so there is no flicker. One
  free-text field, parsed as `title <SEP> description` (split on the **first**
  separator only). It renders a live preview row plus a non-actionable row
  showing the raw parse at every keystroke.
- **Commit** — Return on the preview row runs `aardvark add_id` against the
  throwaway system, reveals the new folder in Finder, and posts a notification.
- **`SEP`** is a workflow configuration variable (default `::`). Change it in
  the workflow's configuration and re-feel the flow.

The real logic is two ~50-line scripts under `workflow/scripts/`. Nothing here
is production shape — it is throwaway.

### Throwaway system

`setup.sh` seeds a self-contained system at `~/.aardvark-ticket06-throwaway/`
so `add_id` really writes folders and index rows without touching "My Life".
The seeded titles deliberately include hyphens
("Insurance - buildings and contents") and one ` :: `
("aardvark-jd :: the CLI") to trap separator choices.

## How to run it

```bash
cd .scratch/alfred-workflow/prototypes/06-argument-entry
conda activate aardvark-jd     # so `aardvark` is on PATH
./setup.sh                     # seeds the throwaway system, writes scripts/env.sh
./regen.sh                     # builds AardvarkArgEntryProbe.alfredworkflow
open AardvarkArgEntryProbe.alfredworkflow   # import into Alfred
```

Then in Alfred: `avid` → pick a category → type a title and description.
Re-run `./setup.sh` any time to wipe the test folders and start clean.
Delete the workflow from Alfred and `rm -rf ~/.aardvark-ticket06-throwaway`
when the ticket closes.

## Test checklist

Work through these and note what each one felt like.

### One action or two

- [ ] After picking a category, does step 2 appear without a flicker or a blink?
- [ ] With the title half-typed, press the key that goes back to the category
      list. What is lost? Does the half-typed title survive the round trip?
- [ ] Does the whole thing read as "add an ID" or as "two separate prompts"?

### The separator

Try `::`, `/`, `—`, ` - `, `>`, `,` in the workflow configuration, against:

- [ ] a plain title, no description
- [ ] `Insurance - buildings and contents` as the **title** (contains a hyphen)
- [ ] a title, then the separator, then a description
- [ ] a description that itself contains the separator
- [ ] only a description (separator first, nothing before it)
- [ ] the separator typed but nothing after it

Which separator never got in the way? Which felt natural to type?

### The second step's display

- [ ] Is the chosen category visible while you type the title? Where —
      subtitle, the parse row, Alfred's own breadcrumb? Is that enough?
- [ ] Does the live preview row help, or is it noise?
- [ ] Is the raw-parse row useful during the test, and would you keep any of
      it in the real thing?

### Committing

- [ ] Does the final Return need a confirmation step, or is the preview row
      enough of one?
- [ ] Mentally insert the emoji step (07) and the spell-check step (08) after
      the title. Where do they go — before the preview, after it? Does the
      flow still read as one action with them in?

### Stretch to the other commands

For each, does this exact shape fit, need a variant, or need a different flow?

- [ ] `add_project` — adds a template choice
- [ ] `add_area` / `add_category` — take an emoji
- [ ] `set_emoji` — an existing reference plus one emoji
- [ ] `archive` — a reference plus a confirmation

## Verdict

* Don't add the path to in the Alfred description 
* Adding the Code in the second step risks the user adding the code to the actual title.


| Sub-question | Finding |
| --- | --- |
| One action or two? | It is fast. 2 prompts are appearing not one.  |
| Going back to change the category | I can't go back to change the catagory. Don't know what key to use. |
| The separator | , |
| What the second step shows | The raw parse is useful, just keep title = <> and desciription = <> ... KISS |
| Preview / confirmation before commit | Give me a confirmation step. |
| Where emoji (07) and spell-check (08) slot in | Spellcheck and emoji before preview |
| Does the shape stretch to the other commands? | yes |

**Decision:** Build the mutating half on the two-step hybrid, with four
corrections. Separator is `,` (comma, split on the first one). Step 2 shows only
the parsed `title = «…»` / `description = «…»` — no JD code (it invites typing
the code into the title), no folder path. The final Return does not commit: an
explicit confirmation screen does. Spell-check (08) and emoji (07) sit after
step 2, before that confirmation — and `add_id` has no emoji step at all, since
IDs carry no emoji. The flow reads as two prompts rather than one; accepted,
the speed is the point. Going back to the category list needs an explicit
affordance with a visible key hint — handed to ticket 13. The shape stretches
to every other mutating command. Full write-up in the ticket's `## Answer`.

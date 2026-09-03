# Can the emoji suggestion survive being on the interactive path in Alfred?

Type: prototype
Status: claimed
Blocked by: 06

## Question

This is the single most likely thing to make the workflow feel bad, which is why it gets a prototype rather than a decision on paper.

`aardvark` suggests an emoji for every new non-ID folder by calling Claude (`emoji_picker.py`: `claude-opus-5`, low effort, **15-second timeout**, no retries), falling back to an offline keyword index built from `emoji.EMOJI_DATA` when the call fails or there is no TTY. In the terminal that call happens while the user is already committed and watching. In Alfred, it would sit between the user typing a title and the folder being created.

Build the emoji step as a real Script Filter and answer:

- **How long does the call actually take?** Measured over enough new-folder titles to see the spread, not one sample. The 15-second timeout is the worst case; the median is what decides this.
- **Can the wait be hidden?** Whether the offline candidates can be shown instantly and the Claude suggestion inserted at the top when it lands — Alfred's `rerun` (ticket 01) is the mechanism if it exists. If that works, the API latency stops being blocking and this whole risk dissolves.
- **What does the user pick from?** Just the suggestion with an accept or reject, or a ranked list of the suggestion plus offline candidates plus a free-text emoji search. Note that Alfred has a built-in emoji surface and the user already has an `emoji` keyword workflow installed, which may make a full picker redundant.
- **What happens on failure or slowness?** Whether Alfred falls back silently as the CLI does, shows the fallback as a visibly different result, or lets the user commit without an emoji and repair later with `set_emoji`.
- **Is it worth it at all?** The standing fallback from the charting grilling is to drop the Alfred emoji surface, accept the offline fallback for Alfred-created folders, and let `set_emoji` and `repair_emoji` clean up afterwards. If the prototype feels slow, take it.

Note that ID folders are never emoji-suffixed, so this step does not exist for `add_id` — it applies to `add_area`, `add_category` and `set_emoji`.

## Progress (2026-09-03)

Prototype built on branch `prototype/ticket-07-emoji-surface`, in `.scratch/alfred-workflow/prototypes/07-emoji-surface/`. Not yet resolved — it needs two hands-on measurements from Dave.

- **Part A — latency harness** (`latency/run_latency.py`): calls the real `claude-opus-5` request shape over 32 realistic new-folder titles, 3 passes, and reports median / p90 / max / fallback rate / output-token counts. Dave runs it with his key; the median decides whether the interactive path is viable.
- **Part B — Alfred fragment** (`AardvarkEmojiProbe.alfredworkflow`, keyword `avemoji`): implements the "offline candidates instantly, detached Claude call, `rerun: 0.3` poll, swap the suggestion in at the top when it lands" pattern, plus a visible fallback path and a `/`-triggered free-text emoji search. Dave imports it and feels it against the titles in the probe README.

Design notes already surfaced, for ticket 13:

- `rerun` (0.1–5.0 s, full-replacement) is the mechanism and it works; there is no partial/streaming update.
- Alfred runs scripts under `/bin/zsh --no-rcs`, so **neither the interpreter path nor `ANTHROPIC_API_KEY` reaches the script from the login shell** — both have to be supplied by the workflow. This widens ticket 10 (`install_alfred`) beyond the binary path: it has to make the key visible too.
- The offline picker (`emoji_picker.pick_emoji`) returns the bare `📁` fallback for most area/category-style titles ("Photography", "Cycling", "Genealogy", "Mortgage"…), so "show offline instantly" often means "show 📁 instantly". That raises the stakes on either the Claude call landing fast or the `/` search / Alfred's own emoji picker carrying the load.
- Even the instant offline path pays the ~0.3–0.5 s `import aardvark_jd` cost per invocation. A slim standalone emoji index may be worth it for the Alfred entry point.

# Can the emoji suggestion survive being on the interactive path in Alfred?

Type: prototype
Status: open
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

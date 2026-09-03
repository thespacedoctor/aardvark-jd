# Can the emoji suggestion survive being on the interactive path in Alfred?

Type: prototype
Status: resolved
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

## Answer (2026-09-03)

**The question is moot: the Claude emoji call was removed from the CLI entirely.** Dave's call, taken before the prototype was run — the API cost, the `anthropic` dependency, the `ANTHROPIC_API_KEY` requirement and the tail latency were not worth a one-character result when the offline pick plus a manual prompt is the honest interaction.

- `emoji_picker.pick_emoji` — the offline keyword search — is now the whole suggester. It is the default at the interactive prompt, the silent pick in a non-interactive run, and `--emoji` overrides it. No network call.
- Recorded as [ADR 0002](../../docs/adr/0002-drop-the-claude-emoji-suggester.md), implemented on branch `feature/drop-claude-emoji-suggester` (test suite green, coverage 96%). `emoji_picker` loses `suggest_emoji`, `llm_enabled`, `_suggest_via_claude`, `_validate_single_emoji`, the `CLAUDE_*` constants and the system prompt; the `emoji: use_llm` setting is gone; `anthropic` leaves `pyproject.toml`.

**For the Alfred surface:** the emoji step is now a plain offline pick plus manual entry — show the `pick_emoji` result as the default, let the user accept it or type/search an emoji (Alfred's built-in emoji picker or a free-text search over the `emoji` index). No latency to hide, no `rerun` dance, no key to plumb into Alfred's `no-rcs` environment. Failure is not a concept here — there is nothing to fail.

**Findings that survive, handed to ticket 13:**

- Alfred runs scripts under `/bin/zsh --no-rcs`, so the interpreter path does not reach a script from the login shell — it must be supplied by the workflow (feeds tickets 10 and 12). `ANTHROPIC_API_KEY` no longer matters.
- `emoji_picker.pick_emoji` returns the bare `📁` fallback for most area/category-style titles ("Photography", "Cycling", "Genealogy", "Mortgage"…), so the Alfred default will often be `📁` and the manual entry / emoji search carries the real load. Worth making that path prominent.
- The offline pick pays the ~0.3–0.5 s `import aardvark_jd` cost per invocation; a slim standalone emoji index may be worth it for the Alfred entry point.
- Ticket 03's mutating-result `emoji_source` field loses its `claude` value (now `offline` / `chosen` / `deferred`).

**Superseded prototype:** `.scratch/alfred-workflow/prototypes/07-emoji-surface/` (branch `prototype/ticket-07-emoji-surface`) built the `rerun`/swap-in machinery and a latency harness. Both are now dead — the harness and worker call `emoji_picker` functions that no longer exist. Kept as a record of the approach considered; its README carries a SUPERSEDED banner.

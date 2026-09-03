# Drop the Claude emoji suggester

New non-ID folders take an emoji. The suggester asked the Claude API (`claude-opus-5`, `low` effort, adaptive thinking, 15 s timeout, no retries) for one and fell back to an offline keyword search of the `emoji` package's CLDR data on any failure. That call is now removed: `emoji_picker.pick_emoji` — the offline search — is the whole suggester, offered as the default at the interactive prompt and accepted silently in a non-interactive run. `--emoji` still sets the value outright.

## Considered options

- **Keep the Claude call, hide its latency in the Alfred workflow.** The wayfinder ticket-07 prototype built the "show offline candidates instantly, swap Claude's pick in when it lands" pattern on Alfred's `rerun`. It works, but it exists only to paper over a call that adds cost, a dependency and a tail latency for a one-character result. The prototype also surfaced that Alfred's `/bin/zsh --no-rcs` gives a script neither the interpreter path nor `ANTHROPIC_API_KEY`, so the workflow would have had to plumb a key it now never needs.
- **Keep the call in the CLI, drop it only for Alfred.** Leaves the `anthropic` dependency and the `ANTHROPIC_API_KEY` requirement in place for a feature whose offline fallback is, in practice, what most area- and category-style titles ("Photography", "Mortgage", "Genealogy") get anyway. The manual prompt is the honest interaction: the user knows the emoji they want faster than a model can guess it.
- **Drop Claude and the prompt — take the offline pick silently.** Rejected: the offline index misses most real titles and lands them on 📁, so a silent pick would be wrong often. The prompt is cheap and the point.

## Consequences

- **No `anthropic` dependency and no `ANTHROPIC_API_KEY`.** `anthropic` leaves `pyproject.toml`; `emoji_picker` loses `suggest_emoji`, `llm_enabled`, `_suggest_via_claude`, `_validate_single_emoji`, the `CLAUDE_*` constants and the system prompt. The `emoji: use_llm:` setting is removed from `default_settings.yaml`; an existing settings file that still carries it is simply ignored.
- **`resolve_emoji` loses its `settings` and `log` parameters.** They only ever fed the Claude path. `add_area` and `add_category` call it with `title`, `description` and `chosenEmoji` alone.
- **Behaviour is unchanged wherever Claude was already unreachable** — which is every environment without credentials, including CI. The interactive prompt, the `--emoji` bypass and the non-interactive silent-accept all keep their shape; only the default shown at the prompt changes from a model pick to the offline pick.
- **The emoji step is now instant.** No 15 s worst case sitting between a typed title and a created folder, which is what made it the riskiest thing to put on the Alfred interactive path.

# Ticket 07 probe — the emoji surface

Throwaway. Answers [issues/07-emoji-surface.md](../../issues/07-emoji-surface.md):
can the Claude emoji suggestion sit on Alfred's interactive path without
making the workflow feel bad?

Two parts. Part A is a latency measurement you run once. Part B is an Alfred
workflow you feel.

## Part A — how long does the call take?

`latency/run_latency.py` calls the Claude API with the exact request shape
`emoji_picker` uses (`claude-opus-5`, `low` effort, adaptive thinking on,
`max_tokens` 1024) over 32 realistic new-folder titles, three passes.

```bash
cd .scratch/alfred-workflow/prototypes/07-emoji-surface/latency
conda activate aardvark-jd            # needs ANTHROPIC_API_KEY + the anthropic package
python run_latency.py
```

It prints a per-call table then a summary block. Paste the summary block into
ticket 07. The median is the number that decides Part B's verdict; the p90/max
tell us how bad the tail is.

## Part B — does it feel bad in Alfred?

### Build it

```bash
cd .scratch/alfred-workflow/prototypes/07-emoji-surface
printf %s 'sk-ant-...' > ~/.aardvark-proto-key && chmod 600 ~/.aardvark-proto-key
conda activate aardvark-jd
./setup.sh          # detects the interpreter, writes workflow/scripts/env.sh
./regen.sh          # zips workflow/ into AardvarkEmojiProbe.alfredworkflow
open AardvarkEmojiProbe.alfredworkflow   # imports into Alfred
```

The key goes in `~/.aardvark-proto-key`, never in the repo — Alfred runs
scripts under `/bin/zsh --no-rcs` so nothing from your `~/.zshrc` reaches
them, `ANTHROPIC_API_KEY` included. (That is itself a finding for ticket 10 —
`install_alfred` has to solve key/interpreter visibility, not just the binary
path.)

### Drive it

Keyword `avemoji`, then a folder title. Try these — the offline picker is
weak on most of them, which is the point:

| Type | Watch for |
|---|---|
| `avemoji Woodworking` | offline shows 📁 only; "Asking Claude…" counts up; does the swap-in feel late or fine? |
| `avemoji Photography` | same; when Claude's 📷 lands at the top, is the reorder jarring or natural? |
| `avemoji Mortgage` | pick an offline row *before* Claude answers — does bailing early feel available or hidden? |
| `avemoji Cycling \| road bike maintenance` | does the description change the pick? |
| `avemoji Genealogy / family tree history` | the `/` free-text emoji search — enough on its own, or redundant with Alfred's own emoji picker? |
| re-type `avemoji Photography` | second entry is cache-served, instant — acceptable or confusing? |
| `rm -rf "$TMPDIR/aardvark-tk07"` then a title with Wi-Fi off | the failure path: offline pick tagged "Claude unavailable", plus "commit without an emoji" — reads as broken, or fine? |

Picking any row fires a notification showing the emoji and its source
(`claude` / `offline` / `offline-fallback` / `deferred`).

### The five questions to answer (from the ticket)

1. **How long does the call take?** — from Part A.
2. **Can the wait be hidden?** — does offline-first + `rerun` swap-in actually
   dissolve the latency, or still feel like waiting?
3. **What does the user pick from?** — just the suggestion, or the ranked
   list (suggestion + offline + `/` search) this builds? Is the `/` search
   worth keeping given Alfred's built-in emoji picker and your `emoji`
   workflow?
4. **What happens on failure/slowness?** — is the visible-fallback +
   commit-without-emoji handling right, or should it fall back silently like
   the CLI does?
5. **Is it worth it at all?** — or take the standing fallback: no Alfred
   emoji surface, accept the offline pick for Alfred-created folders, clean up
   with `set_emoji` / `repair_emoji`.

## Files

- `latency/run_latency.py`, `latency/titles.txt` — Part A.
- `workflow/info.plist` — one Script Filter (`avemoji`) → one Notification.
- `workflow/scripts/sf_emoji.py` — the Script Filter: offline candidates now,
  detached Claude call, `rerun: 0.3` poll, swap-in, fallback rows.
- `workflow/scripts/emoji_worker.py` — the detached call; writes
  `<cache>/<key>.json`.
- `setup.sh` / `regen.sh` — build the `.alfredworkflow`.

## Cleanup

Delete the Alfred workflow (bundle id `dev.thespacedoctor.aardvark.ticket07probe`),
`rm ~/.aardvark-proto-key`, `rm -rf "$TMPDIR/aardvark-tk07"`. The prototype
branch is the archived record.

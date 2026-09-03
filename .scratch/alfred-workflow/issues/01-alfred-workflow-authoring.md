# How is an Alfred 5 workflow authored, and what exactly can a Script Filter return?

Type: research
Status: resolved
Findings: ../research/01-alfred-workflow-authoring.md

## Question

Establish the ground facts every other ticket on this map rests on. The workflow is being written from scratch by someone who has installed 88 of them but authored none, so the shape of the format has to be known before the interaction can be specified.

Find out and write up:

- **The `info.plist` structure.** What a workflow directory contains, how objects (Script Filter, Run Script, Notification, Open URL) and the connections between them are represented, and which parts are stable identifiers versus Alfred-generated churn.
- **The Script Filter JSON schema in full.** `items` and every field on an item: `uid`, `title`, `subtitle`, `arg`, `icon`, `valid`, `match`, `autocomplete`, `text`, `quicklookurl`, `variables`. Confirm what `uid` does to Alfred's result ordering and knowledge, and what `match` does that `title` alone does not — the client-side filtering decision (ticket 05) depends on both.
- **The `mods` block.** How per-modifier alternate actions are declared, which modifiers and combinations are available in Alfred 5, and whether a modifier can carry its own `variables` as well as its own `arg`. Ticket 03's contract has to carry whatever a modifier needs.
- **`rerun` and script-filter run behaviour.** How Alfred re-runs a filter as the user types, what the debounce and "run behaviour" settings do, and whether a filter can return results and then update them. This bounds how much latency the design can absorb.
- **Workflow configuration variables.** How a user-facing configuration variable is declared, read by a script at run time, and given a default — the mechanism ticket 12 needs for the binary path override.
- **Passing state between connected objects.** How a Script Filter hands variables to the next object, which is the mechanism the two-step argument entry in ticket 06 would use.
- **How a script is invoked.** The environment a Run Script action gets (`PATH`, working directory, the `alfred_*` environment variables), and the language options available.

Prefer Alfred's own documentation at `alfredapp.com/help/workflows/` and the Alfred forum over third-party blog posts, and note the Alfred version each claim applies to. There are 88 installed workflows at `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences/workflows/` that can be read as worked examples of anything the documentation leaves ambiguous.

## Answer (2026-09-03)

Full findings: [research/01-alfred-workflow-authoring.md](../research/01-alfred-workflow-authoring.md). Installed version is **Alfred 5.7.3 (build 2320)**, and every claim in the write-up is tagged `[Docs]`, `[Alfred-bundled]`, `[Corpus]` or `[Inferred]`.

Two evidence sources beyond the documentation turned out to be decisive: Alfred **ships first-party template workflows inside its own app bundle** (`/Applications/Alfred 5.app/Contents/Frameworks/Alfred Framework.framework/Versions/A/Resources/*.alfredworkflow`), which settle what Alfred itself writes into `info.plist`; and the 86 parseable installed workflows, surveyed programmatically.

**The facts that change the design:**

- **`PATH` is documented and narrow**: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`, shell `/bin/zsh --no-rcs`. A conda, venv, pipx or uv `aardvark` is not on it, and neither is `~/.local/bin`. The charting decision to bake in `sys.executable` is the approach Alfred's own documentation endorses, as "the method that modifies the least".
- **Configuration defaults live in `info.plist`; user overrides live in `prefs.plist`**, and the documentation says outright to gitignore the latter. Only 1 of 88 installed workflows has a `prefs.plist`, holding solely the setting that user changed. This gives a clean two-layer design: `install_alfred` rewrites the default, a user override wins, and the two never collide.
- **A mod can carry its own `variables`, but replacement is wholesale.** Supplying `variables` on a mod discards the item's entirely; omitting it inherits all. There is no merge. The JSON contract must therefore repeat shared keys inside every mod block.
- **`uid` surrenders result ordering to Alfred.** Three positions: omit it (your order, no learning), supply it (Alfred's order), or supply it with `skipknowledge: true` (your order, learning retained). Knowledge is per-object and keyed on the `uid` strings, so the contract needs stable identifiers or learning attaches to the wrong rows.
- **`match` replaces `title` rather than adding to it**, and applies only when "Alfred Filters Results" is on.
- **Alfred's matching is word-prefix, not true fuzzy subsequence matching.** The map's charting premise overstated this and has been corrected.
- **`cache` with `loosereload`** (Alfred 5.5+) exists and directly addresses the measured 240 ms cold `fd`. The documentation recommends caching only in the "Alfred Filters Results" mode already chosen.
- **The `alfredworkflow` JSON envelope lets a script override the config of downstream objects**, so a single Open URL object can serve all four mirror actions instead of one object per mirror.
- **Connection modifiers and JSON `mods` are separate, composable mechanisms**: the former routes to a different object, the latter varies `arg` and `variables` on the same one. The connection bitmask is the Cocoa `NSEvent` mask and decodes cleanly across all 123 samples.
- **Use External Script (`type: 8`) with a `scriptfile`**, not an inline script body. The language `type` integer is undocumented and was reconstructed by correlation, so it should not be hand-authored — and external files keep the entry points as real files under `aardvark_jd/alfred/` where pytest reaches them.

**Not settled, and why:**

- **The Alfred forum was unreachable** — `alfredforum.com` returns HTTP 403 to every automated fetch, browser user-agent included. Nothing that would normally be settled by a first-party forum post is cited; those claims are marked `[Inferred]` and backed by corpus evidence instead.
- **No documented item-count limit or performance cliff for a Script Filter.** The whole-index assumption remains genuinely untested, which leaves [Does shipping the whole index to Alfred hold up at realistic scale?](05-index-payload-and-filtering.md) as the only way to settle it.
- **Working directory is the workflow folder** on overwhelming corpus evidence, but with no first-party sentence for the inline-script case. Worth one `pwd` in the first prototype.
- Also unverified: the `escaping` bit meanings (moot when using `argv`, which the documentation recommends), `queuedelaycustom` units, and `alfredfiltersresultsmatchmode` beyond `0` being the default.

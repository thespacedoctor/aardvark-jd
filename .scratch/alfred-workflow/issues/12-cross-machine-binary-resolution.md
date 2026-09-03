# How does the workflow find aardvark on a second machine?

Type: grilling
Status: open
Blocked by: 02

## Question

Two facts collide. Alfred's preferences live in Dropbox — `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences` — so a workflow installed on one machine appears on every other machine, configuration included. And the system's folder tree is deliberately shared between machines, so the same entities are reachable from all of them.

But the thing the workflow calls is a conda environment binary at `/Users/dave/anaconda/envs/aardvark-jd/bin/aardvark`, and there is no reason for that path to be identical on the next machine. A path baked in by `install_alfred` on machine A syncs to machine B and is wrong there — silently, because a Script Filter cannot raise.

Decide:

- **Is the binary path per-machine state, and can Alfred hold per-machine state at all?** Ticket 02 establishes what is stored where and what syncs. If everything in the workflow directory syncs, the path cannot live there.
- **Where per-machine configuration goes if not in the workflow.** The user settings file at `~/.config/aardvark/aardvark.yaml` is outside Dropbox and already per-machine, which makes it a candidate — but then the workflow has to find *that*, which is the same problem one level up. A resolution order (workflow variable, then a known config location, then a `PATH` probe, then conda env discovery) is the obvious shape; decide it explicitly rather than letting it accrete.
- **How the workflow behaves when resolution fails.** The charting decision gives errors an actionable row where a fix is obvious. This is the case that most deserves one: "aardvark not found on this machine — Enter to configure". Decide what Enter does.
- **Whether `install_alfred` is re-run per machine.** If it is, most of this resolves itself, and the decision becomes how the workflow detects it is on an unconfigured machine rather than how it guesses the path. Note that this makes `install_alfred` idempotent-on-a-shared-directory, which ticket 10 has to account for.
- **Whether this is a first-class requirement or an accepted limitation.** A defensible answer is that the workflow works on the machine it was installed on and says so clearly elsewhere. Decide deliberately, because the alternative is a silent failure on a machine the user rarely notices.

## Input from research (2026-09-03)

[Ticket 02](02-alfred-deployment-mechanics.md) resolved the storage half of this question, and it is worse than assumed in one place and better in another.

- **The two-layer split is real and supported**: configuration **defaults** live in `info.plist`, **changed values** in `prefs.plist`, which Alfred's own documentation says to gitignore. So `install_alfred` can write a default without fighting a user override, and a user override wins without being clobbered on upgrade.
- **But both files live inside the workflow directory, inside the Dropbox-synced preferences folder.** Neither is per-machine. So the split solves upgrade collisions, not the cross-machine problem this ticket exists for, and the per-machine value still has to come from somewhere outside Alfred entirely.
- **[Ticket 01](01-alfred-workflow-authoring.md) sharpened the failure mode**: Alfred's `PATH` is a documented six entries and a conda, venv, pipx or uv binary is on none of them, so a `PATH` probe is close to worthless as a resolution step on this machine. The resolution order should not lean on it.
- **The vestigial-preferences-folder trap applies here too**: any resolution step that falls back to a plausible default path rather than failing loudly will appear to work and silently do nothing.

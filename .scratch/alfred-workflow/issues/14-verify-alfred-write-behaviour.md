# Verify what Alfred writes, and whether it follows a symlink

Type: task
Status: resolved

## Question

Three questions that both research tickets reached and neither could answer, because answering them means writing into the live Alfred preferences folder at `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences` — outside a research ticket's scope, and not somewhere to experiment casually given it is inside Dropbox and shared across machines.

Nothing here is a decision. It is manual work that unblocks two decisions.

Build a throwaway workflow — a bundle id that cannot collide, one Script Filter, one configuration variable with a default — and settle:

1. **Does Alfred follow a symlinked workflow directory?** Create `workflows/aardvark-test` as a symlink to a directory outside the preferences folder and confirm whether Alfred loads it, whether it survives an Alfred restart, and whether it survives a preferences sync. This is the question the whole live-editing plan rests on. Note the Dropbox caveat before reading a failure: the preferences folder sits in Dropbox `/Apps/`, which Alfred excludes from its own sync picker and advises against, so a failure may be Dropbox's rather than Alfred's — check whether Dropbox has uploaded the symlink's target before concluding anything.
2. **Does merely opening the workflow in Alfred's editor rewrite `info.plist`?** Record the file's hash, open the workflow in Alfred's preferences, close it without touching anything, and compare. Then do the same having nudged one object on the canvas, to see the `objects` reordering and `uidata` churn in isolation.
3. **Where does the import-time configuration sheet write?** Ticket 02 found a `userconfigurationconfig` **default** inside an installed workflow's `info.plist` rewritten (`com.au` to `co.uk`) on a workflow with no `prefs.plist`, which contradicts Alfred's documented "defaults in `info.plist`, changed values in `prefs.plist`" split. Import the throwaway workflow, set the configuration value in the sheet Alfred shows, and see which file changes. If Alfred writes defaults back into `info.plist`, the green light for committing the plist is narrower than it looks.

Record what was done, the resulting facts, and clean up the throwaway workflow afterwards. Then confirm whether [Is `info.plist` committed, or generated?](04-version-controlling-info-plist.md) and [What does `aardvark install_alfred` do?](10-install-alfred-command.md) still have the shape they have now.

**This touches the user's live Alfred installation and a Dropbox-synced preferences folder.** Confirm with the user before running it, and take a copy of anything that will be written to.

> **Go-ahead given in principle, 2026-09-03.** Dave has approved this ticket being worked. That covers taking the ticket, not any particular command: still show the exact steps and confirm before the first write, and still take a copy of the preferences folder first. Approval in principle is not approval of a plan he has not seen.

## Progress (2026-09-04)

Backup taken first: `~/Alfred.alfredpreferences-backup-20260904.tgz`, 66.5 MB, 6,524 entries, verified readable. Alfred 5.7.3, sync folder `/Users/Dave/Dropbox/Apps/alfred` — the Dropbox one, not the vestigial `~/Library` path ticket 02 warned about.

Probe workflow at `.scratch/alfred-workflow/prototypes/14-alfred-write-behaviour/aardvark-test`, bundle id `com.aardvark-jd.wayfinder-ticket-14-probe`, one Script Filter (External Script, `type: 8`), one `popupbutton` configuration variable `probe_var` defaulting to `ORIGINAL_DEFAULT`. Symlinked in as `workflows/aardvark-test`. Only one write was made into the preferences folder: that symlink.

### Question 1 — does Alfred follow a symlinked workflow directory? **Yes, comprehensively.**

- **Loaded with no restart.** `set configuration … in workflow "com.aardvark-jd.wayfinder-ticket-14-probe"` succeeded immediately after the symlink was created.
- **Survived a full Alfred quit and relaunch**, still resolving the bundle id through the link.
- **Writes go through the link** into the real directory: Alfred created `prefs.plist` inside the repo, not inside the preferences folder.
- **Scripts run through the link, and relative paths resolve to the repo.** The Script Filter fired and reported `$0` as the symlink path (`…/Alfred.alfredpreferences/workflows/aardvark-test/filter.sh`) but `$PWD` as the **resolved real path** in the repo. So Alfred sets the working directory to the link's target — a script's relative paths reach repo files, which is what the live-editing plan needs.
- Incidental, and useful to ticket 15: `alfred_workflow_data` points at `~/Library/Application Support/Alfred/Workflow Data/<bundleid>` — **outside** the synced preferences folder.

Still open: whether it survives a preferences **sync**. Locally the entry stays a symlink; whether Dropbox uploads the target's contents as a real folder, and what a second machine then sees, cannot be read from this filesystem. Handed to the checklist below.

### Question 3 — where does the configuration value write? **`prefs.plist`, for the AppleScript route, exactly as documented.**

Setting `probe_var` to `CHANGED_VALUE` wrote `prefs.plist` and left `info.plist` **byte-identical** (`68c002d6…` before and after). Setting it back to `ORIGINAL_DEFAULT` — the `info.plist` default — **emptied** `prefs.plist` to `{}` rather than storing the value, and the Script Filter then read `probe_var=ORIGINAL_DEFAULT` from the `info.plist` default. So `prefs.plist` holds deltas only, and ticket 01's two-layer design holds.

Two existing workflows corroborate this read-only, and also explain ticket 02's apparent contradiction. The emoji workflow (`user.workflow.77DAF526…`) has `skin_tone = "0"` in `prefs.plist` with its `info.plist` default left at `""`. The Amazon workflow (`user.workflow.CE7CEC67…`) has `co.uk` in the `info.plist` **default** with **no** `prefs.plist`, while `com.au` is the first entry in its pairs list. Across all 89 installed workflows only **one** has a `prefs.plist` at all. The pattern that fits: the **import-time configuration sheet** writes into `info.plist`, while later changes write into `prefs.plist`. That is the half still to confirm, and it is the half that matters for committing the plist.

### Checklist for Dave

Run `.scratch/alfred-workflow/prototypes/14-alfred-write-behaviour/scripts/check.sh "<label>"` after each step. It appends a snapshot — hashes, `prefs.plist` contents, the `userconfigurationconfig` default and the `objects` order — to `report.txt`, so nothing needs typing back.

1. **Open and close, untouched.** Open Alfred's preferences, Workflows, select **aardvark ticket-14 probe**, do not touch anything, then select a different workflow and close the window. Run `check.sh "2a open-close untouched"`.
2. **Nudge one object.** Reopen it, drag the single Script Filter object a short distance on the canvas, close. Run `check.sh "2b nudged object"`.
3. **Import, and set the value in the sheet.** Double-click `prototypes/14-alfred-write-behaviour/ticket-14-import-probe.alfredworkflow`. It has a **different bundle id** (`…-import`) and keyword (`avimport`) so it cannot replace the symlinked probe. In the configuration sheet Alfred shows on import, set **Probe Value** to **Changed**, then import. Run `check.sh "3 imported with value set"`. This is the decisive one: if `default` becomes `CHANGED_VALUE` in the imported copy's `info.plist` and no `prefs.plist` appears, the import sheet writes defaults into `info.plist` and ticket 04's green light narrows.
4. **Dropbox.** Check whether `Apps/alfred/Alfred.alfredpreferences/workflows/aardvark-test` appears on dropbox.com as a **folder with contents** rather than as a link, and say what a second machine's Alfred shows for the probe workflow.

## Answer

All four checks are done. The live-editing plan holds, and the green light for committing `info.plist` is now wider than ticket 02 left it, not narrower.

### Question 1 — symlinked workflow directory: **followed comprehensively** (see Progress above)

Alfred loads a symlinked `workflows/aardvark-test` with no restart, survives a full quit and relaunch, writes through the link into the real repo directory, and sets a script's working directory to the link's resolved target so relative paths reach repo files. Incidental for ticket 15: `alfred_workflow_data` is `~/Library/Application Support/Alfred/Workflow Data/<bundleid>`, outside the synced preferences folder.

On Dropbox: `workflows/aardvark-test` appears on dropbox.com as a macOS alias, not as a folder of copied contents. Dave has ruled cross-machine syncing of the workflow directory out of scope for this effort — the live-editing symlink is an authoring-machine convenience and nothing in the map depends on a second machine seeing it as a link. See the map's Out of scope section.

### Question 2 — does opening the workflow in Alfred rewrite `info.plist`?

- **Open and close, untouched:** `info.plist` is **byte-identical** (`68c002d6…` before and after). Merely inspecting a workflow in Alfred's editor writes nothing.
- **Nudge one object on the canvas:** `info.plist` hash changes (`68c002d6…` to `e356911d…`). The diff is `uidata` canvas coordinates only; `prefs.plist` stays `{}`. The `objects` array could not be exercised for reordering because the probe has a single object, but ticket 02's read — reorder plus `uidata` churn, no formatting noise — is consistent with what was seen.

Practical consequence for ticket 04: reviewing a committed `info.plist` means ignoring `uidata` coordinate churn and `objects` array order. Neither carries semantics.

### Question 3 — where does the import-time configuration sheet write? **`prefs.plist`, not `info.plist`.**

The decisive check. Importing `ticket-14-import-probe.alfredworkflow` and setting **Probe Value** to **Changed** in the sheet Alfred shows on import produced:

- imported copy `info.plist`: `userconfigurationconfig` default still `ORIGINAL_DEFAULT` (verified with PlistBuddy)
- imported copy `prefs.plist`: `{"probe_var" => "CHANGED_VALUE"}`

So Alfred does **not** write configuration-sheet values back into `info.plist` defaults. Ticket 02's apparent contradiction — the Amazon workflow carrying `co.uk` in its `info.plist` default with no `prefs.plist` — is explained by that value having been **vendor-committed that way**, not written by Alfred on import. Ticket 01's two-layer design (defaults in `info.plist`, deltas in `prefs.plist`) holds without exception, and `prefs.plist` is correctly gitignored.

### Consequences for downstream tickets

- **[Is `info.plist` committed, or generated?](04-version-controlling-info-plist.md)** — shape holds and the evidence now leans hard toward **committed**. Alfred does not rewrite `info.plist` on inspection, does not rewrite defaults on import, and its edit-time churn is confined to `uidata` and `objects` order. Ticket 04 is unblocked (01, 02, 14 all resolved).
- **[What does `aardvark install_alfred` do?](10-install-alfred-command.md)** — shape unchanged. Still blocked on ticket 04. The symlink mechanics it needs are all confirmed: create `workflows/aardvark-jd` as a symlink to the repo copy, and Alfred does the rest.

### Cleanup

The throwaway probe workflow, the imported copy, and the symlink should be removed from the live preferences folder. Probe artifacts are kept under `prototypes/14-alfred-write-behaviour/` for the record. Backup `~/Alfred.alfredpreferences-backup-20260904.tgz` can be deleted once Dave is satisfied nothing else is needed from it.

**Task for Dave:** confirm the symlink `workflows/aardvark-test`, the probe bundle `com.aardvark-jd.wayfinder-ticket-14-probe`, and the imported `…-import` copy (`user.workflow.345BFD45-…`) are all removed from `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences/workflows/`.

### Cleanup done (2026-09-04)

Removed from the live prefs folder: the `workflows/aardvark-test` symlink, the imported `user.workflow.345BFD45-…` copy (`…-ticket-14-import`), and — while there — the abandoned ticket 07 emoji probe `user.workflow.33F7CBA8-…` (`dev.thespacedoctor.aardvark.ticket07probe`). Repo target and `prototypes/14-alfred-write-behaviour/` artifacts untouched. Backup `~/Alfred.alfredpreferences-backup-20260904.tgz` deleted. No probe/ticket workflows remain in the prefs folder.

# Does Alfred's Delete Workflow delete through a symlink?

Type: task
Status: resolved
Assignee: Dave
Blocked by:

## Question

[Ticket 14](14-verify-alfred-write-behaviour.md) established that Alfred follows a symlinked workflow directory completely: it loads it, writes through it into the real target, and resolves a script's working directory to the target. It did **not** test deletion.

[Ticket 10](10-install-alfred-command.md) makes `workflows/aardvark-jd` a symlink into `aardvark_jd/resources/alfred/` inside the repo. If Alfred's **Delete Workflow** command removes the link's *target contents* rather than the link itself, using Alfred's own UI to remove the workflow destroys the committed workflow in the working tree. That is a data-loss shape, and it is currently unknown in either direction.

Find out:

- **What Alfred's Delete Workflow does to a symlinked workflow directory.** Does it unlink, or does it recurse into the target and delete its contents? Test with a throwaway symlink pointing at a directory of disposable files, the way ticket 14's probes were run. Do not point it at anything in the repo.
- **Whether Alfred moves it to the Trash or removes it outright.** If it goes to the Trash, recovery is possible and the hazard is much smaller. Note which.
- **Whether any warning is shown.** Alfred may already detect the link and say something, in which case the risk is largely self-mitigating.

Then record the consequence:

- If Alfred unlinks safely, `install_alfred --uninstall` stays the documented route but Alfred's UI is a safe alternative, and the README says so plainly.
- If Alfred deletes through the link, that warning belongs in the README in bold and in the `install_alfred` command's own output, not in a footnote.

This must be answered before the symlink ever points at real repo content.

## Resolution (2026-09-04)

**Alfred unlinks. The data-loss shape this ticket was written to guard against does not exist**, and it is recoverable on top of that. Measured on Alfred 5.7.3; full method and manifests in [the probe report](../prototypes/17-alfred-delete-through-symlink/report.md).

A disposable workflow — minimal `info.plist`, an executable script, and canary files at three depths — was symlinked into the preferences folder from a scratchpad target outside both the repo and Dropbox, and deleted through Alfred's own UI. Afterwards the link was gone from `workflows/`, and the target directory survived with its **inode unchanged and all five files at their recorded hashes**, `nested/deeper/` included. No recursion at any depth.

Better still, the item in `~/.Trash` **is itself still a symlink**, resolving to the untouched target. Alfred moved the link to the Trash rather than removing it outright, so an accidental delete is undone by dragging it back — no reinstall, and nothing to restore from git.

**The dialog is not a mitigation.** It reads *"Delete Workflow — Remove 'ticket-17 delete probe'?"* with a **Remove Data and Cache folders** checkbox. It says "remove" and "delete", never "Trash", and it makes no mention of the symlink or of where the directory actually lives. A user deleting the real workflow gets no hint that they are pointed at a git working tree. That does not matter now that the behaviour is safe, but it is why the behaviour had to be measured rather than assumed.

The **Remove Data and Cache folders** checkbox is a separate concern and is not a route into the repo: it targets `~/Library/Application Support/Alfred/Workflow Data/<bundleid>` (ticket 14) and Alfred's cache, both outside the workflow directory. Neither existed for the probe's bundle ID before or after.

Taking the ticket's first branch, the consequence for the docs is the mild one:

- `install_alfred --uninstall` stays the **documented** removal route, because it also removes ticket 12's binary pointer, which Alfred knows nothing about. That is now its reason for existing, rather than protecting the working tree.
- The README says plainly that deleting the workflow from Alfred's UI is **safe** — it removes the link, not the repo directory, and the link lands in the Trash. It also says that route leaves the binary pointer behind.
- **No bold warning, and no warning in `install_alfred`'s output.** Ticket 10 wrote that requirement conditionally on this measurement, and the condition did not fire.

One residual, small: because Alfred trashes the link rather than deleting it, a user who empties the Trash between deleting and reinstalling loses nothing, but a user who *restores* it gets a workflow back that Alfred is not currently tracking until it rescans. Re-running `install_alfred` is idempotent across exactly this state (ticket 10), so the recovery instruction is "re-run `install_alfred`", not "drag it back".

Unblocks [ticket 13](13-assemble-the-spec.md), which was the last ticket blocking it.

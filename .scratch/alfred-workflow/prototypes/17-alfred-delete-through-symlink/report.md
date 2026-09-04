# Ticket 17 probe: does Alfred's Delete Workflow delete through a symlink?

Alfred 5.7.3, macOS 25.6.0, 2026-09-04.

## Method

A disposable workflow was built in the session scratchpad — deliberately outside both the repo and Dropbox, unlike ticket 14's probe, because this experiment destroys its target on the bad outcome. It carried a minimal valid `info.plist` (bundle ID `com.aardvark-jd.wayfinder-ticket-17-delete-probe`, one keyword object), an executable `script.sh`, and three canary files at three depths: top level, `nested/`, and `nested/deeper/`. Every file was SHA-256 hashed and the target directory's inode recorded before the test (`manifest-before.txt`).

`workflows/ticket-17-delete-probe` was symlinked to that target, taking the preferences folder from 88 workflows to 89. Alfred listed the workflow with no restart, consistent with ticket 14.

Dave then deleted it through Alfred's own UI: Workflows, select, right-click, Delete.

## What Alfred showed

Title **Delete Workflow**, body **Remove 'ticket-17 delete probe'?**, plus a **Remove Data and Cache folders** checkbox. The verb is "remove"/"delete" throughout; the Trash is never mentioned, and neither is the symlink or the directory's real location. So the dialog is not itself a mitigation — a user has no way to tell from it that the workflow is a link into a git working tree.

## What Alfred did

**It unlinked. The target is untouched.**

- `workflows/ticket-17-delete-probe` is gone; the folder is back to 88 workflows.
- The item now in `~/.Trash/ticket-17-delete-probe` **is still a symlink**, `readlink` resolving to the same scratchpad target. Alfred moved the link itself to the Trash — not the contents, and not a copy of them.
- The target directory survives with **inode `1669721738` unchanged** and all five files at their recorded hashes, `nested/deeper/CANARY-deeper.txt` included (`manifest-after.txt`). No recursion at any depth.

So the deletion is both non-destructive to the target *and* recoverable: the link can be dragged back out of the Trash.

The **Remove Data and Cache folders** checkbox is a separate matter and is not a route into the repo. It targets `~/Library/Application Support/Alfred/Workflow Data/<bundleid>` (located by ticket 14) and Alfred's cache — both outside the workflow directory and outside the repo. Neither existed for this probe's bundle ID, before or after, since the probe was never run.

## Files

- `manifest-before.txt` — paths, SHA-256 hashes and inode, recorded before the delete.
- `manifest-after.txt` — the same, recorded after. Identical bar the timestamp line.

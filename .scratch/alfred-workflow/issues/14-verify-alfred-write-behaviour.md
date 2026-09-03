# Verify what Alfred writes, and whether it follows a symlink

Type: task
Status: open

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

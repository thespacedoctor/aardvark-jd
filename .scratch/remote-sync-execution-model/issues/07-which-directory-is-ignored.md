# Which directory gets the Dropbox ignore, and how does it get set?

Type: grilling
Status: resolved
Assignee: dave (claimed 2026-08-28; prior session failed, picked up fresh)
Blocked by: none

## Question

Ticket 01 established that the ignore must be applied to a **directory**, because SQLite's `-wal` and `-shm` files are created fresh with no extended attributes and are uploaded by Dropbox regardless of the parent database's ignore status. Which directory, and who sets it?

Decide:

- **Ignore `00_INDEX🗂️` wholesale**, or **move the database into a dedicated ignored subdirectory** such as `00_INDEX🗂️/.db/`. The folder currently contains only `aardvark.db`, so wholesale costs nothing today and needs no migration. Against that, `.00_index` is a reserved system folder that the craft mirror already treats as meaningful at every level, and permanently desyncing the root one may surprise later. The subdirectory option needs a change to `paths.find_db_path` plus a migration for the existing system.
- **Who sets the attribute.** `av init` must set it on a new system. But the attribute is per-machine and unsynced, so a system cloned or restored onto a second machine will have an unignored index directory and will silently start syncing again. Does `repair_emoji`, or some new doctor command, own re-asserting it?
- **What happens when it is missing.** Should any command that opens the database check the attribute and warn, given the failure is silent and its consequence is corruption? A check on every command costs a `getxattr` call, which is negligible against the 500 ms gate.
- **Non-macOS and non-Dropbox systems.** The attribute is a Dropbox-on-macOS mechanism. What does `av init` do when the system root is not inside a Dropbox tree, or the platform is not macOS? Presumably nothing, but the detection needs specifying, and `dropbox_client.local_dropbox_roots()` already knows how to find Dropbox roots.

This decision gates enabling WAL, which in turn gates any background writer.

## Answer

Resolved 2026-08-28 by grilling. This ticket decides the ignore mechanism only; server-side cleanup of data Dropbox has already uploaded is spun off to [Verify ignore-after-sync behaviour and specify server-side purge](11-verify-ignore-after-sync.md).

### Decisions

**1. Ignore `00_INDEX🗂️` wholesale.** `com.dropbox.ignored=1` applied to the directory, per ticket 01's finding that file-level ignore does not cover the `-wal`/`-shm` sidecars. Not a dedicated subdirectory: the folder holds only `aardvark.db`, nothing user-facing has ever lived there, and every other mirror (gdrive explicitly, craft, todoist) already treats it as derived data. Wholesale needs no migration and no change to `paths.find_db_path`. Revisit only if synced content is ever genuinely needed under `00_INDEX🗂️`.

**2. Set at creation, re-assert lazily on every run.**
- `initialiser.get()` sets the attribute on the index folder immediately after `_create_skeleton_folders`, before `db.get_connection` opens the schema.
- Every non-`init`, non-completion command re-asserts it idempotently in `cl_utils.main`'s shared path, after `paths.find_db_path(rootPath)` and before `db.get_connection`. This is self-healing: a second machine that clones the Dropbox tree gets the ignore re-applied on its first `aardvark` command, with no new command surface and no dependence on the user knowing to run `repair_emoji` or a `doctor` command.
- The completion path (`completion._with_connection`) never asserts the attribute: it must stay fast and strictly read-only.
- `setxattr` on a directory is a sub-millisecond syscall, negligible against the 500 ms `av add_project` gate.
- On failure to assert (permissions, missing syscall): log it, print one warning to stderr, continue. Never abort a command over it.

**3. Mechanism: `ctypes` into libc `setxattr`/`getxattr`.** `os.setxattr` does not exist on macOS in CPython, so the options were a `ctypes` libc call, the `xattr` PyPI package (a compiled C extension), or a `/usr/bin/xattr` subprocess. `ctypes` wins: no new dependency (ticket 05 established a firm no-compiled-dependency-for-a-nicety stance), and no process fork on every command (the lazy re-assertion runs per invocation). Wrap it in a new `aardvark_jd/dropbox_ignore.py` exposing `is_ignored(path)` and `set_ignored(path)`. `/usr/bin/xattr` subprocess is the documented fallback if the `ctypes` binding proves fragile.

**4. Gated on Dropbox-tree membership and platform.** The whole mechanism is a no-op unless `dropbox_client.find_containing_root(rootPath, dropbox_client.local_dropbox_roots())` returns a root.
- Not inside a Dropbox tree: silent no-op. The DB is not being synced by Dropbox, so there is nothing to ignore.
- Inside a Dropbox tree but not macOS: no-op plus one logged warning ("Dropbox index-ignore unsupported on this platform; the index DB may sync"). The Linux (`user.com.dropbox.ignored` xattr) and Windows (NTFS alternate data stream) variants are YAGNI until a second platform actually runs aardvark.

### Facts for later tickets

- `com.dropbox.ignored` is currently **absent** from the live `/Users/Dave/Dropbox/aardvark/00_INDEX🗂️/`; only `com.dropbox.attrs` and `com.apple.provenance` are set. The DB is syncing today.
- `repair_emoji` renames `root.index` via a plain filesystem rename (`folders.move_folder_and_reindex`), which preserves the directory's extended attributes. The ignore does not need re-asserting after a `repair_emoji` rename, though the lazy per-run assertion covers it regardless.
- New module to create: `aardvark_jd/dropbox_ignore.py`.

### Unblocks

Ticket 08 (WAL and the concurrency contract). Ticket 08 needs only the decision that the containing directory is ignored, which is now made.

## Update from ticket 11 (2026-08-28)

[Verify ignore-after-sync behaviour and specify server-side purge](11-verify-ignore-after-sync.md) is resolved and simplifies this ticket's implementation:

- **No server-side purge code.** Dropbox purges the server copy automatically when the ignore is set on an already-synced directory (verified empirically). The `setxattr` this ticket specifies is sufficient on its own — the live `aardvark.db` on Dropbox's servers is removed on first assertion. Do **not** add a Dropbox API `files/delete` fallback.
- **Ordering constraint.** The `setxattr` re-assertion must run in `cl_utils.main` **before** `db.get_connection` / `db.initialise_schema`, so the ignore lands (and the purge starts) before any `-wal`/`-shm` sidecar is created. On a second machine `init` never runs, so the per-run re-assertion is the only thing protecting it.
- **Residual window.** Between a second machine cloning the tree and its first `av` run, the DB and a partial WAL can briefly upload; the first run's ignore purges them, but a pull during that window could get a partial DB. Full closure needs a "rebuild index from tree" path, which does not exist. Assert the ignore as early as possible to minimise it.

# Verify Dropbox ignore stops the index DB syncing

Type: task
Status: resolved
Blocked by: none

## Question

Does `xattr -w com.dropbox.ignored 1` actually stop the classic macOS Dropbox client from syncing the aardvark index database, and does it hold for the `-wal` and `-shm` sidecar files that WAL mode would create?

This is a fact that must be established empirically on this machine's client, not asserted from documentation. Everything about WAL and about any future background writer depends on the answer, because the index DB currently lives at `/Users/Dave/Dropbox/aardvark/00_INDEX🗂️/aardvark.db`, inside the synced tree, with `journal_mode = delete`.

Establish:

- Whether the attribute is honoured by the installed client version, verified by observation rather than by reading docs.
- Whether it survives the file being rewritten in place by SQLite, which is the case that matters, since an ignored file that loses its ignore status on the next write is worse than useless.
- Whether it must be applied to `-wal` and `-shm` separately, and what happens to a sidecar file created after the attribute was set on the parent DB.
- Whether the attribute is per-machine, and therefore whether `av init` must set it on every new system on every machine.

The answer records what was done, what was observed, and the exact command sequence `av init` would need to run.

If the attribute turns out not to work, this ticket does not decide the fallback: it reports the fact, and the fallback becomes a fresh ticket.

## Answer

Resolved 2026-08-27, empirically, against the live Dropbox client (classic desktop client, version 268.4.4072, daemon confirmed running). Every claim below was verified by server-side listing through the Dropbox API, not by reading documentation.

### The headline

`com.dropbox.ignored` works on a file, but **file-level ignore is insufficient for WAL**. Directory-level ignore works completely and is the mechanism to use.

### Findings

**1. File-level ignore genuinely stops upload.** Two identical SQLite databases were created side by side in `00_INDEX🗂️/`, with the attribute set on one. A server-side listing showed only the control file. The ignored file was never uploaded.

**2. The attribute is durable across SQLite's write patterns.** It survived 500 in-place inserts, a `journal_mode` switch, and a `VACUUM`, which rewrites the entire database. The inode is preserved through ordinary writes, and the attribute persists.

**3. The sidecars do not inherit it, and Dropbox uploads them.** SQLite creates `-wal` and `-shm` fresh, with no extended attributes at all. With a WAL connection held open, the server-side listing showed `ignored.db-wal` and `ignored.db-shm` uploaded, while the parent `ignored.db` remained correctly absent. The uploaded WAL was **stale and partial**: 4,152 bytes on the server against 103,032 bytes on disk at the moment of listing. That is precisely the corruption scenario, and it is worse than the status quo, because the server would hold a fragment of a write-ahead log with no main database to apply it to.

The attribute cannot be pre-set on the sidecars, because they do not exist until SQLite creates them, and they are created and destroyed per connection.

**4. Directory-level ignore covers everything, including children created later.** With `com.dropbox.ignored` set on a directory before any content existed, a database plus both sidecars were created and held open inside it. A recursive server-side listing of the parent showed no trace of the directory or any child.

**5. `com.dropbox.attrs` is not a sync indicator.** It appears on ignored files too. It means only that Dropbox has seen the file. An early version of this investigation used it as the signal and reached the wrong conclusion. Only a server-side listing is authoritative.

**6. It is per-machine, necessarily.** The attribute is a local extended attribute, and an ignored file is never uploaded, so there is nothing to carry it to another machine. Any machine running aardvark must set it locally, which means `av init` must set it, and a repair path must be able to re-set it.

### Facts later tickets depend on

- The mechanism is `xattr -w com.dropbox.ignored 1 <directory>`, applied to a **directory**, before or after content exists.
- `/Users/Dave/Dropbox/aardvark/00_INDEX🗂️/` currently contains exactly one file, `aardvark.db`. There is nothing else in it to lose by ignoring it.
- The live `aardvark.db` is 528,384 bytes and **is currently syncing to Dropbox**, confirmed present server-side. The hazard described on the map is live today, not hypothetical.
- Probe artefacts were created under `00_INDEX🗂️/_av_ignore_probe/` and `00_INDEX🗂️/_av_dir_probe/` and have been removed locally.

### What this does not decide

Which directory gets ignored is a decision, not a fact, and it is left to a new ticket: ignoring `00_INDEX🗂️` wholesale costs nothing today but takes a reserved system folder permanently out of sync, whereas moving the database into a dedicated ignored subdirectory is cleaner but needs a migration and a change to `paths.find_db_path`.

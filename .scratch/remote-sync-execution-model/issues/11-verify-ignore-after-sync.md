# Verify ignore-after-sync behaviour and specify server-side purge

Type: task
Status: resolved
Blocked by: none

## Question

When `com.dropbox.ignored=1` is set on a directory that Dropbox has **already** uploaded content from, does Dropbox remove the server-side copy, or does the already-synced data persist on the server indefinitely?

Ticket 01 only verified the attribute set **before** any content existed. Two live cases depend on the after-the-fact behaviour:

- The existing system: `aardvark.db` (528,384 bytes) is confirmed present on Dropbox's servers right now.
- A second machine cloning the Dropbox tree: Dropbox may upload the DB and its `-wal`/`-shm` sidecars in the window between folder-clone and the first `aardvark` command that lazily asserts the ignore (see ticket 07).

### The work

- Empirically, with the same method as ticket 01 (server-side listing via the Dropbox API, not documentation): create a directory, let a file in it sync server-side, then set `com.dropbox.ignored=1` on the directory and re-list. Record whether the server copy disappears, persists, or is only removed on the next local write.
- If it does **not** auto-purge, specify the cleanup: whether `initialiser` and a repair path issue a best-effort server-side delete when the Dropbox API is connected (`settings["dropbox"]["enabled"]`), and what the fallback is when it is not (a logged instruction to remove `00_INDEX🗂️` from dropbox.com manually).
- The answer records what was observed and the exact cleanup steps, if any, that ticket 07's implementation must also carry.

## Context from ticket 07 (2026-08-28)

Ticket 07 decided the ignore mechanism (wholesale ignore of `00_INDEX🗂️`, set at init, re-asserted lazily per run via `ctypes` libc `setxattr`, gated on Dropbox-tree membership). It explicitly deferred server-side cleanup of already-uploaded data to this ticket. This ticket blocks nothing on the critical path: ticket 08 (WAL) needs only the ignore decision, which ticket 07 made.

## Answer

Resolved 2026-08-28, empirically, against the live Dropbox client (classic desktop client v268.4.4072, daemon confirmed running) on macOS 26.6. Every server-side claim verified by Dropbox API listing (`list_folder`, `get_file_metadata`, `search`), not documentation. Account `davidrobertyoung@gmail.com`, namespace `8768679`.

### Headline

**Dropbox purges the server-side copy when `com.dropbox.ignored=1` is set on a directory that has already synced.** Promptly (within seconds), with no local content write required — setting the extended attribute alone is the trigger. So the already-uploaded data does **not** persist, and ticket 07 needs **no** server-side cleanup code.

### What was done

| Time (UTC) | Action | Server-side result |
|---|---|---|
| 10:54:52 | Created `/Users/Dave/Dropbox/aardvark/_av_purge_probe/probe.txt` (60 B) | Uploaded within ~10 s — `list_folder` shows it, `file_id id:gZBVNKlIsd0AAAAAAGtGXA` |
| 10:55:00 | `xattr -w com.dropbox.ignored 1` on the **directory** | Within seconds: `list_folder /aardvark/_av_purge_probe` → `FILE_NOT_FOUND`; parent listing no longer contains `_av_purge_probe`; `get_file_metadata` on the file_id → `NOT_FOUND`; `search` finds nothing |
| +90 s, +120 s | (wait) | Still absent — stable, not eventual-consistency lag |
| 10:57:05 | `xattr -d com.dropbox.ignored`, append to `probe.txt`, add `probe2.txt` | +75 s: both files back on the server; `probe.txt` **kept its original `file_id`** |
| 10:58:53 | Deleted local probe dir | Confirmed gone server-side |

### Findings

1. **Ignore-after-sync purges the server copy.** No content write needed; the metadata change from `setxattr` is enough. This is the answer to the ticket's question — the data does not persist indefinitely.
2. **The purge is stable** — verified absent at 2 minutes, and via three independent API paths (folder listing, id lookup, search).
3. **Reversible.** Removing the attribute re-uploads the directory and its contents. The pre-existing file retained its Dropbox `file_id`, so within this window it is a hide/unhide, not a delete/recreate. (Not something aardvark relies on, but it means an accidental ignore-then-unignore loses nothing.)
4. **Client-driven, not API-driven.** The purge is done by the local Dropbox desktop client in response to the xattr. It is completely independent of aardvark's own Dropbox API connection (`settings["dropbox"]["enabled"]` / the app refresh token).

### Cleanup spec for ticket 07

- **No server-side delete step.** The `setxattr` on `00_INDEX🗂️` that ticket 07 already specifies — at `init`, and re-asserted idempotently on every non-completion run in `cl_utils.main` — is sufficient on its own. The live `aardvark.db` (528 KB, currently on Dropbox's servers per ticket 01) will be removed automatically the first time the ignore is asserted.
- **Do not add a Dropbox API `files/delete` fallback.** It is redundant given the above, and mildly dangerous: it would delete a `00_INDEX` copy that a *different* machine might legitimately still be syncing if that machine has opted out of the ignore. The xattr mechanism is correctly per-machine; an API delete is not.
- **No fallback needed when the Dropbox API is not connected.** The purge does not use the API. As long as the Dropbox *client* is running on the machine, the xattr is enough; if the client is not running, nothing syncs anyway.
- **Ordering constraint (carried to ticket 07).** On a second machine the tree already exists, so `init` never runs there — that machine relies entirely on the per-run re-assertion. The `setxattr` must therefore run in `cl_utils.main` **before** `db.get_connection` / `db.initialise_schema` opens the DB, so the ignore is asserted (and the purge begins) before any `-wal`/`-shm` sidecar is created.

### Residual risk (belongs to ticket 07, not resolved here)

The second-machine race still has a non-zero window: between cloning the tree and the first `av` run, Dropbox can upload `aardvark.db` and a partial `-wal` (ticket 01 finding 3). This test confirms the first `av` run's ignore purges them — but a machine that pulls *during* the window could receive a partial DB. Mitigation is asserting the ignore as early as possible (the ordering constraint above); full closure would need a "rebuild index from tree" path, which does not exist today.

### Caveat

This is Dropbox desktop-client behaviour (v268.4.4072), not a documented API guarantee, and could change in a future client version — the same caveat ticket 01 carries.

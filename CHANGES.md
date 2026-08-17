
## Release Notes

**v0.3.0 - August 17, 2026**

- **ENHANCEMENT:** renumbered the six root skeleton folders onto the same two-digit, uppercase scheme already used inside each `00_09_system` folder: `00_index`→`00_INDEX`, `01_inbox`→`01_INBOX`, `P.ROJECTS`→`02_P.ROJECTS`, `A.REAS`→`03_A.REAS`, `R.ESOURCES`→`04_R.ESOURCES`, `09_archive`→`09_ARCHIVE` (numbers 05-08 stay reserved). Run `repair_emoji` to renumber an existing system.
- **FIXED:** `06_bin` was described as "items pending deletion" with a 🗑️ trash-can emoji; it's actually a Unix-`/bin`-style folder for scripts and executables. Description and emoji (now 📜) corrected; the folder's base name is unchanged.
- **FIXED:** `find_db_path` now locates the index folder by a case-insensitive scan rather than an exact-case glob, so it can still find a system's database before that system has been renumbered onto the new uppercase scheme.
- **FIXED:** a rename that only changes a folder's case (e.g. `01_inbox` → `01_INBOX`) no longer raises a false "already exists" error. On a case-insensitive filesystem - the macOS default - the old and new paths resolve to the same directory entry; the collision check now uses `os.path.samefile` to tell that apart from an actual collision with something else.

**v0.2.1 - August 17, 2026**

- **FIXED:** `repair_emoji` failed with `sqlite3.OperationalError: attempt to write a readonly database` against an existing system, because renaming `root.index` - the folder `aardvark.db` itself lives in - permanently write-poisons the open connection for every write that follows, even though the rename that caused it succeeds. `root.index` is now always repaired last, and `set_emoji`'s index write is committed before the physical rename rather than after.
- **FIXED:** dropped the space between a folder's title and its emoji (`Health🏥`, not `Health 🏥`).

**v0.2.0 - August 17, 2026**

- **FEATURE:** new `set_emoji` command, changing the emoji on an existing area, category, project or static system folder. Renaming a folder invalidates the stored path of everything nested inside it, so the rename and a path rewrite across every descendant row land in a single transaction, with the directory move undone if any of the index work fails.
- **FEATURE:** new `repair_emoji` command, resetting every static system folder in an existing system to its declared emoji. Run this once against any system created before v0.2.0.
- **FEATURE:** folder emoji for user-supplied titles are now suggested by Claude, falling back to the offline keyword search whenever the API cannot be reached - the `anthropic` package missing, no credentials, no network, a policy refusal, or a reply that is not exactly one emoji. Set `emoji: use_llm: false` in the settings file to stay offline.
- **FEATURE:** new `--emoji` flag on `add_area`, `add_category` and `new_project`, using a given emoji verbatim and skipping both the suggestion and the prompt. Without it, an interactive session shows the suggestion to accept or replace, while a non-interactive one accepts it silently.
- **FIXED:** the 39 static system folders created by `init` were routed through the keyword picker, which had no match for 11 of their 14 distinct titles and so left most of them on the generic folder emoji, and picked a backhand-pointing-down hand for "Index". Their emoji are now declared alongside the skeleton itself.
- **ENHANCEMENT:** the offline picker now singularises before giving up, so plural titles that used to fall back ("Films", "Links", "Flights") resolve. Exact matches still win, leaving "Books" as a stack of books rather than one book.

**v0.1.3 - August 17, 2026**

- **FIXED:** the v0.1.2 tag itself still carried a mismatched version stamp (`0.1.1` instead of `0.1.2`) since the fix committed for v0.1.1 was tagged one release too late. This release ships with a version stamp that correctly matches its own tag.

**v0.1.2 - August 17, 2026**

- **FIXED:** corrected a stale dev-build version stamp committed at the v0.1.1 tag (`0.1.1.dev5` instead of `0.1.1`), which made setuptools-scm see a dirty tree mid-build and bump the computed version forward on any fresh build.

**v0.1.1 - August 17, 2026**

- **REFACTOR:** renamed distribution/package to aardvark-jd (PyPI/GitHub name 'aardvark' was unavailable); the installed CLI command remains 'aardvark'.

**v0.1.0 - August 17, 2026**

- **FEATURE:** initial aardvark PARA + Johnny Decimal CLI implementation - `init`, `new_project`, `add_area`, `add_category`, `add_id` and `search` commands, an SQLite index with FTS5 search, and automatic emoji suffixing for non-ID folders.

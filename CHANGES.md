
## Release Notes

**v0.1.3 - August 17, 2026**

- **FIXED:** the v0.1.2 tag itself still carried a mismatched version stamp (`0.1.1` instead of `0.1.2`) since the fix committed for v0.1.1 was tagged one release too late. This release ships with a version stamp that correctly matches its own tag.

**v0.1.2 - August 17, 2026**

- **FIXED:** corrected a stale dev-build version stamp committed at the v0.1.1 tag (`0.1.1.dev5` instead of `0.1.1`), which made setuptools-scm see a dirty tree mid-build and bump the computed version forward on any fresh build.

**v0.1.1 - August 17, 2026**

- **REFACTOR:** renamed distribution/package to aardvark-jd (PyPI/GitHub name 'aardvark' was unavailable); the installed CLI command remains 'aardvark'.

**v0.1.0 - August 17, 2026**

- **FEATURE:** initial aardvark PARA + Johnny Decimal CLI implementation - `init`, `new_project`, `add_area`, `add_category`, `add_id` and `search` commands, an SQLite index with FTS5 search, and automatic emoji suffixing for non-ID folders.

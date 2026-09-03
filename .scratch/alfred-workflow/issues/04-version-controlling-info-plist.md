# Is `info.plist` committed, or generated?

Type: grilling
Status: open
Blocked by: 01, 02, 14

## Question

The workflow lives in the repo, but Alfred owns `info.plist` and rewrites it whenever the workflow is edited in Alfred's UI. Decide how the repo copy stays authoritative and reviewable.

Decide:

- **Committed, or generated from source?** Either the plist is the source and is edited in Alfred, or a higher-level source (YAML, Python, a small builder) is the source and the plist is a build artefact. The first makes Alfred's visual editor usable and makes every diff unreadable; the second makes diffs meaningful and means the visual editor's output has to be reverse-engineered or discarded.
- **If committed: how are Alfred's rewrites contained?** Whether a normalisation step (`plutil -convert xml1`, key sorting, stripping generated state) runs before commit, and whether that is a git hook, a make target, or a documented manual step.
- **If generated: what does the source look like, and how faithful must the builder be?** The builder only has to emit the objects this workflow uses, not all of Alfred's — but it has to emit them correctly, and it becomes code that needs tests under the charting rule that the real logic lives in the package.
- **Where the scripts live.** Alfred can hold script bodies inline inside `info.plist` or reference external script files in the workflow directory. External files are diffable, testable and importable; inline bodies are what Alfred's editor produces by default. Decide, and decide whether that choice is what makes the first question answerable.
- **The round trip.** Whether editing in Alfred's UI is supported at all after this decision, and if so, what the path back into the repo is. An answer that forbids the visual editor entirely is legitimate, but it should be a chosen constraint rather than an accident.

Ticket 02's findings on what Alfred actually rewrites, and when, are the decisive input here.

# How a workflow gets from a repo directory into Alfred, and stays linked to it

Research findings for ticket `02-alfred-deployment-mechanics`, written 2026-09-03.

## What was tested

Everything empirical below was observed on this machine, read-only, against **Alfred 5.7.3 (build 2320)** (`/Applications/Alfred 5.app/Contents/Info.plist`). The live preferences folder is `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences`, containing 88 entries under `workflows/`, of which 86 are workflow directories holding an `info.plist`. Nothing in the Alfred preferences folder was modified, created, moved or deleted, and Alfred was not restarted or reconfigured. Where a question could only be answered by changing Alfred's state, it is flagged as unverified rather than guessed.

Documentation claims are pinned to Alfred 5 unless noted. Two of the primary forum sources predate Alfred 5 and are marked accordingly.

## Summary of the decisive findings

- The directory name in `workflows/` is the workflow's **UID**, it is arbitrary, and it is referenced nowhere inside `info.plist`. Alfred loads any directory containing an `info.plist`. A workflow can be installed by creating the directory directly.
- A `.alfredworkflow` file is a **zip archive**, asserted by Alfred's own exported UTI declaration. Alfred's developer states directly that unzipping one into the workflows folder installs it.
- Alfred does **not** gratuitously rewrite `info.plist`. Two workflows on this machine are byte-for-byte identical to the file committed in their upstream Git repository at the matching release tag, after import and use. Alfred's own team version-controls `info.plist` verbatim.
- Alfred **does** rewrite it when the workflow is edited, and the observed rewrite reorders the `objects` array without changing its contents — pure diff noise. One `userconfigurationconfig` default was also found rewritten in place.
- User configuration values are stored in a separate `prefs.plist` **inside the workflow directory**, and Alfred's documentation explicitly tells you to gitignore it. An installer can write it, but Alfred will not notice until the workflow is reloaded; there is a supported AppleScript command that does the write and the reload together.
- `prefs.json`'s `current` key is the de facto way to locate the preferences folder and is what the ecosystem's installers read, but it is **not documented by Alfred**. There is a second, corroborating source in the `com.runningwithcrayons.Alfred-Preferences` defaults domain.
- Symlinking a workflow directory works and is common practice, but it is community practice rather than a documented, supported feature, and it interacts badly with this particular preferences folder, which is inside Dropbox and inside the `/Apps/` subfolder that Alfred explicitly recommends against.

## Locating the preferences folder programmatically

On this machine `~/Library/Application Support/Alfred/prefs.json` reads:

```json
{
  "current" : "/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences",
  "syncfolders" : { "5" : "/Users/Dave/Dropbox/Apps/alfred" },
  "localhash" : "bd157708898b9864090ecde47297c9f8caf9006f"
}
```

The `current` key resolves correctly. Alfred's own help pages do not document this file: the sync page describes only the user-facing `Set preferences folder…` button, and the preferences troubleshooting page names `~/Library/Application Support/Alfred/` and `~/Library/Preferences/com.runningwithcrayons.Alfred*` as locations without explaining how a synced location is recorded. So `current` is observable and reliable in practice, but it is an implementation detail rather than a published contract, and an installer should treat it as such.

It is nonetheless the ecosystem standard. `resolve-alfred-prefs`, the resolver used by `alfred-link` and hence by the whole `alfy` family of npm-installed workflows, reads exactly this key first and falls back to the Alfred 3 `syncfolder` default only if the file is missing:

```js
const prefsPath = JSON.parse(fs.readFileSync(prefsJsonPath)).current;
```

A second, independent source exists on this machine: `defaults read com.runningwithcrayons.Alfred-Preferences syncfolder` returns `/Users/Dave/Dropbox/Apps/alfred`, which is the *parent* of the `.alfredpreferences` bundle, matching `syncfolders."5"` in `prefs.json`. Reading `prefs.json` first and treating this defaults key as a fallback is the safest ordering, because the defaults key is absent when the user has never set a sync folder.

There is a trap worth calling out. `~/Library/Application Support/Alfred/Alfred.alfredpreferences` **also exists on this machine**, but it contains only `preferences/local/<localhash>` — it is a vestigial local shell, not the live preferences. An installer that hardcodes the default path, or that falls back to it when `prefs.json` is unreadable, would silently write a workflow into a folder Alfred never reads. The fallback must be treated as a failure, not as a default.

When Alfred is absent altogether, `prefs.json` does not exist and `/Applications/Alfred 5.app` is missing. The honest behaviour for `aardvark install_alfred` is to detect both, and to fail with a specific message rather than creating directories speculatively. Note also that workflows are a Powerpack (paid) feature, so Alfred being installed is not sufficient — an unlicensed Alfred will accept the directory and never run it. This machine has `license.Q12MRQVQVY.plist` and `powerpack.Q12MRQVQVY.dat` present; I did not attempt to determine a reliable programmatic licence check and would not recommend one.

Inside a running workflow the question does not arise: Alfred sets `alfred_preferences` as a script environment variable, documented as "The location of Alfred.alfredpreferences. If a user has synced their settings, this will allow you to find out where their settings are regardless of sync state." That is the documented answer for code running under Alfred; `prefs.json` is only needed by the installer, which runs outside it.

## How Alfred discovers workflows, and whether the UUID matters

The directory name does not matter, and this is verifiable three ways.

First, six of the 86 installed workflow directories are not named `user.workflow.<UUID>` at all. They are `Google Suggest`, `Kill Process`, `markdust`, `picaxe`, `URL Encode-Decode` and `zettelkasten`. All six contain an `info.plist` with an ordinary `bundleid` (`jdfwarrior.googlesuggest`, `com.tedwise.killprocess`, `co.uk.thespacedoctor.markdust`, and so on), and all six have `disabled` set to `false`. Alfred has loaded them across many years and many restarts. Two stray files at the top of `workflows/` — `alfred-workflows.sublime-project` and `alfred-workflows.sublime-workspace` — are simply ignored, as is any directory without an `info.plist`.

Second, the directory name appears nowhere inside the plist. Grepping all 86 `info.plist` files for the literal string `user.workflow` returns zero matches. No workflow references its own directory name. (Three plists do contain their directory name as a substring — `markdust`, `picaxe`, `zettelkasten` — but only because the directory was named after the workflow's own keyword and bundle id, not because of any cross-reference.)

Third, Alfred's AppleScript dictionary treats the folder name as a first-class identifier, coequal with the bundle id. From `/Applications/Alfred 5.app/Contents/Resources/Alfred.sdef`:

- `reload workflow` — "Reload Workflow with given UID (folder name) or Bundle ID"
- `reveal workflow` — "Reveal Workflow with given UID (folder name) or Bundle ID"

So the directory name *is* the workflow UID, the thing surfaced to scripts as `alfred_workflow_uid`, and the bundle id is a separate identifier. `user.workflow.<UUID>` is merely the name Alfred generates when it creates a workflow itself; nothing requires it. The `user.workflow.` prefix and the UUID have no semantics beyond uniqueness.

This has a direct consequence for the install design: `install_alfred` can create a stable, human-legible directory such as `workflows/aardvark-jd` rather than minting a UUID, and that name will be stable across machines, which a generated UUID would not be. `alfred-link` does exactly this, naming the directory after the npm package.

A forum answer from 2013 states the same rule plainly: "Alfred will pick up any directory in the workflow folder. I created symlinks to my git repository in the workflow folder and it works like a charm." That thread predates Alfred 5, but the behaviour is confirmed by the six non-UUID directories loaded on this machine today.

Can a workflow be installed by creating the directory directly rather than importing a file? Yes. Andrew Pepperrell, Alfred's developer, states it explicitly: "The .alfredworkflow files are actually just a zip of the workflow. You can unzip them into Alfred's Workflow folder (within the Alfred.alfredpreferences) and Alfred will automatically load them ready for use." He attaches one caveat: "Alfred does a number of validations and checks when importing through the UI which would be skipped if you manually placed a workflow in Alfred's workflow folders, but if these are from trusted sources such as your own, then this is absolutely fine." That caveat is satisfied here — the source is the user's own repo. Note that this thread is from the Alfred 3 era; the mechanism still holds on 5.7.3, as evidenced by the loaded non-UUID directories, but the wording is not a current-version statement.

## Symlinks

**Verified on this machine:** a symlinked *subdirectory* inside a workflow works. `workflows/user.workflow.C0DE9A05-0001-4A1F-9E42-A1FEED000001/bin` is a symlink to `/Users/Dave/Dropbox/aardvark/02_PROJECTS🚀/P20_29_atomic⚛️/P22_tooling_setup⚒️/P22.13_alfred-prompts/bin`, and it has survived in place. That workflow is also worth noting for a different reason: both its directory UUID and every object UID inside it (`A1000000-0000-4000-8000-000000000001` and siblings) are hand-crafted rather than random, and Alfred has accepted them. UIDs need only be unique strings; they need not be real UUIDs.

**Not verified:** whether a symlinked *workflow directory* survives an Alfred restart and a preferences sync on this setup. Testing that would require creating a symlink inside the Alfred preferences folder and restarting Alfred, which this investigation was forbidden to do. What follows is therefore documented practice and inference, not measurement here.

Symlinking the workflow directory is well-established community practice and is what the tooling ecosystem does:

- `alfred-link` — the installer behind every `alfy`-based workflow distributed on npm — does literally `fs.symlink(src, dest)` where `dest` is `<prefs>/workflows/<package-name>`. This is the single most widely deployed instance of the pattern.
- deanishe, author of the `alfred-workflow` Python library, on the forum: "I symlink my own workflows. Your code belongs in version control, not in an .alfredpreferences bundle in your Dropbox."
- A separate thread contains the clearest statement of the mechanics: "Alfred doesn't care about the name of the directory your workflow is in… Alfred identifies workflows by their bundle IDs", with the caveat "Alfred is a lot slower to pick up changes to info.plist if they weren't made via Alfred's own GUI."

That last caveat matters for the "live link" promise in the map. Editing `info.plist` in the repo will not necessarily take effect in Alfred immediately. The supported remedy is the AppleScript `reload workflow` command shown above, which accepts either the folder name or the bundle id — so `install_alfred`, and any repo-side edit, can force a reload deterministically.

**No first-party statement either way.** I searched Alfred's help site and the forum and found no post from Andrew or Vero endorsing or forbidding symlinked workflow directories. Several threads asking the question went unanswered by staff. Treat symlinking as tolerated-and-widespread rather than supported.

### The specific risk on this machine

Two documented hazards apply to this preferences folder in particular, and they are the strongest argument against symlinking here.

**The Dropbox `/Apps/` folder.** This preferences folder is at `/Users/Dave/Dropbox/Apps/alfred/…`. Alfred documents that "users who select the *Dropbox/Apps/* folder for syncing have experienced odd behaviour (e.g. preferences not saving correctly)", that the folder is "reserved for applications using the Dropbox API (which Alfred doesn't use)", and that Alfred has "excluded the Apps folder from the available syncing locations and do not recommend that you choose it as your sync folder". Anyone using it anyway does so "at your own risk". This is a pre-existing condition of the machine rather than something the aardvark workflow introduces, but it means intermittent preference-saving failures are already an expected background hazard, and a symlink experiment that appears to fail may be failing for this reason instead.

**Dropbox and symlinks.** Dropbox's own help page states that on macOS "the path of the file or folder the symlink points to can be synced to Dropbox", and warns that on other devices without the target present the link will not resolve. Independent write-ups describe Dropbox following symlinks and uploading target content rather than preserving the link. The sources disagree in detail and I could not resolve the discrepancy authoritatively, so treat the exact behaviour as **unverified**. The safe reading is the pessimistic one: a symlink from inside a Dropbox-synced preferences folder to a Git working tree outside it is, at best, unreliable, and at worst causes Dropbox to upload the entire repository — `.git` included — into the synced preferences. On a second Mac the link would either be broken or materialised as a stale copy, and the "live link to the repo" property would be silently lost while appearing to work.

**Permissions.** Alfred's sync documentation warns that sync clients which "cannot sync file permissions… can break your Workflows", and the forum carries a steady stream of `Couldn't posix_spawn: error 1` reports traced to scripts losing their executable bit through Dropbox. Any file the workflow needs to execute should either be invoked through an interpreter (`python3 script.py`) rather than relying on its executable bit, or have its permissions re-asserted by `install_alfred`.

### What this suggests for the install design

The map's two-track plan survives, but the author track should be specified carefully. Options, best first:

1. **Symlink the workflow directory** at `<prefs>/workflows/aardvark-jd → <repo>/alfred`, then call `reload workflow "aardvark-jd"` via AppleScript. Gives the live link the map wants. Carries the Dropbox risk above, and needs a real test on this machine before being locked in.
2. **Symlink only the code, not the workflow.** Keep a small real directory in `workflows/` holding `info.plist` and icons, and symlink or simply point its scripts at the repo. Since the workflow shells out to the `aardvark` binary anyway, and the map already decided the real logic lives in `aardvark_jd/alfred/` inside the package, the workflow directory may contain almost no code — in which case only `info.plist` genuinely needs to be live, and even that could be a symlinked file rather than a symlinked directory.
3. **Copy on demand.** `install_alfred` copies the repo directory into `workflows/`, preserving `prefs.plist` if present. No live link, but no ambiguity; re-running the command is the edit cycle.

Option 2 deserves attention because it sidesteps the whole question: if the only file that must stay in sync is `info.plist`, and the executable logic is reached through the installed package, then the coupling problem the ticket is trying to solve is much smaller than it first appears.

## What Alfred rewrites in `info.plist`

This is the decisive input to ticket 04, so it was tested directly rather than inferred.

### The vendor version-controls the plist

Alfred's own team commits `info.plist` to Git, unwrapped, at `Workflow/info.plist`. Verified for `alfredapp/google-suggest-workflow`, `alfredapp/shortcuts-workflow`, `alfredapp/snippet-transformer-workflow`, `alfredapp/amazon-suggest-workflow` and `alfredapp/1password-workflow`; `vitorgalvao/pin-plus-workflow` uses the same `Workflow/` layout, and `xilopaint/alfred-things` uses `src/info.plist`. Whatever the drawbacks, this is the pattern the vendor itself uses.

The blog tutorial on sharing workflows via GitHub is less encouraging — it says "Learning how to include the workflow internals in the repository… is left as an exercise for the reader" — but the vendor's own repositories answer the exercise.

### Alfred does not rewrite the plist merely by loading or running a workflow

Five installed workflows on this machine come from `alfredapp` repositories, and every one has a `version` matching an existing upstream Git tag. Fetching each repository at its matching tag and diffing against the installed copy isolates exactly what Alfred changed after import.

| Workflow | Installed version | Diff against upstream tag |
|---|---|---|
| `google-suggest-workflow` | 2023.1 | **0 lines — byte-identical** |
| `snippet-transformer-workflow` | 2023.2 | **0 lines — byte-identical** |
| `amazon-suggest-workflow` | 2023.3 | 48 lines, two semantic changes (below) |

Two workflows are byte-for-byte identical to the file the vendor committed, having been imported, kept and used. This is strong evidence that Alfred does **not** reformat, re-indent, reorder keys, regenerate UIDs, or inject absolute paths on import or on ordinary use. Neither of those two files contains a `/Users/` path.

### What Alfred does rewrite

The `amazon-suggest` diff contains exactly two changes, and no formatting noise:

1. **The `objects` array was reordered.** Parsed as a data structure, the two arrays contain the same objects — `sorted(map(repr, …))` compares equal — but the element order differs: upstream is `[0B28D7B8…, 221025C2…]`, installed is `[221025C2…, 0B28D7B8…]`. No object's content changed. This is the rewrite to worry about: it is invisible semantically and produces a large, meaningless textual diff. On a workflow with dozens of objects, moving a single node on the canvas could reshuffle the array and generate hundreds of changed lines.
2. **A `userconfigurationconfig` default was rewritten in place**, from `com.au` to `co.uk` for the `top_level_domain` variable. See the caveat in the configuration section below — I could not establish which action caused this.

`uidata` is the other rewrite surface. It is a dictionary keyed by object UID holding canvas coordinates, for example `{"xpos": 35.0, "ypos": 35.0}`, and every one of the 86 workflows has it. Any nudge of any node in the editor changes it. It is genuine state that must be preserved (deleting it loses the layout), but it is churny.

The `disabled` key also lives at the top level of `info.plist` — all 86 workflows have it, all set to `false`. Toggling a workflow off in Alfred's UI therefore dirties the version-controlled file.

### The canonical serialisation

Alfred writes standard Apple XML property lists, and the form is completely consistent across all 86 files:

- XML plist 1.0 with the Apple DTD, never binary. `plutil`/`file` report XML for all 86.
- **Tab-indented.** All 86 files begin their body lines with a literal tab (`0x09`); not one uses spaces.
- **Top-level keys in strict alphabetical order**, in every file: `bundleid`, `category`, `connections`, `createdby`, `description`, `disabled`, `name`, `objects`, `readme`, `uidata`, `userconfigurationconfig`, `variables`, `variablesdontexport`, `version`, `webaddress`. This is Cocoa's plist serialiser sorting dictionary keys, and it applies at every level of nesting.

Key frequencies across the 86: `webaddress`, `uidata`, `readme`, `objects`, `name`, `disabled`, `description`, `createdby`, `connections` and `bundleid` appear in all 86; `userconfigurationconfig` in 34; `category` in 33; `version` in 29; `variables` in 16; `variablesdontexport` in 10.

The practical consequence for ticket 04 is that a hand-written `info.plist` will be normalised into this form the moment Alfred saves it. Committing a plist that is already in canonical form — easiest achieved by letting Alfred write it once and committing the result — means the only diffs you will ever see are semantic, plus `uidata` and `objects`-order churn.

### Absolute paths

Twenty-nine of the 86 `info.plist` files contain `/Users/` strings, but every sample inspected is an author-entered value — a script body, a configured file path, a hardcoded command such as `/Users/Dave/anaconda/envs/jekyll/bin/bundle exec jekyll build`. There is no evidence of Alfred injecting machine-specific absolute paths of its own; the two byte-identical vendor workflows contain none. Absolute paths in the aardvark plist would therefore be the workflow author's choice, and the map has already decided the correct answer: the interpreter path is baked in by `install_alfred`, and a workflow configuration variable is the manual override. Both of those belong in `prefs.plist`, not `info.plist` — see below.

### What could not be determined

I could not establish **when** Alfred writes `info.plist`: whether merely opening a workflow in the editor is enough, or whether an actual edit is required. Answering that means opening a workflow in Alfred's UI and watching the file, which would modify the user's installation. The byte-identical pair proves only that import and use are not enough. Treat "opening the editor may dirty the file" as an open risk for ticket 04.

## The `.alfredworkflow` export format

**It is a zip archive**, asserted by Alfred itself. `/Applications/Alfred 5.app/Contents/Info.plist` exports the UTI:

```
UTTypeIdentifier: com.runningwithcrayons.alfred.workflow
UTTypeDescription: Alfred Workflow
UTTypeConformsTo: [ public.zip-archive ]
UTTypeTagSpecification:
  public.filename-extension: [ alfredworkflow, alfred3workflow, alfred4workflow, alfred5workflow ]
```

Conformance to `public.zip-archive` is the vendor's own machine-readable declaration, and it agrees with Andrew's forum statement quoted earlier: "The .alfredworkflow files are actually just a zip of the workflow." The archive's root contains the workflow's files directly — `info.plist`, icons, scripts — not a wrapping folder. The alternative extensions are version-gating hints for authors shipping several builds; Alfred 5 accepts all four.

**Yes, it can be produced from a directory by a script**, which is what the map's release step needs. `zip -r aardvark-jd.alfredworkflow . -x '.*'` from inside the workflow directory is the whole operation. Two things Alfred's own Export does that a naive `zip` does not:

- **`category` is stripped.** Alfred's documentation states that "category information is stripped when exporting so that the user can choose their own ideal category." A scripted export should delete the `category` key to match, or simply never set it.
- **Non-exportable variables are stripped.** A forum contributor describes packaging as "not keeping Workflow Environment Variables that have `Don't Export` checked", handled with `PlistBuddy` before zipping. This is the `variablesdontexport` key, present in 10 of the 86 installed workflows: it lists the names in `variables` whose values must not leave the machine. A scripted export must honour it, or it will ship whatever was in those variables. For the aardvark workflow the cleanest answer is to avoid `variables` entirely and put everything user-specific in `prefs.plist`, which should not be in the archive at all.
- **`prefs.plist` and `.git` must be excluded.** Alfred's configuration documentation says to gitignore `prefs.plist`; the same logic says to exclude it from the archive, so that an installing user gets the author's defaults rather than the author's settings. One forum poster confirms Alfred's own Export "does NOT include a copy of .git directories", so a scripted export should match that.

I did **not** verify the exact contents of an Alfred-produced `.alfredworkflow`, because there is none on this machine and producing one would require driving Alfred's UI. The strip-list above is assembled from Alfred's documentation plus forum reports, not from inspecting an export.

### Installing when the bundle id already exists

Alfred's documentation says a unique bundle id is what "ensur[es] Alfred recognises the workflow if you issue an updated version later on", which establishes that the bundle id — not the directory name — is the identity used for updates. I could **not** find first-party documentation of the exact behaviour when importing a `.alfredworkflow` whose bundle id matches an installed workflow: whether Alfred replaces in place, prompts, or installs a duplicate; and specifically whether it preserves the existing `prefs.plist`, hotkeys and keywords. Andrew's remark that "Alfred historically struggled with preserving user customizations like hotkeys and keywords during updates" suggests this is not a clean guarantee, but that comment is from the Alfred 3 era and may no longer hold.

This is a real gap and it matters for the PyPI/conda track. The safe design is not to rely on import-time merging at all: have `install_alfred` detect an existing directory with the same bundle id, preserve its `prefs.plist`, and replace the rest — rather than shelling out to `open` on the `.alfredworkflow` and hoping.

## Setting a configuration variable from outside Alfred

**Yes, and there are two ways, one of which is officially supported.**

The storage model is documented plainly on Alfred's Workflow Configuration page:

> "Workflow Configuration defaults are stored in `info.plist`, but changed values are saved to `prefs.plist`."

and, in the same breath:

> "Add the latter to your `.gitignore` so as to not commit your personal configuration to version control."

This is confirmed on disk. The *schema* lives in `info.plist` under `userconfigurationconfig`, an array of dictionaries each carrying `label`, `description`, `type`, `variable` and a `config` dictionary holding `default`. For example, the Emoji Search workflow (`com.github.jsumners.alfred-emoji`) declares a `popupbutton` bound to variable `skin_tone`. The *value* lives in a sibling file, `<workflow dir>/prefs.plist`, a plain XML plist keyed by variable name:

```xml
<dict>
	<key>skin_tone</key>
	<string>0</string>
</dict>
```

Note the shape of the evidence: 34 of the 86 workflows declare `userconfigurationconfig`, but only **one** has a `prefs.plist`. Alfred writes the file lazily — only once a value actually diverges from its default. An installer must therefore create `prefs.plist` if it is absent, and merge into it if it is present, never assume it exists.

Documented field types include text fields, popup buttons, checkboxes (which reach scripts as `0` or `1`) and file pickers (which display `~` but expose the full `/Users/…` path). Values reach scripts as environment variables, and "environment variables are always strings".

### Writing it from an installer

**The supported route is AppleScript.** Alfred's scripting dictionary defines:

```
set configuration — Modify workflow configuration value, or set environment variable
    (direct)     The name of the variable
    to value     The value to set
    in workflow  The workflow bundle identifer
    exportable   … This option is ignored for workflow configuration items

remove configuration — Revert workflow configuration value to default, or delete environment variable
    (direct)     The name of the variable
    in workflow  The workflow bundle identifer
```

So `install_alfred` can bake in the interpreter path with a single call:

```bash
osascript -e 'tell application id "com.runningwithcrayons.Alfred" to set configuration "python_path" to value "/opt/homebrew/opt/python@3.12/bin/python3.12" in workflow "com.davidyoung.aardvark-jd"'
```

Andrew confirms on the forum that this "persists the configuration to the `prefs.plist`". It also has the advantage of going through Alfred, so the running instance sees the change immediately. The commands have existed since Alfred 3.6.

**The unsupported route is writing `prefs.plist` directly.** It works — the file is a plain XML plist — but Alfred will not notice. Andrew, in a July 2024 thread, states that Alfred does not hot-reload external changes to `prefs.plist` and gives two workarounds: use the AppleScript command, or edit the file and then issue the `reload workflow` AppleScript command. Direct writes to `prefs.plist` are therefore only safe when Alfred is not running, or when followed by an explicit `reload workflow`.

There is one wrinkle: in that same thread Andrew acknowledged that the AppleScript persistence "turns out to actually be a bug which will be fixed in the next release". That was July 2024 and this machine runs 5.7.3, so the fix is almost certainly present, but I could not verify it without writing a configuration value.

**Recommendation for `install_alfred`:** write `prefs.plist` directly when creating the workflow directory (so a fresh install is correct even if Alfred is not running), then, if Alfred is running, issue `reload workflow` — or use `set configuration` when the workflow already exists. Writing the file directly is also the only option when installing before Alfred has ever loaded the workflow.

### An unresolved anomaly

The `amazon-suggest` diff showed `userconfigurationconfig[1].config.default` changed from `com.au` to `co.uk` — that is, a **default in `info.plist`**, not a value in `prefs.plist`. That workflow has no `prefs.plist`. Two explanations fit, and I could not distinguish them without changing Alfred's state:

- Under some path — plausibly the configuration sheet Alfred presents *at import time* — Alfred writes the chosen value into the `info.plist` default rather than into `prefs.plist`.
- The default was edited deliberately in the workflow editor's configuration builder, which is an author action and legitimately writes `info.plist`.

If the first is true it is significant for ticket 04, because it means ordinary user configuration can dirty the version-controlled file. **Flagged as unverified.** It would be cheap to settle deliberately on a throwaway workflow, and worth doing before committing `info.plist` to the repo.

## Things I could not verify

Stated plainly, so none of these is mistaken for a finding:

- Whether a symlinked **workflow directory** survives an Alfred restart and a Dropbox preferences sync on this machine. Not tested; would have required modifying the Alfred preferences folder.
- Whether merely **opening** a workflow in Alfred's editor rewrites `info.plist`, or whether an edit is required.
- What Alfred does on **import of a `.alfredworkflow` whose bundle id is already installed** — replace, prompt, or duplicate — and whether it preserves `prefs.plist`, hotkeys and keywords.
- The **exact contents of an Alfred-generated `.alfredworkflow`**. The strip-list (`category`, non-exportable variables, `.git`) comes from documentation and forum reports, not from inspecting an export.
- **Dropbox's precise symlink behaviour.** Dropbox's own help page and third-party accounts disagree, and I could not reconcile them.
- Whether the July 2024 `set configuration` persistence bug is fixed in 5.7.3. Very likely, but not confirmed.
- Any **first-party statement on symlinked workflow directories**. I found none, in either direction.
- A reliable **programmatic Powerpack licence check**.

## Sources

Alfred first-party documentation:

- [Workflow Configuration](https://www.alfredapp.com/help/workflows/workflow-configuration/) — `info.plist` defaults vs `prefs.plist` values, gitignore advice, field types
- [Configuring an Installed Workflow](https://www.alfredapp.com/help/workflows/user-configuration/)
- [Exporting and Sharing Workflows](https://www.alfredapp.com/help/workflows/advanced/sharing-workflows/) — `category` stripped on export; bundle id and updates
- [Workflow Variables](https://www.alfredapp.com/help/workflows/advanced/variables/)
- [Script Environment Variables](https://www.alfredapp.com/help/workflows/script-environment-variables/) — `alfred_preferences`, `alfred_workflow_uid`, `alfred_preferences_localhash`
- [Sync your Alfred settings between Macs](https://www.alfredapp.com/help/advanced/sync/) — sync mechanics; permissions warning
- [Using the Dropbox Apps folder](https://www.alfredapp.com/help/troubleshooting/dropbox-apps-folder/) — the `/Apps/` warning
- [Persisting Alfred's Preferences](https://www.alfredapp.com/help/troubleshooting/preferences/)
- [Tutorial: Share your Workflows Using GitHub](https://www.alfredapp.com/blog/guides-and-tutorials/share-workflow-on-github/)

Alfred first-party artefacts on this machine (Alfred 5.7.3, build 2320):

- `/Applications/Alfred 5.app/Contents/Info.plist` — UTI declaration, `public.zip-archive` conformance
- `/Applications/Alfred 5.app/Contents/Resources/Alfred.sdef` — `reload workflow`, `reveal workflow`, `set configuration`, `remove configuration`
- `~/Library/Application Support/Alfred/prefs.json`
- `~/Library/Preferences/com.runningwithcrayons.Alfred-Preferences.plist` (`syncfolder`)
- `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences/workflows/` — 86 workflows

Alfred forum (community; staff posts attributed where identified):

- [How to programmatically add/import a workflow from a .alfredworkflow file?](https://www.alfredforum.com/topic/8842-how-to-programmatically-from-bashiterm-to-addimport-a-workflow-from-a-alfredworkflow-file/) — **Andrew**: zip format, unzip-to-install, skipped validations. Alfred 3 era.
- [Hot-Reload changes to `prefs.plist`](https://www.alfredforum.com/topic/22002-hot-reload-changes-to-prefsplist/) — **Andrew**: no hot-reload; use `set configuration` or `reload workflow`; July 2024 bug acknowledgement
- [Make the "workflows" directory compatible with being a git repository](https://www.alfredforum.com/topic/361-make-the-workflows-directory-compatible-with-being-a-git-repository/) — "Alfred will pick up any directory in the workflow folder". 2013, Alfred 2 era.
- [What is your workflow for developing these workflows?](https://www.alfredforum.com/topic/9251-what-is-your-workflow-for-developing-these-workflows/) — deanishe on symlinking
- [Best way to Develop, Build and Update a Github-based Workflow?](https://www.alfredforum.com/topic/10681-best-way-to-develop-build-and-update-a-github-based-workflow/) — directory name irrelevant; slower `info.plist` pickup; packaging strips non-exportable variables
- [Git-managed, sym-linked development workflow](https://www.alfredforum.com/topic/2385-git-managed-sym-linked-development-workflow/) — export excludes `.git`
- [Help with symlink workflows](https://www.alfredforum.com/topic/11015-help-with-symlink-workflows/)

Vendor and ecosystem repositories:

- [alfredapp/google-suggest-workflow](https://github.com/alfredapp/google-suggest-workflow), [alfredapp/snippet-transformer-workflow](https://github.com/alfredapp/snippet-transformer-workflow), [alfredapp/amazon-suggest-workflow](https://github.com/alfredapp/amazon-suggest-workflow), [alfredapp/shortcuts-workflow](https://github.com/alfredapp/shortcuts-workflow), [alfredapp/1password-workflow](https://github.com/alfredapp/1password-workflow) — `Workflow/info.plist` committed verbatim; tags used for the byte-comparison
- [LitoMore/alfred-link](https://github.com/LitoMore/alfred-link) — `fs.symlink` into `<prefs>/workflows/<package-name>`
- [SamVerschueren/resolve-alfred-prefs](https://github.com/SamVerschueren/resolve-alfred-prefs) — reads `prefs.json` `current`

Third-party:

- [Can Dropbox sync symlinks?](https://help.dropbox.com/sync/symlinks)

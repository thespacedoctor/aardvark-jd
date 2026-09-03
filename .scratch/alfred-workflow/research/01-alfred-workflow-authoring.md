# How an Alfred 5 workflow is authored, and what a Script Filter can return

Research findings for ticket `01-alfred-workflow-authoring`. Written 2026-09-03.

## Scope and provenance

Every claim below is tagged with how it was established:

- **[Docs]** — stated in Alfred's own help at `alfredapp.com/help/workflows/`, quoted or closely paraphrased.
- **[Alfred-bundled]** — read out of the template workflows Alfred 5 ships inside its own application bundle, at `/Applications/Alfred 5.app/Contents/Frameworks/Alfred Framework.framework/Versions/A/Resources/*.alfredworkflow`. These are first-party artefacts written by Alfred itself, so they are the authority on what Alfred actually writes into `info.plist`.
- **[Corpus]** — derived from the 88 workflows installed at `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences/workflows/`, 86 of which contain a parseable `info.plist`.
- **[Inferred]** — a conclusion drawn from consistent evidence but not stated anywhere first-party. Treat these as working assumptions, not facts.

The installed version is **Alfred 5.7.3 (build 2320)**, confirmed from `/Applications/Alfred 5.app/Contents/Info.plist`. Unless a feature is called out below as having a specific introduction version, assume it applies to Alfred 5 generally and is present in 5.7.3.

**The Alfred forum could not be read.** `alfredforum.com` returns HTTP 403 to every direct fetch, from both a plain client and a browser-user-agent client, so no forum thread is cited as a primary source here. Where a search engine surfaced forum content I have treated it as a hint to be confirmed against the docs or the corpus, never as evidence on its own. This is the one research avenue the ticket asked for that I could not open.

---

## 1. What a workflow directory contains, and the shape of `info.plist`

A workflow is a plain directory. Alfred installs workflows into `Alfred.alfredpreferences/workflows/`, normally under a directory named `user.workflow.<UUID>`, but **the directory name is not load-bearing**: 8 of the 88 installed workflows live in human-readable directories (`Google Suggest`, `Kill Process`, `markdust`, `picaxe`, `URL Encode-Decode`, `zettelkasten`) and work normally. [Corpus] The identity Alfred cares about is the `bundleid` inside `info.plist`, which the docs describe as the key "ensuring Alfred recognises the workflow if you issue an updated version later on" ([Sharing Workflows](https://www.alfredapp.com/help/workflows/advanced/sharing-workflows/)). [Docs]

The directory contains `info.plist` (required), an `icon.png` for the workflow, any icons the results reference, and any script files. There is no manifest beyond `info.plist`; anything else in the directory is just files the scripts can reach. [Corpus]

`info.plist` is a standard binary or XML property list. Across the 86 parseable examples, the top-level keys are these. [Corpus]

| Key | Present in | Meaning |
| --- | --- | --- |
| `bundleid` | 86/86 | Workflow identity; the value that drives updating and the `alfred_workflow_bundleid` env var |
| `name` | 86/86 | Display name |
| `description` | 86/86 | Short description |
| `createdby` | 86/86 | Author |
| `webaddress` | 86/86 | Author URL |
| `disabled` | 86/86 | Boolean |
| `readme` | 86/86 | The "About This Workflow" text; Markdown is supported |
| `objects` | 86/86 | Array of workflow objects |
| `connections` | 86/86 | Dictionary of object-to-object links |
| `uidata` | 86/86 | Canvas coordinates, keyed by object UID |
| `category` | 33/86 | Stripped on export, per the docs |
| `version` | 29/86 | Workflow version string |
| `userconfigurationconfig` | 34/86 | The Configuration Builder schema (see section 5) |
| `variables` | 16/86 | Workflow environment variables |
| `variablesdontexport` | 10/86 | Names of variables whose values are blanked on export |

### Objects

`objects` is an array. Each entry is a dictionary with exactly four keys: `uid` (an uppercase UUID string), `type` (a reverse-DNS object-type string), `version` (an integer schema version for that object type, bumped by Alfred, not by you), and `config` (a per-type dictionary). [Alfred-bundled, Corpus]

The object types the ticket asks about, with their exact type strings and the `config` keys Alfred writes: [Alfred-bundled, Corpus]

- **Script Filter** — `alfred.workflow.input.scriptfilter`. Covered in detail in section 4.
- **Run Script** — `alfred.workflow.action.script`. Config keys: `script`, `scriptfile`, `type` (language), `scriptargtype`, `escaping`, `concurrently`.
- **Notification** — `alfred.workflow.output.notification`. Config keys: `title`, `text`, `sticky`, `output`, `onlyshowifquerypopulated`, `lastpathcomponent`, `removeextension`.
- **Open URL** — `alfred.workflow.action.openurl`. Config keys: `url`, `browser`, `spaces`, `skipqueryencode`, `skipvarencode`. (An older `utf8` boolean appears in the docs' example for this object; the corpus writes `skipqueryencode`/`skipvarencode` instead, so the docs' example is stale on this point.)

Other types this project will plausibly need, all confirmed present in the corpus: `alfred.workflow.utility.argument` (Arg and Vars), `alfred.workflow.utility.conditional`, `alfred.workflow.utility.json`, `alfred.workflow.action.revealfile`, `alfred.workflow.action.terminalcommand`, `alfred.workflow.action.browseinalfred`, `alfred.workflow.output.clipboard`, `alfred.workflow.output.largetype`, `alfred.workflow.trigger.universalaction`, `alfred.workflow.input.keyword`, `alfred.workflow.input.listfilter`.

### Connections

`connections` is a dictionary keyed by **source** object UID. Each value is an array of connection dictionaries, one per outgoing link, with these keys: [Alfred-bundled, Corpus]

- `destinationuid` — the UID of the target object.
- `modifiers` — an integer bitmask. `0` means the plain, unmodified connection; a non-zero value makes the link an *alternate action* fired only when those modifier keys are held.
- `modifiersubtext` — the subtitle shown to the user while the modifier is held.
- `vitoclose` — a boolean. `true` means "do not close Alfred's window when traversing this connection". The Alfred-bundled `Chaining Inputs` template sets `vitoclose: true` on exactly the connection its own readme describes as having the "Window Behaviour" checkbox ticked, which pins the meaning. [Alfred-bundled]

The `modifiers` bitmask is the standard Cocoa `NSEvent` modifier-flag mask, not an Alfred-specific enumeration: `shift = 131072` (1 << 17), `control = 262144` (1 << 18), `option/alt = 524288` (1 << 19), `command = 1048576` (1 << 20), `fn = 8388608` (1 << 23). Combinations are the sum. Decoding all 123 non-zero connection modifiers in the corpus with this table produces only valid combinations and no residue — `1572864` is alt+cmd, `393216` is shift+ctrl, `1835008` is shift+alt+cmd. [Corpus, Inferred — the mapping is not documented, but the fit is exact across 123 samples]

Note the deliberate asymmetry here, because ticket 03 depends on it: **connection modifiers and JSON `mods` are two different mechanisms.** A connection modifier routes the flow to a *different object*. A JSON `mods` block (section 3) changes the *arg and variables* handed to the *same* object. They compose, and both are available at once.

### What is stable identity versus Alfred churn

For version control (ticket 04), the useful split is: [Corpus, Inferred]

- **Stable, and yours to author:** `bundleid`, `name`, `description`, `createdby`, `webaddress`, `version`, `readme`, `userconfigurationconfig`, `variables`, every object's `config`, and — critically — every object `uid`. Alfred does not regenerate object UIDs on save; they are minted once when the object is created and then referenced by `connections` and `uidata` forever.
- **Alfred-generated churn:** `uidata` (the `xpos`/`ypos` of every object, rewritten whenever anything is dragged), and each object's `version` integer, which Alfred bumps when it migrates an object to a newer schema.
- **Must not be committed:** `prefs.plist`. See section 5 — the docs explicitly say to gitignore it.

---

## 2. The Script Filter JSON schema in full

Source: [Script Filter JSON Format](https://www.alfredapp.com/help/workflows/inputs/script-filter/json/). [Docs] The script writes JSON to stdout. The top-level object carries `items` plus four optional siblings: `rerun`, `variables`, `skipknowledge` and `cache`.

`items` is an array of zero or more item objects. Every field:

**`uid` : STRING (optional).** "A unique identifier for the item. It allows Alfred to learn about the item for subsequent sorting and ordering of the user's actioned results." The docs are emphatic that "it is important that you use the same UID throughout subsequent executions of your script to take advantage of Alfred's knowledge and sorting."

**`title` : STRING (required).** "There are no options for this element and it is essential that this element is populated."

**`subtitle` : STRING (optional).** Secondary line.

**`arg` : STRING or ARRAY (recommended).** "The argument which is passed through the workflow to the connected output action." An array of strings passes multiple arguments. The docs warn: "If excluded, you won't know which result item the user has selected."

**`icon` : OBJECT (optional).** `{"path": "./custom_icon.png"}`, where `path` is relative to the workflow's root folder. An optional `type` key changes the interpretation: `"fileicon"` makes Alfred fetch the system icon for the path; `"filetype"` makes `path` a UTI such as `com.apple.rtfd`.

**`valid` : true|false (optional, default true).** An invalid item is not actioned on return. Combines with `autocomplete` — see below.

**`match` : STRING (optional).** Covered in section 2.2.

**`autocomplete` : STRING (recommended).** Populated into Alfred's search field when the user presses Tab. Importantly: "If the item is set to `valid: false`, the auto-complete text is populated into Alfred's search field when the user actions the result." That pairing — `valid: false` plus `autocomplete` — is the documented way to build a drill-down where Return descends rather than acts, which is directly relevant to the `av` keyword's command hierarchy.

**`type` : "default" | "file" | "file:skipcheck" (optional, default "default").** `"file"` makes Alfred treat the result as a file, enabling its standard file actions. Alfred verifies existence first, at "a very small performance implication"; `"file:skipcheck"` skips that check.

**`mods` : OBJECT (optional).** Section 3.

**`action` : OBJECT | ARRAY | STRING (optional).** Defines the Universal Action items used when actioning the result, and *overrides* `arg` for actioning purposes. A bare string or array lets Alfred derive the content type; an object gives explicit control via `text`, `url`, `file` and `auto` keys.

**`text` : OBJECT (optional).** `{"copy": "...", "largetype": "..."}`, controlling ⌘C and ⌘L. Without it, `arg` is used for both.

**`quicklookurl` : STRING (optional).** URL or file path (absolute, or `~/`-relative) for Quick Look on Shift or ⌘Y. Falls back to `arg`.

**`variables` : OBJECT (optional).** Per-item variables. Section 6.

### 2.1 What `uid` does to ordering and knowledge

This is the decisive point for ticket 05, and the docs are unambiguous. [Docs]

> "Alfred learns to prioritise item results like he learns any other, meaning the order in which your workflow results are presented will be based on Alfred's knowledge (using the item UID) and not the order your script returns the items."

So supplying `uid` **surrenders control of result order to Alfred**. There are three positions available:

1. **Omit `uid` entirely.** Items appear in exactly the order the script returns them. No learning, ever.
2. **Supply `uid`.** Alfred reorders by learned selection frequency. This is the behaviour the map's note about Alfred "learning selection order" is relying on.
3. **Supply `uid` *and* `skipknowledge: true`** (new in Alfred 5). This "preserves the given item order while allowing Alfred to retain knowledge of your items, like your current selection during a re-run."

Two caveats on `skipknowledge` that the docs state and that matter for a design decision:

> "`skipknowledge` prevents the creation of new knowledge but does not ignore what Alfred already learned. In other words, by adding and removing `skipknowledge` you may generate local ordering which does not exactly match the order of your items."

and

> "Knowledge is retained per object. Replace the object with a duplicate to force reset the ordering."

The practical consequence for this project: knowledge is scoped to the Script Filter *object*, not to the workflow, and it is keyed by the `uid` strings the script emits. If the `--json` contract's identifiers for entities are stable across runs (a JD code, say, rather than a row ID or an array index), Alfred's learning will be genuinely useful and will survive re-indexing. If they are not stable, the learning is worse than useless — it will attach to the wrong rows. The map's "Frecency and recall" open question can be partly answered by simply choosing a stable `uid`, and the third option above (`uid` plus `skipknowledge`) is the setting to reach for during the prototype, because it keeps the selection stable during a `rerun` without polluting Alfred's ordering while the design is still moving.

### 2.2 What `match` adds over `title`

> "The `match` field enables you to define what Alfred matches against when the workflow is set to 'Alfred Filters Results'. If `match` is present, it fully replaces matching on the `title` property."

Three things follow, all load-bearing for ticket 05. [Docs]

- `match` is **only consulted when "Alfred Filters Results" is switched on** in the Script Filter's configuration. In the default mode, where the script re-runs on every keystroke and does its own filtering, `match` is inert.
- It is a **replacement, not an addition**. If you set `match`, the title stops being matched. So the usual construction is to set `match` to a superset string that includes the title plus the extra tokens you want searchable — the corpus shows exactly this, in the 1Password workflow's `` match: `${item["title"]} ${displayURL} ${item["category"]} ${item["tags"]?.join(" ")}` ``, at `user.workflow.02683378-6858-49C5-BB9E-042DC6270563/1password.js`. [Corpus]
- Matching is "always treated as case insensitive, and intelligently treated as diacritic insensitive. If the search query contains a diacritic, the match becomes diacritic sensitive."

The Match Mode setting sits next to the "Alfred Filters Results" checkbox and governs how a query is tested against the phrase (which means the title, or `match` if present). The four modes, with the docs' own examples for the phrase "My Family Photos": [Docs]

| Mode | Behaviour | Matches |
| --- | --- | --- |
| **Exact from start or whitespace** (default) | Exact match from a word boundary | "My Family Photos", "Family Photos", "Photos" |
| **Exact from start** | Strictest; exact from the beginning only | "My Family Photos", "My Family" |
| **Word matching — Any order** | Loose; words in any order, prefixes allowed | "My Family Photos", "Photos Family", "Ph Fa" |
| **Word matching — Sequential** | Loose; words in written order, prefixes allowed | "My Family Photos", "My Photos", "Fa Ph" |

Note that none of these is true fuzzy matching in the "subsequence of characters" sense; the loosest modes are word-prefix matching. For a JD tree where a user might type `31.12` or `aardvark` or `p31`, "Word matching — Any order" is the mode that will feel closest to what the map assumes, and `match` should carry the JD code, the title, and the path segments. This is worth stating plainly because the map's phrase "Alfred's built-in fuzzy matching" slightly overstates what Alfred does.

In `info.plist` these two settings are `alfredfiltersresults` (boolean) and `alfredfiltersresultsmatchmode` (integer). The corpus shows mode `0` in 59 filters and mode `2` in 8, consistent with `0` being the documented default. The full integer-to-mode mapping is **[Inferred]** as the docs' listing order (0 = exact from start or whitespace, 1 = exact from start, 2 = word matching any order, 3 = word matching sequential); only `0` is confirmed as the default, from its dominance in the corpus. Set this in Alfred's UI and read the value back rather than guessing.

### 2.3 Errors

There is no error channel in the schema — which confirms the map's "errors are results, not exceptions" decision as being forced rather than chosen. A Script Filter that fails must still emit well-formed JSON, and the honest pattern is a single item carrying the diagnosis, with `valid` set according to whether Return should attempt a fix. Anything the script writes to stderr goes to the workflow debugger ([Using the Workflow Debugger](https://www.alfredapp.com/help/workflows/advanced/debugger/)) and is invisible to the user. [Docs, Inferred]

---

## 3. The `mods` block

> "The mod element gives you control over how the modifier keys react. It can alter the looks of a result (e.g. subtitle, icon) and output a different `arg` or session variables."

The docs' own example: [Docs]

```json
"mods": {
  "alt":     { "valid": true, "arg": "alfredapp.com/powerpack/", "subtitle": "https://www.alfredapp.com/powerpack/" },
  "cmd":     { "valid": true, "arg": "alfredapp.com/shop/",      "subtitle": "https://www.alfredapp.com/shop/" },
  "cmd+alt": { "valid": true, "arg": "alfredapp.com/blog/",      "subtitle": "https://www.alfredapp.com/blog/" }
}
```

**Available modifiers.** "Valid modifiers include `cmd` (⌘), `alt` (⌥), `ctrl` (⌃), `shift` (⇧), `fn`, and any combination through the use of `+`. For example: `cmd+alt` only activates when both keys are pressed." That is five base modifiers and any combination, which is comfortably more than the map's requirement of Craft, Todoist, Drive and Finder on four separate keys. [Docs]

**Fields a mod may override.** `valid`, `arg`, `subtitle`, `icon` and `variables`. The docs demonstrate the first four and describe the fifth explicitly. [Docs]

**Yes, a mod can carry its own `variables` — and this is the answer ticket 03 needs.** The docs are direct about it, including a sharp inheritance rule that is easy to get wrong:

> "It is also possible to add a `variables` object for each mod in the item object, allowing you to differentiate when a mod result is selected within your workflow. Note that when setting a `variables` object on a mod, this **replaces** the item variables, and doesn't inherit from them, allowing maximum flexibility. When a mod doesn't contain a `variables` object, it will assume the item variables. To prevent this, add an empty variables object: `"variables": {}`."

So the semantics are all-or-nothing per modifier: a mod either inherits the item's entire `variables` dictionary (by omitting its own) or replaces it wholesale (by supplying one). There is no merge. Any contract in which a modifier needs both shared item context *and* a modifier-specific discriminator must therefore repeat the shared keys inside every mod's `variables`.

The corpus contains a worked example of exactly that pattern, and it is an official Alfred Gallery workflow rather than a random third party. In `user.workflow.02683378-6858-49C5-BB9E-042DC6270563/1password.js`, the `getModifiers` function builds one action object per modifier and then does: [Corpus]

```javascript
// Each action has a variable with the same name, plus a set of item variables
Object.keys(actions).forEach(key => actions[key]["variables"] = Object.assign({ action: key }, item_vars))

return {
  none:  actions[envVar("mod_none")],
  cmd:   actions[envVar("mod_cmd")],
  alt:   actions[envVar("mod_alt")],
  ctrl:  actions[envVar("mod_ctrl")],
  shift: actions[envVar("mod_shift")]
}
```

Two things are worth lifting from that. First, it merges the shared `item_vars` into each modifier's own `variables` explicitly, precisely because inheritance does not happen. Second, the `none` key is **not** an Alfred feature — it is not in the documented modifier list. The script emits it inside `mods` (where Alfred ignores it) and separately reads it back to compute the item-level default arg and variables. It is a neat idiom for "one table describes all five behaviours including the unmodified one", but do not expect Alfred to interpret `none`. [Corpus, Inferred]

A second, simpler corpus example without variables is `user.workflow.77DAF526-580B-4D2A-B78D-CF74CB935C21/emoji.js`, which uses `alt`, `shift` and `ctrl` to vary `subtitle`, `arg` and `icon` on the same result. [Corpus]

**Which mechanism to use for the mirror-opening design.** The map wants Enter to open Craft, Todoist and Drive together and each modifier to open one, plus Finder. Both mechanisms can express that:

- *Connection modifiers* — draw four extra links from the Script Filter to four different Open URL / Reveal File objects, each with a `modifiers` bitmask. The subtitle hint comes from `modifiersubtext` and is fixed for the whole filter.
- *JSON `mods`* — one connection, and each item varies its own `arg`/`variables` per modifier. The subtitle hint is per item, so it can name the actual target ("Open in Craft — Project Aardvark").

The second is the better fit here, because the per-item subtitle can show *which* mirror URL will open and can be suppressed (via `valid: false`) on entities that have no such mirror yet. It also keeps the object graph small, which matters for ticket 04's diffability. Note that the per-entity mirror URLs the map already requires in the `--json` contract are exactly the payload each mod's `arg` needs.

---

## 4. `rerun`, caching, and Script Filter run behaviour

### 4.1 `rerun`

> "Scripts can be set to re-run automatically after an interval using the `rerun` key with a value from 0.1 to 5.0 seconds. The script will only be re-run if the script filter is still active and the user hasn't changed the state of the filter by typing and triggering a re-run."

The key is set at the top level of the returned JSON, alongside `items`. [Docs] Alfred's own bundled `Advanced Script Filters` template demonstrates it, with a Script Filter whose script emits `"rerun": 1` and an incrementing `timer` session variable. [Alfred-bundled]

**So yes — a filter can return results and then update them**, but only on its own re-invocation, and only in a full replacement. There is no partial or streaming update: each run returns a complete `items` array that replaces the previous one. The three mechanisms available for "show something fast, then show the real thing" are `rerun` (poll every 0.1–5.0s and swap the whole result set), the `cache` block with `loosereload` (below), and returning a placeholder item immediately while a background process fills a cache the next run reads.

### 4.2 Caching — new in Alfred 5.5

> "Scripts which take a while to return can cache results so users see data sooner on subsequent runs. The Script Filter presents the results from the previous run when caching is active and hasn't expired. Because the script won't execute when loading cached data, we recommend this option only be used with 'Alfred filters results'."

`{"cache": {"seconds": 3600}}`, with `seconds` between 5 and 86400. The optional `loosereload` key "asks the Script Filter to try to show any cached data first. If it's determined to be stale, the script runs in the background and replaces results with the new data when it becomes available." [Docs]

Caches are invalidated by: editing the Script Filter object, clicking **Flush** in the debugger, reloading the workflow (these three act on one workflow), and by typing `reload` into Alfred or restarting Alfred (these two affect all workflows). [Docs]

This is directly relevant to the map's measured 240 ms cold `aardvark fd`. With `cache` plus `loosereload`, the 240 ms is paid once per TTL rather than on every keyword entry, and the user sees the previous index instantly. The docs' own caveat applies neatly: caching is recommended *only* with "Alfred Filters Results", which is the mode the map has already chosen.

### 4.3 Run Behaviour: queue mode, queue delay, whitespace trimming

These are object settings, not JSON, found under the "Run Behaviour" button on the Script Filter. [Docs, [Script Filter Input](https://www.alfredapp.com/help/workflows/inputs/script-filter/)]

**Queue Mode.** Either "wait until the previous script finishes before running the script again with the latest argument", or "terminate the currently running script and run a new instance of the script with the latest argument". The docs' guidance: "if you have a slow script, it may be better to use the 'terminate' option. If you have a script which needs to finish each time and is quite fast, then use the 'queue' option." In `info.plist` this is `queuemode`; the corpus shows `1` in 70 filters and `2` in 11, so `1` is the default. [Docs, Corpus]

**Queue Delay — this is the debounce.** "This option allows you to tweak the behaviour of when a script is queued (or run). It allows you to hold back from running the script if the user is currently typing, which is beneficial if your script is slow or uses a web API. It can also prevent flooding. If you select the Automatic option, Alfred profiles how fast the user is typing and tries to only run the script when the user has stopped typing." The docs then give an explicit recommendation: "Unless you have a reason not to, it's recommended that you select 'Always run immediately for first typed arg character' as this may make your script input perceptually faster to the user." [Docs]

In `info.plist` this is three keys: `queuedelaymode` (corpus: `0` in 71, `1` in 10 — `0` is Automatic), `queuedelayimmediatelyinitially` (a boolean, corpus: `true` in 59, `false` in 22 — this is the "run immediately for first typed arg character" flag the docs recommend), and `queuedelaycustom` (corpus: `3` in 70, `1` in 11). **The unit of `queuedelaycustom` is not documented and I could not determine it** — the values seen are consistent with either an index into a preset list or a count of 0.1 s ticks, and it is presumably only consulted when `queuedelaymode` is `1`. [Corpus, Inferred]

**Argument Whitespaces Trimming.** "By default, the option is set to trim irrelevant spaces to prevent a script from being re-run unnecessarily if there are multiple spaces." The alternative is "Don't trim arg spaces, as they are significant". In `info.plist` this is `argumenttrimmode`, which is `0` in all 68 filters that set it. This matters for ticket 06: if the `title :: description` free-text field is entered through a Script Filter argument, the default trimming is fine, but any design that makes leading or trailing spaces meaningful needs this changed. [Docs, Corpus]

### 4.4 Keyword argument types

The Script Filter's keyword has three argument modes, and the choice changes when the script first runs — which sets the latency budget. [Docs]

- **Argument Required** — "The script is not run until an argument is present." Placeholder title and subtitle show until then; once an argument is typed, the `runningsubtext` ("Please Wait") shows until the first results arrive.
- **Argument Optional** — "The script is run immediately on the keyword matching", with placeholder and running subtext shown until results return.
- **No Argument** — runs immediately on keyword match, and "if an argument is typed, Alfred no longer sees this Script Filter as relevant and any related results are removed from Alfred."

For the map's "one call fetches the whole index on keyword entry", **Argument Optional** is the mode required: it fires the fetch the moment `av` is matched, so the 240 ms overlaps with the user typing their query rather than following it.

In `info.plist` this is `argumenttype`. Alfred's own `Keywords` template confirms two of the three values directly — it contains one keyword with `argumenttype: 0`, `withspace: true` and a `{query}` placeholder in its subtext (Argument Required), and one with `argumenttype: 2`, `withspace: false` and no query use (No Argument). Value `1` is therefore Argument Optional by elimination, given the docs list exactly three modes; it is the most common value in the corpus at 52 of 82 filters. [Alfred-bundled, Corpus, Inferred for the value 1]

The related `runningsubtext` key holds the "Please Wait" replacement text, and `title`/`subtext` hold the placeholder shown before the script runs. The docs note placeholder text "is no longer required, but is recommended... Without a placeholder, your filter will still work, but will not appear until you start typing your search query text." [Docs]

### 4.5 Item count limits

**Not documented, and I could not verify a limit.** Neither the JSON format page nor the Script Filter page states a maximum number of items, and searching Alfred's own site produced nothing. The docs' only performance statement is the opposite one — that letting Alfred filter is "a highly efficient way to return results fast" — plus the note that `type: "file"` costs "a very small performance implication" per item because of the existence check. This leaves the map's assumption ("the index stays small enough to ship whole") genuinely untested, and it is the right thing for the ticket-05 prototype to measure. [Docs]

---

## 5. Workflow configuration variables

There are two distinct mechanisms, and the ticket-12 binary-path override needs the first. [Docs, [Workflow Configuration](https://www.alfredapp.com/help/workflows/workflow-configuration/) and [Using Variables](https://www.alfredapp.com/help/workflows/advanced/variables/)]

**Configuration Builder** — user-facing. Reached by clicking the `[x]` icon at the top right of the workflow editor, "Configuration Builder" tab. This produces the settings sheet a user sees on import and via "Configure Workflow…". This is the right mechanism for a binary-path override, because it is discoverable without opening any script.

**Workflow Environment Variables** — author-facing. Same `[x]` icon, "Environment Variables" tab. The docs draw the line clearly: use these "to set global values you need to reference throughout the Workflow that users should not modify. If you want others to be able to edit these values locally (e.g. to use a custom path or set an API key for a service), see Workflow Configuration."

### Where the values live — the fact ticket 04 needs

> "Workflow Configuration defaults are stored in `info.plist`, but changed values are saved to `prefs.plist`. Add the latter to your `.gitignore` so as to not commit your personal configuration to version control." [Docs]

This is confirmed in the corpus: exactly one of the 88 installed workflows has a `prefs.plist`, and it contains only the single setting that user had actually changed from its default (`skin_tone`), while the workflow's `info.plist` carries the full `userconfigurationconfig` schema including that field's default. **`prefs.plist` does not exist at all until the user changes something.** [Corpus] So a script reading a configuration variable must handle the default coming from `info.plist`, and must never assume `prefs.plist` exists.

### The `userconfigurationconfig` schema

`userconfigurationconfig` is an array. Each entry is a dictionary with `type`, `variable` (the environment-variable name the script will read), `label`, `description` and a type-specific `config`. Three types appear in the corpus, in 34 of the 88 workflows: [Corpus]

```json
{
  "type": "textfield",
  "variable": "items_search_keyword",
  "label": "Search Keyword",
  "description": "",
  "config": { "default": "1p", "placeholder": "", "required": false, "trim": true }
}
```

```json
{
  "type": "checkbox",
  "variable": "logins_only",
  "label": "Item Structure",
  "description": "",
  "config": { "default": false, "required": false, "text": "Only show Login items" }
}
```

```json
{
  "type": "popupbutton",
  "variable": "mod_none",
  "label": "↩",
  "description": "",
  "config": {
    "default": "open_and_fill",
    "pairs": [["Open and Fill", "open_and_fill"], ["View in 1Password", "view_in_1password"]]
  }
}
```

Note `pairs` is an array of `[display label, value]` two-element arrays — the label the user sees is decoupled from the value the script gets.

The docs name two further types not present in this corpus, **File Picker** and **Slider**, and give two behavioural warnings about them that are easy to trip over: [Docs]

> "The Checkbox configuration returns either `0` (unchecked) or `1` (checked)."

> "The File Picker configuration previews the home folder as `~`, but the Workflow sees the real `/Users/[username]` path. Take advantage of this in the Default Value field: using `~` ensures the path is correctly expanded for your users."

The File Picker point is the one that matters for the binary override: a File Picker with a default of `~/...` gives the script an expanded absolute path, which is precisely what shelling out to a Python interpreter needs. Because "environment variables are always strings", the checkbox is `"0"`/`"1"` in the script's environment, not a boolean.

### Reading configuration at run time, and defaulting

Configuration variables arrive in the script's environment as ordinary environment variables named by the `variable` field. In Alfred objects (a keyword field, a URL, an argument box) they are referenced as `{var:myvariable}`. In scripts, "they are set as environment variables and you access them according to the rules of the language." [Docs] The docs also point out the intended pattern for making a keyword itself user-configurable: "Use variables such as `{var:keyword}` in an object's Keyword field to make them user-customisable."

For defaulting there are two layers, and it is worth being explicit about which does what for ticket 12:

1. The Configuration Builder's own `default` in `info.plist` supplies the value when the user has never touched the setting. This is the layer `aardvark install_alfred` should write, baking in `sys.executable`.
2. The script should *still* defend against an empty string, because a user can clear a text field. The idiomatic shape in the corpus is a shell guard, e.g. the 1Password workflow's `if [[ -z "${alfred_workflow_bundleid}" ]]; then echo '...' >&2; exit 1; fi`. [Corpus]

The map's two-layer plan — `install_alfred` bakes the interpreter path in, and a configuration variable is the manual override — maps cleanly onto this. The one thing to get right is direction: the baked-in path should be the Configuration Builder `default` in `info.plist`, so that a user override lands in `prefs.plist` and *wins*, and so that re-running `install_alfred` updates the default without stamping on an override. That works because the two live in separate files.

### `variables` and `variablesdontexport`

Top-level `variables` in `info.plist` is a flat string-to-string dictionary of Workflow Environment Variables (16 of 88 workflows use it). `variablesdontexport` is an array of variable *names* whose values Alfred blanks when the workflow is exported — used for API keys and machine-specific paths. Two workflows in the corpus list five names each, including `scopusKey` and `attachmentsFolder`. [Corpus] This is the mechanism to reach for when producing the committed `.alfredworkflow` export in ticket 02, so that the author's machine-specific interpreter path does not ship to PyPI users.

---

## 6. Passing state between connected objects

Three routes, all first-party. [Docs]

**Session variables from a Script Filter.** A top-level `variables` object in the returned JSON:

> "Variables within a `variables` object will be passed out of the script filter and remain accessible throughout the current session as environment variables. In addition, they are passed back in when the script reruns within the same session. This can be used for managing state between runs as the user types input or when the script is set to re-run after an interval."

Alfred's own `Advanced Script Filters` template demonstrates the round trip: the script reads `$counter` from its environment, increments it, and emits it back under `variables`, so successive runs within a session see the incremented value. [Alfred-bundled]

**Item variables.** "Individual item objects can have `variables` which are passed out of the Script Filter object if the associated result item is selected in Alfred's results list. `variables` set within an item will override any JSON session variables of the same name." So the precedence is: mod variables (if the mod supplies any, replacing wholesale) > item variables > session variables. [Docs]

**The Arg and Vars utility** (`alfred.workflow.utility.argument`). Config keys are `argument` (a template string, defaulting to `{query}`), `passthroughargument` (a boolean — "You may want to simply add variables using this object, and pass through the input object untouched", which preserves a list of files rather than stringifying it), and `variables` (a dictionary whose values may contain `{query}` and `{var:...}` placeholders). [Docs, Corpus]

**The `alfredworkflow` JSON envelope.** This is the general mechanism, and it is the one that makes the two-step argument entry in ticket 06 straightforward. Any Run Script action can emit this on stdout instead of a bare string: [Docs, [JSON Utility](https://www.alfredapp.com/help/workflows/utilities/json/)]

```json
{
  "alfredworkflow": {
    "arg": "{query}",
    "config": { },
    "variables": { }
  }
}
```

- `arg` "sets the argument passed out... Leaving out `arg` will clear the query, and setting it to `{query}` will pass through the query. Can be a string to pass a single argument or an array of strings to pass multiple arguments."
- `variables` "enables new variables to be set, and stream variables to be overridden."
- `config` "enables dynamic (and overriding) configuration of the workflow objects connected to the output... Only the included fields will be overridden, allowing for partial dynamic configuration."

The docs are explicit that this is not confined to the JSON utility object: "Did you know that you can output the above JSON from a Script Action instead of the JSON Utility? The JSON you see above is native to data passed internally through an Alfred workflow stream." The docs' own example of dynamic `config` is an Open URL object, and they give a useful trick for discovering an object's config keys: right-click the object on the canvas and copy its configuration, or "set it to a unique value in the object's configuration sheet and copy the configuration again."

That `config` override is a genuinely useful lever for this project: a single Open URL object can be pointed at whichever mirror URL the chosen modifier selected, rather than needing one Open URL object per mirror.

**Keeping the window open between steps.** For chained inputs, the connection's "Window Behaviour" option ("don't close") stops Alfred flickering between the two entry steps. Alfred's `Chaining Inputs` template is the canonical example: two keyword inputs, each followed by an Arg and Vars utility storing `{query}` into `first` and `second` respectively, with `vitoclose: true` on the connection between the first input and its Arg and Vars. [Docs, Alfred-bundled]

---

## 7. How a script is invoked

### PATH — the single most important environment fact

> "Alfred's defined `PATH` is `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`, which includes the default install locations for Homebrew on both Intel and Apple Silicon Macs." [Docs, [Understanding the Scripting Environment](https://www.alfredapp.com/help/workflows/advanced/understanding-scripting-environment/)]

> "Note: Prior to Alfred 5, Alfred's PATH was `/usr/bin:/bin:/usr/sbin:/sbin`."

This is decisive for the map's binary-resolution problem. A `pipx`, `uv tool`, conda, or virtualenv install of `aardvark` is **not** on that PATH. Neither is `~/.local/bin`. The docs' framing is that this is deliberate: "Making your Workflow independent of external settings benefits you both as a Workflow developer and user: by ensuring a common starting point, changing this environment must be a conscious decision with clear consequences."

The docs list three remedies, in their own order of preference: [Docs]

1. "Use the full path to your tool. Instead of `do-something`, call `~/my-scripts/do-something`."
2. "Set `PATH` before calling your tools. This can be done before calling your script or in the Workflow Environment Variables."
3. "`source` your shell's configuration file before calling your script. Example: `source \"${HOME}/.zshrc\"`. May make your script slower due to loading unnecessary configurations."

Method 1 is what the map's `install_alfred` plan already does by baking in `sys.executable`, and the docs endorse it as the method that "modifies the least". Method 3 should be avoided outright here, given the map's latency budget.

### The shell, and `~/.zshenv`

> "Note: `~/.zshenv` is a notable exception. It is loaded in every environment by default, which can affect workflow behaviour. Alfred defaults to `/bin/zsh --no-rcs` to avoid this." [Docs]

So the default shell for a shell-language Run Script is zsh with rc files suppressed — no `.zshrc`, no `.zprofile`, and `--no-rcs` also suppresses `.zshenv`. Do not expect any shell function, alias, or PATH edit from the user's dotfiles.

### Working directory

**The working directory is the workflow's own folder.** This is not stated on the Run Script page in those words, but it is implied by "If you don't specify an absolute path, Alfred will look relative to the workflow's folder" for External Scripts, and it is confirmed overwhelmingly by the corpus: script bodies across many workflows invoke `./1password.js 'sanity_checks'`, `python main.py {query}`, `python gollum.py --searchPages "{query}"` and `ruby kill.rb {query}` with no path qualification and no `cd`. [Docs for External Script; Corpus + Inferred for the general cwd claim]

I have marked this **[Inferred]** rather than [Docs] because Alfred's help does not state it for the inline-script case in so many words, and the forum thread that reportedly states it plainly could not be retrieved. The corpus evidence is strong enough to build on, but it is worth confirming in the prototype with a one-line `pwd`.

The reliable, documented way to locate the workflow folder regardless is not a cwd assumption at all — it is to derive it from `alfred_preferences` plus `alfred_workflow_uid`, both of which are documented environment variables.

### The `alfred_*` environment variables

Every one of these is populated for both Run Script actions and Script Filters. Referenced in Alfred object fields as `{const:myvariable}`, and read as ordinary environment variables in scripts. [Docs, [Script Environment Variables](https://www.alfredapp.com/help/workflows/script-environment-variables/)]

| Variable | Meaning |
| --- | --- |
| `alfred_preferences` | Path to `Alfred.alfredpreferences`, wherever the user has synced it |
| `alfred_preferences_localhash` | Mac-specific hash; local prefs live at `…/preferences/local/[hash]` |
| `alfred_theme` | Current theme identifier |
| `alfred_theme_background` | Theme background colour, e.g. `rgba(255,255,255,0.98)` |
| `alfred_theme_selection_background` | Selected-result colour |
| `alfred_theme_subtext` | The user's subtext display mode |
| `alfred_version`, `alfred_version_build` | e.g. `5.0` and `2058` — "useful if your workflow depends on a particular Alfred version's features" |
| `alfred_workflow_bundleid` | Bundle ID of the running workflow |
| `alfred_workflow_cache` | `~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/[bundle id]` |
| `alfred_workflow_data` | `~/Library/Application Support/Alfred/Workflow Data/[bundle id]` |
| `alfred_workflow_name` | Workflow name |
| `alfred_workflow_description` | Workflow description |
| `alfred_workflow_uid` | e.g. `user.workflow.B0AC54EC-…` |
| `alfred_workflow_version` | Workflow version |
| `alfred_debug` | Set to `1` **only** when the debug panel is open — otherwise absent entirely |
| `alfred_workflow_keyword` | "The keyword text used to start an action. **Exclusive to the Script Filter Input.**" |

Two of these deserve emphasis for this project. `alfred_workflow_cache` and `alfred_workflow_data` "will only be populated if your workflow has a bundle id set", so setting `bundleid` is a prerequisite, not a nicety. And `alfred_workflow_keyword` being Script-Filter-exclusive is a clean way for a single `av` entry point to know which sub-command surface it was invoked through, should the design ever grow the direct-keyword layer the map defers.

The docs' own worked example of the values:

```
"alfred_preferences" = "/Users/Crayons/Dropbox/Alfred/Alfred.alfredpreferences";
"alfred_preferences_localhash" = adbd4f66bc3ae8493832af61a41ee609b20d8705;
"alfred_theme" = "alfred.theme.yosemite";
"alfred_workflow_bundleid" = "com.alfredapp.googlesuggest";
"alfred_workflow_uid" = "user.workflow.B0AC54EC-601C-479A-9428-01F9FD732959";
"alfred_debug" = 1;
```

Configuration variables and workflow environment variables arrive in the same environment, alongside these.

### Language options and how the input is passed

> "Select the language you'd like to run the script in, from the available interpreters. The listed runtimes are or have been included with macOS by default, but you're not limited to those entries: by setting the language to **External Script** and using the proper shebang or calling your runtime from a shell (such as `/bin/zsh`), any language can be used." [Docs, [Run Script Action](https://www.alfredapp.com/help/workflows/actions/run-script/)]

> "If you select External Script as the language, you can run a script saved to a file. If you don't specify an absolute path, Alfred will look relative to the workflow's folder. Ensure that you have the script's execute permission set." [Docs]

The docs do not enumerate the languages, and in `info.plist` the language is an undocumented integer under the `type` key. Correlating that integer with the script bodies across the corpus gives the following, which is **[Inferred]** and should be treated as a reading aid, not a spec:

| `type` | Language | Evidence |
| --- | --- | --- |
| 0 | `/bin/bash` | 171 uses; the default in Alfred's own bundled templates |
| 1 | `/usr/bin/php` | `require_once('workflows.php')`, `$wf = new Workflows()` |
| 2 | `/usr/bin/ruby` | `require 'cgi'`, `puts CGI::escape(...)` |
| 3 | `/usr/bin/python` (Python 2) | `#!/usr/local/bin/python`, `# encoding: utf-8` headers |
| 5 | `/bin/zsh` | `[[ -z "${...}" ]]` guards, `./things.js` invocations |
| 6 | `/usr/bin/osascript` (AppleScript) | `on run argv … end run` |
| 7 | `/usr/bin/osascript` (JavaScript / JXA) | `$.NSProcessInfo.processInfo.environment` |
| 8 | External Script | the only value where `scriptfile` is non-empty, e.g. `frankenstein.exp` |
| 9 | `/usr/bin/python3` | `from urllib.parse import quote` |
| 11 | `/bin/zsh --no-rcs` | used by the current 1Password Gallery workflow; matches the docs' stated default shell |

Values 4 and 10 were not observed; `4` is most likely Perl. **Do not hand-author this integer.** The safe routes are to build the object once in Alfred's editor and read the value back, or to use External Script (`type: 8`) with a `scriptfile`, which is both self-documenting and testable outside Alfred. For this project the latter is clearly right: it keeps the Alfred-invoked entry points as real files under `aardvark_jd/alfred/` where pytest can reach them, exactly as the map intends.

**`scriptargtype` decides how the query reaches the script,** and the docs recommend one of the two: "The input can be passed in as `argv` or you can replace `{query}` with the script. It's recommended that you use `argv`, as you don't have to worry about correctly escaping the inputted query." Correlating the integer against script bodies across the corpus is unambiguous: [Corpus, Inferred]

- `scriptargtype: 0` → `{query}` substitution. Of 114 such scripts, 92 contain `{query}` and **none** reference `argv`.
- `scriptargtype: 1` → `argv`. Of 138 such scripts, 64 reference `$1`/`argv`/`sys.argv` and only 13 contain `{query}`.

Take the documented advice and use `argv`. Doing so also makes the `escaping` integer irrelevant — it is a bitmask governing which characters Alfred escapes when substituting `{query}`, observed as `127` (all bits, Alfred's default in its own templates), `102`, `68`, `63` and `0` in the corpus. The individual bit meanings are **not documented and I did not verify them**; with `argv` you never need them.

**Concurrency.** The Run Script action's `concurrently` boolean selects between "run scripts sequentially (subsequent instances of your script will wait until the previous one finishes)" and "concurrently (a new instance of your script is started every time, even if the previous one hasn't finished)". The corpus default is `false` (185 of 195). [Docs, Corpus] For the map's backgrounded mutating commands, `false` is the safer setting — it stops two `add_*` runs racing on the index.

---

## What I could not verify

- **The Alfred forum.** `alfredforum.com` returns HTTP 403 to all automated fetches. No forum thread is cited here as evidence. Anything below that would normally be settled by an Andrew or vitor post is instead marked [Inferred] and backed by corpus evidence.
- **Working directory of an inline Run Script.** Very strong corpus evidence that it is the workflow folder, but no first-party sentence saying so for the inline case. Confirm with `pwd` in the prototype.
- **The language `type` integer enumeration.** Inferred from correlation; values 4 and 10 unobserved. Avoid depending on it by using External Script.
- **The `escaping` bitmask bit meanings.** Undocumented; avoided entirely by using `argv`.
- **`queuedelaycustom` units.** Undocumented; values `1` and `3` observed.
- **`alfredfiltersresultsmatchmode` integer mapping** beyond `0` being the default.
- **Any maximum item count or documented performance cliff for a Script Filter.** Nothing found on Alfred's site. This is the ticket-05 prototype's job.
- **Whether Alfred follows a symlinked workflow directory** (relevant to the map's "point `user.workflow.<UUID>` at the repo copy"). Not tested, because testing it would have meant writing into Alfred's preferences directory, which is outside this ticket's write scope. Ticket 02 should settle it.

## Sources

- [Workflows overview](https://www.alfredapp.com/help/workflows/)
- [Script Filter Input](https://www.alfredapp.com/help/workflows/inputs/script-filter/)
- [Script Filter JSON Format](https://www.alfredapp.com/help/workflows/inputs/script-filter/json/)
- [Run Script Action](https://www.alfredapp.com/help/workflows/actions/run-script/)
- [Script Environment Variables](https://www.alfredapp.com/help/workflows/script-environment-variables/)
- [Understanding the Scripting Environment](https://www.alfredapp.com/help/workflows/advanced/understanding-scripting-environment/)
- [Using Variables in Workflows](https://www.alfredapp.com/help/workflows/advanced/variables/)
- [Arg and Vars Utility](https://www.alfredapp.com/help/workflows/utilities/argument/)
- [JSON Utility](https://www.alfredapp.com/help/workflows/utilities/json/)
- [Workflow Configuration (for creators)](https://www.alfredapp.com/help/workflows/workflow-configuration/)
- [Configuring an Installed Workflow (for users)](https://www.alfredapp.com/help/workflows/user-configuration/)
- [Exporting and Sharing Workflows](https://www.alfredapp.com/help/workflows/advanced/sharing-workflows/)
- [Using Alternative Actions](https://www.alfredapp.com/help/workflows/advanced/alternative-actions/)
- [Workflow Object Inbound Configuration](https://www.alfredapp.com/help/workflows/inbound-configuration/)
- [Using the Workflow Debugger](https://www.alfredapp.com/help/workflows/advanced/debugger/)

Alfred-bundled templates read from `/Applications/Alfred 5.app/Contents/Frameworks/Alfred Framework.framework/Versions/A/Resources/`: `Advanced Script Filters.alfredworkflow`, `Script Filter to Script to Notification.alfredworkflow`, `Keywords.alfredworkflow`, `Chaining Inputs.alfredworkflow`.

Installed workflows cited from `/Users/Dave/Dropbox/Apps/alfred/Alfred.alfredpreferences/workflows/`: `user.workflow.02683378-6858-49C5-BB9E-042DC6270563` (1Password, per-mod variables and `match`), `user.workflow.77DAF526-580B-4D2A-B78D-CF74CB935C21` (Emoji search, `mods` and `prefs.plist`), `user.workflow.AD3EAF0C-3313-431A-96F3-522BD1F6485B` (Shortcuts, JXA Script Filter), `Google Suggest`, `Kill Process`, `markdust`, `picaxe`.

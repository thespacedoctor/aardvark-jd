# Quickstart

## Initialising a system

Create a new PARA + Johnny Decimal system by giving it a name and a parent folder to live in:

```bash
aardvark init "My Life" ~/
```

This creates the full folder tree (`00_INDEX`, `01_INBOX`, `02_PROJECTS`, `03_AREAS`, `04_RESOURCES`, `09_ARCHIVE`) under `~/My Life`, an `aardvark.db` SQLite index inside `00_INDEX`, and records the system as active in your user settings file at `~/.config/aardvark/aardvark.yaml`. Every non-ID folder is suffixed with an emoji; the static system folders carry a fixed emoji each.

## Shell completion

Enable tab completion for `aardvark`/`av`, its commands, and Johnny Decimal references by evaluating the generated script from your shell's startup file:

```bash
eval "$(aardvark completion zsh)"    # ~/.zshrc
eval "$(aardvark completion bash)"   # ~/.bashrc
```

With this loaded, `aardvark add_category A<TAB>` lists existing areas, `aardvark archive <TAB>` lists archivable references, and `aardvark <TAB>` lists the commands themselves. `aardvark --help-all` also lists every command, including the setup/connection commands that the default `--help` screen hides to keep the everyday ones easy to find.

## Folder emoji

Areas, categories and projects get an emoji suggested from their title and description. Suggestions come from the Claude API, so make credentials available the way the [Anthropic SDK expects](https://platform.claude.com/docs/en/api/overview) - typically an `ANTHROPIC_API_KEY` environment variable. Without them aardvark quietly falls back to an offline keyword search, which is thinner: it has no entry for "doctor" or "finance", so those land on the generic 📁.

In an interactive session the suggestion is shown for you to accept or replace:

```bash
aardvark add_area A "Doctors" "GP and specialists"
# Suggested emoji for 'Doctors': 🩺
# Press Enter to accept, or type a replacement emoji:
```

Pass `--emoji` to skip both the API call and the prompt:

```bash
aardvark add_area A "Taxes" "Self assessment and receipts" --emoji 🧾
```

To stay offline permanently, set `use_llm: false` under `emoji:` in your settings file.

### Changing an emoji later

`set_emoji` retargets something that already exists, renaming the folder and repointing the index at it in one step:

```bash
aardvark set_emoji A10-19 🏥        # an area
aardvark set_emoji A11 🩺           # a category
aardvark set_emoji P11 🌐           # a project category
aardvark set_emoji root.areas 🧭    # a static system folder
```

Renaming a folder moves everything nested inside it, so the paths recorded for those descendants are rewritten at the same time - nothing is left pointing at the old location.

If you created your system before v0.2.0, its static system folders were named by the old keyword search and most will be sitting on 📁. Reset them all at once:

```bash
aardvark repair_emoji
```

## Growing the Johnny Decimal index

`02_PROJECTS`, `03_AREAS` and `04_RESOURCES` are all Johnny Decimal systems, named by their domain letter: `P`, `A` and `R`. Every reference you pass on the command-line carries that letter, so nothing has to say which system it means - `A11` is a category under Areas, `P11` the same number under Projects.

Add an area, then a category within it, then IDs within that category - each level auto-numbers itself:

```bash
aardvark add_area A "Health" "Everything related to my physical and mental health"
aardvark add_category A10-19 "Doctors" "Doctors, specialists and appointments"
aardvark add_id A11 "Cardiologist" "Dr Smith, cardiology follow-ups"
```

Area and category folders are named `<X><AC>_<title><emoji>` - domain letter, lowercase, spaces
turned into underscores, e.g. `A10_19_health🏥` and `A11_doctors🩺`. ID folders drop the emoji:
`A11.10_cardiologist`.

Every area and category also gets reserved scaffolding alongside it: an area gets its own
`<X><D0>_system⚙️` folder (occupying the reserved `X0` category slot), and a category gets ten
reserved system IDs, `.00` through `.09` (`A11.00_index🗂️`, `A11.01_inbox📥`, ... `A11.09_archive🗄️`)
- the same names/emoji as the domain-level `00_09_system` folder's own subfolders. Because `.00`-`.09`
are reserved, the first ID you create in a category is `.10`, not `.01`.

If you created your system before this scaffolding existed, or before folder names carried the
domain letter, bring it up to date in one pass:

```bash
aardvark repair_emoji
```

This renames any area/category/ID folder whose on-disk name doesn't match its stored title/emoji,
and backfills any missing reserved scaffolding - safe to run repeatedly.

## Starting a new project

A project is a Johnny Decimal ID in the `projects` domain, so it needs an existing project category to live in - add an area and category first, the same way as for `areas`/`resources`:

```bash
aardvark add_area P "Launches" "Things I'm shipping"
aardvark add_category P10-19 "Website" "The site rebuild"
aardvark add_project P11 "Relaunch"
```

Lists any zip templates found in category `P11`'s own `P11.04_templates/` folder plus "New blank project" (`README.md`, `input/`, `output/`) as the default, and creates the chosen project inside category `P11` as `P11.10_Relaunch`, with no emoji - matching every other Johnny Decimal ID. Templates are scoped to their own category - drop a zip into `P11.04_templates/` and it's only offered for projects created under `P11`. Pass `-t <templateName>` to skip the picker (`aardvark add_project P11 "Relaunch" -t website`), or `-t blank` to force the blank scaffold non-interactively.

## Searching the index

A plain term does a keyword search:

```bash
aardvark search cardio
```

Run `search` with no argument to print the whole index as a tree, reserved `.00`-`.09` system IDs excluded:

```bash
aardvark search
```

```
03 AREAS🧭
└── A10-19 health🏥
    └── A11 doctors🩺
        └── A11.10 cardiologist
```

Pass a Johnny Decimal reference instead of a term to jump straight to that branch - `A` or `A10-19` prints the subtree
for that area, `A11` the subtree for that category, and `A11.10` the single matching entry, the same line `search
cardio` would have printed for it. A reference-shaped term that doesn't actually resolve falls back to an ordinary
keyword search, so `search A11` never errors just because you meant the letter "A" followed by "11".

## Opening a folder interactively

`open` with no path launches an arrow-key picker: use the up/down arrows to move, Enter to descend into a domain,
area or category (or open the highlighted level directly), `q`/Esc to cancel. It starts pre-selected on wherever the
current directory resolves to, so if you're already inside a mirrored folder, `open` then Enter-Enter reproduces
today's "open the current directory" behaviour in two keystrokes:

```bash
cd ~/aardvark/03_AREAS/A11_doctors/A11.10_cardiologist
aardvark open
```

Passing a path explicitly (`aardvark open <path>`) skips the picker entirely, as before.

## Connecting to craft.do

Aardvark can mirror its folder tree into a [craft.do](https://craft.do) space, so the same PARA + Johnny Decimal index is browsable there too. Craft spaces can't be created via API, so the mirror lives inside your existing space as top-level folders rather than as separate spaces: `01_INBOX`, `02_PROJECTS`, `03_AREAS`, `04_RESOURCES` and `09_ARCHIVE` become top-level Craft folders, and areas, categories and IDs all nest as folders below them - an ID's folder carries a single `00 Index` document inside it. Every folder holds a `00 Index` document listing the level directly below it, one level deep, with each child's code and title linking straight to its Craft folder or document.

Create an API Connection from inside your Craft space (Connections tab in the sidebar) and copy both values it shows you - the connection's unique API URL and its token, then connect them:

```bash
aardvark connect_craft <your-api-url> <your-api-token>
```

The API URL is unique to that one connection (there's no shared global endpoint), so it has to come from Craft itself rather than being something aardvark can guess. This saves both values to your settings file and runs the first full mirror. From then on, `add_area`, `add_category`, `add_id`, `set_emoji` and `add_project` all push their changes to Craft automatically - if a push fails, the command still succeeds locally and prints a warning rather than aborting, since the filesystem and SQLite index are always the source of truth.

To backfill an existing system, or repair drift after a failed auto-push:

```bash
aardvark craft_sync
```

Inbox and Archive are mirrored as empty top-level folders only - they aren't tracked as structured entries in the SQLite index today, so there's nothing to list inside them yet.

## Connecting to Todoist

Aardvark can also mirror into Todoist, for the actionable side reference material in Craft doesn't cover. Since a personal Todoist plan has no Workspaces, everything lives under one top-level project named after your aardvark system, with `03 AREAS` and `02 PROJECTS` nested inside it: `03 AREAS` mirrors areas and their categories, two deep, while `02 PROJECTS` mirrors every project ID as a flat list directly underneath it, skipping the project areas/categories above it. `01 INBOX`, `04 RESOURCES`, `09 ARCHIVE` and every `00-09` system folder are never mirrored.

Grab a personal API token from Todoist (Settings -> Integrations -> Developer), then connect it:

```bash
aardvark connect_todoist <your-api-token>
```

This validates the token, saves it to your settings file, and runs the first full mirror. From then on, every mutating command pushes to Todoist automatically, always before it pushes to Craft, so each mirrored project's Craft link is already in place by the time Craft's own link row is written. To backfill or repair drift on demand:

```bash
aardvark todoist_sync
```

Each mirrored project's description carries a Finder/Dropbox/Craft link row back to its sibling objects, matching the Finder/Dropbox/Todoist row Craft documents carry.

## Connecting to Google Drive

Aardvark can also mirror its folder structure - folders only, no documents - into Google Drive. Create an OAuth
client of type **Desktop app** in a Google Cloud project (APIs & Services -> Credentials), then connect it:

```bash
aardvark connect_gdrive <your-client-id> <your-client-secret>
```

This opens a browser for you to sign in and grant access (the full `drive` scope, so aardvark can also see and adopt
folders you've already created by hand - expect a one-off "unverified app" warning for a personal OAuth client
unless you've verified it with Google), captures the authorisation code over a local loopback listener, stores a
refresh token in your settings file, and runs the first full mirror.

At your Drive root, aardvark creates one folder named after your aardvark system, and inside it mirrors
`01_INBOX`, `02_PROJECTS`, `03_AREAS`, `04_RESOURCES` and `09_ARCHIVE`, with areas/categories/IDs nested under each
domain exactly as they are on disk - `00_INDEX` is deliberately excluded, since it holds `aardvark.db`, which has no
business leaving your machine. Every system folder only carries its three commonly used reserved subfolders -
`P01_inbox📥`, `P04_templates📐`, `P09_archive🗄️` (rendered per domain) - the other reserved slots aren't
mirrored. No documents are written, only folders.

To backfill or repair drift on demand:

```bash
aardvark gdrive_sync
```

If a folder already exists at the right place and name in Drive, aardvark adopts its existing folder ID instead of
creating a duplicate - this also means a corrupted or reset local database can be repaired by re-running the sync
rather than by re-creating everything from scratch.

## Opening a folder in Craft, Todoist and Google Drive

Once connected, `open` resolves a filesystem path back to whichever of the Craft folder/document, Todoist project and
Google Drive folder mirror it, and opens every one that's synced:

```bash
cd ~/aardvark/03_AREAS/A11_doctors/A11.10_cardiologist
aardvark open
```

It defaults to the current directory, or takes a path directly: `aardvark open <path>`. Every command is also available under the shorter `av` alias - `av open` does the same thing.

## Adding Dropbox links

If your aardvark system root sits inside a Dropbox-synced folder, every document `craft_sync` writes to (and every project `todoist_sync` writes to) also gets a Dropbox share link alongside its Finder link. Create an app in the [Dropbox App Console](https://www.dropbox.com/developers/apps) (with the `sharing.write`, `sharing.read` and `files.metadata.read` scopes), then connect it:

```bash
aardvark connect_dropbox <your-app-key> <your-app-secret>
```

This opens a browser to authorise the app, prompts you to paste back the code Dropbox shows you, and stores a long-lived refresh token in your settings file - Dropbox access tokens themselves only last 4 hours, so aardvark re-exchanges the refresh token on every sync rather than needing you to reconnect. `craft_sync` mints each folder's share link once and caches it, so re-running doesn't re-request one that already exists.

## Archiving an area, category or project

`archive <ref>` retires an area, category or project ID - and everything nested inside it - freeing its Johnny
Decimal number for reuse:

```bash
aardvark archive A11.10
```

This moves the folder on disk to the nearest `09_archive` folder above it (an ID moves into its own category's
`AC.09_archive🗄️`; a category into its area's `A0.09_archive🗄️`; an area into the domain's root
`09_ARCHIVE🗄️`), does the same move in Google Drive if connected, flags the entry archived in the database -
removing it from `search` and freeing its number for the next `add_area`/`add_category`/`add_id`/`add_project`
- and archives (not deletes) its mirrored Todoist project. The archived folder name carries a date suffix so that,
once a number is reused, the old and new occupants never collide inside the same archive folder.

Craft's API can neither move nor delete a folder or document, so archiving there is necessarily best-effort: aardvark
drops a warning block into the folder's index document and prints a note that you'll need to delete the Craft folder
by hand. There is no `unarchive` in this version - `archive` moves real folders and asks for confirmation before it
does (skip the prompt with `-y`/`--yes`).

## Command-Line Usage

:::{include} usage.md
:::

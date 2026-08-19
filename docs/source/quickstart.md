# Quickstart

## Initialising a system

Create a new PARA + Johnny Decimal system by giving it a name and a parent folder to live in:

```bash
aardvark init "My Life" ~/
```

This creates the full folder tree (`00_INDEX`, `01_INBOX`, `02_PROJECTS`, `03_AREAS`, `04_RESOURCES`, `09_ARCHIVE`) under `~/My Life`, an `aardvark.db` SQLite index inside `00_INDEX`, and records the system as active in your user settings file at `~/.config/aardvark/aardvark.yaml`. Every non-ID folder is suffixed with an emoji; the static system folders carry a fixed emoji each.

## Folder emoji

Areas, categories and projects get an emoji suggested from their title and description. Suggestions come from the Claude API, so make credentials available the way the [Anthropic SDK expects](https://platform.claude.com/docs/en/api/overview) - typically an `ANTHROPIC_API_KEY` environment variable. Without them aardvark quietly falls back to an offline keyword search, which is thinner: it has no entry for "doctor" or "finance", so those land on the generic 📁.

In an interactive session the suggestion is shown for you to accept or replace:

```bash
aardvark add_area areas "Doctors" "GP and specialists"
# Suggested emoji for 'Doctors': 🩺
# Press Enter to accept, or type a replacement emoji:
```

Pass `--emoji` to skip both the API call and the prompt:

```bash
aardvark add_area areas "Taxes" "Self assessment and receipts" --emoji 🧾
```

To stay offline permanently, set `use_llm: false` under `emoji:` in your settings file.

### Changing an emoji later

`set_emoji` retargets something that already exists, renaming the folder and repointing the index at it in one step:

```bash
aardvark set_emoji areas 10 🏥            # an area
aardvark set_emoji areas 11 🩺            # a category
aardvark set_emoji projects "Website Rebuild" 🌐
aardvark set_emoji system root.areas 🧭   # a static system folder
```

Renaming a folder moves everything nested inside it, so the paths recorded for those descendants are rewritten at the same time - nothing is left pointing at the old location.

If you created your system before v0.2.0, its static system folders were named by the old keyword search and most will be sitting on 📁. Reset them all at once:

```bash
aardvark repair_emoji
```

## Growing the Johnny Decimal index

Only `03_AREAS` and `04_RESOURCES` are Johnny Decimal systems. Add an area, then a category within it, then IDs within that category - each level auto-numbers itself:

```bash
aardvark add_area areas "Health" "Everything related to my physical and mental health"
aardvark add_category areas 10 "Doctors" "Doctors, specialists and appointments"
aardvark add_id areas 11 "Cardiologist" "Dr Smith, cardiology follow-ups"
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

```bash
aardvark new_project
```

Lists any zip templates found in `02_PROJECTS/00_09_system/04_templates/` plus a blank option (`README.md`, `input/`, `output/`), and creates the chosen project folder under `02_PROJECTS/`.

## Searching the index

```bash
aardvark search cardio
```

## Connecting to craft.do

Aardvark can mirror its folder tree into a [craft.do](https://craft.do) space, so the same PARA + Johnny Decimal index is browsable there too. Craft spaces can't be created via API, so the mirror lives inside your existing space as top-level folders rather than as separate spaces: `01_INBOX`, `02_PROJECTS`, `03_AREAS`, `04_RESOURCES` and `09_ARCHIVE` become top-level Craft folders, areas and categories nest as folders below them, and IDs become Craft documents named with their `X.AC.ID` code. Every folder holds a `00 Index` document listing the level directly below it, one level deep, with each child's code and title linking straight to its Craft folder or document.

Create an API Connection from inside your Craft space (Connections tab in the sidebar) and copy both values it shows you - the connection's unique API URL and its token, then connect them:

```bash
aardvark connect_craft <your-api-url> <your-api-token>
```

The API URL is unique to that one connection (there's no shared global endpoint), so it has to come from Craft itself rather than being something aardvark can guess. This saves both values to your settings file and runs the first full mirror. From then on, `add_area`, `add_category`, `add_id`, `set_emoji` and `new_project` all push their changes to Craft automatically - if a push fails, the command still succeeds locally and prints a warning rather than aborting, since the filesystem and SQLite index are always the source of truth.

To backfill an existing system, or repair drift after a failed auto-push:

```bash
aardvark craft_sync
```

Inbox and Archive are mirrored as empty top-level folders only - they aren't tracked as structured entries in the SQLite index today, so there's nothing to list inside them yet. Projects aren't Johnny-Decimal coded, so each mirrors as a flat document under the Projects folder rather than a nested folder tree.

## Command-Line Usage

:::{include} usage.md
:::

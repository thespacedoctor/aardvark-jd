# Quickstart

## Initialising a system

Create a new PARA + Johnny Decimal system by giving it a name and a parent folder to live in:

```bash
aardvark init "My Life" ~/
```

This creates the full folder tree (`00_INDEX`, `01_INBOX`, `02_P.ROJECTS`, `03_A.REAS`, `04_R.ESOURCES`, `09_ARCHIVE`) under `~/My Life`, an `aardvark.db` SQLite index inside `00_INDEX`, and records the system as active in your user settings file at `~/.config/aardvark/aardvark.yaml`. Every non-ID folder is suffixed with an emoji; the static system folders carry a fixed emoji each.

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

Only `03_A.REAS` and `04_R.ESOURCES` are Johnny Decimal systems. Add an area, then a category within it, then IDs within that category - each level auto-numbers itself:

```bash
aardvark add_area areas "Health" "Everything related to my physical and mental health"
aardvark add_category areas 10 "Doctors" "Doctors, specialists and appointments"
aardvark add_id areas 11 "Cardiologist" "Dr Smith, cardiology follow-ups"
```

## Starting a new project

```bash
aardvark new_project
```

Lists any zip templates found in `02_P.ROJECTS/00_09_system/04_templates/` plus a blank option (`README.md`, `input/`, `output/`), and creates the chosen project folder under `02_P.ROJECTS/`.

## Searching the index

```bash
aardvark search cardio
```

## Command-Line Usage

:::{include} usage.md
:::

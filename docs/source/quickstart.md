# Quickstart

## Initialising a system

Create a new PARA + Johnny Decimal system by giving it a name and a parent folder to live in:

```bash
aardvark init "My Life" ~/
```

This creates the full folder tree (`00_index`, `01_inbox`, `P.ROJECTS`, `A.REAS`, `R.ESOURCES`, `09_archive`) under `~/My Life`, an `aardvark.db` SQLite index inside `00_index`, and records the system as active in your user settings file at `~/.config/aardvark/aardvark.yaml`. Non-ID folders are automatically suffixed with an emoji picked from their title/description.

## Growing the Johnny Decimal index

Only `A.REAS` and `R.ESOURCES` are Johnny Decimal systems. Add an area, then a category within it, then IDs within that category - each level auto-numbers itself:

```bash
aardvark add_area areas "Health" "Everything related to my physical and mental health"
aardvark add_category areas 10 "Doctors" "Doctors, specialists and appointments"
aardvark add_id areas 11 "Cardiologist" "Dr Smith, cardiology follow-ups"
```

## Starting a new project

```bash
aardvark new_project
```

Lists any zip templates found in `P.ROJECTS/00_09_system/04_templates/` plus a blank option (`README.md`, `input/`, `output/`), and creates the chosen project folder under `P.ROJECTS/`.

## Searching the index

```bash
aardvark search cardio
```

## Command-Line Usage

:::{include} usage.md
:::

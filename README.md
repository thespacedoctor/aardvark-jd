# aardvark-jd

<!-- INFO BADGES -->  

[![](https://img.shields.io/pypi/pyversions/aardvark-jd)](https://pypi.org/project/aardvark-jd/)
[![](https://img.shields.io/pypi/v/aardvark-jd)](https://pypi.org/project/aardvark-jd/)
[![](https://img.shields.io/conda/vn/conda-forge/aardvark-jd)](https://anaconda.org/conda-forge/aardvark-jd)
[![](https://pepy.tech/badge/aardvark-jd)](https://pepy.tech/project/aardvark-jd)
[![](https://img.shields.io/github/license/thespacedoctor/aardvark-jd)](https://github.com/thespacedoctor/aardvark-jd)

<!-- STATUS BADGES -->  

[![](https://soxs-eso-data.org/ci/buildStatus/icon?job=aardvark-jd%2Fmain&subject=build%20main)](https://soxs-eso-data.org/ci/blue/organizations/jenkins/aardvark-jd/activity?branch=main)
[![](https://soxs-eso-data.org/ci/buildStatus/icon?job=aardvark-jd%2Fdevelop&subject=build%20dev)](https://soxs-eso-data.org/ci/blue/organizations/jenkins/aardvark-jd/activity?branch=develop)
[![](https://cdn.jsdelivr.net/gh/thespacedoctor/aardvark-jd@main/coverage.svg)](https://raw.githack.com/thespacedoctor/aardvark-jd/main/htmlcov/index.html)
[![](https://readthedocs.org/projects/aardvark-jd/badge/?version=main)](https://aardvark-jd.readthedocs.io/en/main/)
[![](https://img.shields.io/github/issues/thespacedoctor/aardvark-jd/type:%20bug?label=bug%20issues)](https://github.com/thespacedoctor/aardvark-jd/issues?q=is%3Aissue+is%3Aopen+label%3A%22type%3A+bug%22+)

*A PARA + Johnny Decimal filing and indexing system, backed by SQLite*. Installs as the `aardvark-jd` package; the command-line tool itself is called `aardvark`.

Documentation for aardvark is hosted by [Read the Docs](https://aardvark-jd.readthedocs.io/en/main/) ([development version](https://aardvark-jd.readthedocs.io/en/develop/) and [main version](https://aardvark-jd.readthedocs.io/en/main/)). The code lives on [github](https://github.com/thespacedoctor/aardvark-jd). Please report any issues you find [here](https://github.com/thespacedoctor/aardvark-jd/issues). If you want to contribute, [pull requests](https://github.com/thespacedoctor/aardvark-jd/pulls) are welcomed!


## Features

* `init` a PARA + Johnny Decimal root folder structure, indexed in a local SQLite database
* `add_area` / `add_category` / `add_id` to grow the Johnny Decimal index under Areas or Resources, with auto-numbering
* `add_project` to spin up a new (optionally templated) project folder under Projects
* `search` the index by keyword or phrase, or with no argument to print the whole index as a tree; pass a Johnny Decimal reference (`A`, `A10-19`, `A11`, `A11.10`) to browse or jump straight to that branch
* `fd` to find in the index by keyword or phrase, or with no argument to print the whole index as a tree; pass a Johnny Decimal reference (`A`, `A10-19`, `A11`, `A11.10`) to browse or jump straight to that branch
* `cd <target>` to change directory straight into a domain, area, category or ID's folder - tab-completes the same references as `fd` (needs `av shell_init`, see Shell completion below)
* `archive <ref>` to retire an area, category or project ID - the folder moves to its nearest `09_archive` folder on disk (and in Google Drive, best-effort in Craft/Todoist), the entry is flagged archived in the database, and its Johnny Decimal number becomes free for reuse
* `open` with no argument launches an arrow-key picker through Areas/Resources/Projects down to an ID, seeded from the current directory when it resolves to one
* shell tab completion for commands, references and flag values, and (via `aardvark shell_init zsh|bash`) a working `cd` - see Shell completion below
* every non-ID folder is suffixed with a relevant emoji, suggested offline from the title and confirmable at the prompt (or set outright with `--emoji`)
* `set_emoji` / `repair_emoji` to change an emoji after the fact, moving the folder and repointing the index together
* `connect_craft` / `craft_sync` to mirror the whole index into a craft.do space, with a Finder link (and, once `connect_dropbox` is set up, a Dropbox share link) on every synced document
* `connect_gdrive` / `gdrive_sync` to mirror the folder structure into Google Drive as well, linked alongside Craft and Todoist
* `open [<path>]` to jump straight from a filesystem path back to its mirrored Craft folder/document/Todoist project/Drive folder (defaults to the current directory)
* every command is also available under the shorter `av` alias, e.g. `av open`, `av fd cardio`
* `aardvark --help-all` lists every command, including the less commonly used setup/connection commands hidden from the default `--help` screen



## Installation

The easiest way to install aardvark is to use `conda`:

``` bash
conda create -n aardvark-jd python=3.14 pip aardvark-jd -c conda-forge
conda activate aardvark-jd
```

To upgrade to the latest version of aardvark use the command:

``` bash
conda upgrade aardvark-jd -c conda-forge
```

It is also possible to install via pip if required:

``` bash
pip install aardvark-jd
```

Or you can clone the [github repo](https://github.com/thespacedoctor/aardvark-jd) and install from a local version of the code:

``` bash
git clone git@github.com:thespacedoctor/aardvark-jd.git
cd aardvark-jd
python setup.py install
```

To check installation was successful run `aardvark -v`. This should return the version number of the install.

## Initialising a system

Give your system a name and a parent folder to live in:

```bash
aardvark init "My Life" ~/
```

This builds the full PARA + Johnny Decimal folder tree, creates the `aardvark.db` SQLite index, and records the system as active in your user settings file at `~/.config/aardvark/aardvark.yaml` (created automatically on first run, populated with aardvark's default settings).

## Shell completion

Add tab completion for commands, Johnny Decimal references and flag values, plus a working `aardvark cd`/`av cd`, by evaluating the generated script in your shell's startup file:

```bash
echo 'eval "$(aardvark shell_init zsh)"' >> ~/.zshrc    # zsh
echo 'eval "$(aardvark shell_init bash)"' >> ~/.bashrc  # bash
```

Both `aardvark` and `av` complete once this is loaded, and `aardvark cd <target>`/`av cd <target>` moves the shell straight into that area's, category's or ID's folder. A plain subprocess cannot change its parent shell's working directory - `shell_init` wraps `aardvark`/`av` in a shell function that does the `cd` for you, which is why it, not `aardvark completion`, is the recommended install line. `aardvark completion zsh|bash` still exists on its own for the `~/.zsh/completions/_aardvark` fpath-cache route, where it does not include the `cd` wrapper.

## The Alfred workflow

On macOS, aardvark ships an [Alfred 5](https://www.alfredapp.com) workflow that drives the same index from the keyboard. Install it with:

```bash
aardvark install_alfred
```

That does two things: it records where this Mac's `aardvark` command lives, and it links the packaged workflow into Alfred. Alfred runs scripts with a fixed six-entry `PATH` that carries no conda, venv, pipx or uv binary, so the recorded path is how the workflow finds aardvark at all.

Type `av` in Alfred to search the whole index at once - by Johnny Decimal reference, title, folder name or description. On the result you want:

| Key | What it does |
| --- | --- |
| ↩ | Opens every mirror the entity is synced to, the same as `aardvark open` |
| ⌘ | Reveals the folder in Finder |
| ⌥ | Opens a terminal tab at the folder |
| ⌃ | Shows Craft, Todoist, Google Drive and Dropbox as four rows, offering to sync any that is not yet mirrored |

Two settings are available under Alfred's **Configure Workflow…**: `AARDVARK_TERMINAL_APP`, the app the ⌥ handoff opens (empty means iTerm when it is installed, and Terminal otherwise), and `AARDVARK_BINARY`, an explicit path to the `aardvark` command that overrides the recorded one.

Remove the workflow with:

```bash
aardvark install_alfred --uninstall
```

Removing it through Alfred's own interface is safe - Alfred unlinks the workflow rather than deleting through the link, so nothing inside the package is touched. `--uninstall` is the documented route only because it also removes the recorded path.

**On a fresh Mac, the order is:** install the package, run `aardvark install_alfred`, then point the CLI at your tree (`aardvark init`, or an existing `~/.config/aardvark/aardvark.yaml`). `install_alfred` deliberately does not need a system to exist yet, so it can run first.

You are now ready to start using aardvark - see the [quickstart](https://aardvark-jd.readthedocs.io/en/main/quickstart.html) for the full command reference.

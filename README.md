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
* `search` the index by keyword or phrase
* every non-ID folder is suffixed with a relevant emoji, suggested by Claude and confirmable at the prompt (or set outright with `--emoji`)
* `set_emoji` / `repair_emoji` to change an emoji after the fact, moving the folder and repointing the index together
* `connect_craft` / `craft_sync` to mirror the whole index into a craft.do space, with a Finder link (and, once `connect_dropbox` is set up, a Dropbox share link) on every synced document
* `open [<path>]` to jump straight from a filesystem path back to its mirrored Craft folder/document (defaults to the current directory)
* every command is also available under the shorter `av` alias, e.g. `av open`, `av search cardio`



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

You are now ready to start using aardvark - see the [quickstart](https://aardvark-jd.readthedocs.io/en/main/quickstart.html) for the full command reference.

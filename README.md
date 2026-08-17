# aardvark

<!-- INFO BADGES -->  

[![](https://img.shields.io/pypi/pyversions/aardvark)](https://pypi.org/project/aardvark/)
[![](https://img.shields.io/pypi/v/aardvark)](https://pypi.org/project/aardvark/)
[![](https://img.shields.io/conda/vn/conda-forge/aardvark)](https://anaconda.org/conda-forge/aardvark)
[![](https://pepy.tech/badge/aardvark)](https://pepy.tech/project/aardvark)
[![](https://img.shields.io/github/license/thespacedoctor/aardvark)](https://github.com/thespacedoctor/aardvark)

<!-- STATUS BADGES -->  

[![](https://soxs-eso-data.org/ci/buildStatus/icon?job=aardvark%2Fmain&subject=build%20main)](https://soxs-eso-data.org/ci/blue/organizations/jenkins/aardvark/activity?branch=main)
[![](https://soxs-eso-data.org/ci/buildStatus/icon?job=aardvark%2Fdevelop&subject=build%20dev)](https://soxs-eso-data.org/ci/blue/organizations/jenkins/aardvark/activity?branch=develop)
[![](https://cdn.jsdelivr.net/gh/thespacedoctor/aardvark@main/coverage.svg)](https://raw.githack.com/thespacedoctor/aardvark/main/htmlcov/index.html)
[![](https://readthedocs.org/projects/aardvark/badge/?version=main)](https://aardvark.readthedocs.io/en/main/)
[![](https://img.shields.io/github/issues/thespacedoctor/aardvark/type:%20bug?label=bug%20issues)](https://github.com/thespacedoctor/aardvark/issues?q=is%3Aissue+is%3Aopen+label%3A%22type%3A+bug%22+)

*A PARA + Johnny Decimal filing and indexing system, backed by SQLite*.

Documentation for aardvark is hosted by [Read the Docs](https://aardvark.readthedocs.io/en/main/) ([development version](https://aardvark.readthedocs.io/en/develop/) and [main version](https://aardvark.readthedocs.io/en/main/)). The code lives on [github](https://github.com/thespacedoctor/aardvark). Please report any issues you find [here](https://github.com/thespacedoctor/aardvark/issues). If you want to contribute, [pull requests](https://github.com/thespacedoctor/aardvark/pulls) are welcomed!


## Features

* `init` a PARA + Johnny Decimal root folder structure, indexed in a local SQLite database
* `add-area` / `add-category` / `add-id` to grow the Johnny Decimal index under Areas or Resources, with auto-numbering
* `new-project` to spin up a new (optionally templated) project folder under Projects
* `search` the index by keyword or phrase
* every non-ID folder is automatically suffixed with a relevant emoji



## Installation

The easiest way to install aardvark is to use `conda`:

``` bash
conda create -n aardvark python=3.14 pip aardvark -c conda-forge
conda activate aardvark
```

To upgrade to the latest version of aardvark use the command:

``` bash
conda upgrade aardvark -c conda-forge
```

It is also possible to install via pip if required:

``` bash
pip install aardvark
```

Or you can clone the [github repo](https://github.com/thespacedoctor/aardvark) and install from a local version of the code:

``` bash
git clone git@github.com:thespacedoctor/aardvark.git
cd aardvark
python setup.py install
```

To check installation was successful run `aardvark -v`. This should return the version number of the install.

## Initialising a system

Give your system a name and a parent folder to live in:

```bash
aardvark init "My Life" ~/
```

This builds the full PARA + Johnny Decimal folder tree, creates the `aardvark.db` SQLite index, and records the system as active in your user settings file at `~/.config/aardvark/aardvark.yaml` (created automatically on first run, populated with aardvark's default settings).

You are now ready to start using aardvark - see the [quickstart](https://aardvark.readthedocs.io/en/main/quickstart.html) for the full command reference.

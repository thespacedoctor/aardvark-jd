#!/usr/bin/env python
# encoding: utf-8
"""
*Read/write helpers for the aardvark user settings YAML file*

Author
: David Young
"""

import yaml


def read_settings(pathToSettings):
    """
    *read the aardvark settings YAML file into a dict*

    **Key Arguments:**

    - ``pathToSettings`` -- path to the settings YAML file

    **Return:**

    - ``settings`` -- the settings dictionary
    """
    with open(pathToSettings, "r") as stream:
        return yaml.safe_load(stream)


def write_settings(pathToSettings, settings):
    """
    *write a dict back out to the aardvark settings YAML file*

    **Key Arguments:**

    - ``pathToSettings`` -- path to the settings YAML file
    - ``settings`` -- the settings dictionary to write
    """
    with open(pathToSettings, "w") as stream:
        yaml.safe_dump(settings, stream, default_flow_style=False, sort_keys=False)

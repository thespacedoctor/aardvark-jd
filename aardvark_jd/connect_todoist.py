#!/usr/bin/env python
# encoding: utf-8
"""
*Validate a Todoist personal API token and persist it to the user settings*

Simpler than `connect_dropbox.py` - Todoist's personal API token needs no
OAuth exchange, just a single validating request against the account it
authenticates.

Author
: David Young
"""

from aardvark_jd import settings_writer
from aardvark_jd.todoist_client import TodoistApiError, TodoistClient


class connect_todoist(object):
    """
    *validate a Todoist personal API token and persist it to the user settings*

    **Key Arguments:**

    - ``log`` -- logger
    - ``apiToken`` -- a personal API token, from Todoist's Integrations -> Developer settings
    - ``pathToSettingsFile`` -- path to the aardvark user settings YAML file

    **Usage:**

    ```python
    from aardvark_jd.connect_todoist import connect_todoist
    connect_todoist(log=log, apiToken="...", pathToSettingsFile="~/.config/aardvark/aardvark.yaml").get()
    ```
    """

    def __init__(self, log, apiToken, pathToSettingsFile):
        self.log = log
        self.apiToken = apiToken
        self.pathToSettingsFile = pathToSettingsFile

    def get(self):
        """
        *validate the token against the Todoist API and persist it*

        **Return:**

        - ``apiToken`` -- the validated token, unchanged
        """
        self.log.debug("starting the ``get`` method")

        try:
            TodoistClient(apiToken=self.apiToken).list_projects()
        except TodoistApiError as error:
            raise ValueError(f"todoist token validation failed: {error}")

        self._update_settings()

        self.log.debug("completed the ``get`` method")
        return self.apiToken

    def _update_settings(self):
        """
        *persist the validated token to the user settings YAML file*
        """
        settings = settings_writer.read_settings(self.pathToSettingsFile)
        settings.setdefault("todoist", {})
        settings["todoist"]["enabled"] = True
        settings["todoist"]["api_token"] = self.apiToken
        settings_writer.write_settings(self.pathToSettingsFile, settings)

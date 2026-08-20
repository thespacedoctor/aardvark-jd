import logging

import pytest
import yaml

from aardvark_jd import connect_todoist as connect_todoist_module
from aardvark_jd import settings_writer
from aardvark_jd.connect_todoist import connect_todoist
from aardvark_jd.todoist_client import TodoistApiError

log = logging.getLogger("test_connect_todoist")
log.addHandler(logging.NullHandler())


class FakeTodoistClient(object):
    def __init__(self, apiToken, listProjectsError=None):
        self.apiToken = apiToken
        self._listProjectsError = listProjectsError

    def list_projects(self):
        if self._listProjectsError:
            raise self._listProjectsError
        return []


@pytest.fixture
def settingsPath(tmp_path):
    path = str(tmp_path / "settings.yaml")
    with open(path, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    return path


def test_connect_todoist_persists_the_token(settingsPath, monkeypatch):
    monkeypatch.setattr(connect_todoist_module, "TodoistClient", lambda apiToken: FakeTodoistClient(apiToken))

    result = connect_todoist(log=log, apiToken="my-token", pathToSettingsFile=settingsPath).get()

    assert result == "my-token"
    settings = settings_writer.read_settings(settingsPath)
    assert settings["todoist"]["enabled"] is True
    assert settings["todoist"]["api_token"] == "my-token"


def test_connect_todoist_raises_a_clear_error_on_an_invalid_token(settingsPath, monkeypatch):
    monkeypatch.setattr(
        connect_todoist_module, "TodoistClient",
        lambda apiToken: FakeTodoistClient(apiToken, listProjectsError=TodoistApiError("401")),
    )

    with pytest.raises(ValueError):
        connect_todoist(log=log, apiToken="bad-token", pathToSettingsFile=settingsPath).get()

    settings = settings_writer.read_settings(settingsPath)
    assert "todoist" not in settings

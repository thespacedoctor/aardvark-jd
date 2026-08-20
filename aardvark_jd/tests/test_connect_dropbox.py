import logging
import sys

import pytest
import requests
import yaml

from aardvark_jd import settings_writer
from aardvark_jd.connect_dropbox import connect_dropbox

log = logging.getLogger("test_connect_dropbox")
log.addHandler(logging.NullHandler())


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_body


@pytest.fixture
def settingsPath(tmp_path):
    path = str(tmp_path / "settings.yaml")
    with open(path, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    return path


def test_connect_dropbox_requires_a_tty(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError):
        connect_dropbox(log=log, appKey="key", appSecret="secret", pathToSettingsFile=settingsPath).get()


def test_connect_dropbox_persists_refresh_token(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "auth-code-123")
    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr(
        requests, "post",
        lambda url, data: FakeResponse(json_body={"refresh_token": "refresh-abc", "access_token": "atok"}),
    )

    refreshToken = connect_dropbox(
        log=log, appKey="key", appSecret="secret", pathToSettingsFile=settingsPath,
    ).get()

    assert refreshToken == "refresh-abc"
    settings = settings_writer.read_settings(settingsPath)
    assert settings["dropbox"]["enabled"] is True
    assert settings["dropbox"]["app_key"] == "key"
    assert settings["dropbox"]["app_secret"] == "secret"
    assert settings["dropbox"]["refresh_token"] == "refresh-abc"


def test_connect_dropbox_raises_when_no_refresh_token_is_returned(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "auth-code-123")
    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr(requests, "post", lambda url, data: FakeResponse(json_body={"access_token": "atok"}))

    with pytest.raises(ValueError):
        connect_dropbox(log=log, appKey="key", appSecret="secret", pathToSettingsFile=settingsPath).get()


def test_connect_dropbox_raises_on_token_exchange_failure(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "bad-code")
    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr(requests, "post", lambda url, data: FakeResponse(status_code=400, text="invalid_grant"))

    with pytest.raises(ValueError):
        connect_dropbox(log=log, appKey="key", appSecret="secret", pathToSettingsFile=settingsPath).get()

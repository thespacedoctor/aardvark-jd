import base64
import hashlib
import logging
import sys
import threading
import urllib.request

import pytest
import requests
import yaml

from aardvark_jd import oauth, settings_writer
from aardvark_jd.connect_gdrive import connect_gdrive

log = logging.getLogger("test_connect_gdrive")
log.addHandler(logging.NullHandler())


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_body


@pytest.fixture
def settingsPath(tmp_path):
    path = str(tmp_path / "settings.yaml")
    with open(path, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": "Test", "root_path": "/tmp/x"}}, stream)
    return path


def test_pkce_pair_challenge_is_the_s256_of_the_verifier():
    codeVerifier, codeChallenge = oauth.pkce_pair()
    digest = hashlib.sha256(codeVerifier.encode("ascii")).digest()
    assert codeChallenge == base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert "=" not in codeVerifier and "=" not in codeChallenge


def test_loopback_capture_code_reads_the_code_from_the_redirect(monkeypatch):
    monkeypatch.setattr("webbrowser.open", lambda url: None)
    captured = {}

    def visit(url):
        captured["url"] = url
        # SIMULATE GOOGLE REDIRECTING THE BROWSER BACK WITH THE CODE
        redirectUri = url.split("redirect_uri=")[1].split("&")[0]
        threading.Thread(
            target=lambda: urllib.request.urlopen(f"{redirectUri}?code=auth-123").read(),
            daemon=True,
        ).start()
        return url

    monkeypatch.setattr("webbrowser.open", visit)
    authCode, redirectUri = oauth.loopback_capture_code(
        lambda uri: f"https://accounts.google.com/o/oauth2/v2/auth?redirect_uri={uri}",
    )
    assert authCode == "auth-123"
    assert redirectUri.startswith("http://127.0.0.1:")


def test_loopback_capture_code_raises_when_access_is_refused(monkeypatch):
    def visit(url):
        redirectUri = url.split("redirect_uri=")[1].split("&")[0]
        threading.Thread(
            target=lambda: urllib.request.urlopen(f"{redirectUri}?error=access_denied").read(),
            daemon=True,
        ).start()
        return url

    monkeypatch.setattr("webbrowser.open", visit)
    with pytest.raises(ValueError, match="refused"):
        oauth.loopback_capture_code(lambda uri: f"https://example.com/auth?redirect_uri={uri}")


def test_connect_requires_a_terminal(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="interactive terminal"):
        connect_gdrive(
            log=log, clientId="cid", clientSecret="secret", pathToSettingsFile=settingsPath
        ).get()


def test_a_successful_connect_stores_the_refresh_token(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        oauth, "loopback_capture_code",
        lambda builder, timeoutSeconds=180: ("auth-123", "http://127.0.0.1:9999/"),
    )
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kwargs: FakeResponse(json_body={"refresh_token": "rt-1"}),
    )

    refreshToken = connect_gdrive(
        log=log, clientId="cid", clientSecret="secret", pathToSettingsFile=settingsPath
    ).get()

    assert refreshToken == "rt-1"
    settings = settings_writer.read_settings(settingsPath)
    assert settings["gdrive"]["enabled"] is True
    assert settings["gdrive"]["client_id"] == "cid"
    assert settings["gdrive"]["refresh_token"] == "rt-1"
    assert settings["gdrive"]["scope"].endswith("/auth/drive")


def test_the_authorise_url_asks_for_offline_access_and_pkce(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    built = {}

    def capture(builder, timeoutSeconds=180):
        built["url"] = builder("http://127.0.0.1:9999/")
        return "auth-123", "http://127.0.0.1:9999/"

    monkeypatch.setattr(oauth, "loopback_capture_code", capture)
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kwargs: FakeResponse(json_body={"refresh_token": "rt-1"}),
    )
    connect_gdrive(
        log=log, clientId="cid", clientSecret="secret", pathToSettingsFile=settingsPath
    ).get()

    assert "access_type=offline" in built["url"]
    assert "prompt=consent" in built["url"]
    assert "code_challenge_method=S256" in built["url"]
    assert "auth%2Fdrive" in built["url"]


def test_a_missing_refresh_token_is_an_error(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        oauth, "loopback_capture_code",
        lambda builder, timeoutSeconds=180: ("auth-123", "http://127.0.0.1:9999/"),
    )
    monkeypatch.setattr(
        requests, "post", lambda url, **kwargs: FakeResponse(json_body={"access_token": "at"}),
    )
    with pytest.raises(ValueError, match="no refresh token"):
        connect_gdrive(
            log=log, clientId="cid", clientSecret="secret", pathToSettingsFile=settingsPath
        ).get()


def test_a_failed_exchange_is_an_error(settingsPath, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        oauth, "loopback_capture_code",
        lambda builder, timeoutSeconds=180: ("auth-123", "http://127.0.0.1:9999/"),
    )
    monkeypatch.setattr(
        requests, "post", lambda url, **kwargs: FakeResponse(status_code=400, text="nope"),
    )
    with pytest.raises(ValueError, match="token exchange failed"):
        connect_gdrive(
            log=log, clientId="cid", clientSecret="secret", pathToSettingsFile=settingsPath
        ).get()

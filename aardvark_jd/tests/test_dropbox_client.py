import json

import pytest
import requests

from aardvark_jd import dropbox_client
from aardvark_jd.dropbox_client import DropboxApiError, DropboxClient


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_body


# ---------------------------------------------------------------------- #
# local root detection
# ---------------------------------------------------------------------- #

def test_local_dropbox_roots_reads_info_json(tmp_path, monkeypatch):
    infoPath = tmp_path / ".dropbox" / "info.json"
    infoPath.parent.mkdir()
    infoPath.write_text(json.dumps({"personal": {"path": "/Users/dave/Dropbox", "host": 1}}))
    monkeypatch.setattr("os.path.expanduser", lambda p: p.replace("~", str(tmp_path)))

    assert dropbox_client.local_dropbox_roots() == ["/Users/dave/Dropbox"]


def test_local_dropbox_roots_returns_empty_list_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("os.path.expanduser", lambda p: p.replace("~", str(tmp_path)))
    assert dropbox_client.local_dropbox_roots() == []


def test_find_containing_root_matches_a_subpath():
    root = dropbox_client.find_containing_root(
        "/Users/dave/Dropbox/aardvark/03_AREAS", ["/Users/dave/Dropbox"],
    )
    assert root == "/Users/dave/Dropbox"


def test_find_containing_root_is_case_insensitive():
    root = dropbox_client.find_containing_root(
        "/Users/Dave/Dropbox/aardvark", ["/Users/dave/Dropbox"],
    )
    assert root == "/Users/dave/Dropbox"


def test_find_containing_root_rejects_a_lookalike_sibling():
    root = dropbox_client.find_containing_root(
        "/Users/dave/Dropbox_old/aardvark", ["/Users/dave/Dropbox"],
    )
    assert root is None


def test_find_containing_root_returns_none_when_not_inside_any_root():
    assert dropbox_client.find_containing_root("/nonexistent-test-root/outside", ["/Users/dave/Dropbox"]) is None


def test_to_dropbox_path_converts_relative_to_the_root():
    dropboxPath = dropbox_client.to_dropbox_path(
        "/Users/dave/Dropbox/aardvark/03_AREAS", "/Users/dave/Dropbox",
    )
    assert dropboxPath == "/aardvark/03_AREAS"


def test_to_dropbox_path_returns_none_outside_the_root():
    assert dropbox_client.to_dropbox_path("/nonexistent-test-root/outside", "/Users/dave/Dropbox") is None


# ---------------------------------------------------------------------- #
# API client
# ---------------------------------------------------------------------- #

def _client(monkeypatch, postResponses):
    """*build a DropboxClient whose `requests.Session.post` calls are served in order from `postResponses`*"""
    calls = []

    def fakePost(self, url, **kwargs):
        calls.append({"url": url, "kwargs": kwargs})
        return postResponses.pop(0)

    monkeypatch.setattr(requests.Session, "post", fakePost)
    client = DropboxClient(appKey="key", appSecret="secret", refreshToken="refresh")
    return client, calls


def test_shared_link_mints_a_new_link(monkeypatch):
    client, calls = _client(monkeypatch, [
        FakeResponse(json_body={"access_token": "atok"}),
        FakeResponse(json_body={"url": "https://www.dropbox.com/scl/fo/abc"}),
    ])
    url = client.shared_link("/aardvark/03_AREAS")
    assert url == "https://www.dropbox.com/scl/fo/abc"
    assert calls[1]["url"] == f"{DropboxClient._API_URL}/sharing/create_shared_link_with_settings"
    assert calls[1]["kwargs"]["json"] == {"path": "/aardvark/03_AREAS"}


def test_shared_link_adopts_an_existing_link_on_conflict(monkeypatch):
    client, _calls = _client(monkeypatch, [
        FakeResponse(json_body={"access_token": "atok"}),
        FakeResponse(status_code=409, text='{"error_summary": "shared_link_already_exists/..."}'),
        FakeResponse(json_body={"access_token": "atok"}),
        FakeResponse(json_body={"links": [{"url": "https://www.dropbox.com/scl/fo/existing"}]}),
    ])
    url = client.shared_link("/aardvark/03_AREAS")
    assert url == "https://www.dropbox.com/scl/fo/existing"


def test_shared_link_reraises_other_api_errors(monkeypatch):
    client, _calls = _client(monkeypatch, [
        FakeResponse(json_body={"access_token": "atok"}),
        FakeResponse(status_code=400, text="malformed_path"),
    ])
    with pytest.raises(DropboxApiError):
        client.shared_link("/aardvark/03_AREAS")

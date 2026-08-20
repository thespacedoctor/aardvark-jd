import logging

import pytest
import requests

from aardvark_jd.gdrive_client import GDriveApiError, GDriveClient

log = logging.getLogger("test_gdrive_client")
log.addHandler(logging.NullHandler())

_FOLDER_MIME = "application/vnd.google-apps.folder"


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json_body = json_body if json_body is not None else {}
        self.text = text
        self.content = b"{}" if json_body is not None else b""
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_body


@pytest.fixture
def client():
    return GDriveClient(clientId="cid", clientSecret="secret", refreshToken="refresh")


def _mock_token(monkeypatch, captured=None):
    def fakePost(self, url, **kwargs):
        if captured is not None:
            captured["token"] = kwargs.get("data")
        return FakeResponse(json_body={"access_token": "at-1", "expires_in": 3600})

    monkeypatch.setattr(requests.Session, "post", fakePost)


def test_the_refresh_token_is_exchanged_for_an_access_token(client, monkeypatch):
    captured = {}
    _mock_token(monkeypatch, captured)
    assert client._access_token() == "at-1"
    assert captured["token"] == {
        "grant_type": "refresh_token",
        "refresh_token": "refresh",
        "client_id": "cid",
        "client_secret": "secret",
    }


def test_the_access_token_is_cached_across_calls(client, monkeypatch):
    calls = []

    def fakePost(self, url, **kwargs):
        calls.append(url)
        return FakeResponse(json_body={"access_token": "at-1", "expires_in": 3600})

    monkeypatch.setattr(requests.Session, "post", fakePost)
    client._access_token()
    client._access_token()
    assert len(calls) == 1


def test_a_failed_token_refresh_raises(client, monkeypatch):
    monkeypatch.setattr(
        requests.Session, "post",
        lambda self, url, **kwargs: FakeResponse(status_code=400, text="bad"),
    )
    with pytest.raises(GDriveApiError):
        client._access_token()


def test_list_child_folders_queries_for_untrashed_folders(client, monkeypatch):
    _mock_token(monkeypatch)
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return FakeResponse(json_body={"files": [{"id": "f1", "name": "03 AREAS🧭"}]})

    monkeypatch.setattr(requests.Session, "request", fakeRequest)
    folders = client.list_child_folders("parent-1")

    assert captured["method"] == "GET"
    assert captured["url"].endswith("/files")
    assert captured["params"]["q"] == (
        f"'parent-1' in parents and mimeType = '{_FOLDER_MIME}' and trashed = false"
    )
    assert folders == [{"id": "f1", "name": "03 AREAS🧭"}]


def test_list_child_folders_follows_pagination(client, monkeypatch):
    _mock_token(monkeypatch)
    pages = [
        {"files": [{"id": "f1", "name": "one"}], "nextPageToken": "tok"},
        {"files": [{"id": "f2", "name": "two"}]},
    ]

    def fakeRequest(self, method, url, **kwargs):
        return FakeResponse(json_body=pages.pop(0))

    monkeypatch.setattr(requests.Session, "request", fakeRequest)
    assert [f["id"] for f in client.list_child_folders("parent-1")] == ["f1", "f2"]


def test_create_folder_sends_the_folder_mime_type_and_parent(client, monkeypatch):
    _mock_token(monkeypatch)
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["json"] = kwargs.get("json")
        return FakeResponse(json_body={
            "id": "new-1", "name": "A11 doctors🩺",
            "webViewLink": "https://drive.google.com/drive/folders/new-1",
        })

    monkeypatch.setattr(requests.Session, "request", fakeRequest)
    folderId, url = client.create_folder("A11 doctors🩺", parentId="parent-1")

    assert captured["json"] == {
        "name": "A11 doctors🩺", "mimeType": _FOLDER_MIME, "parents": ["parent-1"],
    }
    assert folderId == "new-1"
    assert url.endswith("/new-1")


def test_create_folder_at_the_root_sends_no_parents(client, monkeypatch):
    _mock_token(monkeypatch)
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["json"] = kwargs.get("json")
        return FakeResponse(json_body={"id": "new-1"})

    monkeypatch.setattr(requests.Session, "request", fakeRequest)
    client.create_folder("Scratch")
    assert "parents" not in captured["json"]


def test_move_folder_adds_and_removes_parents(client, monkeypatch):
    _mock_token(monkeypatch)
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return FakeResponse(json_body={"id": "f1", "parents": ["archive-1"]})

    monkeypatch.setattr(requests.Session, "request", fakeRequest)
    assert client.move_folder("f1", "archive-1", "old-1") == "f1"
    assert captured["method"] == "PATCH"
    assert captured["url"].endswith("/files/f1")
    assert captured["params"]["addParents"] == "archive-1"
    assert captured["params"]["removeParents"] == "old-1"


def test_a_failed_request_raises(client, monkeypatch):
    _mock_token(monkeypatch)
    monkeypatch.setattr(
        requests.Session, "request",
        lambda self, method, url, **kwargs: FakeResponse(status_code=403, text="denied"),
    )
    with pytest.raises(GDriveApiError):
        client.list_child_folders("parent-1")


def test_folder_url_is_built_from_the_id():
    assert GDriveClient.folder_url("abc") == "https://drive.google.com/drive/folders/abc"

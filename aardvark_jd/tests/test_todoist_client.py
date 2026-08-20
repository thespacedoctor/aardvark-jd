import pytest
import requests

from aardvark_jd.todoist_client import TodoistApiError, TodoistClient

_API_URL = "https://api.todoist.com/api/v1"


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self.content = b"1" if json_body is not None else b""
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_body


def test_create_project_posts_expected_body(monkeypatch):
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse(json_body={"id": "proj-1"})

    monkeypatch.setattr(requests.Session, "request", fakeRequest)

    projectId = TodoistClient(apiToken="tok").create_project("03 AREAS🧭", parentId="parent-1")

    assert projectId == "proj-1"
    assert captured["method"] == "POST"
    assert captured["url"] == f"{_API_URL}/projects"
    assert captured["json"] == {"name": "03 AREAS🧭", "parent_id": "parent-1"}


def test_create_project_omits_optional_fields_when_unset(monkeypatch):
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["json"] = kwargs.get("json")
        return FakeResponse(json_body={"id": "proj-1"})

    monkeypatch.setattr(requests.Session, "request", fakeRequest)

    TodoistClient(apiToken="tok").create_project("02 PROJECTS🚀")

    assert captured["json"] == {"name": "02 PROJECTS🚀"}


def test_list_projects_follows_pagination_to_completion(monkeypatch):
    pages = [
        {"results": [{"id": "1", "name": "A", "parent_id": None}], "next_cursor": "cursor-2"},
        {"results": [{"id": "2", "name": "B", "parent_id": "1"}], "next_cursor": None},
    ]
    calls = []

    def fakeRequest(self, method, url, **kwargs):
        calls.append(kwargs.get("params"))
        return FakeResponse(json_body=pages[len(calls) - 1])

    monkeypatch.setattr(requests.Session, "request", fakeRequest)

    projects = TodoistClient(apiToken="tok").list_projects()

    assert [p["id"] for p in projects] == ["1", "2"]
    assert calls[0] == {}
    assert calls[1] == {"cursor": "cursor-2"}


def test_update_project_description_posts_to_the_project(monkeypatch):
    captured = {}

    def fakeRequest(self, method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse(json_body={})

    monkeypatch.setattr(requests.Session, "request", fakeRequest)

    TodoistClient(apiToken="tok").update_project_description("proj-1", "[Craft](url)")

    assert captured["method"] == "POST"
    assert captured["url"] == f"{_API_URL}/projects/proj-1"
    assert captured["json"] == {"description": "[Craft](url)"}


def test_project_url_and_app_url():
    assert TodoistClient.project_url("proj-1") == "https://app.todoist.com/app/project/proj-1"
    assert TodoistClient.project_app_url("proj-1") == "todoist://project?id=proj-1"


def test_request_failure_raises_todoist_api_error(monkeypatch):
    def fakeRequest(self, method, url, **kwargs):
        return FakeResponse(status_code=500, text="boom")

    monkeypatch.setattr(requests.Session, "request", fakeRequest)

    with pytest.raises(TodoistApiError):
        TodoistClient(apiToken="tok").create_project("Areas")


def test_authorization_header_carries_the_api_token():
    client = TodoistClient(apiToken="secret-token")
    assert client._session.headers["Authorization"] == "Bearer secret-token"

#!/usr/bin/env python
# encoding: utf-8
"""
*Thin HTTP client for the Todoist API v1 - project listing and creation*

Modelled on `craft_client.CraftClient`: a minimal wrapper over the one
handful of endpoints `todoist_sync` needs, raising `TodoistApiError` on
any non-2xx response. Authenticated with a personal API token (Todoist ->
Settings -> Integrations -> Developer) rather than OAuth - there is no
multi-user aardvark deployment to justify the extra flow `connect_dropbox`
needs.

Endpoint shapes (`GET/POST /projects`, cursor-paginated list responses
under `results`/`next_cursor`) follow Todoist's published v1 API
reference at the time of writing but are not yet confirmed against a
live account - unlike `craft_client.py`'s endpoints, which were probed
empirically. Verify `list_projects`/`create_project` against a real
account before relying on this in production.

Author
: David Young
"""

import requests


class TodoistApiError(Exception):
    pass


class TodoistClient(object):
    """
    *a minimal client for the Todoist API v1, authenticated via a personal API token*

    **Key Arguments:**

    - ``apiToken`` -- a personal API token, from Todoist's Integrations -> Developer settings

    **Usage:**

    ```python
    from aardvark_jd.todoist_client import TodoistClient
    client = TodoistClient(apiToken="...")
    projectId = client.create_project("03 AREAS🧭")
    ```
    """

    _API_URL = "https://api.todoist.com/api/v1"

    def __init__(self, apiToken):
        self.apiToken = apiToken
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {apiToken}",
            "Content-Type": "application/json",
        })

    def _request(self, method, path, **kwargs):
        """
        *issue an authenticated request against the Todoist API, raising `TodoistApiError` on failure*

        **Key Arguments:**

        - ``method`` -- the HTTP method, e.g. `"POST"`
        - ``path`` -- the request path, relative to `_API_URL`

        **Return:**

        - ``payload`` -- the parsed JSON response body
        """
        response = self._session.request(method, f"{self._API_URL}{path}", **kwargs)
        if not response.ok:
            raise TodoistApiError(f"todoist API {method} {path} failed ({response.status_code}): {response.text}")
        if not response.content:
            return {}
        return response.json()

    def list_projects(self):
        """
        *list every project in the account, following pagination to completion*

        **Return:**

        - ``projects`` -- a flat list of project dicts, each carrying at least `id`, `name` and `parent_id`
        """
        projects = []
        cursor = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            payload = self._request("GET", "/projects", params=params)
            projects.extend(payload.get("results") or [])
            cursor = payload.get("next_cursor")
            if not cursor:
                break
        return projects

    def create_project(self, name, parentId=None, description=None):
        """
        *create a Todoist project, optionally nested under an existing one*

        **Key Arguments:**

        - ``name`` -- the project's name
        - ``parentId`` -- the parent project's id, or `None` for a top-level project. Default `None`.
        - ``description`` -- the project's description, if any. Default `None`.

        **Return:**

        - ``projectId`` -- the new project's id
        """
        body = {"name": name}
        if parentId is not None:
            body["parent_id"] = parentId
        if description is not None:
            body["description"] = description
        payload = self._request("POST", "/projects", json=body)
        return payload["id"]

    def update_project_description(self, projectId, description):
        """
        *set an existing project's description*

        **Key Arguments:**

        - ``projectId`` -- the project's id
        - ``description`` -- the description text to set
        """
        self._request("POST", f"/projects/{projectId}", json={"description": description})

    @staticmethod
    def project_url(projectId):
        """
        *build a project's shareable web URL*

        **Key Arguments:**

        - ``projectId`` -- the project's id

        **Return:**

        - ``url`` -- the project's `https://app.todoist.com/...` URL
        """
        return f"https://app.todoist.com/app/project/{projectId}"

    @staticmethod
    def project_app_url(projectId):
        """
        *build a project's `todoist://` deep link, for opening in the desktop/mobile app*

        **Key Arguments:**

        - ``projectId`` -- the project's id

        **Return:**

        - ``url`` -- the project's `todoist://project?id=...` URL
        """
        return f"todoist://project?id={projectId}"

    def archive_project(self, projectId):
        """
        *archive a Todoist project, hiding it without destroying its tasks*

        Archived rather than deleted deliberately: a mirrored project may
        have accumulated real tasks of its own, and `DELETE /projects/{id}`
        would take them with it irreversibly.

        Follows the published v1 reference; like the rest of this module's
        endpoints it has not been confirmed against a live account, so
        callers should treat a failure as a warning rather than an abort.

        **Key Arguments:**

        - ``projectId`` -- the project's Todoist id

        **Usage:**

        ```python
        client.archive_project("2203306141")
        ```
        """
        self._request("POST", f"/projects/{projectId}/archive")

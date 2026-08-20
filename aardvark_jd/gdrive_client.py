#!/usr/bin/env python
# encoding: utf-8
"""
*Thin HTTP client for the Google Drive v3 API - folder listing, creation and moves*

Hand-rolled on `requests` rather than built on `google-api-python-client`,
for the same reason `craft_client`, `todoist_client` and `dropbox_client`
are: aardvark needs four endpoints, and the whole test suite mocks the
network by monkeypatching `requests.Session.request`. Pulling in the
official SDK would add a large transitive dependency tree and would not fit
that pattern.

Unlike Dropbox, an access token *is* cached here for its stated lifetime -
a full mirror touches every folder in the system, so re-exchanging the
refresh token on each call would mean hundreds of extra round trips rather
than the handful `DropboxClient` makes.

Author
: David Young
"""

import time

import requests

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# REFRESH A LITTLE BEFORE THE STATED EXPIRY, SO A LONG SYNC CANNOT HAVE A
# TOKEN GO STALE BETWEEN THE CHECK AND THE REQUEST IT AUTHORISES.
_TOKEN_EXPIRY_MARGIN_SECONDS = 60


class GDriveApiError(Exception):
    """*raised when the Google Drive API returns a non-2xx response*"""
    pass


class GDriveClient(object):
    """
    *a minimal client for the Google Drive v3 API, authenticated via a long-lived refresh token*

    **Key Arguments:**

    - ``clientId`` -- the Google Cloud OAuth "Desktop app" client ID
    - ``clientSecret`` -- the matching client secret
    - ``refreshToken`` -- a long-lived refresh token, from `connect_gdrive.py`'s loopback flow

    **Usage:**

    ```python
    from aardvark_jd.gdrive_client import GDriveClient
    client = GDriveClient(clientId="...", clientSecret="...", refreshToken="...")
    folderId, url = client.create_folder("03 AREAS🧭", parentId="root")
    ```
    """

    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _API_URL = "https://www.googleapis.com/drive/v3"

    def __init__(self, clientId, clientSecret, refreshToken):
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.refreshToken = refreshToken
        self._accessToken = None
        self._accessTokenExpiresAt = 0
        self._session = requests.Session()

    def _access_token(self):
        """
        *return a valid access token, exchanging the refresh token only when the cached one is stale*

        **Return:**

        - ``accessToken`` -- a currently valid Google API access token
        """
        if self._accessToken and time.time() < self._accessTokenExpiresAt:
            return self._accessToken

        response = self._session.post(
            self._TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refreshToken,
                "client_id": self.clientId,
                "client_secret": self.clientSecret,
            },
        )
        if not response.ok:
            raise GDriveApiError(
                f"google drive token refresh failed ({response.status_code}): {response.text}"
            )
        payload = response.json()
        self._accessToken = payload["access_token"]
        self._accessTokenExpiresAt = (
            time.time() + int(payload.get("expires_in", 3600)) - _TOKEN_EXPIRY_MARGIN_SECONDS
        )
        return self._accessToken

    def _request(self, method, path, **kwargs):
        """
        *issue an authenticated request against the Drive API, raising `GDriveApiError` on failure*

        **Key Arguments:**

        - ``method`` -- the HTTP method
        - ``path`` -- the API path, e.g. `"/files"`
        - ``kwargs`` -- passed straight through to `requests`

        **Return:**

        - ``payload`` -- the parsed JSON response, or `{}` for an empty body
        """
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token()}"
        response = self._session.request(method, f"{self._API_URL}{path}", headers=headers, **kwargs)
        if not response.ok:
            raise GDriveApiError(
                f"google drive {method} {path} failed ({response.status_code}): {response.text}"
            )
        if not response.content:
            return {}
        return response.json()

    def list_child_folders(self, parentId):
        """
        *every non-trashed folder directly inside a Drive folder*

        Drive has no cheap whole-tree listing, so the sync indexes one
        parent at a time, on demand - see `gdrive_sync._children`.

        **Key Arguments:**

        - ``parentId`` -- the parent folder's id, or `"root"` for the Drive root

        **Return:**

        - ``folders`` -- a list of dicts carrying `id`, `name` and `webViewLink`

        **Usage:**

        ```python
        children = client.list_child_folders("root")
        ```
        """
        folders = []
        pageToken = None
        query = (
            f"'{parentId}' in parents and mimeType = '{_FOLDER_MIME_TYPE}' and trashed = false"
        )
        while True:
            params = {
                "q": query,
                "fields": "nextPageToken,files(id,name,webViewLink)",
                "pageSize": 1000,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if pageToken:
                params["pageToken"] = pageToken
            payload = self._request("GET", "/files", params=params)
            folders.extend(payload.get("files") or [])
            pageToken = payload.get("nextPageToken")
            if not pageToken:
                return folders

    def create_folder(self, name, parentId=None):
        """
        *create a folder in Drive*

        **Key Arguments:**

        - ``name`` -- the folder's name
        - ``parentId`` -- the parent folder's id. Default *None*, meaning the Drive root.

        **Return:**

        - ``folderId``, ``url`` -- the new folder's id and its web URL
        """
        body = {"name": name, "mimeType": _FOLDER_MIME_TYPE}
        if parentId:
            body["parents"] = [parentId]
        payload = self._request(
            "POST", "/files",
            params={"fields": "id,name,webViewLink", "supportsAllDrives": "true"},
            json=body,
        )
        return payload["id"], payload.get("webViewLink") or self.folder_url(payload["id"])

    def move_folder(self, folderId, newParentId, oldParentId):
        """
        *move a folder to a different parent*

        Drive models parentage as a list, so a move is "add the new parent,
        remove the old one" in a single `PATCH` - unlike Craft, whose API
        offers no move at all.

        **Key Arguments:**

        - ``folderId`` -- the folder to move
        - ``newParentId`` -- the destination parent's id
        - ``oldParentId`` -- the parent to detach from

        **Return:**

        - ``folderId`` -- the moved folder's id
        """
        payload = self._request(
            "PATCH", f"/files/{folderId}",
            params={
                "addParents": newParentId,
                "removeParents": oldParentId,
                "fields": "id,parents",
                "supportsAllDrives": "true",
            },
        )
        return payload.get("id", folderId)

    @staticmethod
    def folder_url(folderId):
        """
        *the browser URL for a Drive folder*

        **Key Arguments:**

        - ``folderId`` -- the folder's id

        **Return:**

        - ``url`` -- the folder's `drive.google.com` URL
        """
        return f"https://drive.google.com/drive/folders/{folderId}"

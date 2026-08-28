#!/usr/bin/env python
# encoding: utf-8
"""
*Local Dropbox-root detection, and a thin HTTP client for the Dropbox API v2*

Detecting whether the aardvark system root lives inside a Dropbox-synced
folder is entirely local - Dropbox's desktop client writes its synced
account root(s) to `~/.dropbox/info.json` on every platform it supports.
The API half mints/reuses a share link for a given local path, the same
create-or-adopt idempotency `craft_sync.py` already uses for Craft
folders: sharing a path that is already shared just returns the existing
link rather than erroring.

Short-lived Dropbox access tokens expire after 4 hours, so this client is
built around a long-lived refresh token (from `connect_dropbox.py`'s
one-time PKCE flow) rather than a pasted access token.

Author
: David Young
"""

import json
import os

import requests

from aardvark_jd import db, http_retry


class DropboxApiError(Exception):
    pass


def local_dropbox_roots():
    """
    *read every locally-synced Dropbox account root from `~/.dropbox/info.json`*

    Returns an empty list - rather than raising - when the file is
    missing, so the Dropbox link feature degrades cleanly on a machine
    without the Dropbox desktop client installed.

    **Return:**

    - ``roots`` -- a list of absolute local Dropbox root paths
    """
    infoPath = os.path.expanduser("~/.dropbox/info.json")
    if not os.path.isfile(infoPath):
        return []
    with open(infoPath, "r") as stream:
        info = json.load(stream)
    return [account["path"] for account in info.values() if account.get("path")]


def _normalise(path):
    """
    *resolve a path to its canonical, symlink-free, case-folded form*

    Shared with the same rationale as `locate._normalise` - case
    differences between a settings-file path and the live filesystem must
    not break a prefix match.

    **Key Arguments:**

    - ``path`` -- the path to normalise

    **Return:**

    - ``normalised`` -- the resolved, lower-cased path
    """
    return os.path.realpath(os.path.expanduser(path)).lower()


def find_containing_root(localPath, roots):
    """
    *find which, if any, local Dropbox root contains a path*

    **Key Arguments:**

    - ``localPath`` -- the path to check, e.g. the aardvark system root
    - ``roots`` -- candidate Dropbox root paths, from `local_dropbox_roots`

    **Return:**

    - ``root`` -- the containing root path, or `None` if `localPath` isn't inside any of them
    """
    targetPath = _normalise(localPath)
    for root in roots:
        rootPath = _normalise(root)
        if targetPath == rootPath or targetPath.startswith(rootPath + os.sep):
            return root
    return None


def to_dropbox_path(localPath, dropboxRoot):
    """
    *convert a local filesystem path into a Dropbox API path, relative to its synced root*

    **Key Arguments:**

    - ``localPath`` -- the local path, e.g. an aardvark entity's `folder_path`
    - ``dropboxRoot`` -- the local Dropbox root that contains it, from `find_containing_root`

    **Return:**

    - ``dropboxPath`` -- the Dropbox-API-relative path (leading `/`, forward slashes), or `None` if `localPath` isn't inside `dropboxRoot`
    """
    targetPath = os.path.realpath(os.path.expanduser(localPath))
    rootPath = os.path.realpath(os.path.expanduser(dropboxRoot))
    if _normalise(targetPath) != _normalise(rootPath) and not _normalise(targetPath).startswith(_normalise(rootPath) + os.sep):
        return None
    relative = targetPath[len(rootPath):].lstrip(os.sep)
    return "/" + relative.replace(os.sep, "/")


class DropboxClient(object):
    """
    *a minimal client for the Dropbox API v2, authenticated via a long-lived refresh token*

    **Key Arguments:**

    - ``appKey`` -- the Dropbox app's key, from the App Console
    - ``appSecret`` -- the Dropbox app's secret, from the App Console
    - ``refreshToken`` -- a long-lived refresh token, from `connect_dropbox.py`'s PKCE flow

    **Usage:**

    ```python
    from aardvark_jd.dropbox_client import DropboxClient
    client = DropboxClient(appKey="...", appSecret="...", refreshToken="...")
    url = client.shared_link("/aardvark/03_AREAS/A11_doctors")
    ```
    """

    _TOKEN_URL = "https://api.dropbox.com/oauth2/token"
    _API_URL = "https://api.dropboxapi.com/2"

    def __init__(self, appKey, appSecret, refreshToken):
        self.appKey = appKey
        self.appSecret = appSecret
        self.refreshToken = refreshToken
        self._accessToken = None
        self._session = requests.Session()

    def _access_token(self):
        """
        *exchange the refresh token for a short-lived access token, on every call*

        Not cached across calls - a `craft_sync` run mints at most a
        handful of share links, so trading simplicity for one extra token
        exchange per sync is a reasonable trade against silently using a
        token past its ~4 hour expiry.

        **Return:**

        - ``accessToken`` -- a short-lived Dropbox access token
        """
        response = self._session.post(
            self._TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refreshToken,
                "client_id": self.appKey,
                "client_secret": self.appSecret,
            },
            timeout=http_retry.HTTP_TIMEOUT,
        )
        if not response.ok:
            raise DropboxApiError(f"dropbox token refresh failed ({response.status_code}): {response.text}")
        return response.json()["access_token"]

    def _request(self, path, jsonBody):
        """
        *issue an authenticated POST against the Dropbox API, raising `DropboxApiError` on failure*

        **Key Arguments:**

        - ``path`` -- the request path, relative to the API base URL
        - ``jsonBody`` -- the request body

        **Return:**

        - ``payload`` -- the parsed JSON response body
        """
        accessToken = self._access_token()
        response = self._session.post(
            f"{self._API_URL}{path}",
            headers={"Authorization": f"Bearer {accessToken}"},
            json=jsonBody,
            timeout=http_retry.HTTP_TIMEOUT,
        )
        if not response.ok:
            raise DropboxApiError(f"dropbox API {path} failed ({response.status_code}): {response.text}")
        return response.json()

    def shared_link(self, dropboxPath):
        """
        *mint a shared link for a Dropbox path, adopting one that already exists*

        **Key Arguments:**

        - ``dropboxPath`` -- the Dropbox-API-relative path, from `to_dropbox_path`

        **Return:**

        - ``url`` -- the folder's Dropbox share URL
        """
        try:
            payload = self._request(
                "/sharing/create_shared_link_with_settings", {"path": dropboxPath},
            )
            return payload["url"]
        except DropboxApiError as error:
            if "shared_link_already_exists" not in str(error):
                raise
            return self._existing_shared_link(dropboxPath)

    def _existing_shared_link(self, dropboxPath):
        """
        *look up the share link already minted for a path*

        **Key Arguments:**

        - ``dropboxPath`` -- the Dropbox-API-relative path

        **Return:**

        - ``url`` -- the existing share URL

        **Raises:**

        - ``DropboxApiError`` -- if no existing link is found, despite Dropbox reporting one exists
        """
        payload = self._request("/sharing/list_shared_links", {"path": dropboxPath, "direct_only": True})
        links = payload.get("links") or []
        if not links:
            raise DropboxApiError(f"dropbox reported an existing shared link for '{dropboxPath}' but none was found")
        return links[0]["url"]


def url_for_path(dbConn, client, dropboxRoot, folderPath, log):
    """
    *resolve (and cache) a folder's Dropbox share URL, or `None` if it isn't reachable via Dropbox*

    Shared between `craft_sync` and `todoist_sync`, both of which need the
    same folder's Dropbox link for their own link row - caching in
    `dropbox_links` means it's minted once regardless of how many mirrors
    ask for it. A Dropbox API failure degrades to `None` and a logged
    warning rather than raising, so the caller's own sync (whose
    filesystem/index/Craft state is already correct by the time this
    runs) is never aborted by it.

    **Key Arguments:**

    - ``dbConn`` -- an open SQLite connection
    - ``client`` -- an authenticated `DropboxClient`, or `None` if Dropbox isn't connected
    - ``dropboxRoot`` -- the local Dropbox root containing the aardvark system, from `find_containing_root`, or `None`
    - ``folderPath`` -- the folder's absolute local path
    - ``log`` -- logger, for a warning on API failure

    **Return:**

    - ``dropboxUrl`` -- the folder's Dropbox share URL, or `None`
    """
    if not client or not dropboxRoot:
        return None

    cached = db.get_dropbox_link(dbConn, folderPath)
    if cached:
        return cached["dropbox_url"]

    dropboxPath = to_dropbox_path(folderPath, dropboxRoot)
    if not dropboxPath:
        return None

    try:
        url = client.shared_link(dropboxPath)
    except DropboxApiError as error:
        log.warning(f"dropbox share link failed for '{folderPath}': {error}")
        return None

    db.upsert_dropbox_link(dbConn, folderPath, url)
    return url

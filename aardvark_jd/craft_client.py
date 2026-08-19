#!/usr/bin/env python
# encoding: utf-8
"""
*Thin HTTP client for the craft.do API - folder, document and block creation/content*

There is no fixed global base URL for the Craft API - every API Connection
created in-app (Craft -> Connections tab) generates its own unique base URL
(shape `https://connect.craft.do/links/<connectionId>/api/v1`), paired with
its own token. Both must be supplied by the caller; aardvark cannot compute
either. Endpoint names/methods below (`/folders`, `/documents`, `/blocks`)
and request body shapes (each write is an array of items under a
plural top-level key, e.g. `{"folders": [...]}`) are confirmed against
Craft's public Space-API reference (`connect.craft.do/api-docs/space`);
some item-level fields (e.g. whether `icon` is honoured on folder
creation) are still a best-effort match, unconfirmed against a real
response - see `docs/source/quickstart.md`'s "Connecting to craft.do"
section.

Author
: David Young
"""

from urllib.parse import quote

import requests


class CraftApiError(Exception):
    pass


class CraftClient(object):
    """
    *a minimal client for the craft.do API, scoped to one space via one API connection*

    **Key Arguments:**

    - ``apiUrl`` -- the connection's unique API base URL, copied from Craft's Connections tab
    - ``apiToken`` -- the connection's API token, copied from the same screen

    **Usage:**

    ```python
    from aardvark_jd.craft_client import CraftClient
    client = CraftClient(apiUrl="https://connect.craft.do/links/abc123/api/v1", apiToken="pdk_...")
    folderId, url = client.create_folder("03 Areas", icon="🧭")
    ```
    """

    def __init__(self, apiUrl, apiToken):
        self.apiUrl = apiUrl
        self.apiToken = apiToken
        self.baseUrl = apiUrl.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {apiToken}",
            "Content-Type": "application/json",
        })
        self._connectionInfo = None

    def _request(self, method, path, **kwargs):
        """
        *issue an authenticated request against the Craft API, raising `CraftApiError` on failure*

        **Key Arguments:**

        - ``method`` -- the HTTP method, e.g. `"POST"`
        - ``path`` -- the request path, relative to `baseUrl`

        **Return:**

        - ``payload`` -- the parsed JSON response body
        """
        response = self._session.request(method, f"{self.baseUrl}{path}", **kwargs)
        if not response.ok:
            raise CraftApiError(f"craft API {method} {path} failed ({response.status_code}): {response.text}")
        if not response.content:
            return {}
        return response.json()

    @staticmethod
    def _first(payload):
        """
        *unwrap a response that may be a single object or a one-item list, either way*

        Craft's docs describe `/folders` and `/documents` as creating "one or
        more" at a time, so the response shape (bare object vs a list of
        created items) isn't confirmed - this accepts either.

        **Key Arguments:**

        - ``payload`` -- the parsed JSON response body

        **Return:**

        - ``item`` -- the single created item, as a dict
        """
        if isinstance(payload, list):
            return payload[0]
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return payload["items"][0]
        return payload

    def _connection_info(self):
        """
        *fetch and cache this space's connection metadata, including its deep-link URL templates*

        **Return:**

        - ``connectionInfo`` -- the parsed `GET /connection` response body
        """
        if self._connectionInfo is None:
            self._connectionInfo = self._request("GET", "/connection")
        return self._connectionInfo

    def _deep_link(self, itemId):
        """
        *build a shareable Craft URL for a folder, document or block id*

        Craft's `/folders` and `/documents` create-responses carry no URL of
        their own; `GET /connection` returns a `urlTemplates` object with a
        `{blockId}` placeholder that resolves any item id (folder, document
        or block) to a deep link into the space.

        **Key Arguments:**

        - ``itemId`` -- the created item's id

        **Return:**

        - ``url`` -- the item's deep-link URL, or `None` if no template was available
        """
        templates = self._connection_info().get("urlTemplates") or {}
        template = templates.get("web") or templates.get("app")
        if not template:
            return None
        return template.replace("{blockId}", itemId)

    def folder_deep_link(self, folderId, title):
        """
        *build a deep link that opens a folder in the Craft app*

        Folders are not addressable through the `urlTemplates` block link -
        they use a separate `openfolder` route, which Craft's API reference
        does not document at all (the format was read off a link copied from
        the app). Treat it as more fragile than `_deep_link`.

        **Key Arguments:**

        - ``folderId`` -- the folder's id, as reported by `list_folders`
        - ``title`` -- the folder's name, carried in the link for display

        **Return:**

        - ``url`` -- the folder's deep-link URL, or `None` if the space id was unavailable
        """
        spaceId = (self._connection_info().get("space") or {}).get("id")
        if not spaceId:
            return None
        return f"craftdocs://openfolder?folderId={quote(folderId)}&spaceId={quote(spaceId)}&title={quote(title)}"

    def list_folders(self):
        """
        *list every folder in the space, as a nested tree*

        Each item carries `id`, `name` and a `folders` list of its children.
        This is the only trustworthy source of folder ids - see
        `create_folder` for why.

        **Return:**

        - ``items`` -- the space's top-level folders, each with nested `folders`
        """
        return self._request("GET", "/folders").get("items") or []

    def create_folder(self, name, parentFolderId=None):
        """
        *create a Craft folder, optionally nested under an existing folder*

        The returned id resolves immediately, but is **not durable**: once the
        Craft app syncs the new folder it is re-keyed to a different permanent
        id, and this one stops resolving (verified against a live space -
        documents do not behave this way). Callers that need a lasting
        reference must re-resolve the folder through `list_folders` rather
        than storing this id. Craft's API has no folder icon/emoji field, so
        an emoji has to be carried in `name` itself.

        **Key Arguments:**

        - ``name`` -- the folder's name
        - ``parentFolderId`` -- the parent folder's id, or `None` for a top-level folder

        **Return:**

        - ``folderId`` -- the new folder's id, valid until the Craft app next syncs
        """
        folder = {"name": name}
        if parentFolderId is not None:
            folder["parentFolderId"] = parentFolderId
        item = self._first(self._request("POST", "/folders", json={"folders": [folder]}))
        return item["id"]

    def create_document(self, title, folderId=None):
        """
        *create a Craft document, inside a folder or left unfiled*

        **Key Arguments:**

        - ``title`` -- the document's title
        - ``folderId`` -- the containing folder's id, or `None` to leave it unfiled. Default `None`.

        **Return:**

        - ``documentId`` -- the new document's id
        - ``url`` -- the new document's shareable URL
        """
        body = {"documents": [{"title": title}]}
        if folderId is not None:
            body["destination"] = {"folderId": folderId}
        item = self._first(self._request("POST", "/documents", json=body))
        return item["id"], self._deep_link(item["id"])

    def add_block(self, documentId, markdown, position="end"):
        """
        *insert a new markdown block into a document, returning its block id*

        Used once per "00 Index" document, the first time it's created; use
        `update_block` on every later refresh instead of inserting again.

        **Key Arguments:**

        - ``documentId`` -- the containing document's id
        - ``markdown`` -- the block's content, as markdown
        - ``position`` -- `"start"` or `"end"`. Default `"end"`.

        **Return:**

        - ``blockId`` -- the new block's id
        """
        body = {
            "blocks": [{"type": "text", "markdown": markdown}],
            "position": {"pageId": documentId, "position": position},
        }
        item = self._first(self._request("POST", "/blocks", json=body))
        return item["id"]

    def update_block(self, blockId, markdown):
        """
        *overwrite an existing block's markdown content*

        **Key Arguments:**

        - ``blockId`` -- the block's id, as returned by `add_block`
        - ``markdown`` -- the block's new content, as markdown
        """
        self._request("PUT", "/blocks", json={"blocks": [{"id": blockId, "markdown": markdown}]})

#!/usr/bin/env python
# encoding: utf-8
"""
*Shared OAuth2 pieces - PKCE pairs, and a one-shot loopback listener for the redirect*

`connect_dropbox` was aardvark's first OAuth flow and deliberately omits
`redirect_uri` entirely, because Dropbox requires any redirect URI actually
used to be pre-registered in the App Console - something aardvark cannot do
on the user's behalf - and omitting it puts Dropbox into a copy-the-code
flow instead. Google has no such mode: a `redirect_uri` is mandatory. What
Google *does* allow, for an OAuth client of type "Desktop app", is any
`http://127.0.0.1:<port>` loopback address without pre-registration, which
is what `loopback_capture_code` below exploits - bind an ephemeral port,
serve exactly one request, take the code straight out of the query string.

Author
: David Young
"""

import base64
import hashlib
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

_SUCCESS_PAGE = b"""<!doctype html><html><head><meta charset="utf-8">
<title>aardvark</title></head><body style="font-family:sans-serif;padding:3rem">
<h1>Authorised</h1><p>aardvark has what it needs. You can close this window.</p>
</body></html>"""

_FAILURE_PAGE = b"""<!doctype html><html><head><meta charset="utf-8">
<title>aardvark</title></head><body style="font-family:sans-serif;padding:3rem">
<h1>Authorisation failed</h1><p>No authorisation code came back. Return to the
terminal and try again.</p></body></html>"""


def pkce_pair():
    """
    *mint a PKCE code verifier and its S256 challenge*

    **Return:**

    - ``codeVerifier``, ``codeChallenge`` -- the verifier to send at token exchange, and the S256 challenge to send at authorisation

    **Usage:**

    ```python
    from aardvark_jd.oauth import pkce_pair
    codeVerifier, codeChallenge = pkce_pair()
    ```
    """
    codeVerifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(codeVerifier.encode("ascii")).digest()
    codeChallenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return codeVerifier, codeChallenge


class _CallbackHandler(BaseHTTPRequestHandler):
    """*capture the `code` query parameter from the single redirect request, then stop*"""

    authCode = None
    errorMessage = None

    def do_GET(self):
        """*serve the one redirect request, stash the authorisation code and reply*"""
        query = parse_qs(urlparse(self.path).query)
        _CallbackHandler.authCode = (query.get("code") or [None])[0]
        _CallbackHandler.errorMessage = (query.get("error") or [None])[0]

        body = _SUCCESS_PAGE if _CallbackHandler.authCode else _FAILURE_PAGE
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """*silence the default stderr request logging*"""
        return


def loopback_capture_code(authorizeUrlBuilder, timeoutSeconds=180):
    """
    *open the browser at an authorisation URL and catch the redirected code on a loopback port*

    **Key Arguments:**

    - ``authorizeUrlBuilder`` -- a callable taking the chosen `redirectUri` and returning the full authorisation URL to open
    - ``timeoutSeconds`` -- how long to wait for the user to finish in the browser. Default *180*.

    **Return:**

    - ``authCode``, ``redirectUri`` -- the captured authorisation code, and the redirect URI it was issued against (needed again at token exchange)

    **Raises:**

    - ``ValueError`` -- if the user denied access, or nothing arrived before the timeout

    **Usage:**

    ```python
    from aardvark_jd.oauth import loopback_capture_code
    authCode, redirectUri = loopback_capture_code(lambda uri: f"https://example.com/auth?redirect_uri={uri}")
    ```
    """
    _CallbackHandler.authCode = None
    _CallbackHandler.errorMessage = None

    # PORT 0 LETS THE OS PICK A FREE EPHEMERAL PORT; GOOGLE ACCEPTS ANY
    # LOOPBACK PORT FOR A "DESKTOP APP" CLIENT, SO NOTHING NEEDS REGISTERING.
    server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    server.timeout = timeoutSeconds
    try:
        redirectUri = f"http://127.0.0.1:{server.server_port}/"
        authorizeUrl = authorizeUrlBuilder(redirectUri)

        print("opening your browser to authorise aardvark ...")
        print(f"if it doesn't open, visit:\n\n{authorizeUrl}\n")
        webbrowser.open(authorizeUrl)

        server.handle_request()
    finally:
        server.server_close()

    if _CallbackHandler.errorMessage:
        raise ValueError(f"authorisation was refused: {_CallbackHandler.errorMessage}")
    if not _CallbackHandler.authCode:
        raise ValueError("no authorisation code came back from the browser - please try again")
    return _CallbackHandler.authCode, redirectUri

#!/usr/bin/env python
# encoding: utf-8
"""
*One-time Dropbox PKCE authorisation, exchanging a pasted auth code for a long-lived refresh token*

Dropbox access tokens expire after 4 hours, so `craft_sync`'s Dropbox
integration is built on a refresh token instead - minted once here via
the OAuth2 PKCE flow (`token_access_type=offline` is what makes Dropbox
hand back a refresh token at all) and stored in the user settings file
alongside the connecting app's key/secret.

`redirect_uri` is deliberately omitted from both the authorise URL and
the token exchange, rather than pointed at some fixed aardvark-chosen
value: Dropbox requires any redirect URI actually used to be
pre-registered against the connecting app in the App Console, which
aardvark has no way to do on the user's behalf. Omitting it entirely
puts Dropbox into its "no redirect" flow instead, where the
authorisation page displays the code directly for the user to copy -
exactly what this flow already prompts for.

Author
: David Young
"""

import base64
import hashlib
import secrets
import sys
import webbrowser

import requests

from aardvark_jd import settings_writer

_AUTHORIZE_URL = "https://www.dropbox.com/oauth2/authorize"
_TOKEN_URL = "https://api.dropbox.com/oauth2/token"


class connect_dropbox(object):
    """
    *authorise a Dropbox app via PKCE and persist a long-lived refresh token to the user settings*

    **Key Arguments:**

    - ``log`` -- logger
    - ``appKey`` -- the Dropbox app's key, from the App Console
    - ``appSecret`` -- the Dropbox app's secret, from the App Console
    - ``pathToSettingsFile`` -- path to the aardvark user settings YAML file

    **Usage:**

    ```python
    from aardvark_jd.connect_dropbox import connect_dropbox
    connect_dropbox(
        log=log, appKey="...", appSecret="...", pathToSettingsFile="~/.config/aardvark/aardvark.yaml",
    ).get()
    ```
    """

    def __init__(self, log, appKey, appSecret, pathToSettingsFile):
        self.log = log
        self.appKey = appKey
        self.appSecret = appSecret
        self.pathToSettingsFile = pathToSettingsFile

    def get(self):
        """
        *run the PKCE flow end-to-end and persist the resulting refresh token*

        **Return:**

        - ``refreshToken`` -- the newly-minted long-lived refresh token
        """
        self.log.debug("starting the ``get`` method")

        if not sys.stdin.isatty():
            raise ValueError("connect_dropbox requires an interactive terminal to complete the browser authorisation")

        codeVerifier, codeChallenge = self._pkce_pair()
        authorizeUrl = (
            f"{_AUTHORIZE_URL}?client_id={self.appKey}&response_type=code"
            f"&code_challenge={codeChallenge}&code_challenge_method=S256"
            f"&token_access_type=offline"
        )
        print(f"opening Dropbox authorisation page - if it doesn't open automatically, visit:\n{authorizeUrl}")
        webbrowser.open(authorizeUrl)
        authCode = input("paste the authorisation code shown by Dropbox: ").strip()

        refreshToken = self._exchange_code(authCode, codeVerifier)
        self._update_settings(refreshToken)

        self.log.debug("completed the ``get`` method")
        return refreshToken

    def _pkce_pair(self):
        """
        *generate a PKCE code verifier and its S256 challenge*

        **Return:**

        - ``codeVerifier``, ``codeChallenge`` -- the PKCE pair
        """
        codeVerifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        digest = hashlib.sha256(codeVerifier.encode()).digest()
        codeChallenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return codeVerifier, codeChallenge

    def _exchange_code(self, authCode, codeVerifier):
        """
        *exchange the pasted authorisation code for a refresh token*

        **Key Arguments:**

        - ``authCode`` -- the authorisation code pasted by the user
        - ``codeVerifier`` -- the PKCE code verifier generated for this flow

        **Return:**

        - ``refreshToken`` -- the long-lived refresh token
        """
        response = requests.post(
            _TOKEN_URL,
            data={
                "code": authCode,
                "grant_type": "authorization_code",
                "client_id": self.appKey,
                "client_secret": self.appSecret,
                "code_verifier": codeVerifier,
            },
        )
        if not response.ok:
            raise ValueError(f"dropbox authorisation failed ({response.status_code}): {response.text}")
        payload = response.json()
        refreshToken = payload.get("refresh_token")
        if not refreshToken:
            raise ValueError(
                "dropbox did not return a refresh token - check the app is configured for offline access"
            )
        return refreshToken

    def _update_settings(self, refreshToken):
        """
        *persist the connected Dropbox app's credentials to the user settings YAML file*

        **Key Arguments:**

        - ``refreshToken`` -- the newly-minted long-lived refresh token
        """
        settings = settings_writer.read_settings(self.pathToSettingsFile)
        settings.setdefault("dropbox", {})
        settings["dropbox"]["enabled"] = True
        settings["dropbox"]["app_key"] = self.appKey
        settings["dropbox"]["app_secret"] = self.appSecret
        settings["dropbox"]["refresh_token"] = refreshToken
        settings_writer.write_settings(self.pathToSettingsFile, settings)

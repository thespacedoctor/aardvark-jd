#!/usr/bin/env python
# encoding: utf-8
"""
*One-time Google Drive authorisation, exchanging a loopback-captured auth code for a refresh token*

Google access tokens are short-lived, so - as with Dropbox - the durable
credential aardvark stores is a refresh token, minted once here and kept in
the user settings file alongside the connecting OAuth client's id and
secret. `access_type=offline` is what makes Google return a refresh token
at all, and `prompt=consent` forces it to be re-issued even if the user has
authorised this client before (Google only sends a refresh token on the
first consent otherwise, so a re-run would silently store nothing).

The scope defaults to full `drive` rather than the narrower `drive.file`.
That is a deliberate trade: `drive.file` only ever shows an app the files it
created itself, which would make it impossible to adopt a folder the user
made by hand - and adopting whatever is already in place, rather than
duplicating it, is exactly what `gdrive_sync` is built to do. The cost is a
one-off "unverified app" warning on the consent screen for a personal OAuth
client. Narrow it via the `gdrive.scope` setting if that trade is not worth
it, accepting that hand-made folders then become invisible.

Author
: David Young
"""

import sys
from urllib.parse import urlencode

import requests

from aardvark_jd import oauth, settings_writer

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DEFAULT_SCOPE = "https://www.googleapis.com/auth/drive"


class connect_gdrive(object):
    """
    *authorise a Google Drive account via a loopback OAuth flow and persist a refresh token*

    **Key Arguments:**

    - ``log`` -- logger
    - ``clientId`` -- the Google Cloud OAuth "Desktop app" client ID
    - ``clientSecret`` -- the matching client secret
    - ``pathToSettingsFile`` -- path to the aardvark user settings YAML file

    **Usage:**

    ```python
    from aardvark_jd.connect_gdrive import connect_gdrive
    connect_gdrive(
        log=log, clientId="...", clientSecret="...",
        pathToSettingsFile="~/.config/aardvark/aardvark.yaml",
    ).get()
    ```
    """

    def __init__(self, log, clientId, clientSecret, pathToSettingsFile):
        self.log = log
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.pathToSettingsFile = pathToSettingsFile

    def get(self):
        """
        *run the one-time authorisation and store the resulting refresh token*

        **Return:**

        - ``refreshToken`` -- the long-lived Google refresh token

        **Raises:**

        - ``ValueError`` -- if there is no terminal to prompt at, or Google returns no refresh token
        """
        self.log.debug("starting the ``get`` method")

        if not sys.stdin.isatty():
            raise ValueError(
                "connect_gdrive needs an interactive terminal - run it directly rather than in a pipe"
            )

        settings = settings_writer.read_settings(self.pathToSettingsFile) or {}
        scope = (settings.get("gdrive") or {}).get("scope") or _DEFAULT_SCOPE

        codeVerifier, codeChallenge = oauth.pkce_pair()

        def build_url(redirectUri):
            return _AUTHORIZE_URL + "?" + urlencode({
                "client_id": self.clientId,
                "redirect_uri": redirectUri,
                "response_type": "code",
                "scope": scope,
                "access_type": "offline",
                "prompt": "consent",
                "code_challenge": codeChallenge,
                "code_challenge_method": "S256",
            })

        authCode, redirectUri = oauth.loopback_capture_code(build_url)
        refreshToken = self._exchange_code(authCode, codeVerifier, redirectUri)
        self._update_settings(refreshToken, scope)

        self.log.debug("completed the ``get`` method")
        return refreshToken

    def _exchange_code(self, authCode, codeVerifier, redirectUri):
        """
        *trade the one-time authorisation code for a long-lived refresh token*

        **Key Arguments:**

        - ``authCode`` -- the code captured from the loopback redirect
        - ``codeVerifier`` -- the PKCE verifier matching the challenge sent at authorisation
        - ``redirectUri`` -- the same redirect URI the code was issued against

        **Return:**

        - ``refreshToken`` -- the long-lived refresh token

        **Raises:**

        - ``ValueError`` -- if the exchange fails, or carries no refresh token
        """
        response = requests.post(_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": authCode,
            "client_id": self.clientId,
            "client_secret": self.clientSecret,
            "redirect_uri": redirectUri,
            "code_verifier": codeVerifier,
        })
        if not response.ok:
            raise ValueError(
                f"google token exchange failed ({response.status_code}): {response.text}"
            )
        refreshToken = response.json().get("refresh_token")
        if not refreshToken:
            raise ValueError(
                "google returned no refresh token - revoke aardvark's access at "
                "https://myaccount.google.com/permissions and run connect_gdrive again"
            )
        return refreshToken

    def _update_settings(self, refreshToken, scope):
        """
        *write the Drive credentials back to the user settings file*

        **Key Arguments:**

        - ``refreshToken`` -- the long-lived refresh token
        - ``scope`` -- the scope the token was granted against
        """
        settings = settings_writer.read_settings(self.pathToSettingsFile) or {}
        settings.setdefault("gdrive", {})
        settings["gdrive"]["enabled"] = True
        settings["gdrive"]["client_id"] = self.clientId
        settings["gdrive"]["client_secret"] = self.clientSecret
        settings["gdrive"]["refresh_token"] = refreshToken
        settings["gdrive"]["scope"] = scope
        settings_writer.write_settings(self.pathToSettingsFile, settings)

"""
load/auth.py — Shared OAuth2 credentials for Drive and Gmail.

Single token file (config.OAUTH_TOKEN_PATH) covers both services.
Combined scopes so one authorization grants access to both.
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import OAUTH_CLIENT_SECRETS, OAUTH_TOKEN_PATH

_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]

_credentials: Credentials | None = None


def get_credentials() -> Credentials:
    """
    Returns valid OAuth2 credentials covering Drive and Gmail.
    Loads from token file, refreshes if expired, runs browser flow if needed.
    Token saved to OAUTH_TOKEN_PATH after any change.
    """
    global _credentials
    if _credentials and _credentials.valid:
        return _credentials

    creds = None
    if os.path.exists(OAUTH_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(OAUTH_TOKEN_PATH, _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  [auth] Refreshing OAuth token...")
            creds.refresh(Request())
        else:
            print("  [auth] Opening browser for Google authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_SECRETS, _SCOPES)
            creds = flow.run_local_server(port=0)

        with open(OAUTH_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print("  [auth] Token saved.")

    _credentials = creds
    return creds

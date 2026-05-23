"""
load/gmail.py — Email the weekly analysis report via Gmail API.

Auth: OAuth2 credentials (Desktop app type) stored in
      ./credentials/gmail_oauth_credentials.json
On first run, opens a browser window for authorization.
Token saved to ./credentials/gmail_token.json for subsequent runs.

Setup in Google Cloud Console:
  1. Enable the Gmail API on your project.
  2. APIs & Services → Credentials → Create Credentials → OAuth client ID
     → Application type: Desktop app → Download JSON
  3. Save the downloaded file as ./credentials/gmail_oauth_credentials.json
  4. Add GMAIL_RECIPIENT to .env (the address to send weekly reports to).
"""

import base64
import os
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import GMAIL_RECIPIENT, GMAIL_CREDENTIALS_JSON, GMAIL_TOKEN_PATH

_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _get_service():
    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_JSON, _SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_weekly_report(week_label: str, markdown_content: str) -> None:
    """
    Emails the weekly fitness report to GMAIL_RECIPIENT.
    Silently skips if GMAIL_RECIPIENT or credentials are not configured.
    """
    if not GMAIL_RECIPIENT:
        print("  [gmail] GMAIL_RECIPIENT not set — skipping email delivery.")
        return

    if not os.path.exists(GMAIL_CREDENTIALS_JSON):
        print(f"  [gmail] OAuth credentials not found at {GMAIL_CREDENTIALS_JSON} — skipping.")
        return

    svc = _get_service()

    subject = f"Fitness Review — {week_label}"
    message = MIMEText(markdown_content, "plain", "utf-8")
    message["to"] = GMAIL_RECIPIENT
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"  [gmail] Weekly report emailed → {GMAIL_RECIPIENT}")

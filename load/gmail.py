"""
load/gmail.py — Email the weekly analysis report via Gmail API.

Auth: shared OAuth2 token via load.auth (covers Drive + Gmail together).
First run opens a browser for authorization; token reused automatically after.
"""

import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from load.auth import get_credentials
from config import EMAIL_RECIPIENT


def send_weekly_report(week_label: str, markdown_content: str) -> None:
    """
    Emails the weekly fitness report to EMAIL_RECIPIENT.
    Silently skips if EMAIL_RECIPIENT is not configured.
    """
    if not EMAIL_RECIPIENT:
        print("  [gmail] EMAIL_RECIPIENT not set — skipping email delivery.")
        return

    svc = build("gmail", "v1", credentials=get_credentials())

    subject = f"Fitness Review — {week_label}"
    message = MIMEText(markdown_content, "plain", "utf-8")
    message["to"] = EMAIL_RECIPIENT
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"  [gmail] Weekly report emailed to {EMAIL_RECIPIENT}")

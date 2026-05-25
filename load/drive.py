"""
load/drive.py — Append new rows to master CSVs on Google Drive.

Append logic:
1. Download existing file from Drive (if it exists).
2. Load into memory, extract existing primary keys.
3. Filter incoming records to only net-new PKs.
4. Append new rows to the CSV content.
5. Upload the full updated file back to Drive (overwrite).

This makes the operation idempotent: re-running for the same date range
produces the same result — no duplicates.

Auth: Google Service Account. Create one in Google Cloud Console:
  IAM & Admin → Service Accounts → Create → download JSON key
  Share your Drive folder with the service account email.
"""

import csv
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from config import GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FOLDER_ID
from transform.normalize import get_columns

_SCOPES = ["https://www.googleapis.com/auth/drive"]
_MIME_CSV = "text/csv"

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES
        )
        _service = build("drive", "v3", credentials=creds)
    return _service


def _find_file_id(filename: str, folder_id: str) -> str | None:
    """Returns Drive file ID if file exists in folder, else None."""
    svc = _get_service()
    query = (
        f"name='{filename}' and "
        f"'{folder_id}' in parents and "
        f"trashed=false"
    )
    results = svc.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def _download_csv(file_id: str) -> list[dict]:
    """Downloads a CSV from Drive and returns list of row dicts."""
    svc = _get_service()
    buffer = io.BytesIO()
    request = svc.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    reader = csv.DictReader(io.StringIO(buffer.read().decode("utf-8")))
    return list(reader)


def _upload_csv(
    filename: str,
    folder_id: str,
    rows: list[dict],
    columns: list[str],
    file_id: str | None
) -> str:
    """
    Uploads rows as CSV to Drive. Overwrites if file_id provided, creates if not.
    Returns the file_id.
    """
    svc = _get_service()

    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)

    content = output.getvalue().encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=_MIME_CSV, resumable=False)

    if file_id:
        svc.files().update(fileId=file_id, media_body=media).execute()
        return file_id
    else:
        metadata = {"name": filename, "parents": [folder_id]}
        result = svc.files().create(
            body=metadata, media_body=media, fields="id"
        ).execute()
        return result["id"]


def append_to_master(source: str, new_records: list[dict], filename: str) -> int:
    """
    Appends new_records to the master CSV for a source on Drive.
    Returns count of rows actually appended (net-new only).

    source: one of "activities", "sleep", "daily", "dayone"
    new_records: normalized list of dicts
    filename: Drive file name (from config.DRIVE_FILES)
    """
    if not new_records:
        print(f"  [drive] {source}: no records to append.")
        return 0

    columns = get_columns(source)

    # Determine primary key for dedup
    pk_map = {
        "activities": "activity_id",
        "sleep":      "date",
        "daily":      "date",
        "dayone":     "entry_id",
    }
    pk = pk_map[source]

    # Check for existing file and load it
    file_id = _find_file_id(filename, GOOGLE_DRIVE_FOLDER_ID)
    existing_rows = []
    existing_pks = set()

    if file_id:
        try:
            existing_rows = _download_csv(file_id)
            existing_pks = {row.get(pk) for row in existing_rows if row.get(pk)}
        except Exception as e:
            print(f"  [drive] Warning: could not download existing {filename}: {e}")
            existing_rows = []
            existing_pks = set()

    # Filter to net-new records only
    net_new = [
        r for r in new_records
        if str(r.get(pk, "")) not in existing_pks
    ]

    if not net_new:
        print(f"  [drive] {source}: 0 net-new rows (all already exist). Skipping upload.")
        return 0

    # Merge and upload
    # Convert existing rows to match column schema (fill missing cols with None)
    all_rows = existing_rows + [
        {col: r.get(col) for col in columns} for r in net_new
    ]

    _upload_csv(filename, GOOGLE_DRIVE_FOLDER_ID, all_rows, columns, file_id)
    print(f"  [drive] {source}: appended {len(net_new)} rows → {filename}")
    return len(net_new)


def upload_analysis_report(week_label: str, markdown_content: str) -> None:
    """
    Uploads the weekly narrative report as a .md file to Drive.
    File name: analysis_YYYY-WW.md
    Creates a 'weekly_reports' subfolder if it doesn't exist.
    """
    svc = _get_service()
    filename = f"analysis_{week_label}.md"

    # Find or create weekly_reports subfolder
    subfolder_id = _find_or_create_subfolder("weekly_reports")

    file_id = _find_file_id(filename, subfolder_id)
    content = markdown_content.encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="text/markdown", resumable=False)

    if file_id:
        svc.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": filename, "parents": [subfolder_id]}
        svc.files().create(body=metadata, media_body=media, fields="id").execute()

    print(f"  [drive] Analysis report uploaded → {filename}")


def _find_or_create_subfolder(name: str) -> str:
    """Returns folder ID of subfolder within the main Drive folder. Creates if absent."""
    svc = _get_service()
    query = (
        f"name='{name}' and "
        f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )
    results = svc.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [GOOGLE_DRIVE_FOLDER_ID],
    }
    folder = svc.files().create(body=metadata, fields="id").execute()
    return folder["id"]

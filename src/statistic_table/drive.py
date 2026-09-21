from __future__ import annotations

from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from statistic_table.config import Config, get_credentials


def list_pdf_files(config: Config) -> list[dict]:
    service = build("drive", "v3", credentials=get_credentials(config))
    query = (
        f"'{config.drive_folder_id}' in parents "
        "and mimeType='application/pdf' and trashed=false"
    )
    result = (
        service.files()
        .list(q=query, fields="files(id, name)", pageSize=1000)
        .execute()
    )
    return result.get("files", [])


def download_file(config: Config, file_id: str, destination: str | Path) -> Path:
    service = build("drive", "v3", credentials=get_credentials(config))
    request = service.files().get_media(fileId=file_id)
    destination = Path(destination)
    with destination.open("wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
    return destination

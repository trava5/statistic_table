from __future__ import annotations

from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

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


def find_or_create_folder(config: Config, parent_id: str, name: str) -> str:
    """Vrátí ID podsložky `name` v `parent_id`; založí ji, pokud chybí (viz
    pre-scout, PLAN.MD 20. 10. 2026). Název se hledá přesně – Drive samo
    duplicitní jména nezakazuje, proto se nejdřív ověří existující shoda,
    ať opakované spuštění pro stejný tým nezaloží druhou složku navíc."""
    service = build("drive", "v3", credentials=get_credentials(config))
    escaped_name = name.replace("'", "\\'")
    query = (
        f"'{parent_id}' in parents and name='{escaped_name}' "
        "and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    existing = service.files().list(q=query, fields="files(id)", pageSize=1).execute().get(
        "files", []
    )
    if existing:
        return existing[0]["id"]
    folder = (
        service.files()
        .create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
            fields="id",
        )
        .execute()
    )
    return folder["id"]


def upload_file(
    config: Config, folder_id: str, local_path: str | Path, mime_type: str
) -> str:
    """Nahraje `local_path` do složky `folder_id`, vrátí ID souboru. Pokud ve
    složce už existuje soubor se stejným jménem, přepíše jeho obsah (ne
    druhý soubor stejného jména navíc) – opakovaný pre-scout pro stejný tým
    tak staré klipy nahradí, nekumuluje je."""
    service = build("drive", "v3", credentials=get_credentials(config))
    local_path = Path(local_path)
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

    escaped_name = local_path.name.replace("'", "\\'")
    query = f"'{folder_id}' in parents and name='{escaped_name}' and trashed=false"
    existing = service.files().list(q=query, fields="files(id)", pageSize=1).execute().get(
        "files", []
    )
    if existing:
        file_id = existing[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id

    created = (
        service.files()
        .create(
            body={"name": local_path.name, "parents": [folder_id]},
            media_body=media,
            fields="id",
        )
        .execute()
    )
    return created["id"]

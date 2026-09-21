from __future__ import annotations

from googleapiclient.discovery import build

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

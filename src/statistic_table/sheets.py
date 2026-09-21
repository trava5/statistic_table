from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import Config, get_credentials


def read_range(config: Config, range_: str) -> list[list[str]]:
    service = build("sheets", "v4", credentials=get_credentials(config))
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=config.spreadsheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])

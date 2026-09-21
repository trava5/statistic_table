from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SESTAVY_COLUMNS,
    SESTAVY_HEADER_ROW,
    SESTAVY_SHEET,
    SEZNAM_HRACU_DATA_START_ROW,
    SEZNAM_HRACU_SHEET,
    ZAPASY_COLUMNS,
    ZAPASY_HEADER_ROW,
    ZAPASY_SHEET,
    ColumnGroup,
    Config,
    col_to_index,
    get_credentials,
)
from statistic_table.model import RosterPlayer


def read_range(config: Config, range_: str) -> list[list[str]]:
    service = build("sheets", "v4", credentials=get_credentials(config))
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=config.spreadsheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])


def header_mismatches(
    sheet: str,
    header_row_values: list[str],
    columns: dict[str, ColumnGroup],
    header_row: int,
) -> list[str]:
    """Čistá funkce (bez sítě): porovná načtený řádek záhlaví s očekávanými hodnotami."""
    mismatches = []
    for group in columns.values():
        if group.header is None:
            continue
        idx = col_to_index(group.start)
        actual = header_row_values[idx] if idx < len(header_row_values) else ""
        if actual != group.header:
            cell = f"{sheet}!{group.start}{header_row}"
            mismatches.append(f"{cell}: očekáváno {group.header!r}, nalezeno {actual!r}")
    return mismatches


def check_headers(config: Config) -> None:
    errors: list[str] = []
    for sheet, columns, header_row in (
        (ZAPASY_SHEET, ZAPASY_COLUMNS, ZAPASY_HEADER_ROW),
        (SESTAVY_SHEET, SESTAVY_COLUMNS, SESTAVY_HEADER_ROW),
    ):
        last_col = max(columns.values(), key=lambda g: col_to_index(g.end)).end
        values = read_range(config, f"{sheet}!A{header_row}:{last_col}{header_row}")
        row = values[0] if values else []
        errors.extend(header_mismatches(sheet, row, columns, header_row))

    if errors:
        raise RuntimeError(
            "Rozložení tabulky neodpovídá očekávání, import odmítnut:\n" + "\n".join(errors)
        )


def read_player_registry(config: Config) -> list[RosterPlayer]:
    values = read_range(
        config, f"{SEZNAM_HRACU_SHEET}!A{SEZNAM_HRACU_DATA_START_ROW}:F1000"
    )
    players = []
    for row in values:
        last_name = row[1] if len(row) > 1 else ""
        if not last_name:
            continue
        players.append(
            RosterPlayer(
                last_name=last_name,
                first_name=row[2] if len(row) > 2 else "",
                registration_number=row[3] if len(row) > 3 else "",
                jersey_number=row[4] if len(row) > 4 else "",
                position=row[5] if len(row) > 5 else "",
            )
        )
    return players

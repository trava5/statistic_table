from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    IMPORT_LOG_DATA_START_ROW,
    IMPORT_LOG_HEADER,
    IMPORT_LOG_HEADER_ROW,
    IMPORT_LOG_SHEET,
    SESTAVY_COLUMNS,
    SESTAVY_HEADER_ROW,
    SESTAVY_SHEET,
    SEZNAM_HRACU_DATA_START_ROW,
    SEZNAM_HRACU_SHEET,
    ZAPASY_COLUMNS,
    ZAPASY_DATA_START_ROW,
    ZAPASY_HEADER_ROW,
    ZAPASY_SHEET,
    ColumnGroup,
    Config,
    col_to_index,
    get_credentials,
)
from statistic_table.model import ImportLogEntry, RosterPlayer

# Kontrolní sloupce, které se po zápisu čtou a hlásí ve výpisu (PLAN.MD Krok 5).
CHECK_CELLS = {
    "kontrola jmen (Zápasy)": (ZAPASY_SHEET, "AP"),
    "kontrola tresty (Zápasy)": (ZAPASY_SHEET, "CA"),
    "kontrola ročníky (Zápasy)": (ZAPASY_SHEET, "CQ"),
    "kontrola jmen (Sestavy)": (SESTAVY_SHEET, "AC"),
}


def read_range(
    config: Config, range_: str, spreadsheet_id: str | None = None
) -> list[list[str]]:
    """Bez `spreadsheet_id` čte z produkční tabulky (`config.spreadsheet_id`)."""
    service = build("sheets", "v4", credentials=get_credentials(config))
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id or config.spreadsheet_id, range=range_)
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


def find_or_create_row(config: Config, date: str, home: str, away: str) -> int:
    """Řádek existujícího zápasu (shoda datum+home+away), jinak první volný od 6."""
    values = read_range(config, f"{ZAPASY_SHEET}!A{ZAPASY_DATA_START_ROW}:C1000")
    first_free_offset = None
    for offset, row in enumerate(values):
        row_date = row[0] if len(row) > 0 else ""
        row_home = row[1] if len(row) > 1 else ""
        row_away = row[2] if len(row) > 2 else ""
        if row_date == date and row_home == home and row_away == away:
            return ZAPASY_DATA_START_ROW + offset
        if not row_date and first_free_offset is None:
            first_free_offset = offset
    if first_free_offset is not None:
        return ZAPASY_DATA_START_ROW + first_free_offset
    return ZAPASY_DATA_START_ROW + len(values)


def write_batch(config: Config, spreadsheet_id: str, updates: dict[str, list]) -> None:
    """Zapíše všechny rozsahy jedním batchUpdate (vzorce v ostatních buňkách
    zůstávají nedotčené, protože se zapisují jen explicitně vyjmenované rozsahy)."""
    service = build("sheets", "v4", credentials=get_credentials(config))
    data = [{"range": range_, "values": [values]} for range_, values in updates.items()]
    body = {"valueInputOption": "USER_ENTERED", "data": data}
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def read_checks(config: Config, row: int) -> dict[str, str]:
    """Přečte kontrolní sloupce pro daný řádek (viz CHECK_CELLS)."""
    results = {}
    for label, (sheet, col) in CHECK_CELLS.items():
        values = read_range(config, f"{sheet}!{col}{row}")
        results[label] = values[0][0] if values and values[0] else ""
    return results


def ensure_import_log_sheet(config: Config, spreadsheet_id: str) -> None:
    """Založí skrytý list Import log (s hlavičkou) v dané tabulce, pokud ještě
    neexistuje. Parametrizováno tabulkou (ne natvrdo `config.spreadsheet_id`) –
    od LIT Seznamy 2.0 žije Import log v Seznamy DB, ne v produkční tabulce."""
    service = build("sheets", "v4", credentials=get_credentials(config))
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    titles = {s["properties"]["title"] for s in meta["sheets"]}
    if IMPORT_LOG_SHEET in titles:
        return
    body = {
        "requests": [
            {"addSheet": {"properties": {"title": IMPORT_LOG_SHEET, "hidden": True}}}
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    header_range = f"{IMPORT_LOG_SHEET}!A{IMPORT_LOG_HEADER_ROW}:E{IMPORT_LOG_HEADER_ROW}"
    write_batch(config, spreadsheet_id, {header_range: IMPORT_LOG_HEADER})


def read_import_log(config: Config, spreadsheet_id: str) -> list[ImportLogEntry]:
    values = read_range(
        config,
        f"{IMPORT_LOG_SHEET}!A{IMPORT_LOG_DATA_START_ROW}:E1000000",
        spreadsheet_id=spreadsheet_id,
    )
    entries = []
    for row in values:
        file_id = row[0] if len(row) > 0 else ""
        if not file_id:
            continue
        entries.append(
            ImportLogEntry(
                file_id=file_id,
                checksum=row[1] if len(row) > 1 else "",
                game_number=row[2] if len(row) > 2 else "",
                imported_at=row[3] if len(row) > 3 else "",
                result=row[4] if len(row) > 4 else "",
            )
        )
    return entries


def append_import_log(
    config: Config, spreadsheet_id: str, entries: list[ImportLogEntry]
) -> None:
    if not entries:
        return
    service = build("sheets", "v4", credentials=get_credentials(config))
    values = [
        [e.file_id, e.checksum, e.game_number, e.imported_at, e.result] for e in entries
    ]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{IMPORT_LOG_SHEET}!A{IMPORT_LOG_DATA_START_ROW}",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


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

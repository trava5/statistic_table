"""Jednorázový skript: v Liga 2.0 (`LEAGUE_V2_SPREADSHEET_ID`) doplní na list
`Pořadí - liga` čitelný přehled vedle syrového IMPORTRANGE mirroru z DB.

Mirror v A1:D5000 (viz `build_league_v2_mirrors.py`) je dlouhý formát – jeden
řádek = jeden tým v jednom kole, obě skupiny (8+8 týmů) prostě za sebou. Pro
čtení „od oka“ je to nepřehledné, proto se sem přidávají:

- pomocný sloupec F (`skupina`) – `INDEX/MATCH` proti `Skupiny - liga`
  (skupina týmu se v sezóně nemění, takže stačí prosté vyhledání podle jména);
- dvě samostatné `QUERY` tabulky vedle sebe (Skupina 1 ve sloupcích H:J,
  Skupina 2 ve sloupcích L:N), obě filtrované přes sloupec F.

Nic z toho nezasahuje do A1:D5000 (vlastní IMPORTRANGE) ani do listu v DB –
čistě přídavná vzorcová vrstva v Liga 2.0.

Použití:
    .venv\\Scripts\\python.exe scripts\\build_league_poradi_view.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_PORADI_SHEET,
    LEAGUE_SKUPINY_SHEET,
    get_credentials,
    load_config,
    require_league_v2_spreadsheet_id,
)

ROWS = 5000
SK = f"'{LEAGUE_SKUPINY_SHEET}'"


def main() -> None:
    config = load_config()
    spreadsheet_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = next(
        s["properties"]["sheetId"]
        for s in meta["sheets"]
        if s["properties"]["title"] == LEAGUE_PORADI_SHEET
    )

    data = [
        {"range": f"'{LEAGUE_PORADI_SHEET}'!F1", "values": [["skupina"]]},
        {
            "range": f"'{LEAGUE_PORADI_SHEET}'!F2",
            "values": [[
                f"=ARRAYFORMULA(IF($A$2:$A${ROWS}=\"\";\"\";"
                f"IFNA(INDEX({SK}!$B:$B;MATCH($C$2:$C${ROWS};{SK}!$A:$A;0)))))"
            ]],
        },
        {"range": f"'{LEAGUE_PORADI_SHEET}'!H1", "values": [["SKUPINA 1"]]},
        {
            "range": f"'{LEAGUE_PORADI_SHEET}'!H2",
            "values": [[
                # Bez "and A <> ''" – sloupec A je číselný, porovnání s prázdným
                # řetězcem u číselného typu QUERY vždy vyhodnotí jako nepravdu
                # a vrátí 0 řádků. Filtr "F = 1" prázdné (nedoimportované) řádky
                # stejně vyloučí sám (tam je F prázdné, ne 1/2).
                f"=QUERY($A$1:$F${ROWS};\"select A, C, D where F = 1 "
                f"order by A asc, D asc label A 'Kolo', C 'Tým', D 'Pořadí'\";1)"
            ]],
        },
        {"range": f"'{LEAGUE_PORADI_SHEET}'!L1", "values": [["SKUPINA 2"]]},
        {
            "range": f"'{LEAGUE_PORADI_SHEET}'!L2",
            "values": [[
                f"=QUERY($A$1:$F${ROWS};\"select A, C, D where F = 2 "
                f"order by A asc, D asc label A 'Kolo', C 'Tým', D 'Pořadí'\";1)"
            ]],
        },
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 7,
                            "endColumnIndex": 14,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 5,
                            "endIndex": 6,
                        },
                        "properties": {"hiddenByUser": True},
                        "fields": "hiddenByUser",
                    }
                },
            ]
        },
    ).execute()
    print(f"Přehled Skupina 1 / Skupina 2 doplněn na list '{LEAGUE_PORADI_SHEET}'.")


if __name__ == "__main__":
    main()

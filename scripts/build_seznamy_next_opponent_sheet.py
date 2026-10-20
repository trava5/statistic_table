"""Jednorázový skript: postaví list `Příští soupeř` v SEZNAMY_V2_SPREADSHEET_ID
(„HC LIT jun 2026/27“) – zrcadlí přes `IMPORTRANGE` celý list daného soupeře
z Liga 2.0 (`LEAGUE_V2_SPREADSHEET_ID`), stejné hodnoty, jaké by trenér viděl,
kdyby si tu kartu otevřel přímo v Liga 2.0.

Název týmu (musí přesně odpovídat názvu listu v Liga 2.0) se čte z buňky
`SEZNAMY_NEXT_OPPONENT_TEAM_CELL` (B1) – tu přepisuje `cli pre-scout`/menu
`main.py` při každém výběru příštího soupeře (viz `prescout`, PLAN.MD).
Druhý argument `IMPORTRANGE` je proto sestavený jako dynamický řetězec
(`"'" & B1 & "'!A1:X120"`), ne napevno – stejný princip jako dynamické
`QUERY` jinde v projektu (`"where B = '" & $B$1 & "'"` u Liga 2.0 team
template), jen pro `IMPORTRANGE`.

`IMPORTRANGE` kopíruje jen VYPOČÍTANÉ HODNOTY buněk, ne grafy (vlastní
objekty, ne data) – 3 grafy z karty týmu (Skóre po zápasech/po třetinách,
Pořadí v tabulce) se proto na „Příští soupeř“ nezobrazí, jen číselné
přehledy (Sezónní přehled, Přesilovky/oslabení, Vyloučení a TM, Odehrané
zápasy, Bodování, Brankáři). Vedlejší efekt, který tenhle přístup řeší bez
rizika rozbitých vzorců: přímé zkopírování listu (`copyTo`) by grafy
zachovalo, ale QUERY/SUMIF vzorce uvnitř by ukazovaly #REF! (odkazují na
listy Zápasy - liga (tým)/Skupiny - liga, které v „HC LIT jun 2026/27“
neexistují) – IMPORTRANGE se naopak žádné formule nedotýká, jen čte její
výsledek.

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_next_opponent_sheet.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAMY_NEXT_OPPONENT_SHEET,
    SEZNAMY_NEXT_OPPONENT_TEAM_CELL,
    get_credentials,
    load_config,
    require_league_v2_spreadsheet_id,
    require_seznamy_v2_spreadsheet_id,
)


def main() -> None:
    config = load_config()
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    league_v2_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    if SEZNAMY_NEXT_OPPONENT_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {"addSheet": {"properties": {"title": SEZNAMY_NEXT_OPPONENT_SHEET}}}
                ]
            },
        ).execute()
        titles = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
        }
    sheet_id = titles[SEZNAMY_NEXT_OPPONENT_SHEET]
    sheet = f"'{SEZNAMY_NEXT_OPPONENT_SHEET}'"

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:Z200"
    ).execute()

    team_cell = SEZNAMY_NEXT_OPPONENT_TEAM_CELL
    error_message = (
        f"Vyber příštího soupeře (menu „pre-scout“) – list se naplní podle "
        f"názvu v {team_cell}, přesně jak je v Liga 2.0."
    )
    import_formula = (
        f'=IFERROR(IMPORTRANGE("{league_v2_id}"; "\'" & {team_cell} & "\'!A1:X120");'
        f'"{error_message}")'
    )
    data = [
        {"range": f"{sheet}!A1", "values": [["Příští soupeř:"]]},
        {"range": f"{sheet}!A3", "values": [[import_formula]]},
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()

    # IMPORTRANGE kopíruje jen hodnoty, ne formát buňky – datum a Bodový zisk
    # by se bez vlastního formátu zobrazily jako syrové sériové číslo/podíl
    # (46283,81…, 0,54…), ne jako datum/procenta. Řádky odpovídají layoutu
    # Liga 2.0 team template (build_league_team_template.py) posunutému o
    # import_formula začínající na řádku 3 (tým.A1 -> řádek 3, sezónní
    # přehled data řádek 5 -> řádek 7, Odehrané zápasy data řádek 51 -> 53).
    format_requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                },
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 6,
                    "endRowIndex": 7,
                    "startColumnIndex": 7,
                    "endColumnIndex": 8,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 52,
                    "endRowIndex": 150,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "DATE", "pattern": "dd.mm.yyyy"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": format_requests}
    ).execute()
    print(f"List '{SEZNAMY_NEXT_OPPONENT_SHEET}' postaven.")
    print(
        "Jednou je potřeba v prohlížeči otevřít „Povolit přístup“ pro "
        "IMPORTRANGE Liga 2.0 -> HC LIT jun 2026/27 (pokud ještě nebylo)."
    )


if __name__ == "__main__":
    main()

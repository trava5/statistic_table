"""Jednorázový skript: postaví v SEZNAMY_V2_SPREADSHEET_ID („Seznamy 2.0“)
list `Tým` – sezónní přehled LIT:soupeř jako vzorec nad zrcadlenými listy
`Zápasy (tým)` a `Zápasy` (viz scripts/build_seznamy_v2_mirrors.py).

Obsahuje (viz PLAN.MD, rozsah odsouhlasený s uživatelem):
1. Sezónní přehled + Přesilovky/oslabení + Vyloučení a TM – SUMIF/COUNTIF
   nad `Zápasy (tým)` (LIT řádky vs. řádky ostatních týmů = "soupeř").
2. Skóre po třetinách – z `Zápasy` (text "h:a" v 1.P/2.P/3.P/OT), rozpad na
   LIT/soupeř podle toho, kdo byl domácí/hosté, přes REGEXEXTRACT
   v pomocných sloupcích F:M (skryté).

Záměrně BEZ sekce Ročníky (odloženo na další krok – vyžaduje dopočítat rok
narození z registrace v Bruslaři/Brankáři (zápasy) a zprůměrovat počty
hráčů na zápas podle ročníku, viz PLAN.MD).

Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_tym_sheet.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAMY_TYM_SHEET,
    SEZNAMY_ZAPASY_SHEET,
    SEZNAMY_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_seznamy_v2_spreadsheet_id,
)

ZT = f"'{SEZNAMY_ZAPASY_TYM_SHEET}'"
Z = f"'{SEZNAMY_ZAPASY_SHEET}'"
ROWS = 5000

LIT_CRIT = '"LIT"'
OPP_CRIT = '"<>LIT"'


def _sumif(col: str, criteria: str) -> str:
    return f"=SUMIF({ZT}!$B$2:$B${ROWS};{criteria};{ZT}!${col}$2:${col}${ROWS})"


def _row(label: str, col: str) -> list:
    return [label, _sumif(col, LIT_CRIT), _sumif(col, OPP_CRIT)]


def _sum_pair(lit_col: str, opp_col: str) -> tuple[str, str]:
    return (f"=SUM({lit_col}2:{lit_col}{ROWS})", f"=SUM({opp_col}2:{opp_col}{ROWS})")


def _period_pair(period_col: str) -> tuple[str, str]:
    home_part = (
        f"VALUE(REGEXEXTRACT({Z}!${period_col}$2:${period_col}${ROWS};\"^(\\d+):\"))"
    )
    away_part = (
        f"VALUE(REGEXEXTRACT({Z}!${period_col}$2:${period_col}${ROWS};\":(\\d+)$\"))"
    )
    is_home = f'{Z}!$C$2:$C${ROWS}="LIT"'
    blank = f'{Z}!$A$2:$A${ROWS}=""'
    lit = f"=ARRAYFORMULA(IF({blank};\"\";IF({is_home};{home_part};{away_part})))"
    opp = f"=ARRAYFORMULA(IF({blank};\"\";IF({is_home};{away_part};{home_part})))"
    return lit, opp


def _ot_pair() -> tuple[str, str]:
    home_part = f'VALUE(REGEXEXTRACT({Z}!$K$2:$K${ROWS};"^(\\d+):"))'
    away_part = f'VALUE(REGEXEXTRACT({Z}!$K$2:$K${ROWS};":(\\d+)$"))'
    is_home = f'{Z}!$C$2:$C${ROWS}="LIT"'
    blank = f'OR({Z}!$A$2:$A${ROWS}="";{Z}!$K$2:$K${ROWS}="")'
    lit = f"=ARRAYFORMULA(IF({blank};\"\";IF({is_home};{home_part};{away_part})))"
    opp = f"=ARRAYFORMULA(IF({blank};\"\";IF({is_home};{away_part};{home_part})))"
    return lit, opp


def _refetch_sheet_id(service, spreadsheet_id: str, title: str) -> int:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for s in meta["sheets"]:
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    raise RuntimeError(f"List '{title}' nenalezen")


def main() -> None:
    config = load_config()
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    if SEZNAMY_TYM_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": SEZNAMY_TYM_SHEET}}}]},
        ).execute()
    sheet = f"'{SEZNAMY_TYM_SHEET}'"

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:Z{ROWS}"
    ).execute()

    # COUNTIF s "<>LIT" počítá i prázdné buňky pod daty jako "různé od LIT" –
    # COUNTIFS s druhou podmínkou "<>" (neprázdné) to opraví.
    opp_odehrano = f"COUNTIFS({ZT}!$B$2:$B${ROWS};\"<>\";{ZT}!$B$2:$B${ROWS};{OPP_CRIT})"
    prehled_rows = [
        ["Odehráno", f"=COUNTIF({ZT}!$B$2:$B${ROWS};{LIT_CRIT})", f"={opp_odehrano}"],
        _row("Góly", "E"),
        _row("Přesilovky (počet)", "I"),
        _row("Góly v přesilovce", "J"),
        ["Využití přesilovek", '=IF(B6=0;"";B7/B6)', '=IF(C6=0;"";C7/C6)'],
        _row("Oslabení (počet)", "K"),
        _row("Obdržené góly v oslabení", "L"),
        ["Úspěšnost oslabení", '=IF(B9=0;"";1-B10/B9)', '=IF(C9=0;"";1-C10/C9)'],
        _row("Góly v oslabení (vstřelené)", "M"),
        _row("Vyloučení (počet)", "N"),
        _row("Trestné minuty", "O"),
        ["Trestné minuty na zápas", '=IF(B4=0;"";B14/B4)', '=IF(C4=0;"";C14/C4)'],
    ]

    lit_p1, opp_p1 = _period_pair("H")
    lit_p2, opp_p2 = _period_pair("I")
    lit_p3, opp_p3 = _period_pair("J")
    lit_ot, opp_ot = _ot_pair()

    treting_lit1, treting_opp1 = _sum_pair("F", "G")
    treting_lit2, treting_opp2 = _sum_pair("H", "I")
    treting_lit3, treting_opp3 = _sum_pair("J", "K")
    treting_lit_ot, treting_opp_ot = _sum_pair("L", "M")

    data = [
        {"range": f"{sheet}!A1", "values": [["Týmové statistiky"]]},
        {"range": f"{sheet}!A3", "values": [["", "LIT", "soupeř"]]},
        {"range": f"{sheet}!A4", "values": prehled_rows},
        {"range": f"{sheet}!A17", "values": [["Skóre po třetinách"]]},
        {"range": f"{sheet}!A19", "values": [["", "LIT", "soupeř"]]},
        {
            "range": f"{sheet}!A20",
            "values": [
                ["1. třetina", treting_lit1, treting_opp1],
                ["2. třetina", treting_lit2, treting_opp2],
                ["3. třetina", treting_lit3, treting_opp3],
                ["Prodloužení (OT)", treting_lit_ot, treting_opp_ot],
            ],
        },
        {
            "range": f"{sheet}!F2",
            "values": [[lit_p1, opp_p1, lit_p2, opp_p2, lit_p3, opp_p3, lit_ot, opp_ot]],
        },
    ]

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()

    sheet_id = titles.get(SEZNAMY_TYM_SHEET) or _refetch_sheet_id(
        service, spreadsheet_id, SEZNAMY_TYM_SHEET
    )
    percent_format = {"type": "PERCENT", "pattern": "0.00%"}
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row - 1,
                    "endRowIndex": row,
                    "startColumnIndex": 1,
                    "endColumnIndex": 3,
                },
                "cell": {"userEnteredFormat": {"numberFormat": percent_format}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }
        for row in (8, 11)  # Využití přesilovek, Úspěšnost oslabení
    ]
    requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,
                    "endIndex": 13,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
    )
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()
    print(f"List '{SEZNAMY_TYM_SHEET}' postaven (bez sekce Ročníky, viz PLAN.MD).")


if __name__ == "__main__":
    main()

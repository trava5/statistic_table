"""Jednorázový skript: postaví list `Dashboard` v SEZNAMY_V2_SPREADSHEET_ID
(„Seznamy 2.0“) – přehled pro trenérský štáb nad už hotovými listy `Tým`,
`Zápasy (tým)`, `Zápasy`, `Bodování`, `Brankáři`.

Na rozdíl od produkčního Dashboardu (viz PLAN.MD) **nemá „Pořadí v lize"** –
to dnes zapisuje samostatný příkaz `standings` přímo do produkční tabulky,
Seznamy DB tuhle hodnotu zatím nemá (rozšíření `standings` na zápis do DB
je samostatný krok).

Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).
Pozn. k `endRowIndex` u grafů: viz build_league_team_template.py – Sheets
API tiše zahazuje `series` grafu nad moc velkým zdrojovým rozsahem, proto
`source(3, 40, ...)`, ne velkorysejší číslo.

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_dashboard.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAMY_BODOVANI_SHEET,
    SEZNAMY_BRANKARI_SHEET,
    SEZNAMY_DASHBOARD_SHEET,
    SEZNAMY_TYM_SHEET,
    SEZNAMY_ZAPASY_SHEET,
    SEZNAMY_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_seznamy_v2_spreadsheet_id,
)

ZT = f"'{SEZNAMY_ZAPASY_TYM_SHEET}'"
Z = f"'{SEZNAMY_ZAPASY_SHEET}'"
TYM = f"'{SEZNAMY_TYM_SHEET}'"
BOD = f"'{SEZNAMY_BODOVANI_SHEET}'"
GOA = f"'{SEZNAMY_BRANKARI_SHEET}'"
LIT = '"LIT"'


def build_value_updates() -> dict[str, list[list]]:
    updates: dict[str, list[list]] = {}

    def put(cell: str, value) -> None:
        updates[cell] = [[value]]

    def put_row(start_cell: str, values: list) -> None:
        updates[start_cell] = [values]

    put("A1", "Dashboard – HC Stadion Litoměřice U20")

    # --- Sezónní přehled -----------------------------------------------------
    put("A3", "SEZÓNNÍ PŘEHLED")
    put_row("A4", ["Odehráno", "V", "VP", "PP", "P", "Body", "Skóre (LIT:soupeř)"])
    put("A5", f"={TYM}!B4")
    put("B5", f'=COUNTIFS({ZT}!$B:$B;{LIT};{ZT}!$G:$G;"V")')
    put("C5", f'=COUNTIFS({ZT}!$B:$B;{LIT};{ZT}!$G:$G;"VP")')
    put("D5", f'=COUNTIFS({ZT}!$B:$B;{LIT};{ZT}!$G:$G;"PP")')
    put("E5", f'=COUNTIFS({ZT}!$B:$B;{LIT};{ZT}!$G:$G;"P")')
    put("F5", f"=SUMIF({ZT}!$B:$B;{LIT};{ZT}!$H:$H)")
    put("G5", f'={TYM}!B5&":"&{TYM}!C5')

    # --- Přesilovky / oslabení -------------------------------------------------
    put("A7", "PŘESILOVKY / OSLABENÍ")
    put_row(
        "A8",
        ["Přesilovky", "Využití PP", "Oslabení", "Úspěšnost PK", "Obdržené v oslabení",
         "Vstřelené v oslabení"],
    )
    put("A9", f"={TYM}!B6")
    put("B9", f"={TYM}!B8")
    put("C9", f"={TYM}!B9")
    put("D9", f"={TYM}!B11")
    put("E9", f"={TYM}!B10")
    put("F9", f"={TYM}!B12")

    # --- Vyloučení a trestné minuty --------------------------------------------
    put("A11", "VYLOUČENÍ A TRESTNÉ MINUTY")
    put_row(
        "A12",
        ["Vyloučení", "Vyloučení soupeř", "TM", "TM soupeř", "TM/zápas", "TM/zápas soupeř"],
    )
    put("A13", f"={TYM}!B13")
    put("B13", f"={TYM}!C13")
    put("C13", f"={TYM}!B14")
    put("D13", f"={TYM}!C14")
    put("E13", f"={TYM}!B15")
    put("F13", f"={TYM}!C15")

    put("A15", "SKÓRE PO ZÁPASECH")
    put("A32", "SKÓRE PO TŘETINÁCH")

    # --- Podkladová data pro graf „Skóre po zápasech" (sloupce N:P, skryté) --
    # Zápasy (tým) nemá datum – dohledá se přes číslo zápisu do Zápasy.
    put_row("N4", ["Datum", "Skóre LIT", "Skóre soupeř"])
    put(
        "N5",
        f"=ARRAYFORMULA(IFERROR(VLOOKUP("
        f"FILTER({ZT}!$A$2:$A$5000;{ZT}!$B$2:$B$5000={LIT});{Z}!$A:$B;2;FALSE)))",
    )
    put("O5", f"=FILTER({ZT}!$E$2:$E$5000;{ZT}!$B$2:$B$5000={LIT})")
    put("P5", f"=FILTER({ZT}!$F$2:$F$5000;{ZT}!$B$2:$B$5000={LIT})")

    # --- Bodování (všichni hráči) a Brankáři (vedle sebe) ----------------------
    put("A49", "BODOVÁNÍ")
    put(
        "A50",
        f'=QUERY({BOD}!A:G;"select A, C, D, E, F order by F desc";1)',
    )
    put("I49", "BRANKÁŘI")
    put("I50", f'=QUERY({GOA}!A:F;"select *";1)')

    return updates


def main() -> None:
    config = load_config()
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    if SEZNAMY_DASHBOARD_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [{"addSheet": {"properties": {"title": SEZNAMY_DASHBOARD_SHEET}}}]
            },
        ).execute()
        titles = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
        }
    sheet_id = titles[SEZNAMY_DASHBOARD_SHEET]
    tym_sheet_id = titles[SEZNAMY_TYM_SHEET]
    sheet = f"'{SEZNAMY_DASHBOARD_SHEET}'"

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:Z1000"
    ).execute()

    updates = build_value_updates()
    data = [{"range": f"{sheet}!{cell}", "values": values} for cell, values in updates.items()]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Zapsáno {len(data)} rozsahů do listu '{SEZNAMY_DASHBOARD_SHEET}'.")

    bold_ranges = [
        "A1:A1", "A3:A3", "A7:A7", "A11:A11", "A15:A15", "A32:A32", "A49:A49", "I49:I49",
        "A4:G4", "A8:F8", "A12:F12",
    ]

    def range_to_grid(a1: str) -> dict:
        start, end = a1.split(":")
        col_start = ord(start[0]) - ord("A")
        col_end = ord(end[0]) - ord("A") + 1
        row = int(start[1:]) - 1
        return {
            "sheetId": sheet_id,
            "startRowIndex": row,
            "endRowIndex": row + 1,
            "startColumnIndex": col_start,
            "endColumnIndex": col_end,
        }

    format_requests = [
        {
            "repeatCell": {
                "range": range_to_grid(rng),
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        }
        for rng in bold_ranges
    ]

    percent_format = {"type": "PERCENT", "pattern": "0.00%"}
    format_requests += [
        {
            "repeatCell": {
                "range": range_to_grid(rng),
                "cell": {"userEnteredFormat": {"numberFormat": percent_format}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }
        for rng in ("B9:B9", "D9:D9")
    ]

    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 13,
                    "endIndex": 16,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
    )

    chart_meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[sheet],
        fields="sheets(charts.chartId)",
    ).execute()
    existing_chart_ids = [c["chartId"] for c in chart_meta["sheets"][0].get("charts", [])]
    delete_chart_requests = [
        {"deleteEmbeddedObject": {"objectId": cid}} for cid in existing_chart_ids
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [*delete_chart_requests, *format_requests]},
    ).execute()

    def source(sid, row_start, row_end, col_start, col_end):
        return {
            "sourceRange": {
                "sources": [
                    {
                        "sheetId": sid,
                        "startRowIndex": row_start,
                        "endRowIndex": row_end,
                        "startColumnIndex": col_start,
                        "endColumnIndex": col_end,
                    }
                ]
            }
        }

    def create_chart_robust(spec: dict, position: dict, expected_series: int) -> None:
        """Viz build_league_team_template.py – addChart nespolehlivě zahazuje
        druhou a další sérii, řešení je smazat a zkusit znovu od nuly."""
        chart_id = None
        actual = 0
        for attempt in range(1, 8):
            if chart_id is not None:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [{"deleteEmbeddedObject": {"objectId": chart_id}}]},
                ).execute()
            resp = service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"addChart": {"chart": {"spec": spec, "position": position}}}]},
            ).execute()
            chart_id = resp["replies"][0]["addChart"]["chart"]["chartId"]
            check = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[sheet],
                fields="sheets(charts(chartId,spec.basicChart.series))",
            ).execute()
            chart = next(c for c in check["sheets"][0]["charts"] if c["chartId"] == chart_id)
            actual = len(chart["spec"]["basicChart"].get("series", []))
            if actual == expected_series:
                print(f"  graf '{spec['title']}': OK ({actual} sérií, pokus {attempt})")
                return
        print(
            f"  POZOR: graf '{spec['title']}' má {actual}/{expected_series} sérií "
            f"i po {attempt} pokusech – zkontroluj ručně v tabulce."
        )

    create_chart_robust(
        {
            "title": "Skóre po zápasech",
            # Zdrojové sloupce N:P jsou skryté (hiddenByUser výše) – bez SHOW_ALL
            # by Sheets při uložení tiše zahodilo i `series`, ne jen graficky
            # nezobrazilo (viz PLAN.MD, stejná past jako u produkčního Dashboardu).
            "hiddenDimensionStrategy": "SHOW_ALL",
            "basicChart": {
                "chartType": "LINE",
                "legendPosition": "BOTTOM_LEGEND",
                "axis": [
                    {"position": "BOTTOM_AXIS", "title": "Datum"},
                    {"position": "LEFT_AXIS", "title": "Góly"},
                ],
                "domains": [{"domain": source(sheet_id, 3, 40, 13, 14)}],
                "series": [
                    {
                        "series": source(sheet_id, 3, 40, 14, 15),
                        "targetAxis": "LEFT_AXIS",
                        "pointStyle": {"shape": "CIRCLE", "size": 6},
                    },
                    {
                        "series": source(sheet_id, 3, 40, 15, 16),
                        "targetAxis": "LEFT_AXIS",
                        "pointStyle": {"shape": "CIRCLE", "size": 6},
                    },
                ],
                "headerCount": 1,
            },
        },
        {
            "overlayPosition": {
                "anchorCell": {"sheetId": sheet_id, "rowIndex": 14},
                "widthPixels": 600,
                "heightPixels": 320,
            }
        },
        expected_series=2,
    )

    create_chart_robust(
        {
            "title": "Skóre po třetinách (celá sezóna)",
            "basicChart": {
                "chartType": "COLUMN",
                "legendPosition": "BOTTOM_LEGEND",
                "axis": [
                    {"position": "BOTTOM_AXIS", "title": "Třetina"},
                    {"position": "LEFT_AXIS", "title": "Góly"},
                ],
                # Zdroj přímo z listu Tým (A19:C23) – žádná duplikace dat na Dashboardu.
                "domains": [{"domain": source(tym_sheet_id, 18, 23, 0, 1)}],
                "series": [
                    {"series": source(tym_sheet_id, 18, 23, 1, 2), "targetAxis": "LEFT_AXIS"},
                    {"series": source(tym_sheet_id, 18, 23, 2, 3), "targetAxis": "LEFT_AXIS"},
                ],
                "headerCount": 1,
            },
        },
        {
            "overlayPosition": {
                "anchorCell": {"sheetId": sheet_id, "rowIndex": 31},
                "widthPixels": 600,
                "heightPixels": 320,
            }
        },
        expected_series=2,
    )
    print("Formátování a grafy přidány.")


if __name__ == "__main__":
    main()

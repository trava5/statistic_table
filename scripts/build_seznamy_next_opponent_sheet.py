"""Jednorázový skript: postaví list `Příští soupeř` v SEZNAMY_V2_SPREADSHEET_ID
(„HC LIT jun 2026/27“) – zrcadlí přes `IMPORTRANGE` celý list daného soupeře
z Liga 2.0 (`LEAGUE_V2_SPREADSHEET_ID`), stejné hodnoty, jaké by trenér viděl,
kdyby si tu kartu otevřel přímo v Liga 2.0.

Název týmu (musí přesně odpovídat názvu listu v Liga 2.0) se čte z buňky
`SEZNAMY_NEXT_OPPONENT_TEAM_CELL` (B1) – od 21. 10. 2026 ji vybírá trenér
ručně přes rozbalovací seznam (data validation) přímo v tabulce, `cli
pre-scout`/menu `main.py` ji už nepřepisuje (viz PLAN.MD – oddělené od
stahování videí). Zdroj rozbalovacího seznamu je skrytý sloupec `Z`,
který přes `IMPORTRANGE` zrcadlí názvy týmů z `Skupiny - liga` (Liga
2.0) – ne napevno vypsaný seznam, ať se sám udrží v souladu, kdyby se
složení ligy v sezóně změnilo. Druhý argument hlavního `IMPORTRANGE`
(karta soupeře) je sestavený jako dynamický řetězec (`"'" & B1 &
"'!A1:X120"`), ne napevno – stejný princip jako dynamické `QUERY` jinde
v projektu (`"where B = '" & $B$1 & "'"` u Liga 2.0 team template).

`IMPORTRANGE` kopíruje jen VYPOČÍTANÉ HODNOTY buněk, ne grafy (vlastní
objekty, ne data) – proto se 3 grafy z karty týmu (Skóre po zápasech/po
třetinách, Pořadí v tabulce) musí postavit znovu, nativně, na „Příští
soupeř“ – stejné zdrojové sloupce (N:P, R:T, V:X) jako šablona
(`build_league_team_template.py`), jen posunuté o +2 řádky (import
začíná na řádku 3, ne 1). Vedlejší efekt, který tenhle přístup (mirror
hodnot + vlastní grafy) řeší bez rizika rozbitých vzorců: přímé
zkopírování listu (`copyTo`) by grafy zachovalo, ale QUERY/SUMIF vzorce
uvnitř by ukazovaly #REF! (odkazují na listy Zápasy - liga (tým)/
Skupiny - liga, které v „HC LIT jun 2026/27“ neexistují) – IMPORTRANGE
se naopak žádné formule nedotýká, jen čte její výsledek; grafy nad
hodnotami samými zůstávají platné i po přepnutí soupeře v `B1`.

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
    error_message = f"Vyber příštího soupeře z rozbalovacího seznamu v {team_cell}."
    import_formula = (
        f'=IFERROR(IMPORTRANGE("{league_v2_id}"; "\'" & {team_cell} & "\'!A1:X120");'
        f'"{error_message}")'
    )
    # Skrytý zdroj rozbalovacího seznamu pro B1 (data validation níž) – týmy
    # podle Skupiny - liga (Liga 2.0), ne napevno vypsané, ať se seznam sám
    # udrží v souladu, kdyby se složení ligy v sezóně změnilo.
    team_list_formula = f'=IMPORTRANGE("{league_v2_id}"; "\'Skupiny - liga\'!A2:A50")'
    data = [
        {"range": f"{sheet}!A1", "values": [["Příští soupeř:"]]},
        # B1 musí po tomhle skriptu zůstat vyplněné nějakým reálným týmem
        # natrvalo, ne prázdné, jinak by IMPORTRANGE vrátil jen chybovou
        # hlášku a grafy níž by se stavěly nad prázdnými daty (Sheets API
        # v takovém případě tiše zahodí `series`, viz past u "Skóre po
        # třetinách" - stejný důvod, proč i Liga 2.0 team template
        # (`PLACEHOLDER_TEAM`) nechává B1 vyplněné natrvalo). Dál už se
        # nepřepisuje kódem (`cli pre-scout`/menu) - jen rozbalovacím
        # seznamem ručně v tabulce, viz PLAN.MD 21. 10. 2026.
        {"range": f"{sheet}!{team_cell}", "values": [["HC Stadion Litoměřice"]]},
        {"range": f"{sheet}!A3", "values": [[import_formula]]},
        {"range": f"{sheet}!Z1", "values": [["Soupeři (pom.)"]]},
        {"range": f"{sheet}!Z2", "values": [[team_list_formula]]},
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
        # Rozbalovací seznam na B1 – zdroj je skrytý sloupec Z (IMPORTRANGE
        # týmů ze Skupiny - liga, viz výš). `strict` odmítne ruční zápis
        # jména mimo seznam (B1 krmí hlavní IMPORTRANGE, překlep by ho
        # rozbil beze slova).
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_RANGE",
                        "values": [{"userEnteredValue": f"={sheet}!$Z$2:$Z$50"}],
                    },
                    "showCustomUi": True,
                    "strict": True,
                },
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 25,
                    "endIndex": 26,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": format_requests}
    ).execute()
    print(f"List '{SEZNAMY_NEXT_OPPONENT_SHEET}' postaven.")

    # Staré grafy smazat před znovupostavením (opakované spuštění skriptu by
    # jinak hromadilo duplicity – `values().clear()` výš se grafů netýká,
    # to jsou vlastní objekty, ne hodnoty buněk).
    existing_charts = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, ranges=[sheet], fields="sheets(charts.chartId)")
        .execute()["sheets"][0]
        .get("charts", [])
    )
    if existing_charts:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {"deleteEmbeddedObject": {"objectId": c["chartId"]}} for c in existing_charts
                ]
            },
        ).execute()

    def source(row_start, row_end, col_start, col_end):
        return {
            "sourceRange": {
                "sources": [
                    {
                        "sheetId": sheet_id,
                        "startRowIndex": row_start,
                        "endRowIndex": row_end,
                        "startColumnIndex": col_start,
                        "endColumnIndex": col_end,
                    }
                ]
            }
        }

    def create_chart_robust(spec: dict, position: dict, expected_series: int) -> None:
        """Viz build_league_team_template.py – `addChart` nespolehlivě zahazuje
        druhou a další `series`, řešení je smazat a zkusit znovu od nuly."""
        chart_id = None
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

    # Zdrojové sloupce (N:P, R:T, V:X) jsou přesně ty, co IMPORTRANGE přinesl
    # z karty týmu (build_league_team_template.py) – jen řádky posunuté o +2
    # (náš import začíná na řádku 3, šablona na řádku 1).
    create_chart_robust(
        {
            "title": "Skóre po zápasech",
            "basicChart": {
                "chartType": "LINE",
                "legendPosition": "BOTTOM_LEGEND",
                "axis": [
                    {"position": "BOTTOM_AXIS", "title": "Zápas"},
                    {"position": "LEFT_AXIS", "title": "Góly"},
                ],
                "domains": [{"domain": source(5, 42, 13, 14)}],
                "series": [
                    {
                        "series": source(5, 42, 14, 15),
                        "targetAxis": "LEFT_AXIS",
                        "pointStyle": {"shape": "CIRCLE", "size": 6},
                    },
                    {
                        "series": source(5, 42, 15, 16),
                        "targetAxis": "LEFT_AXIS",
                        "pointStyle": {"shape": "CIRCLE", "size": 6},
                    },
                ],
                "headerCount": 1,
            },
        },
        {
            "overlayPosition": {
                "anchorCell": {"sheetId": sheet_id, "rowIndex": 16},
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
                "domains": [{"domain": source(4, 8, 17, 18)}],
                "series": [
                    {"series": source(4, 8, 18, 19), "targetAxis": "LEFT_AXIS"},
                    {"series": source(4, 8, 19, 20), "targetAxis": "LEFT_AXIS"},
                ],
                "headerCount": 1,
            },
        },
        {
            "overlayPosition": {
                "anchorCell": {"sheetId": sheet_id, "rowIndex": 33},
                "widthPixels": 600,
                "heightPixels": 320,
            }
        },
        expected_series=2,
    )

    create_chart_robust(
        {
            "title": "Pořadí v tabulce",
            "basicChart": {
                "chartType": "LINE",
                "legendPosition": "NO_LEGEND",
                "axis": [
                    {"position": "BOTTOM_AXIS", "title": "Kolo"},
                    {
                        "position": "LEFT_AXIS",
                        "title": "Pořadí",
                        # Pevný rozsah 1–8 (skupina má 8 týmů), stejně jako
                        # šablona – hodnoty jsou záporné (sloupec X), min/max
                        # jsou tedy prohozené oproti zobrazenému 1/8.
                        "viewWindowOptions": {
                            "viewWindowMode": "EXPLICIT",
                            "viewWindowMin": -8,
                            "viewWindowMax": -1,
                        },
                    },
                ],
                "domains": [{"domain": source(5, 42, 21, 22)}],
                "series": [
                    {
                        "series": source(5, 42, 23, 24),
                        "targetAxis": "LEFT_AXIS",
                        "dataLabel": {"type": "DATA"},
                        "pointStyle": {"shape": "CIRCLE", "size": 7},
                    }
                ],
                "headerCount": 1,
            },
        },
        {
            "overlayPosition": {
                "anchorCell": {"sheetId": sheet_id, "rowIndex": 16, "columnIndex": 7},
                "widthPixels": 500,
                "heightPixels": 320,
            }
        },
        expected_series=1,
    )

    print(
        "Jednou je potřeba v prohlížeči otevřít „Povolit přístup“ pro "
        "IMPORTRANGE Liga 2.0 -> HC LIT jun 2026/27 (pokud ještě nebylo)."
    )


if __name__ == "__main__":
    main()

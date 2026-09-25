"""Jednorázový skript: postaví list „Tým – šablona" v LEAGUE_SPREADSHEET_ID.

Spouští se ručně jednou (při zakládání ligové tabulky, nebo když je potřeba
šablonu přepsat/opravit). Skript `league sync-teams` tento list dál jen
klonuje – nikdy ho nepřepisuje. Vzorce používají `;` jako oddělovač
argumentů (tabulka je v cs_CZ locale).

Pozn. k `endRowIndex` u grafů: Sheets API při vytváření grafu přes
`addChart` tiše zahodí druhou (a další) `series`, pokud zdrojový rozsah
zahrnuje příliš mnoho řádků (ověřeno – 300 řádků graf rozbije, 40 ne,
hranice je někde mezi 40 a 60). Proto grafy s více sériemi používají
`endRowIndex: 40` místo velkorysejšího čísla – nezvyšovat bez otestování.

Použití:
    .venv\\Scripts\\python.exe scripts\\build_league_team_template.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_GOALIES_SHEET,
    LEAGUE_PORADI_SHEET,
    LEAGUE_SKATERS_SHEET,
    LEAGUE_TEAM_TEMPLATE_SHEET,
    LEAGUE_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_league_v2_spreadsheet_id,
)

ZT = f"'{LEAGUE_ZAPASY_TYM_SHEET}'"
BR = f"'{LEAGUE_SKATERS_SHEET}'"
GO = f"'{LEAGUE_GOALIES_SHEET}'"
PO = f"'{LEAGUE_PORADI_SHEET}'"


def build_value_updates() -> dict[str, list[list]]:
    updates: dict[str, list[list]] = {}

    def put(cell: str, value) -> None:
        updates[cell] = [[value]]

    def put_row(start_cell: str, values: list) -> None:
        updates[start_cell] = [values]

    put("A1", "Tým:")

    # --- Sezónní přehled ----------------------------------------------------
    put("A3", "SEZÓNNÍ PŘEHLED")
    put_row("A4", ["Odehráno", "V", "VP", "PP", "P", "Body", "Skóre (tým:soupeř)"])
    put("A5", f"=COUNTIF({ZT}!$B:$B;$B$1)")
    put("B5", f'=COUNTIFS({ZT}!$B:$B;$B$1;{ZT}!$H:$H;"V")')
    put("C5", f'=COUNTIFS({ZT}!$B:$B;$B$1;{ZT}!$H:$H;"VP")')
    put("D5", f'=COUNTIFS({ZT}!$B:$B;$B$1;{ZT}!$H:$H;"PP")')
    put("E5", f'=COUNTIFS({ZT}!$B:$B;$B$1;{ZT}!$H:$H;"P")')
    put("F5", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$I:$I)")
    put(
        "G5",
        f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$F:$F)&\":\"&SUMIF({ZT}!$B:$B;$B$1;{ZT}!$G:$G)",
    )

    # --- Přesilovky / oslabení -----------------------------------------------
    put("A7", "PŘESILOVKY / OSLABENÍ")
    put_row(
        "A8",
        [
            "Přesilovky",
            "Využití PP",
            "Oslabení",
            "Úspěšnost PK",
            "Obdržené v oslabení",
            "Vstřelené v oslabení",
        ],
    )
    put("A9", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$M:$M)")
    put("B9", f"=IF(A9=0;\"\";SUMIF({ZT}!$B:$B;$B$1;{ZT}!$N:$N)/A9)")
    put("C9", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$O:$O)")
    put("D9", f"=IF(C9=0;\"\";1-SUMIF({ZT}!$B:$B;$B$1;{ZT}!$P:$P)/C9)")
    put("E9", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$P:$P)")
    put("F9", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$Q:$Q)")

    # --- Vyloučení a trestné minuty ------------------------------------------
    put("A11", "VYLOUČENÍ A TRESTNÉ MINUTY")
    put_row(
        "A12",
        ["Vyloučení", "Vyloučení soupeř", "TM", "TM soupeř", "TM/zápas", "TM/zápas soupeř"],
    )
    put("A13", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$R:$R)")
    put("B13", f"=SUMIF({ZT}!$C:$C;$B$1;{ZT}!$R:$R)")
    put("C13", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$S:$S)")
    put("D13", f"=SUMIF({ZT}!$C:$C;$B$1;{ZT}!$S:$S)")
    put("E13", '=IF($A$5=0;"";C13/$A$5)')
    put("F13", '=IF($A$5=0;"";D13/$A$5)')

    # --- Podkladová data pro graf „Skóre po zápasech" (sloupce N:P) ----------
    put_row("N4", ["Datum", "Skóre tým", "Skóre soupeř"])
    put("N5", f"=QUERY({ZT}!A:S;\"select D, F, G where B = '\"&$B$1&\"'\";0)")

    # --- Podkladová data pro graf „Skóre po třetinách" (sloupce R:T) ---------
    put("A15", "SKÓRE PO ZÁPASECH")
    put("A32", "SKÓRE PO TŘETINÁCH")
    put_row("R3", ["", "Tým", "Soupeř"])
    put("R4", "1. třetina")
    put("S4", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$J:$J)")
    put("T4", f"=SUMIF({ZT}!$C:$C;$B$1;{ZT}!$J:$J)")
    put("R5", "2. třetina")
    put("S5", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$K:$K)")
    put("T5", f"=SUMIF({ZT}!$C:$C;$B$1;{ZT}!$K:$K)")
    put("R6", "3. třetina")
    put("S6", f"=SUMIF({ZT}!$B:$B;$B$1;{ZT}!$L:$L)")
    put("T6", f"=SUMIF({ZT}!$C:$C;$B$1;{ZT}!$L:$L)")

    # --- Podkladová data pro graf „Pořadí v tabulce" (sloupce V:X) -----------
    # Web nezveřejňuje historii tabulky, proto `league sync-games` při každém
    # nálezu nových zápasů uloží aktuální pořadí všech týmů jako jeden snímek
    # do listu Pořadí - liga (viz PROJECT.MD, „Pořadí po kole"). Sloupec X je
    # záporná hodnota pořadí – jen kvůli ose grafu (níže = lepší pořadí, tedy
    # výš na ose). Zobrazené číslo (popisek bodu i osa) přitom vypadá kladně
    # díky vlastnímu formátu buňky „0;0" (druhá sekce = záporná čísla, bez
    # znaménka) – viz `number_format_requests` níže. Přímé zobrazení kladné
    # hodnoty bez obrácení osy bylo vizuálně matoucí (lepší pořadí vycházelo
    # níž na grafu), obrácení osy přes `viewWindowOptions`/`customLabelData`
    # se v API ukázalo nespolehlivé (beze změny vykreslení, resp. `500
    # Internal error`) – viz PLAN.MD.
    put_row("V4", ["Kolo", "Pořadí"])
    put("V5", f"=QUERY({PO}!A:D;\"select A, D where C = '\"&$B$1&\"' order by A\";0)")
    put("X4", "Pořadí (záporně, pro graf)")
    put("X5", '=ARRAYFORMULA(IF($W$5:$W$40="";"";-$W$5:$W$40))')

    # --- Odehrané zápasy / Bodování / Brankáři (vedle sebe) ------------------
    put("A49", "ODEHRANÉ ZÁPASY")
    put_row(
        "A50",
        ["Datum", "Soupeř", "D/V", "Skóre tým", "Skóre soupeř", "Výsledek", "Body"],
    )
    put(
        "A51",
        f"=QUERY({ZT}!A:S;\"select D, C, E, F, G, H, I where B = '\"&$B$1&\"'\";0)",
    )

    # Bruslaři - liga a Brankáři - liga jsou už sezónní součty (jeden řádek na
    # hráče) postavené vzorcem přes scripts/build_league_aggregate_sheets.py,
    # takže sem stačí prostý filtr podle týmu, žádné group by. Stejně jako u
    # BODOVÁNÍ/BRANKÁŘI dřív (group by) i `headers:1` u QUERY vždy vygeneruje
    # vlastní záhlavní řádek – proto vzorec začíná rovnou na řádku 50, žádné
    # ruční záhlaví vedle něj.
    put("I49", "BODOVÁNÍ")
    put(
        "I50",
        f"=QUERY({BR}!A:J;\"select C, B, E, F, G, H, I where A = '\"&$B$1&\"' "
        f"order by H desc label C 'Hráč', B 'Číslo', E 'Z', F 'G', G 'A', "
        f"H 'B', I 'TM'\";1)",
    )

    put("P49", "BRANKÁŘI")
    put(
        "P50",
        f"=QUERY({GO}!A:K;\"select C, D, E, F, J, K where A = '\"&$B$1&\"' "
        f"order by J desc label C 'Hráč', D 'Z', E 'IG', F 'IG/zápas', "
        f"J 'Výhry', K 'Shutouty'\";1)",
    )

    return updates


PLACEHOLDER_TEAM = "HC Stadion Litoměřice"


def main() -> None:
    config = load_config()
    spreadsheet_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))
    placeholder_team = PLACEHOLDER_TEAM

    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    titles = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}

    if LEAGUE_TEAM_TEMPLATE_SHEET not in titles:
        first_sheet_id = meta["sheets"][0]["properties"]["sheetId"]
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": first_sheet_id,
                                "title": LEAGUE_TEAM_TEMPLATE_SHEET,
                            },
                            "fields": "title",
                        }
                    }
                ]
            },
        ).execute()
        sheet_id = first_sheet_id
    else:
        sheet_id = titles[LEAGUE_TEAM_TEMPLATE_SHEET]

    updates = build_value_updates()
    data = [
        {"range": f"'{LEAGUE_TEAM_TEMPLATE_SHEET}'!{cell}", "values": values}
        for cell, values in updates.items()
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()
    print(f"Zapsáno {len(data)} rozsahů do listu '{LEAGUE_TEAM_TEMPLATE_SHEET}'.")

    bold_ranges = [
        "A1:A1", "A3:A3", "A7:A7", "A11:A11", "A15:A15", "A32:A32",
        "A49:A49", "I49:I49", "P49:P49",
        "A4:G4", "A8:F8", "A12:F12", "A50:G50", "I50:O50", "P50:U50",
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

    # Využití PP (B9) a Úspěšnost PK (D9) jsou podíly – bez tohoto formátu se
    # zobrazují jako syrové desetinné číslo (0,1666...) místo procent.
    percent_ranges = ["B9:B9", "D9:D9"]
    percent_format = {"type": "PERCENT", "pattern": "0.00%"}
    format_requests += [
        {
            "repeatCell": {
                "range": range_to_grid(rng),
                "cell": {"userEnteredFormat": {"numberFormat": percent_format}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }
        for rng in percent_ranges
    ]

    # Sloupec X (záporné pořadí, jen kvůli ose grafu) – vlastní formát „0;0"
    # zobrazí zápornou hodnotu bez znaménka (druhá sekce formátu = záporná
    # čísla, bez explicitního „-"), takže popisek bodu i osa grafu (obojí čte
    # formát zdrojové buňky) vypadají jako kladné skutečné pořadí.
    format_requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 4,
                    "endRowIndex": 40,
                    "startColumnIndex": 23,
                    "endColumnIndex": 24,
                },
                "cell": {
                    "userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0;0"}}
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        }
    )

    chart_meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[f"'{LEAGUE_TEAM_TEMPLATE_SHEET}'"],
        fields="sheets(charts.chartId)",
    ).execute()
    existing_chart_ids = [c["chartId"] for c in chart_meta["sheets"][0].get("charts", [])]
    delete_chart_requests = [
        {"deleteEmbeddedObject": {"objectId": chart_id}} for chart_id in existing_chart_ids
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [*delete_chart_requests, *format_requests]},
    ).execute()

    # Sheets API tiše zahodí `series` grafu, kdykoli je zdrojový rozsah prázdný –
    # nejen při vytvoření grafu, ale i zpětně při dalším přepočtu (proto $B$1
    # v šabloně musí zůstat vyplněné natrvalo, ne jen dočasně kvůli vytvoření
    # grafů – jinak by QUERY vrátila 0 řádků a grafy by se znovu rozbily).
    # `league sync-teams` B1 v každé kopii přepíše skutečným týmem.
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{LEAGUE_TEAM_TEMPLATE_SHEET}'!B1",
        valueInputOption="USER_ENTERED",
        body={"values": [[placeholder_team]]},
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
        """Vytvoří graf a ověří, že si Sheets API uložilo všechny `series`.

        Sheets API při `addChart` s víc sériemi nespolehlivě (ne vždy, ale
        opakovaně ověřeno) zahodí druhou a další sérii, aniž by to nahlásilo
        jako chybu (`updateChartSpec` na opravu už existujícího grafu má navíc
        tendenci spadnout na 500). Řešení: celý graf se zkusí smazat a znovu
        vytvořit od nuly, dokud API vážně neuloží všechny série."""
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
                ranges=[f"'{LEAGUE_TEAM_TEMPLATE_SHEET}'"],
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
            "basicChart": {
                "chartType": "LINE",
                "legendPosition": "BOTTOM_LEGEND",
                "axis": [
                    {"position": "BOTTOM_AXIS", "title": "Zápas"},
                    {"position": "LEFT_AXIS", "title": "Góly"},
                ],
                "domains": [{"domain": source(3, 40, 13, 14)}],
                "series": [
                    {
                        "series": source(3, 40, 14, 15),
                        "targetAxis": "LEFT_AXIS",
                        "pointStyle": {"shape": "CIRCLE", "size": 6},
                    },
                    {
                        "series": source(3, 40, 15, 16),
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
                "domains": [{"domain": source(2, 6, 17, 18)}],
                "series": [
                    {"series": source(2, 6, 18, 19), "targetAxis": "LEFT_AXIS"},
                    {"series": source(2, 6, 19, 20), "targetAxis": "LEFT_AXIS"},
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
                        # Pevný rozsah 1–8 (skupina má 8 týmů, viz Skupiny -
                        # liga), ne automatické přizpůsobení odehraným kolům –
                        # jinak by na začátku sezóny (jen pár kol, úzký rozsah
                        # skutečných hodnot) osa neukazovala celou tabulku.
                        # Hodnoty jsou záporné (viz sloupec X výše), min/max
                        # jsou tedy prohozené oproti zobrazenému 1/8.
                        "viewWindowOptions": {
                            "viewWindowMode": "EXPLICIT",
                            "viewWindowMin": -8,
                            "viewWindowMax": -1,
                        },
                    },
                ],
                "domains": [{"domain": source(3, 40, 21, 22)}],
                "series": [
                    {
                        "series": source(3, 40, 23, 24),
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
                "anchorCell": {"sheetId": sheet_id, "rowIndex": 14, "columnIndex": 7},
                "widthPixels": 500,
                "heightPixels": 320,
            }
        },
        expected_series=1,
    )
    print("Formátování a grafy přidány.")
    print(
        f"B1 v šabloně zůstává vyplněné ({placeholder_team!r}) – Sheets API tiše "
        "zahazuje `series` grafu i zpětně, kdykoliv se zdrojový rozsah stane prázdným "
        "(ne jen v okamžiku vytvoření), takže vyčištění B1 by grafy znovu rozbilo. "
        "`league sync-teams` stejně B1 v každé kopii hned přepíše skutečným týmem."
    )


if __name__ == "__main__":
    main()

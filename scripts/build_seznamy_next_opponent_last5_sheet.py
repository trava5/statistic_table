"""Jednorázový skript: postaví list `Příští soupeř Last 5` v
SEZNAMY_V2_SPREADSHEET_ID („HC LIT jun 2026/27“) – stejné kategorie a
rozložení jako list `Last 5` (LIT), ale pro **kterýkoli tým Ligy juniorů**,
vybraný rozbalovacím seznamem na listu `Příští soupeř` (`B1`).

Proč samostatný skript, ne rozšíření `build_seznamy_last5_sheet.py`: LIT
Last 5 počítá z `Zápasy (tým)`/`Bruslaři`/`Brankáři (zápasy)` v Seznamy DB,
která zná jen LIT. Soupeř může být libovolný z 16 týmů ligy, takže zdroj
dat musí být Liga DB (`Zápasy - liga (tým)`, `Bruslaři/Brankáři - liga
(zápasy)`) – ty žije jen v Liga 2.0, proto tři skryté `IMPORTRANGE` mirrory
(sloupce AA:AT, BA:BJ, CA:CM) místo místních listů. Tým se nefiltruje
napevno jako LIT, ale dynamickým odkazem na `'Příští soupeř'!$B$1`
(stejný princip jako dynamické `QUERY` jinde v projektu).

„Posledních 5 zápasů“ se tu (na rozdíl od LIT, kde chybí sloupec s datem)
řadí podle **kola** (`Zápasy - liga (tým)` ho má) – každý tým hraje
v lize přesně jeden zápas na kolo, takže poslední kolo = poslední zápas,
bez rizika textového řazení data (past u Liga 2.0, viz PLAN.MD).

Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_next_opponent_last5_sheet.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_GOALIES_LOG_SHEET,
    LEAGUE_SKATERS_LOG_SHEET,
    LEAGUE_ZAPASY_TYM_SHEET,
    SEZNAMY_NEXT_OPPONENT_LAST5_SHEET,
    SEZNAMY_NEXT_OPPONENT_SHEET,
    SEZNAMY_NEXT_OPPONENT_TEAM_CELL,
    get_credentials,
    load_config,
    require_league_v2_spreadsheet_id,
    require_seznamy_v2_spreadsheet_id,
)

ZT = f"'{LEAGUE_ZAPASY_TYM_SHEET}'"
SK_LOG = f"'{LEAGUE_SKATERS_LOG_SHEET}'"
GO_LOG = f"'{LEAGUE_GOALIES_LOG_SHEET}'"
ROWS = 5000

# Sloupce skrytého mirroru Zápasy - liga (tým) (IMPORTRANGE A2:T, bez
# hlavičky) - stejné pořadí jako LEAGUE_ZAPASY_TYM_HEADER, jen posunuté na
# AA:AT (QUERY/SUMPRODUCT uvnitř rozsahu, který nezačíná na A, se musí
# odkazovat na SKUTEČNÁ písmena sloupců tabulky, ne přepočítávat zpět na
# A/B/C - ověřeno živě při stavbě listu Tabulka, viz PLAN.MD).
ZT_GAME_ID, ZT_TYM, ZT_SOUPER, ZT_DATUM = "AA", "AB", "AC", "AD"
ZT_SKORE_TYM, ZT_SKORE_SOUPER, ZT_VYSLEDEK, ZT_BODY = "AF", "AG", "AH", "AI"
ZT_PRESILOVKY, ZT_GOLY_PP, ZT_OSLABENI = "AM", "AN", "AO"
ZT_OBDRZENE_OSLAB, ZT_GOLY_OSLAB = "AP", "AQ"
ZT_VYLOUCENI, ZT_TM, ZT_KOLO = "AR", "AS", "AT"

# Sloupce skrytého mirroru Bruslaři - liga (zápasy) (IMPORTRANGE A2:J).
SK_GAME_ID, SK_TYM, SK_HRAC = "BA", "BB", "BD"
SK_G, SK_A, SK_B = "BF", "BG", "BH"

# Sloupce skrytého mirroru Brankáři - liga (zápasy) (IMPORTRANGE A2:L) +
# CM = místní pomocný sloupec "vychytaná výhra" (log má jen jeden řádek na
# brankáře, co v zápase skutečně chytal - na rozdíl od Seznamy DB tu není
# potřeba žádná "chytal" podmínka, viz PLAN.MD).
GO_GAME_ID, GO_TYM, GO_HRAC = "CA", "CB", "CD"
GO_OBDRZENE, GO_VYSLEDEK_TYMU, GO_VYCHYTANA = "CG", "CL", "CM"

TEAM_REF = f"'{SEZNAMY_NEXT_OPPONENT_SHEET}'!${SEZNAMY_NEXT_OPPONENT_TEAM_CELL[0]}" + (
    f"${SEZNAMY_NEXT_OPPONENT_TEAM_CELL[1:]}"
)
LAST5_RANGE = "$N$2:$N$6"
IN_LAST5 = f"COUNTIF({LAST5_RANGE};${ZT_GAME_ID}$2:${ZT_GAME_ID}${ROWS})"
TEAM_FILTER = f"(${ZT_TYM}$2:${ZT_TYM}${ROWS}={TEAM_REF})"
# Prázdné řádky pod daty by "<>TEAM" vyhodnotilo jako "soupeř" - stejná past
# jako u LIT Last 5/Tým, proto navíc "<>" (neprázdné).
OPP_FILTER = (
    f"(${ZT_TYM}$2:${ZT_TYM}${ROWS}<>\"\")*(${ZT_TYM}$2:${ZT_TYM}${ROWS}<>{TEAM_REF})"
)


def _sum_team(col: str) -> str:
    return f"=SUMPRODUCT(({TEAM_FILTER})*{IN_LAST5}*${col}$2:${col}${ROWS})"


def _sum_opp(col: str) -> str:
    return f"=SUMPRODUCT({OPP_FILTER}*{IN_LAST5}*${col}$2:${col}${ROWS})"


def _count_result(result_value: str) -> str:
    return (
        f"=SUMPRODUCT(({TEAM_FILTER})*{IN_LAST5}*"
        f'(${ZT_VYSLEDEK}$2:${ZT_VYSLEDEK}${ROWS}="{result_value}"))'
    )


def _last5_or_tokens(col: str) -> list[str]:
    """Vzorcové tokeny pro `(col="&N2&" or col="&N3&" ... or col="&N6&")` –
    QUERY neumí přímo "je hodnota v rozsahu N2:N6" (stejný princip jako
    u LIT Last 5, jen parametrizovaný sloupcem). **Bez uvozovek** kolem
    game_id – na rozdíl od LIT („číslo zápisu“, text) je `game_id` v Liga
    DB číslo (`league_scraper.py` ho parsuje přes `int()`); `BA='181025'`
    (textové porovnání) v GViz Query proti číselnému sloupci tiše vrátí
    0 řádků, bez chyby – past nalezená živě (viz PLAN.MD)."""
    tokens = [f'"({col}="']
    for row in range(2, 7):
        tokens.append(f"N{row}")
        tokens.append(f'" or {col}="' if row < 6 else '")"')
    return tokens


def _query_formula(source_range: str, game_id_col: str, select_with_placeholders: str) -> str:
    """`select_with_placeholders` obsahuje přesně jedno `{TEAM}` (nahradí se
    dynamickým odkazem na `'Příští soupeř'!$B$1`) a jedno `{FILTER}`
    (posledních 5 game_id, viz `_last5_or_tokens`)."""
    before, mid = select_with_placeholders.split("{TEAM}")
    mid, after = mid.split("{FILTER}")
    tokens = [f'"{before}"', TEAM_REF, f'"{mid}"', *_last5_or_tokens(game_id_col), f'"{after}"']
    return f"=QUERY({source_range};{'&'.join(tokens)};0)"


def main() -> None:
    config = load_config()
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    league_v2_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    if SEZNAMY_NEXT_OPPONENT_LAST5_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {"addSheet": {"properties": {"title": SEZNAMY_NEXT_OPPONENT_LAST5_SHEET}}}
                ]
            },
        ).execute()
        titles = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
        }
    sheet_id = titles[SEZNAMY_NEXT_OPPONENT_LAST5_SHEET]
    sheet = f"'{SEZNAMY_NEXT_OPPONENT_LAST5_SHEET}'"

    # Mirror sahá do CM (index 90) - výchozích 26 sloupců nestačí (stejná
    # past jako u Dashboardu/Tabulky, viz PLAN.MD). Řádky se nastavují
    # napevno na ROWS + rezerva PŘED zápisem vzorců ze stejného důvodu:
    # pokud by mřížka musela růst AŽ PO zapsání absolutních odkazů
    # ($AB$5000 apod.), Sheets ji nastaví vložením řádků, co posune
    # všechny takové odkazy dolů (nalezeno živě – $5000 se samo přepsalo
    # na $7014, viz PLAN.MD).
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"columnCount": 95, "rowCount": ROWS + 100},
                        },
                        "fields": "gridProperties.columnCount,gridProperties.rowCount",
                    }
                }
            ]
        },
    ).execute()

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:CZ{ROWS}"
    ).execute()

    updates: dict[str, list] = {}

    def put(cell: str, value) -> None:
        updates[cell] = [[value]]

    def put_row(start_cell: str, values: list) -> None:
        updates[start_cell] = [values]

    put("A1", f'="Last 5 – posledních 5 zápasů " & {TEAM_REF}')

    # --- Skryté mirrory Liga DB (IMPORTRANGE, bez hlavičky zdroje). -------
    put("AA2", f'=IMPORTRANGE("{league_v2_id}";"{ZT}!A2:T{ROWS}")')
    put("BA2", f'=IMPORTRANGE("{league_v2_id}";"{SK_LOG}!A2:J{ROWS}")')
    put("CA2", f'=IMPORTRANGE("{league_v2_id}";"{GO_LOG}!A2:L{ROWS}")')
    # Log má jen jeden řádek na brankáře, co v zápase skutečně chytal (na
    # rozdíl od Seznamy DB) - "vychytaná výhra" je tak jen V/VP bez další
    # podmínky.
    put(
        "CM2",
        f"=ARRAYFORMULA(IF(${GO_TYM}$2:${GO_TYM}${ROWS}=\"\";\"\";"
        f'IF((${GO_VYSLEDEK_TYMU}$2:${GO_VYSLEDEK_TYMU}${ROWS}="V")+'
        f'(${GO_VYSLEDEK_TYMU}$2:${GO_VYSLEDEK_TYMU}${ROWS}="VP");1;0)))',
    )

    # Posledních 5 kol (= zápasů, jeden na kolo) vybraného týmu - skrytý
    # pomocný sloupec, všechny ostatní vzorce na listu se na něj odkazují.
    put("N1", "posledních 5 game_id soupeře (pom.)")
    put(
        "N2",
        f'=QUERY($AA$2:${ZT_KOLO}${ROWS};"select {ZT_GAME_ID} where {ZT_TYM} = \'" & '
        f'{TEAM_REF} & "\' order by {ZT_KOLO} desc limit 5";0)',
    )

    # --- Sezónní přehled (posledních 5 zápasů) -------------------------------
    put("A3", "SEZÓNNÍ PŘEHLED (POSLEDNÍCH 5 ZÁPASŮ)")
    put_row("A4", ["Odehráno", "V", "VP", "PP", "P", "Body", "Skóre (tým:soupeř)"])
    put("A5", "=COUNTA($N$2:$N$6)")
    put("B5", _count_result("V"))
    put("C5", _count_result("VP"))
    put("D5", _count_result("PP"))
    put("E5", _count_result("P"))
    put("F5", _sum_team(ZT_BODY))
    # _sum_team/_sum_opp vrací kompletní vzorec vč. úvodního "=" (pro použití
    # jako samostatná buňka) - při vnořování do jiného výrazu (zřetězení
    # skóre) musí "=" odpadnout, jinak vznikne neplatný zápis "==...".
    put("G5", f'={_sum_team(ZT_SKORE_TYM)[1:]}&":"&{_sum_opp(ZT_SKORE_TYM)[1:]}')

    # --- Přesilovky / oslabení ------------------------------------------------
    put("A7", "PŘESILOVKY / OSLABENÍ (POSLEDNÍCH 5 ZÁPASŮ)")
    put_row(
        "A8",
        ["Přesilovky", "Využití PP", "Oslabení", "Úspěšnost PK",
         "Obdržené v oslabení", "Vstřelené v oslabení"],
    )
    put("A9", _sum_team(ZT_PRESILOVKY))
    put("B9", '=IF(A9=0;"";J9/A9)')
    put("C9", _sum_team(ZT_OSLABENI))
    put("D9", '=IF(C9=0;"";1-E9/C9)')
    put("E9", _sum_team(ZT_OBDRZENE_OSLAB))
    put("F9", _sum_team(ZT_GOLY_OSLAB))
    # Pomocný sloupec J9 pro "Využití PP" výše.
    put("J9", _sum_team(ZT_GOLY_PP))

    # --- Vyloučení a trestné minuty --------------------------------------------
    put("A11", "VYLOUČENÍ A TRESTNÉ MINUTY (POSLEDNÍCH 5 ZÁPASŮ)")
    put_row(
        "A12",
        ["Vyloučení", "Vyloučení soupeř", "TM", "TM soupeř", "TM/zápas", "TM/zápas soupeř"],
    )
    put("A13", _sum_team(ZT_VYLOUCENI))
    put("B13", _sum_opp(ZT_VYLOUCENI))
    put("C13", _sum_team(ZT_TM))
    put("D13", _sum_opp(ZT_TM))
    put("E13", '=IF($A$5=0;"";C13/$A$5)')
    put("F13", '=IF($A$5=0;"";D13/$A$5)')

    # --- Bodování a Brankáři (vedle sebe, jen posledních 5 zápasů) -------------
    # `{{TEAM}}`/`{{FILTER}}` jsou escapované literály (zůstanou v textu
    # jako "{TEAM}"/"{FILTER}") – `_query_formula` je sama nahradí dynamickým
    # odkazem na tým a podmínkou na posledních 5 game_id.
    put("A16", "BODOVÁNÍ (POSLEDNÍCH 5 ZÁPASŮ)")
    skater_select = (
        f"select {SK_HRAC}, count({SK_GAME_ID}), sum({SK_G}), sum({SK_A}), sum({SK_B}) "
        f"where {SK_TYM} = '{{TEAM}}' and {{FILTER}} group by {SK_HRAC} "
        f"order by sum({SK_B}) desc "
        f"label {SK_HRAC} 'Hráč', count({SK_GAME_ID}) 'Z', sum({SK_G}) 'G', "
        f"sum({SK_A}) 'A', sum({SK_B}) 'B'"
    )
    put("A17", _query_formula(f"$BA$2:$BJ${ROWS}", SK_GAME_ID, skater_select))

    put("I16", "BRANKÁŘI (POSLEDNÍCH 5 ZÁPASŮ)")
    goalie_select = (
        f"select {GO_HRAC}, count({GO_GAME_ID}), sum({GO_OBDRZENE}), "
        f"sum({GO_OBDRZENE})/count({GO_GAME_ID}), sum({GO_VYCHYTANA}), "
        f"sum({GO_VYCHYTANA})/count({GO_GAME_ID}) where {GO_TYM} = '{{TEAM}}' and {{FILTER}} "
        f"group by {GO_HRAC} order by count({GO_GAME_ID}) desc "
        f"label {GO_HRAC} 'Hráč', count({GO_GAME_ID}) 'Z', sum({GO_OBDRZENE}) 'obdržené góly', "
        f"sum({GO_OBDRZENE})/count({GO_GAME_ID}) 'průměr', "
        f"sum({GO_VYCHYTANA}) 'Vychytané výhry', "
        f"sum({GO_VYCHYTANA})/count({GO_GAME_ID}) '% výher'"
    )
    put("I17", _query_formula(f"$CA$2:$CM${ROWS}", GO_GAME_ID, goalie_select))

    data = [{"range": f"{sheet}!{cell}", "values": values} for cell, values in updates.items()]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Zapsáno {len(data)} rozsahů do listu '{SEZNAMY_NEXT_OPPONENT_LAST5_SHEET}'.")

    def range_to_grid(a1: str) -> dict:
        start, end = a1.split(":")
        col_start = ord(start[0]) - ord("A")
        col_end = ord(end[0]) - ord("A") + 1
        return {
            "sheetId": sheet_id,
            "startRowIndex": int(start[1:]) - 1,
            "endRowIndex": int(end[1:]),
            "startColumnIndex": col_start,
            "endColumnIndex": col_end,
        }

    bold_ranges = [
        "A1:A1", "A3:A3", "A7:A7", "A11:A11", "A16:A16", "I16:I16",
        "A4:G4", "A8:F8", "A12:F12",
    ]
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
        for rng in ("B9:B9", "D9:D9", "N18:N50")
    ]
    # N (posledních 5 game_id) a J (pomocný čitatel pro Využití PP) skryté,
    # ať nepletou pohled na list - stejně celý mirror blok AA:CM.
    hidden_column_ranges = [(9, 10), (13, 14), (26, 90)]
    for start_index, end_index in hidden_column_ranges:
        format_requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "properties": {"hiddenByUser": True},
                    "fields": "hiddenByUser",
                }
            }
        )
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": format_requests}
    ).execute()
    print("Formátování přidáno.")


if __name__ == "__main__":
    main()

"""Jednorázový skript: postaví v SEZNAMY_V2_SPREADSHEET_ID („Seznamy 2.0“)
list `Last 5` – stejné kategorie a rozložení jako Dashboard (sezónní
přehled, přesilovky/oslabení, vyloučení a TM, pod tím Bodování a Brankáři
vedle sebe), jen počítané z **posledních 5 odehraných zápasů LIT** místo
celé sezóny, ať je vidět aktuální forma týmu. Bez grafů (odsouhlaseno
s uživatelem).

Bodování/Brankáři NEčtou ze sezónních agregátů `Bodování`/`Brankáři`
(postavené `build_seznamy_aggregate_sheets.py`) – ty jsou vždy za celou
sezónu, nejde je dodatečně omezit na posledních 5 zápasů. Místo toho
počítají znovu přímo z `Bruslaři (zápasy)`/`Brankáři (zápasy)` (stejný
zdroj, stejné QUERY group by), jen s navíc podmínkou na posledních 5 čísel
zápisu – stejný princip jako u týmových statistik níž.

Zdroj dat je stejný list `Zápasy (tým)` jako u `Tým`/Dashboardu, ale ten
nemá sloupec s datem (viz `SEZNAMY_ZAPASY_TYM_HEADER`) – pro „posledních
5“ se tedy řadí podle sloupce A („číslo zápisu“), ne podle data. Čísla
zápisů přiděluje svaz postupně podle termínu utkání, takže `order by A desc`
v QUERY dává stejné pořadí jako chronologicky – QUERY navíc sloupec se
samými čísly automaticky vyhodnotí jako číselný typ, takže na rozdíl od
řazení data jako textu (past u Liga 2.0, viz PLAN.MD) tu nehrozí problém
s různým počtem znaků mezi měsíci/sezónami.

Posledních 5 čísel zápisů LIT je skrytý pomocný sloupec N2:N6 – všechny
ostatní vzorce ho používají jako "je tohle číslo zápisu mezi posledními
pěti" filtr přes `COUNTIF` uvnitř `SUMPRODUCT` (`SUMIF`/`COUNTIFS` neumí
filtrovat podle "je v seznamu hodnot", jen podle jedné rovnosti).

„Bodový zisk“ (H5, `=F5/(A5*3)`) – stejná buňka jako na Liga 2.0 team
template, jen přes okno posledních 5 zápasů – doplněno 5. 10. 2026 na
žádost uživatele.

Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_last5_sheet.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAMY_GOALIES_LOG_SHEET,
    SEZNAMY_LAST5_SHEET,
    SEZNAMY_SKATERS_LOG_SHEET,
    SEZNAMY_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_seznamy_v2_spreadsheet_id,
)

ZT = f"'{SEZNAMY_ZAPASY_TYM_SHEET}'"
SKATERS_LOG = f"'{SEZNAMY_SKATERS_LOG_SHEET}'"
GOALIES_LOG = f"'{SEZNAMY_GOALIES_LOG_SHEET}'"
ROWS = 5000
LIT_CRIT = '"LIT"'
LAST5_RANGE = "$N$2:$N$6"
IN_LAST5 = f"COUNTIF({LAST5_RANGE};{ZT}!$A$2:$A${ROWS})"
LIT_FILTER = f"{ZT}!$B$2:$B${ROWS}={LIT_CRIT}"
# Prázdné řádky pod daty by "<>LIT" vyhodnotilo jako "soupeř" – stejná past
# jako v build_seznamy_tym_sheet.py, proto navíc "<>" (neprázdné).
OPP_FILTER = f'({ZT}!$B$2:$B${ROWS}<>"")*({ZT}!$B$2:$B${ROWS}<>{LIT_CRIT})'


def _sum_lit(col: str) -> str:
    return f"=SUMPRODUCT(({LIT_FILTER})*{IN_LAST5}*{ZT}!${col}$2:${col}${ROWS})"


def _sum_opp(col: str) -> str:
    return f"=SUMPRODUCT({OPP_FILTER}*{IN_LAST5}*{ZT}!${col}$2:${col}${ROWS})"


def _count_result(result_value: str) -> str:
    return (
        f"=SUMPRODUCT(({LIT_FILTER})*{IN_LAST5}*"
        f'({ZT}!$G$2:$G${ROWS}="{result_value}"))'
    )


def _last5_or_tokens(col: str) -> list[str]:
    """Vzorcové tokeny, které po spojení "&" dají text (jako součást query
    stringu) `(col='" & N2 & "' or col='" & N3 & "' or ... or col='" & N6 &
    "')` – QUERY neumí přímo "je hodnota v rozsahu N2:N6", takže se musí
    sestavit jako dynamický řetězec místo 5 čísel napevno."""
    tokens = [f'"({col}=\'"']
    for row in range(2, 7):
        tokens.append(f"N{row}")
        tokens.append('"\' or {col}=\'"'.format(col=col) if row < 6 else '"\')"')
    return tokens


def _query_formula(sheet: str, last_col: str, select_and_label: str) -> str:
    """`select_and_label` obsahuje `{FILTER}` tam, kam patří podmínka na
    posledních 5 čísel zápisu (viz `_last5_or_tokens`)."""
    before, after = select_and_label.split("{FILTER}")
    tokens = [f'"{before}"', *_last5_or_tokens("A"), f'"{after}"']
    return f"=QUERY({sheet}!A:{last_col};{'&'.join(tokens)};1)"


def main() -> None:
    config = load_config()
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    if SEZNAMY_LAST5_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": SEZNAMY_LAST5_SHEET}}}]},
        ).execute()
        titles = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
        }
    sheet_id = titles[SEZNAMY_LAST5_SHEET]
    sheet = f"'{SEZNAMY_LAST5_SHEET}'"

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:Z{ROWS}"
    ).execute()

    updates: dict[str, list] = {}

    def put(cell: str, value) -> None:
        updates[cell] = [[value]]

    def put_row(start_cell: str, values: list) -> None:
        updates[start_cell] = [values]

    put("A1", "Last 5 – posledních 5 zápasů LIT")

    # Posledních 5 čísel zápisu LIT (nejnovější první) – pomocný sloupec,
    # skrytý níž. Všechny ostatní vzorce na listu se na něj odkazují.
    put("N1", "posledních 5 čísel zápisu LIT (pomocné)")
    put(
        "N2",
        # Uvnitř QUERY jazyka je textový literál v JEDNODUCHÝCH uvozovkách
        # ('LIT'), ne v dvojitých (ty uzavírají celý query string) - LIT_CRIT
        # je naopak pro přímé SUMIF/SUMPRODUCT podmínky mimo QUERY, nehodí se
        # sem (past, kterou jsem si sám musel opravit při psaní tohohle listu).
        # Rozsah musí zahrnovat i sloupec B (přes který se filtruje), ne jen
        # A (co se vybírá) - #VALUE!, pokud QUERY sloupec z podmínky vůbec
        # nedostane (druhá past, taky nalezena při psaní).
        f"=QUERY({ZT}!A2:B{ROWS};\"select A where B = 'LIT' order by A desc limit 5\";0)",
    )

    # --- Sezónní přehled (posledních 5 zápasů) -------------------------------
    put("A3", "SEZÓNNÍ PŘEHLED (POSLEDNÍCH 5 ZÁPASŮ)")
    put_row(
        "A4",
        ["Odehráno", "V", "VP", "PP", "P", "Body", "Skóre (LIT:soupeř)", "Bodový zisk"],
    )
    put("A5", "=COUNTA($N$2:$N$6)")
    put("B5", _count_result("V"))
    put("C5", _count_result("VP"))
    put("D5", _count_result("PP"))
    put("E5", _count_result("P"))
    put("F5", _sum_lit("H"))
    # _sum_lit/_sum_opp vrací kompletní vzorec vč. úvodního "=" (pro použití
    # jako samostatná buňka) - při vnořování do jiného výrazu (zřetězení
    # skóre) musí "=" odpadnout, jinak vznikne neplatný zápis "==...".
    put("G5", f'={_sum_lit("E")[1:]}&":"&{_sum_opp("E")[1:]}')
    # Bodový zisk = podíl ze zisku maximálně možných bodů (3 za zápas) ze
    # stejného okna posledních 5 zápasů jako zbytek listu – stejná buňka
    # jako na Liga 2.0 team template, doplněno 5. 10. 2026 na žádost
    # uživatele.
    put("H5", "=F5/(A5*3)")

    # --- Přesilovky / oslabení ------------------------------------------------
    put("A7", "PŘESILOVKY / OSLABENÍ (POSLEDNÍCH 5 ZÁPASŮ)")
    put_row(
        "A8",
        ["Přesilovky", "Využití PP", "Oslabení", "Úspěšnost PK",
         "Obdržené v oslabení", "Vstřelené v oslabení"],
    )
    put("A9", _sum_lit("I"))
    put("B9", '=IF(A9=0;"";J9/A9)')
    put("C9", _sum_lit("K"))
    put("D9", '=IF(C9=0;"";1-E9/C9)')
    put("E9", _sum_lit("L"))
    put("F9", _sum_lit("M"))
    # Pomocný sloupec J9 pro "Využití PP" výše – "góly v přesilovce" nemá
    # vlastní viditelný sloupec v přehledu (na rozdíl od Tým sheetu), ale
    # vzorec ho potřebuje jako čitatele.
    put("J9", _sum_lit("J"))

    # --- Vyloučení a trestné minuty --------------------------------------------
    put("A11", "VYLOUČENÍ A TRESTNÉ MINUTY (POSLEDNÍCH 5 ZÁPASŮ)")
    put_row(
        "A12",
        ["Vyloučení", "Vyloučení soupeř", "TM", "TM soupeř", "TM/zápas", "TM/zápas soupeř"],
    )
    put("A13", _sum_lit("N"))
    put("B13", _sum_opp("N"))
    put("C13", _sum_lit("O"))
    put("D13", _sum_opp("O"))
    put("E13", '=IF($A$5=0;"";C13/$A$5)')
    put("F13", '=IF($A$5=0;"";D13/$A$5)')

    # --- Bodování a Brankáři (vedle sebe, jen posledních 5 zápasů) -------------
    # Stejné rozložení jako na Dashboardu (BODOVÁNÍ vlevo, BRANKÁŘI o pár
    # sloupců vpravo), ale počítané přímo z Bruslaři/Brankáři (zápasy) se
    # stejnou "posledních 5 čísel zápisu" podmínkou jako výš - ne ze
    # sezónních agregátů Bodování/Brankáři, ty se nedají dodatečně omezit.
    put("A16", "BODOVÁNÍ (POSLEDNÍCH 5 ZÁPASŮ)")
    skater_select = (
        "select D, sum(G), sum(H), sum(I), sum(J) where B = 'LIT' and {FILTER} "
        "group by D order by sum(J) desc "
        "label D 'Hráč', sum(G) 'Z', sum(H) 'G', sum(I) 'A', sum(J) 'B'"
    )
    put("A17", _query_formula(SKATERS_LOG, "K", skater_select))

    put("I16", "BRANKÁŘI (POSLEDNÍCH 5 ZÁPASŮ)")
    goalie_select = (
        "select D, sum(F), sum(G), sum(G)/sum(F), sum(L), sum(L)/sum(F) "
        "where B = 'LIT' and {FILTER} group by D order by sum(F) desc "
        "label D 'Hráč', sum(F) 'Z', sum(G) 'obdržené góly', sum(G)/sum(F) 'průměr', "
        "sum(L) 'Vychytané výhry', sum(L)/sum(F) '% výher'"
    )
    put("I17", _query_formula(GOALIES_LOG, "L", goalie_select))

    data = [{"range": f"{sheet}!{cell}", "values": values} for cell, values in updates.items()]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Zapsáno {len(data)} rozsahů do listu '{SEZNAMY_LAST5_SHEET}'.")

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
        "A4:H4", "A8:F8", "A12:F12",
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
        for rng in ("B9:B9", "D9:D9", "N18:N50", "H5:H5")
    ]
    # N (pomocný seznam čísel zápisu) a J (pomocný čitatel pro Využití PP)
    # skryté, ať nepletou pohled na list.
    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 9,
                    "endIndex": 10,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
    )
    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 13,
                    "endIndex": 14,
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

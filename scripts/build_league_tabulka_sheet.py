"""Jednorázový skript: postaví list `Tabulka` v LEAGUE_V2_SPREADSHEET_ID
(„Liga 2.0“) – tabulky obou skupin vedle sebe (Pořadí, Tým, Z, V, VP, PP, P,
Skóre, Body), počítané vzorcem nad `Zápasy - liga (tým)`/`Skupiny - liga`
(mirror DB, ne živý scrape). Správnost se kontroluje ručně proti oficiální
stránce Ligy juniorů (`STANDINGS_URL`), ne automaticky – žádný nový Python
kód, jen vzorce vedle existujících mirrorů.

Řazení (Body desc, pak rozdíl skóre desc, pak vstřelené góly desc) je
stejné pravidlo jako `league_sheets.recompute_standings_history` (Python,
pro `Pořadí - liga`) – tahle tabulka počítá nezávisle vlastním vzorcem nad
týmiž syrovými daty (`Zápasy - liga (tým)`), ne čtením `Pořadí - liga`,
ať jde o druhý, nezávislý výpočet pro porovnání s webem.

Postup (QUERY nejde přímo filtrovat podle skupiny, protože ta není sloupec
v `Zápasy - liga (tým)`):
1. Skrytý „stage 1“ blok (U:AD) – jedna `QUERY group by` dá Tým/Z/GF/GA/Body
   za všech 16 týmů najednou, `ARRAYFORMULA`+`COUNTIFS` (s polem týmů jako
   kritériem – stejný vzor jako `build_league_aggregate_sheets.py` u
   Výher/Shutoutů brankářů) doplní V/VP/PP/P a `INDEX`+`MATCH` do
   `Skupiny - liga` doplní skupinu.
2. Skrytý „stage 2“ blok (AF:AN pro skupinu 1, AP:AX pro skupinu 2) – druhá
   `QUERY` nad stage 1 vybere a seřadí řádky jedné skupiny.
3. Viditelná tabulka (A:I resp. K:S) jen odkazuje na stage 2 po sloupcích
   (`ARRAYFORMULA` s hlídáním prázdna) – stejný princip jako „Odehrané
   zápasy“ v `build_seznamy_dashboard.py`. Pořadí (1., 2., ...) je prostě
   řádek v rámci už seřazeného stage 2, ne vzorec s `RANK`.

Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).

Použití:
    .venv\\Scripts\\python.exe scripts\\build_league_tabulka_sheet.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_SKUPINY_SHEET,
    LEAGUE_TABULKA_SHEET,
    LEAGUE_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_league_v2_spreadsheet_id,
)

ZT = f"'{LEAGUE_ZAPASY_TYM_SHEET}'"
SK = f"'{LEAGUE_SKUPINY_SHEET}'"
MAX_TEAMS = 16  # celá liga (obě skupiny) - stage 1 má jeden řádek na tým
MAX_PER_GROUP = 10  # headroom nad reálných 8 týmů/skupina

# QUERY s agregací (sum/count/group by) vždy vypíše vlastní syntetický
# hlavičkový řádek (popisky typu "sum F"), bez ohledu na parametr `headers`
# – ten řeší jen kolik řádků VSTUPU se má přeskočit, ne jestli VÝSTUP má
# hlavičku (past nalezená živě 12. 10. 2026 – `;0)` nestačilo, data byla
# posunutá o řádek a poslední tým chyběl). Stage 1 proto počítá s hlavičkou
# na řádku 2, skutečná data jsou až 3..STAGE1_LAST_ROW.
STAGE1_DATA_START = 3
STAGE1_LAST_ROW = 2 + MAX_TEAMS

HEADER_ROW = ["Pořadí", "Tým", "Z", "V", "VP", "PP", "P", "Skóre", "Body"]


def build_value_updates() -> dict[str, list[list]]:
    updates: dict[str, list[list]] = {}

    def put(cell: str, value) -> None:
        updates[cell] = [[value]]

    def put_row(start_cell: str, values: list) -> None:
        updates[start_cell] = [values]

    # --- Stage 1 (skrytý): Tým/Z/GF/GA/Body za všech 16 týmů, pak V/VP/PP/P
    # a skupina doplněné zvlášť (QUERY group by neumí podmíněné počítání,
    # stejná past jako u Výher/Shutoutů brankářů v build_league_aggregate_
    # sheets.py). ---------------------------------------------------------
    put(
        "U2",
        f"=QUERY({ZT}!A:T;\"select B, count(A), sum(F), sum(G), sum(I) "
        f"where B <> '' group by B\";1)",
    )
    u_range = f"$U${STAGE1_DATA_START}:$U${STAGE1_LAST_ROW}"
    # VLOOKUP, ne INDEX/MATCH - INDEX(range;MATCH(pole;...)) pod ARRAYFORMULA
    # nebroadcastuje správně (vrátí jeden výsledek pro všechny řádky, past
    # nalezená živě 12. 10. 2026 - stejný důvod, proč má i hotová
    # build_league_poradi_view.py tenhle sloupec rozbitý, viz PLAN.MD).
    # VLOOKUP pod ARRAYFORMULA s polem je naopak ověřeně spolehlivé (stejný
    # vzor jako Dashboard/Last 5 "Datum").
    put(
        f"Z{STAGE1_DATA_START}",
        f"=ARRAYFORMULA(IF({u_range}=\"\";\"\";"
        f"IFERROR(VLOOKUP({u_range};{SK}!$A:$B;2;FALSE))))",
    )
    for col, result in (("AA", "V"), ("AB", "VP"), ("AC", "PP"), ("AD", "P")):
        put(
            f"{col}{STAGE1_DATA_START}",
            f"=ARRAYFORMULA(IF({u_range}=\"\";\"\";"
            f"COUNTIFS({ZT}!$B:$B;{u_range};{ZT}!$H:$H;\"{result}\")))",
        )

    # --- Stage 2 (skrytý): stage 1 filtrovaný a seřazený po skupinách. ----
    # Stejné pravidlo jako league_sheets.recompute_standings_history
    # (Body desc, rozdíl skóre desc, vstřelené góly desc), ale počítané
    # samostatně vzorcem – druhý, nezávislý výpočet pro kontrolu proti webu.
    stage2_select = (
        "select U, V, AA, AB, AC, AD, W, X, Y where Z = {group} "
        "order by Y desc, (W - X) desc, W desc"
    )
    put(
        "AF3",
        f'=QUERY($U$1:$AD${STAGE1_LAST_ROW};"{stage2_select.format(group=1)}";0)',
    )
    put(
        "AP3",
        f'=QUERY($U$1:$AD${STAGE1_LAST_ROW};"{stage2_select.format(group=2)}";0)',
    )

    # --- Viditelné tabulky (odkaz na stage 2 po sloupcích). ---------------
    # Stage 2 sloupce jsou v pořadí Tým,Z,V,VP,PP,P,GF,GA,Body (viz select
    # výš) - stage2_cols musí mít přesně tenhle pořadí pro oba select()y.
    last_row = 2 + MAX_PER_GROUP  # stage 2 data řádky 3..last_row

    def guard(col: str) -> str:
        return f"${col}$3:${col}${last_row}"

    def group_table(visible_cols: str, title: str, stage2_cols: list[str]) -> None:
        a, b, c, d, e, f, g, h, i = visible_cols
        tym, z, v, vp, pp, p, gf, ga, body = stage2_cols
        put(f"{a}1", title)
        put_row(f"{a}2", HEADER_ROW)
        put(f"{a}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";ROW({guard(tym)})-2))")
        put(f"{b}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(tym)}))")
        put(f"{c}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(z)}))")
        put(f"{d}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(v)}))")
        put(f"{e}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(vp)}))")
        put(f"{f}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(pp)}))")
        put(f"{g}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(p)}))")
        put(
            f"{h}3",
            f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(gf)}&\":\"&{guard(ga)}))",
        )
        put(f"{i}3", f"=ARRAYFORMULA(IF({guard(tym)}=\"\";\"\";{guard(body)}))")

    group_table(
        "ABCDEFGHI", "SKUPINA 1",
        ["AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM", "AN"],
    )
    group_table(
        "KLMNOPQRS", "SKUPINA 2",
        ["AP", "AQ", "AR", "AS", "AT", "AU", "AV", "AW", "AX"],
    )

    return updates


def main() -> None:
    config = load_config()
    spreadsheet_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    if LEAGUE_TABULKA_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": LEAGUE_TABULKA_SHEET}}}]},
        ).execute()
        titles = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
        }
    sheet_id = titles[LEAGUE_TABULKA_SHEET]
    sheet = f"'{LEAGUE_TABULKA_SHEET}'"

    # Výchozích 26 sloupců nestačí - skrytý stage 2 pro skupinu 2 sahá do AX
    # (index 49), potřeba aspoň 50 sloupců (past nalezená u Dashboardu, viz
    # PLAN.MD 5. 10. 2026).
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "gridProperties": {"columnCount": 52}},
                        "fields": "gridProperties.columnCount",
                    }
                }
            ]
        },
    ).execute()

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:AZ1000"
    ).execute()

    updates = build_value_updates()
    data = [{"range": f"{sheet}!{cell}", "values": values} for cell, values in updates.items()]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Zapsáno {len(data)} rozsahů do listu '{LEAGUE_TABULKA_SHEET}'.")

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

    bold_ranges = ["A1:A1", "K1:K1", "A2:I2", "K2:S2"]
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
    # U:AX (indexy 20-49) = skryté stage 1/stage 2 bloky.
    format_requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 20,
                    "endIndex": 50,
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

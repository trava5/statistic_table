"""Jednorázový skript: postaví v SEZNAMY_V2_SPREADSHEET_ID („Seznamy 2.0“)
listy `Bodování` a `Brankáři` (sezónní součty LIT, jeden řádek na hráče) jako
vzorce nad syrovým logem (`Bruslaři (zápasy)` / `Brankáři (zápasy)`), místo
aby je Python přepočítával a přepisoval – stejný vzor jako
scripts/build_league_aggregate_sheets.py u Ligy.

Na rozdíl od produkční tabulky Seznamy (INDEX/MATCH proti Seznam hráčů,
SUMPRODUCT proti pozičním sloupcům Zápasy/Sestavy) čte přímo z normalizovaného
logu a nepotřebuje Seznam hráčů vůbec – jméno hráče je už v logu (z PDF).

`Brankáři` má „Vychytané výhry“/„% výher“ (ne celou produkční sadu – bez
shutoutu, ø při výhře/prohře) – spočítané ze sloupců `K`/`L` (výsledek,
vychytaná výhra), které `build_seznamy_v2_mirrors.py` doplňuje na mirror
listu `Brankáři (zápasy)` navíc k IMPORTRANGE spillu. `G`/`A`/`TM` u
brankářů (na rozdíl od produkční tabulky) nejsou – u brankáře nejsou
zajímavá čísla a QUERY select je bez nich čitelnější.

`Bodování` je navíc nativní Sheets „Tabulka“ (ne jen vzorec) – aby šlo
řadit podle sloupců kliknutím na hlavičku, stejně jako produkční `Bodování`/
`Brankáři`. **Past:** Tabulka nad rozsahem, kam píše `QUERY`, dřív (viz
PLAN.MD) tiše přebíjela vzorcem vygenerované hlavičky vlastními „Sloupec N“
– řešení je `deleteTable` před přepsáním vzorce, pak `addTable` znovu.

Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_aggregate_sheets.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAMY_BODOVANI_SHEET,
    SEZNAMY_BRANKARI_SHEET,
    SEZNAMY_GOALIES_LOG_SHEET,
    SEZNAMY_SKATERS_LOG_SHEET,
    get_credentials,
    load_config,
    require_seznamy_v2_spreadsheet_id,
)

SKATERS_LOG = f"'{SEZNAMY_SKATERS_LOG_SHEET}'"
GOALIES_LOG = f"'{SEZNAMY_GOALIES_LOG_SHEET}'"


def main() -> None:
    config = load_config()
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    missing = [
        name for name in (SEZNAMY_BODOVANI_SHEET, SEZNAMY_BRANKARI_SHEET) if name not in titles
    ]
    if missing:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": n}}} for n in missing]},
        ).execute()

    # Vyčistit případná stará data před vzorcem (na jistotu, ať list vždy
    # obsahuje jen aktuální formuli, ne zbytky z ručních úprav).
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{SEZNAMY_BODOVANI_SHEET}'!A1:Z1000000"
    ).execute()
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{SEZNAMY_BRANKARI_SHEET}'!A1:Z1000000"
    ).execute()

    # Bruslaři (zápasy): A číslo zápisu, B tým, C číslo, D jméno, E registrace,
    # F post, G nastoupil, H G, I A, J B, K TM.
    skater_query = (
        f"=QUERY({SKATERS_LOG}!A:K;\"select D, max(F), sum(G), sum(H), sum(I), sum(J), sum(K) "
        f"where B = 'LIT' group by D order by sum(J) desc "
        f"label D 'Hráč', max(F) 'Post', sum(G) 'Z', sum(H) 'G', sum(I) 'A', sum(J) 'B', "
        f"sum(K) 'TM'\";1)"
    )
    # Brankáři (zápasy): A číslo zápisu, B tým, C číslo, D jméno, E registrace,
    # F chytal, G obdržené góly, H G, I A, J TM, K výsledek, L vychytaná výhra
    # (K, L doplňuje build_seznamy_v2_mirrors.py mimo IMPORTRANGE spill A:J).
    goalie_query = (
        f"=QUERY({GOALIES_LOG}!A:L;\"select D, sum(F), sum(G), sum(G)/sum(F), sum(L), "
        f"sum(L)/sum(F) where B = 'LIT' group by D order by sum(F) desc "
        f"label D 'Hráč', sum(F) 'Z', sum(G) 'obdržené góly', "
        f"sum(G)/sum(F) 'průměr', sum(L) 'Vychytané výhry', sum(L)/sum(F) '% výher'\";1)"
    )

    data = [
        {"range": f"'{SEZNAMY_BODOVANI_SHEET}'!A1", "values": [[skater_query]]},
        {"range": f"'{SEZNAMY_BRANKARI_SHEET}'!A1", "values": [[goalie_query]]},
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Vzorce zapsány do '{SEZNAMY_BODOVANI_SHEET}' a '{SEZNAMY_BRANKARI_SHEET}'.")

    # "% výher" jako podíl – bez formátu je to syrové desetinné číslo.
    sheet_ids = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    percent_format_request = {
        "repeatCell": {
            "range": {
                "sheetId": sheet_ids[SEZNAMY_BRANKARI_SHEET],
                "startRowIndex": 1,
                "endRowIndex": 1000,
                "startColumnIndex": 5,
                "endColumnIndex": 6,
            },
            "cell": {
                "userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}
            },
            "fields": "userEnteredFormat.numberFormat",
        }
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": [percent_format_request]}
    ).execute()

    _ensure_sortable_table(
        service, spreadsheet_id, sheet_ids[SEZNAMY_BODOVANI_SHEET], SEZNAMY_BODOVANI_SHEET
    )
    print(f"'{SEZNAMY_BODOVANI_SHEET}' je nativní Tabulka (řazení kliknutím na hlavičku).")


def _ensure_sortable_table(service, spreadsheet_id: str, sheet_id: int, name: str) -> None:
    """Nativní Sheets „Tabulka“ nad rozsahem, kam píše QUERY – dřív (viz
    PLAN.MD) tiché přebití hlaviček „Sloupec N“, proto vždy nejdřív smazat
    starou tabulku (pokud existuje) a založit znovu, ne upravovat na místě."""
    meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId),tables(tableId))"
    ).execute()
    sheet = next(s for s in meta["sheets"] if s["properties"]["sheetId"] == sheet_id)
    delete_requests = [
        {"deleteTable": {"tableId": t["tableId"]}} for t in sheet.get("tables", [])
    ]
    add_request = {
        "addTable": {
            "table": {
                "name": name,
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7,
                },
            }
        }
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": [*delete_requests, add_request]}
    ).execute()


if __name__ == "__main__":
    main()

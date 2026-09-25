"""Jednorázový skript: postaví v SEZNAMY_V2_SPREADSHEET_ID („Seznamy 2.0“)
zrcadlové listy syrových dat ze Seznamy DB, jeden list = jeden `IMPORTRANGE`.

Listy mají záměrně STEJNÁ jména jako v DB (Zápasy, Góly, Vyloučení, Bruslaři
(zápasy), Brankáři (zápasy)), aby na ně šly napojit formule Bodování/
Brankáři/Tým/Dashboard stejným způsobem jako u Ligy.

Navíc zrcadlí `Seznam hráčů` z PRODUKČNÍ tabulky Seznamy (SPREADSHEET_ID) –
ale JEN neosobní sloupce B:F (Příjmení, Jméno, č. reg., číslo, post), NE
celý list. Od sloupce J má produkční Seznam hráčů citlivé osobní údaje
(pojišťovna, rodné číslo, telefon, e-mail hráčů i rodičů) – ty se nesmí
dostat do Seznamy 2.0, viz PLAN.MD bod 6 (přesunou se později do samostatné
nesdílené tabulky, teprve pak se zdroj IMPORTRANGE přepne tam). `Trenéři`
se nezrcadlí vůbec – žádná formule v Bodování/Brankáři/Tým/Dashboard ho
nepotřebuje a je celý citlivý (PIN, telefon, e-mail).

Po prvním spuštění je potřeba **ručně** otevřít Seznamy 2.0 v prohlížeči
a kliknout na „Povolit přístup“ u IMPORTRANGE vzorců (jednou za dvojici
tabulek, pro DB → Seznamy 2.0 i pro Seznamy (produkční) → Seznamy 2.0
zvlášť) – Google to nejde autorizovat přes API.

Použití:
    .venv\\Scripts\\python.exe scripts\\build_seznamy_v2_mirrors.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAM_HRACU_SHEET,
    SEZNAMY_GOALIES_LOG_SHEET,
    SEZNAMY_GOLY_SHEET,
    SEZNAMY_SKATERS_LOG_SHEET,
    SEZNAMY_VYLOUCENI_SHEET,
    SEZNAMY_ZAPASY_SHEET,
    SEZNAMY_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_seznamy_db_spreadsheet_id,
    require_seznamy_v2_spreadsheet_id,
)

# Jméno listu -> poslední sloupec s daty (viz SEZNAMY_*_HEADER v config.py).
DB_MIRRORS = {
    SEZNAMY_ZAPASY_SHEET: "K",
    SEZNAMY_ZAPASY_TYM_SHEET: "O",
    SEZNAMY_GOLY_SHEET: "H",
    SEZNAMY_VYLOUCENI_SHEET: "I",
    SEZNAMY_SKATERS_LOG_SHEET: "K",
    SEZNAMY_GOALIES_LOG_SHEET: "J",
}
ROWS = 5000

SEZNAM_HRACU_HEADER = ["Příjmení:", "Jméno:", "č. reg.", "číslo:", "post"]


def main() -> None:
    config = load_config()
    db_id = require_seznamy_db_spreadsheet_id(config)
    v2_id = require_seznamy_v2_spreadsheet_id(config)
    production_id = config.spreadsheet_id
    service = build("sheets", "v4", credentials=get_credentials(config))

    sheet_names = [*DB_MIRRORS, SEZNAM_HRACU_SHEET]
    meta = service.spreadsheets().get(spreadsheetId=v2_id).execute()
    titles = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}

    # První list v tabulce (výchozí "List 1") přejmenovat na první zrcadlo,
    # ať v tabulce nezůstane prázdný list navíc.
    requests = []
    remaining = list(sheet_names)
    if remaining and remaining[0] not in titles and meta["sheets"]:
        first_sheet_id = meta["sheets"][0]["properties"]["sheetId"]
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": first_sheet_id, "title": remaining[0]},
                    "fields": "title",
                }
            }
        )
        titles[remaining[0]] = first_sheet_id
        remaining = remaining[1:]

    missing = [name for name in remaining if name not in titles]
    requests += [{"addSheet": {"properties": {"title": name}}} for name in missing]
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=v2_id, body={"requests": requests}
        ).execute()

    data = []
    for name, last_col in DB_MIRRORS.items():
        formula = f'=IMPORTRANGE("{db_id}"; "\'{name}\'!A1:{last_col}{ROWS}")'
        data.append({"range": f"'{name}'!A1", "values": [[formula]]})

    data.append({"range": f"'{SEZNAM_HRACU_SHEET}'!A1", "values": [SEZNAM_HRACU_HEADER]})
    hraci_formula = f'=IMPORTRANGE("{production_id}"; "\'{SEZNAM_HRACU_SHEET}\'!B3:F1000")'
    data.append({"range": f"'{SEZNAM_HRACU_SHEET}'!A2", "values": [[hraci_formula]]})

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=v2_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Zapsáno {len(data)} vzorců/hlaviček do Seznamy 2.0.")
    print(
        "Teď otevři Seznamy 2.0 v prohlížeči a klikni na „Povolit přístup“ – "
        "jednou za DB -> Seznamy 2.0, jednou za produkční Seznamy -> Seznamy 2.0."
    )


if __name__ == "__main__":
    main()

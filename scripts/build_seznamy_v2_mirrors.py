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

GOLY = f"'{SEZNAMY_GOLY_SHEET}'"
ZAPASY_TYM = f"'{SEZNAMY_ZAPASY_TYM_SHEET}'"
EXTRA_COLUMN_ROWS = 100  # dost i na několik sezón zápasů LIT

# Jméno listu -> poslední sloupec s daty (viz SEZNAMY_*_HEADER v config.py).
DB_MIRRORS = {
    SEZNAMY_ZAPASY_SHEET: "L",  # K + "pořadí po kole" (standings.py, doplněno dodatečně)
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

    # Starší běh skriptu psal "Zápasy!L:M" (Góly/Asistence) – ten sloupec teď
    # patří rozšířenému IMPORTRANGE spillu (A:L = "pořadí po kole" z DB) a
    # leftover vzorec ve staré pozici L by spill blokoval (#REF! – "array
    # result was not expanded because it would overwrite data"). Vyčistit před
    # zápisem nové formule, ne po – jinak by IMPORTRANGE ještě jednu chvíli
    # dopočítávalo přes starý obsah.
    service.spreadsheets().values().clear(
        spreadsheetId=v2_id,
        range=f"'{SEZNAMY_ZAPASY_SHEET}'!L1:L{1 + EXTRA_COLUMN_ROWS}",
    ).execute()

    data = []
    for name, last_col in DB_MIRRORS.items():
        formula = f'=IMPORTRANGE("{db_id}"; "\'{name}\'!A1:{last_col}{ROWS}")'
        data.append({"range": f"'{name}'!A1", "values": [[formula]]})

    data.append({"range": f"'{SEZNAM_HRACU_SHEET}'!A1", "values": [SEZNAM_HRACU_HEADER]})
    hraci_formula = f'=IMPORTRANGE("{production_id}"; "\'{SEZNAM_HRACU_SHEET}\'!B3:F1000")'
    data.append({"range": f"'{SEZNAM_HRACU_SHEET}'!A2", "values": [[hraci_formula]]})

    # --- Zápasy!M:N – střelci/nahrávači LIT za daný zápas (mimo IMPORTRANGE
    # spill A:L – sloupec L je teď "pořadí po kole" zrcadlené z DB, proto tyhle
    # dva sloupce navíc začínají až na M, ne na L jako dřív). Počítá se z Góly
    # zvlášť za každý řádek – FILTER nejde vektorizovat přes ARRAYFORMULA,
    # protože kritérium (číslo zápisu) se mění po řádcích, proto je vzorec
    # zapsaný zvlášť pro každý z EXTRA_COLUMN_ROWS řádků, ne jako jeden spill.
    data.append({"range": f"'{SEZNAMY_ZAPASY_SHEET}'!M1", "values": [["Góly", "Asistence"]]})
    zapasy_extra_rows = []
    for row in range(2, 2 + EXTRA_COLUMN_ROWS):
        goly = (
            f'=IF($A{row}="";"";IFERROR(TEXTJOIN(", ";TRUE;'
            f'FILTER({GOLY}!$E$2:$E$5000;{GOLY}!$A$2:$A$5000=$A{row};'
            f'{GOLY}!$B$2:$B$5000="LIT"));""))'
        )
        asistence = (
            f'=IF($A{row}="";"";IFERROR(TEXTJOIN(", ";TRUE;'
            f'FILTER({GOLY}!$F$2:$F$5000;{GOLY}!$A$2:$A$5000=$A{row};'
            f'{GOLY}!$B$2:$B$5000="LIT");'
            f'FILTER({GOLY}!$G$2:$G$5000;{GOLY}!$A$2:$A$5000=$A{row};'
            f'{GOLY}!$B$2:$B$5000="LIT"));""))'
        )
        zapasy_extra_rows.append([goly, asistence])
    data.append({"range": f"'{SEZNAMY_ZAPASY_SHEET}'!M2", "values": zapasy_extra_rows})

    # --- Brankáři (zápasy)!K:L – výsledek zápasu z pohledu LIT + příznak
    # "vychytaná výhra" (V/VP), mimo IMPORTRANGE spill A:J. MATCH pod
    # ARRAYFORMULA se zřetězeným polem jako lookup_value i lookup_array
    # (VLOOKUP+`{}` i INDEX/MATCH) se choval nespolehlivě – vždy vrátilo
    # výsledek prvního řádku, ne správný. Stejné řešení jako u Zápasy!M:N
    # výše: obyčejný (ne ARRAYFORMULA) vzorec po řádcích, se skalárním
    # lookup_value (jen $A{row}/$B{row}), ne polem – MATCH se skalárem je
    # spolehlivý stejně jako všude jinde v projektu.
    data.append(
        {
            "range": f"'{SEZNAMY_GOALIES_LOG_SHEET}'!K1",
            "values": [["výsledek", "vychytaná výhra"]],
        }
    )
    goalies_extra_rows = []
    for row in range(2, 2 + EXTRA_COLUMN_ROWS):
        vysledek = (
            f'=IF($A{row}="";"";IFERROR(INDEX({ZAPASY_TYM}!$G$2:$G${ROWS};'
            f'MATCH($A{row}&"|"&$B{row};'
            f'{ZAPASY_TYM}!$A$2:$A${ROWS}&"|"&{ZAPASY_TYM}!$B$2:$B${ROWS};0));""))'
        )
        vychytana_vyhra = f'=IF(K{row}="";"";IF(OR(K{row}="V";K{row}="VP");1;0))'
        goalies_extra_rows.append([vysledek, vychytana_vyhra])
    data.append({"range": f"'{SEZNAMY_GOALIES_LOG_SHEET}'!K2", "values": goalies_extra_rows})

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

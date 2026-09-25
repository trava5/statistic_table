"""Jednorázový skript: postaví v LEAGUE_V2_SPREADSHEET_ID („Liga 2.0“)
zrcadlové listy syrových dat z DB tabulky (LEAGUE_DB_SPREADSHEET_ID), jeden
list = jeden `IMPORTRANGE`.

Listy mají záměrně STEJNÁ jména jako v DB, takže `build_league_aggregate_
sheets.py` a `build_league_team_template.py` fungují beze změny – čtou
z listu podle jména, ne podle toho, jestli je to syrová data od Pythonu,
nebo zrcadlo přes IMPORTRANGE.

Po prvním spuštění je potřeba **ručně** otevřít Liga 2.0 v prohlížeči a
kliknout na „Povolit přístup“ u prvního IMPORTRANGE vzorce – Google to
vyžaduje jednou za dvojici tabulek (DB → Liga 2.0), nejde to přes API.
Dokud se to nepotvrdí, buňky ukazují chybu (#REF!/„Načítání…“).

Použití:
    .venv\\Scripts\\python.exe scripts\\build_league_v2_mirrors.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_GOALIES_LOG_SHEET,
    LEAGUE_GOLY_SHEET,
    LEAGUE_PORADI_SHEET,
    LEAGUE_SKATERS_LOG_SHEET,
    LEAGUE_SKUPINY_SHEET,
    LEAGUE_VYLOUCENI_SHEET,
    LEAGUE_ZAPASY_SHEET,
    LEAGUE_ZAPASY_TYM_SHEET,
    get_credentials,
    load_config,
    require_league_db_spreadsheet_id,
    require_league_v2_spreadsheet_id,
)

# Jméno listu -> poslední sloupec s daty (viz *_HEADER v config.py), s malou
# rezervou. Řádky bez potřeby přesnosti – 5000 je víc než na celou sezónu.
MIRRORED_SHEETS = {
    LEAGUE_ZAPASY_SHEET: "O",
    LEAGUE_ZAPASY_TYM_SHEET: "T",
    LEAGUE_GOLY_SHEET: "H",
    LEAGUE_VYLOUCENI_SHEET: "G",
    LEAGUE_SKATERS_LOG_SHEET: "J",
    LEAGUE_GOALIES_LOG_SHEET: "L",
    LEAGUE_PORADI_SHEET: "D",
    LEAGUE_SKUPINY_SHEET: "B",
}
ROWS = 5000


def main() -> None:
    config = load_config()
    db_id = require_league_db_spreadsheet_id(config)
    v2_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    meta = service.spreadsheets().get(spreadsheetId=v2_id).execute()
    titles = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    sheet_names = list(MIRRORED_SHEETS)

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
    for name, last_col in MIRRORED_SHEETS.items():
        formula = f'=IMPORTRANGE("{db_id}"; "\'{name}\'!A1:{last_col}{ROWS}")'
        data.append({"range": f"'{name}'!A1", "values": [[formula]]})
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=v2_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Zapsáno {len(data)} IMPORTRANGE vzorců do Liga 2.0.")
    print(
        "Teď otevři Liga 2.0 v prohlížeči a u prvního listu klikni na "
        "„Povolit přístup“ – jinak zůstanou buňky v chybě."
    )


if __name__ == "__main__":
    main()

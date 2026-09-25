"""Jednorázový skript: postaví listy `Bruslaři - liga` a `Brankáři - liga`
(sezónní součty za celou ligu, jeden řádek na hráče) jako vzorce nad syrovým
logem `*-liga (zápasy)`, místo aby je Python přepočítával a přepisoval.

Spouští se ručně jednou (při zakládání ligové tabulky, nebo když je potřeba
listy přestavět). `league sync-games` do těchto dvou listů dál nezapisuje nic
– jen do `*-liga (zápasy)`, ze kterých si vzorce samy dopočítají zbytek.
Vzorce používají `;` jako oddělovač argumentů (tabulka je v cs_CZ locale).

Tvar výstupních sloupců je záměrně stejný, jaký dřív zapisoval Python
(LEAGUE_SKATERS_HEADER / LEAGUE_GOALIES_HEADER v config.py) – list
„Tým – šablona“ (`scripts/build_league_team_template.py`) na něj odkazuje
a nemusí se kvůli tomuto přechodu měnit.

Použití:
    .venv\\Scripts\\python.exe scripts\\build_league_aggregate_sheets.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_GOALIES_LOG_SHEET,
    LEAGUE_GOALIES_SHEET,
    LEAGUE_SKATERS_LOG_SHEET,
    LEAGUE_SKATERS_SHEET,
    get_credentials,
    load_config,
    require_league_v2_spreadsheet_id,
)

BR_LOG = f"'{LEAGUE_SKATERS_LOG_SHEET}'"
GO_LOG = f"'{LEAGUE_GOALIES_LOG_SHEET}'"


def main() -> None:
    config = load_config()
    spreadsheet_id = require_league_v2_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()["sheets"]
    }
    missing = [name for name in (LEAGUE_SKATERS_SHEET, LEAGUE_GOALIES_SHEET) if name not in titles]
    if missing:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": n}}} for n in missing]},
        ).execute()

    # Vyčistit případná stará (dřív Pythonem zapsaná) data před vzorcem.
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{LEAGUE_SKATERS_SHEET}'!A1:Z1000000"
    ).execute()
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{LEAGUE_GOALIES_SHEET}'!A1:Z1000000"
    ).execute()

    skater_query = (
        f"=QUERY({BR_LOG}!A:J;\"select B, max(C), D, max(E), count(A), sum(F), sum(G), "
        f"sum(H), sum(I), sum(J) where B <> '' group by B, D order by sum(H) desc "
        f"label B 'tým', max(C) 'číslo', D 'hráč', max(E) 'post', count(A) 'Z', "
        f"sum(F) 'G', sum(G) 'A', sum(H) 'B', sum(I) 'TM', sum(J) '+/-'\";1)"
    )
    goalie_query = (
        f"=QUERY({GO_LOG}!A:L;\"select B, max(C), D, count(A), sum(G), sum(G)/count(A), "
        f"sum(I), sum(J), sum(K) where B <> '' group by B, D order by sum(G) "
        f"label B 'tým', max(C) 'číslo', D 'hráč', count(A) 'Z', "
        f"sum(G) 'obdržené góly', sum(G)/count(A) 'obdržené góly/zápas', "
        f"sum(I) 'G', sum(J) 'A', sum(K) 'TM'\";1)"
    )

    data = [
        {"range": f"'{LEAGUE_SKATERS_SHEET}'!A1", "values": [[skater_query]]},
        {"range": f"'{LEAGUE_GOALIES_SHEET}'!A1", "values": [[goalie_query]]},
        # QUERY s group by dá jen 9 sloupců (A:I) – Výhry/Shutouty potřebují
        # podmíněné počítání přes zápasy, což GViz QUERY samo neumí (žádné
        # SUMIF uvnitř group by), proto zvlášť jako ARRAYFORMULA+COUNTIFS.
        {"range": f"'{LEAGUE_GOALIES_SHEET}'!J1", "values": [["Výhry", "Shutouty"]]},
        {
            "range": f"'{LEAGUE_GOALIES_SHEET}'!J2",
            "values": [[
                "=ARRAYFORMULA(IF($A2:$A500=\"\";\"\";"
                f"COUNTIFS({GO_LOG}!$B:$B;$A2:$A500;{GO_LOG}!$D:$D;$C2:$C500;"
                f"{GO_LOG}!$L:$L;\"V\")+"
                f"COUNTIFS({GO_LOG}!$B:$B;$A2:$A500;{GO_LOG}!$D:$D;$C2:$C500;"
                f"{GO_LOG}!$L:$L;\"VP\")))",
                "=ARRAYFORMULA(IF($A2:$A500=\"\";\"\";"
                f"COUNTIFS({GO_LOG}!$B:$B;$A2:$A500;{GO_LOG}!$D:$D;$C2:$C500;"
                f"{GO_LOG}!$G:$G;0)))",
            ]],
        },
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Vzorce zapsány do '{LEAGUE_SKATERS_SHEET}' a '{LEAGUE_GOALIES_SHEET}'.")


if __name__ == "__main__":
    main()

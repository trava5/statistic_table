"""Jednorázový skript: znovu postaví list `Seznam hráčů` v produkční tabulce
Seznamy (`SPREADSHEET_ID`), smazaný při přesunu osobních údajů do soukromé
tabulky (viz PLAN.MD, 2. 10. 2026).

Smazání rozbilo vzorce v listech Bodování/Brankáři (INDEX/MATCH proti
`'Seznam hráčů'!...`) – produkční tabulka je sice od cutoveru (26. 9. 2026)
zamrzlá a nedostává nové zápasy, ale pořád slouží jako historický záznam
sezóny do té doby, takže má zůstat čitelná.

Obnovený list NENÍ čistý `IMPORTRANGE` mirror jako u Seznamy 2.0 – kombinuje
dva zdroje:
- sloupce A:F a H:I (index, Příjmení, Jméno, č. reg., číslo, post, Z-status,
  poznámka) – `IMPORTRANGE` ze soukromé tabulky (SEZNAMY_PRIVATE_SPREADSHEET_ID),
  neosobní administrativní údaje,
- sloupec G (Z = počet odehraných zápasů) a P:S (pomocné sloupce góly/
  asistence/body/klíč řazení pro řazení v Bodování) – **místní vzorce**
  počítané přímo z produkční `Sestavy`/`Zápasy`, přesně stejné znění, jaké
  mělo původní (smazané) `Seznam hráčů` (zjištěno z formulí zachovaných
  i v soukromé tabulce, kde ale po kopii ukazují #REF! – `Sestavy`/`Zápasy`
  tam nejsou). Tyhle sloupce IMPORTRANGE záměrně NEpokrývá – byl by to jen
  přenos už vypočtené (a v soukromé tabulce rozbité) hodnoty, ne čerstvý
  přepočet proti aktuální produkční tabulce.

Osobní sloupce (J+: pojišťovna, rodné číslo, telefon, e-mail) se do
produkční tabulky vůbec nevrací – to je celý smysl přesunu.

Použití:
    .venv\\Scripts\\python.exe scripts\\restore_production_seznam_hracu.py
"""

from __future__ import annotations

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAM_HRACU_DATA_START_ROW,
    SEZNAM_HRACU_SHEET,
    get_credentials,
    load_config,
    require_seznamy_private_spreadsheet_id,
)

# Sestavy: F = počet brankářů, G = brankář, který chytal, H:N = obránci (7),
# O:AB = útočníci (14) – viz PROJECT.MD. Sloupec "Z" počítá, jestli se jméno
# hráče objevilo kdekoliv v G:AB (brankář nebo hráč do pole) v daném zápase.
SESTAVY_LINEUP_COLS = [
    "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z", "AA", "AB",
]
LAST_ROW = 60  # headroom nad původních 34 hráčů, Bodování stejně čte jen B3:B34


def _z_formula(row: int) -> str:
    terms = "+".join(
        f"COUNTIFS(Sestavy!${c}$6:${c}$500;B{row};Sestavy!$AD$6:$AD$500;1)"
        for c in SESTAVY_LINEUP_COLS
    )
    return f'=IF(B{row}="";"";{terms})'


def _pom_formulas(row: int) -> tuple[str, str, str, str]:
    goly = f"=IF(B{row}=\"\";\"\";COUNTIF('Zápasy'!$J$6:$T$500;B{row}))"
    asistence = f"=IF(B{row}=\"\";\"\";COUNTIF('Zápasy'!$U$6:$AM$500;B{row}))"
    body = f'=IF(B{row}="";"";P{row}+Q{row})'
    klic = (
        f'=IF(B{row}="";"";R{row}*1000000000+P{row}*1000000+'
        f"IF(G{row}=0;0;999-G{row})*1000+(1000-ROW()))"
    )
    return goly, asistence, body, klic


def main() -> None:
    config = load_config()
    production_id = config.spreadsheet_id
    private_id = require_seznamy_private_spreadsheet_id(config)
    service = build("sheets", "v4", credentials=get_credentials(config))

    titles = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in service.spreadsheets().get(spreadsheetId=production_id).execute()["sheets"]
    }
    if SEZNAM_HRACU_SHEET not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=production_id,
            body={"requests": [{"addSheet": {"properties": {"title": SEZNAM_HRACU_SHEET}}}]},
        ).execute()

    data = [
        {
            "range": f"'{SEZNAM_HRACU_SHEET}'!A1",
            "values": [[f'=IMPORTRANGE("{private_id}"; "\'{SEZNAM_HRACU_SHEET}\'!A1:F1000")']],
        },
        {
            "range": f"'{SEZNAM_HRACU_SHEET}'!H1",
            "values": [[f'=IMPORTRANGE("{private_id}"; "\'{SEZNAM_HRACU_SHEET}\'!H1:I1000")']],
        },
        {"range": f"'{SEZNAM_HRACU_SHEET}'!G{SEZNAM_HRACU_DATA_START_ROW - 1}", "values": [["Z"]]},
        {
            "range": f"'{SEZNAM_HRACU_SHEET}'!P{SEZNAM_HRACU_DATA_START_ROW - 1}",
            "values": [["góly (pom.)", "asistence (pom.)", "body (pom.)", "klíč řazení (pom.)"]],
        },
    ]
    for row in range(SEZNAM_HRACU_DATA_START_ROW, LAST_ROW + 1):
        data.append({"range": f"'{SEZNAM_HRACU_SHEET}'!G{row}", "values": [[_z_formula(row)]]})
        data.append(
            {"range": f"'{SEZNAM_HRACU_SHEET}'!P{row}", "values": [list(_pom_formulas(row))]}
        )

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=production_id, body={"valueInputOption": "USER_ENTERED", "data": data}
    ).execute()
    print(f"Obnoveno {len(data)} rozsahů v '{SEZNAM_HRACU_SHEET}' (produkční Seznamy).")
    print(
        "Teď otevři produkční Seznamy v prohlížeči a klikni na „Povolit přístup“ "
        "u IMPORTRANGE ze soukromé tabulky."
    )


if __name__ == "__main__":
    main()

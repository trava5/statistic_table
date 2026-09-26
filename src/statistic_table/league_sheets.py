from __future__ import annotations

import logging

from googleapiclient.discovery import build

from statistic_table.config import (
    LEAGUE_GOALIES_LOG_HEADER,
    LEAGUE_GOALIES_LOG_SHEET,
    LEAGUE_GOLY_HEADER,
    LEAGUE_GOLY_SHEET,
    LEAGUE_PORADI_HEADER,
    LEAGUE_PORADI_SHEET,
    LEAGUE_SKATERS_LOG_HEADER,
    LEAGUE_SKATERS_LOG_SHEET,
    LEAGUE_SKUPINY_HEADER,
    LEAGUE_SKUPINY_SHEET,
    LEAGUE_TEAM_NAME_CELL,
    LEAGUE_TEAM_TEMPLATE_SHEET,
    LEAGUE_VYLOUCENI_HEADER,
    LEAGUE_VYLOUCENI_SHEET,
    LEAGUE_ZAPASY_HEADER,
    LEAGUE_ZAPASY_SHEET,
    LEAGUE_ZAPASY_TYM_HEADER,
    LEAGUE_ZAPASY_TYM_SHEET,
    Config,
    get_credentials,
)
from statistic_table.league_model import (
    LeagueGame,
    LeagueGoal,
    LeagueGoalieStat,
    LeaguePenalty,
    LeagueSkaterStat,
)
from statistic_table.league_stats import team_perspective_rows
from statistic_table.standings import fetch_standings_html, parse_standings

RAW_SHEETS = (
    (LEAGUE_ZAPASY_SHEET, LEAGUE_ZAPASY_HEADER),
    (LEAGUE_ZAPASY_TYM_SHEET, LEAGUE_ZAPASY_TYM_HEADER),
    (LEAGUE_GOLY_SHEET, LEAGUE_GOLY_HEADER),
    (LEAGUE_VYLOUCENI_SHEET, LEAGUE_VYLOUCENI_HEADER),
    (LEAGUE_SKATERS_LOG_SHEET, LEAGUE_SKATERS_LOG_HEADER),
    (LEAGUE_GOALIES_LOG_SHEET, LEAGUE_GOALIES_LOG_HEADER),
    (LEAGUE_PORADI_SHEET, LEAGUE_PORADI_HEADER),
    (LEAGUE_SKUPINY_SHEET, LEAGUE_SKUPINY_HEADER),
)
# Bruslaři/Brankáři - liga (sezónní součty) záměrně NEJSOU v RAW_SHEETS – jsou
# to vzorce (QUERY group by nad *_LOG_SHEET), postavené jednorázově skriptem
# scripts/build_league_aggregate_sheets.py, Python do nich nikdy nezapisuje.

logger = logging.getLogger("statistic_table")


def _service(config: Config):
    return build("sheets", "v4", credentials=get_credentials(config))


def _sheet_titles(config: Config, spreadsheet_id: str) -> dict[str, int]:
    meta = _service(config).spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def ensure_league_sheets(config: Config, spreadsheet_id: str) -> None:
    """Založí syrové listy (viz RAW_SHEETS) s hlavičkou, pokud ještě neexistují."""
    titles = _sheet_titles(config, spreadsheet_id)
    missing = [(name, header) for name, header in RAW_SHEETS if name not in titles]
    if missing:
        body = {
            "requests": [
                {"addSheet": {"properties": {"title": name}}} for name, _ in missing
            ]
        }
        _service(config).spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
    for name, header in missing:
        _write_row(config, spreadsheet_id, f"{name}!A1", header)


def _protect(value):
    """S valueInputOption=USER_ENTERED bere Sheets text začínající na +-=@ jako
    vzorec (např. hlavička "+/-" skončí jako #ERROR!). Vodicí apostrof vynutí
    text, stejně jako při ručním zápisu do buňky."""
    if isinstance(value, str) and value[:1] in ("+", "-", "=", "@"):
        return "'" + value
    return value


def _protect_row(row: list) -> list:
    return [_protect(v) for v in row]


def _write_row(config: Config, spreadsheet_id: str, range_: str, values: list) -> None:
    _service(config).spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        body={"values": [_protect_row(values)]},
    ).execute()


def _append_rows(
    config: Config, spreadsheet_id: str, sheet: str, rows: list[list]
) -> str | None:
    """Vrací rozsah, kam se skutečně zapsalo (`updates.updatedRange`), nebo
    None, pokud nebylo co zapsat – použito pro rollback v `_append_all_or_nothing`."""
    if not rows:
        return None
    result = (
        _service(config)
        .spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet}!A2",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [_protect_row(row) for row in rows]},
        )
        .execute()
    )
    return result.get("updates", {}).get("updatedRange")


def _append_all_or_nothing(
    config: Config, spreadsheet_id: str, writes: list[tuple[str, list[list]]]
) -> None:
    """Zapíše víc listů (`_append_rows` po jednom, Sheets API nemá atomický
    append přes víc listů najednou). Dedup dalšího běhu (`read_known_game_ids`)
    se dívá jen na první zapisovaný list (`LEAGUE_ZAPASY_SHEET`) – pokud by
    zápis pozdějšího listu (Góly/Vyloučení/Bruslaři/Brankáři) selhal, zápas by
    se navenek tvářil jako už synchronizovaný, ale chyběla by mu část dat, a
    žádný další běh by to už nedoplnil. Proto se při chybě smažou i rozsahy
    zapsané předchozími kroky v tomto volání (kompenzační transakce) – zápas
    tak buď skončí zapsaný celý, nebo vůbec, a příští běh ho zkusí znovu."""
    written: list[str] = []
    try:
        for sheet, rows in writes:
            updated_range = _append_rows(config, spreadsheet_id, sheet, rows)
            if updated_range:
                written.append(updated_range)
    except Exception:
        for range_ in written:
            try:
                _service(config).spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id, range=range_
                ).execute()
            except Exception:  # noqa: BLE001 – rollback je best-effort, nesmí zastřít původní chybu
                logger.warning("Rollback rozsahu %s po chybě zápisu se nezdařil", range_)
        raise


def read_known_game_ids(config: Config, spreadsheet_id: str) -> set[int]:
    values = (
        _service(config)
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{LEAGUE_ZAPASY_SHEET}!A2:A1000000")
        .execute()
        .get("values", [])
    )
    return {int(row[0]) for row in values if row and row[0]}


def _period_score(periods: list[tuple[int, int]], index: int) -> str:
    if index >= len(periods):
        return ""
    home, away = periods[index]
    return f"{home}:{away}"


def append_game(
    config: Config,
    spreadsheet_id: str,
    game: LeagueGame,
    goals: list[LeagueGoal],
    penalties: list[LeaguePenalty],
    skaters: list[LeagueSkaterStat],
    goalies: list[LeagueGoalieStat],
) -> None:
    """Zapíše jeden zápas a jeho podrobnosti do syrových listů (append, žádný přepis)."""
    game_row = [
        game.game_id,
        game.game_number,
        game.date,
        game.home_team,
        game.away_team,
        game.home_score,
        game.away_score,
        _period_score(game.period_scores, 0),
        _period_score(game.period_scores, 1),
        _period_score(game.period_scores, 2),
        f"{game.ot_score[0]}:{game.ot_score[1]}" if game.ot_score else "",
        game.ending or "",
        game.attendance if game.attendance is not None else "",
        game.referees or "",
        game.round if game.round is not None else "",
    ]
    goal_rows = [
        [g.game_id, g.team, g.period, g.time, g.scorer, g.assist1, g.assist2, g.situation]
        for g in goals
    ]
    penalty_rows = [
        [p.game_id, p.team, p.period, p.time, p.player, p.minutes, p.reason] for p in penalties
    ]
    skater_rows = [
        [
            s.game_id, s.team, s.jersey_number, s.name, s.position,
            s.goals, s.assists, s.points, s.penalty_minutes, s.plus_minus,
        ]
        for s in skaters
    ]
    tym_rows = team_perspective_rows(game, goals, penalties)
    result_by_team = {row[1]: row[7] for row in tym_rows}  # tým -> výsledek (V/VP/PP/P)

    goalie_rows = [
        [
            g.game_id, g.team, g.jersey_number, g.name, g.time_on_ice,
            g.saves, g.goals_against, g.save_percentage, g.goals, g.assists, g.penalty_minutes,
            result_by_team.get(g.team, ""),
        ]
        for g in goalies
    ]

    _append_all_or_nothing(
        config,
        spreadsheet_id,
        [
            (LEAGUE_ZAPASY_SHEET, [game_row]),
            (LEAGUE_ZAPASY_TYM_SHEET, tym_rows),
            (LEAGUE_GOLY_SHEET, goal_rows),
            (LEAGUE_VYLOUCENI_SHEET, penalty_rows),
            (LEAGUE_SKATERS_LOG_SHEET, skater_rows),
            (LEAGUE_GOALIES_LOG_SHEET, goalie_rows),
        ],
    )


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _overwrite_sheet(
    config: Config, spreadsheet_id: str, sheet: str, header: list[str], rows: list[list]
) -> None:
    service = _service(config)
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet}!A1:Z1000000"
    ).execute()
    # `values().clear()` maže jen obsah, ne formát buněk – bez tohoto by nový
    # sloupec zdědil např. formát "TOI" (mm:ss) po starším rozvržení listu a
    # číslo jako 0 by se zobrazilo jako čas "0:00:00".
    sheet_id = _sheet_titles(config, spreadsheet_id).get(sheet)
    if sheet_id is not None:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "repeatCell": {
                            "range": {"sheetId": sheet_id},
                            "cell": {"userEnteredFormat": {}},
                            "fields": "userEnteredFormat.numberFormat",
                        }
                    }
                ]
            },
        ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [_protect_row(header), *(_protect_row(r) for r in rows)]},
    ).execute()


def refresh_group_membership(config: Config, spreadsheet_id: str) -> None:
    """Obnoví LEAGUE_SKUPINY_SHEET živým scrapem oficiální tabulky (členství
    ve skupině se v sezóně nemění, ale scrapuje se znovu při každém běhu, ať
    je fakt v DB vždy aktuální). Při chybě ponechá, co už je v tabulce
    uložené – bez skupin nejde spočítat pořadí, ale nesmí to shodit sync."""
    try:
        standings = parse_standings(fetch_standings_html())
    except Exception:  # noqa: BLE001 – nepovinný krok, nesmí shodit sync
        return
    rows = [[s.team, s.group] for s in standings]
    _overwrite_sheet(config, spreadsheet_id, LEAGUE_SKUPINY_SHEET, LEAGUE_SKUPINY_HEADER, rows)


def read_group_membership(config: Config, spreadsheet_id: str) -> dict[str, int]:
    values = (
        _service(config)
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{LEAGUE_SKUPINY_SHEET}!A2:B1000000")
        .execute()
        .get("values", [])
    )
    return {row[0]: _int(row[1]) for row in values if len(row) >= 2 and row[0] and row[1]}


def recompute_standings_history(config: Config, spreadsheet_id: str) -> None:
    """Přepočte pořadí po každém odehraném kole (LEAGUE_PORADI_SHEET) z vlastní
    tabulky Zápasy - liga (tým) – web historii tabulky nezveřejňuje, takže se
    pořadí po každém kole musí dopočítat zpětně z výsledků (viz PROJECT.MD,
    „Pořadí po kole“). Skupina (Skupina 1/2) se čte z LEAGUE_SKUPINY_SHEET
    (obnovuje `refresh_group_membership`), ne živým scrapem zvlášť."""
    team_groups = read_group_membership(config, spreadsheet_id)

    rows = (
        _service(config)
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{LEAGUE_ZAPASY_TYM_SHEET}!A2:T1000000")
        .execute()
        .get("values", [])
    )
    contributions = []  # (kolo, tym, body, gf, ga)
    max_round = 0
    for row in rows:
        if len(row) < 20 or not row[19]:
            continue
        kolo = _int(row[19])
        tym = row[1]
        contributions.append((kolo, tym, _int(row[8]), _int(row[5]), _int(row[6])))
        max_round = max(max_round, kolo)

    def _sort_key(item):
        entry = item[1]
        return (-entry["points"], -(entry["gf"] - entry["ga"]), -entry["gf"])

    result_rows = []
    for round_n in range(1, max_round + 1):
        totals: dict[str, dict] = {}
        for kolo, tym, body, gf, ga in contributions:
            if kolo > round_n:
                continue
            entry = totals.setdefault(tym, {"points": 0, "gf": 0, "ga": 0})
            entry["points"] += body
            entry["gf"] += gf
            entry["ga"] += ga

        by_group: dict[int, list] = {}
        for tym, entry in totals.items():
            by_group.setdefault(team_groups.get(tym, 0), []).append((tym, entry))

        for _group, teams in by_group.items():
            teams.sort(key=_sort_key)
            for position, (tym, _entry) in enumerate(teams, start=1):
                result_rows.append([round_n, "", tym, position])

    _overwrite_sheet(config, spreadsheet_id, LEAGUE_PORADI_SHEET, LEAGUE_PORADI_HEADER, result_rows)


def read_known_teams(config: Config, spreadsheet_id: str) -> set[str]:
    """Týmy, které se už objevily v syrových datech (ze soupisek bruslařů)."""
    values = (
        _service(config)
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{LEAGUE_SKATERS_LOG_SHEET}!B2:B1000000")
        .execute()
        .get("values", [])
    )
    return {row[0] for row in values if row and row[0]}


def team_sheet_title(team: str) -> str:
    return team[:100]  # limit Google Sheets na název listu


def ensure_team_sheet(
    config: Config, spreadsheet_id: str, team: str, *, dry_run: bool = False
) -> bool:
    """Naklonuje šablonový list pro daný tým, pokud ještě neexistuje. Vrací True,
    pokud list chybí (a byl založen, pokud `dry_run` není True). Skript nikdy
    nezapisuje do vzorců šablony, jen do buňky se jménem týmu (LEAGUE_TEAM_NAME_CELL)."""
    titles = _sheet_titles(config, spreadsheet_id)
    title = team_sheet_title(team)
    if title in titles:
        return False
    if dry_run:
        return True
    template_id = titles.get(LEAGUE_TEAM_TEMPLATE_SHEET)
    if template_id is None:
        raise RuntimeError(
            f"Šablonový list '{LEAGUE_TEAM_TEMPLATE_SHEET}' v tabulce chybí – spusť "
            "scripts/build_league_team_template.py, který ho založí se vzorci QUERY/SUMIF."
        )
    _service(config).spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "duplicateSheet": {
                        "sourceSheetId": template_id,
                        "newSheetName": title,
                    }
                }
            ]
        },
    ).execute()
    _write_row(config, spreadsheet_id, f"'{title}'!{LEAGUE_TEAM_NAME_CELL}", [team])
    return True

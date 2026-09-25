from __future__ import annotations

from collections import Counter

from googleapiclient.discovery import build

from statistic_table.config import (
    SEZNAMY_GOALIES_LOG_HEADER,
    SEZNAMY_GOALIES_LOG_SHEET,
    SEZNAMY_GOLY_HEADER,
    SEZNAMY_GOLY_SHEET,
    SEZNAMY_SKATERS_LOG_HEADER,
    SEZNAMY_SKATERS_LOG_SHEET,
    SEZNAMY_VYLOUCENI_HEADER,
    SEZNAMY_VYLOUCENI_SHEET,
    SEZNAMY_ZAPASY_HEADER,
    SEZNAMY_ZAPASY_SHEET,
    SEZNAMY_ZAPASY_TYM_HEADER,
    SEZNAMY_ZAPASY_TYM_SHEET,
    Config,
    get_credentials,
)
from statistic_table.model import Game, TeamSheet
from statistic_table.players import identify_lit, opponent_alias
from statistic_table.stats import (
    goal_situation_counts,
    note,
    penalty_totals,
    power_plays,
    third_and_relative_time,
)

RAW_SHEETS = (
    (SEZNAMY_ZAPASY_SHEET, SEZNAMY_ZAPASY_HEADER),
    (SEZNAMY_ZAPASY_TYM_SHEET, SEZNAMY_ZAPASY_TYM_HEADER),
    (SEZNAMY_GOLY_SHEET, SEZNAMY_GOLY_HEADER),
    (SEZNAMY_VYLOUCENI_SHEET, SEZNAMY_VYLOUCENI_HEADER),
    (SEZNAMY_SKATERS_LOG_SHEET, SEZNAMY_SKATERS_LOG_HEADER),
    (SEZNAMY_GOALIES_LOG_SHEET, SEZNAMY_GOALIES_LOG_HEADER),
)


def _service(config: Config):
    return build("sheets", "v4", credentials=get_credentials(config))


def _sheet_titles(config: Config, spreadsheet_id: str) -> dict[str, int]:
    meta = _service(config).spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def ensure_seznamy_sheets(config: Config, spreadsheet_id: str) -> None:
    """Založí syrové listy (viz RAW_SHEETS) s hlavičkou, pokud ještě neexistují."""
    titles = _sheet_titles(config, spreadsheet_id)
    missing = [(name, header) for name, header in RAW_SHEETS if name not in titles]
    if missing:
        body = {
            "requests": [{"addSheet": {"properties": {"title": name}}} for name, _ in missing]
        }
        _service(config).spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
    for name, header in missing:
        _write_row(config, spreadsheet_id, f"'{name}'!A1", header)


# RAW (ne USER_ENTERED): DB listy nikdy neobsahují vzorce, jen syrová data od
# Pythonu, takže se nemusí řešit apostrofový trik proti "+-=@" na začátku
# textu (viz league_sheets._protect) – RAW navíc nechá časy jako "29:06"
# být, zatímco USER_ENTERED je u delších hodnot samo přeformátovává na
# "29:06:00" (stejná třída chyby jako dřívější TOI/"0:00:00" u Ligy).
def _write_row(config: Config, spreadsheet_id: str, range_: str, values: list) -> None:
    _service(config).spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="RAW",
        body={"values": [values]},
    ).execute()


def _append_rows(config: Config, spreadsheet_id: str, sheet: str, rows: list[list]) -> None:
    if not rows:
        return
    _service(config).spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet}'!A2",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


def read_known_game_numbers(config: Config, spreadsheet_id: str) -> set[str]:
    values = (
        _service(config)
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{SEZNAMY_ZAPASY_SHEET}'!A2:A1000000")
        .execute()
        .get("values", [])
    )
    return {row[0] for row in values if row and row[0]}


def _format_date(pdf_date: str) -> str:
    day, month, year = pdf_date.split(".")
    return f"{int(day)}.{int(month)}.{year}"


def _period_score_cells(game: Game) -> list[str]:
    periods = list(game.period_scores) + [None] * (3 - len(game.period_scores))
    cells = [f"{p[0]}:{p[1]}" if p is not None else "" for p in periods[:3]]
    cells.append(f"{game.ot_score[0]}:{game.ot_score[1]}" if game.ot_score else "")
    return cells


def _player_name(team: TeamSheet, number: str) -> str:
    for p in team.roster:
        if p.number == number:
            return f"{p.last_name} {p.first_name}".strip()
    return ""


def _short_name(team: TeamSheet, lit: TeamSheet, config: Config) -> str:
    return config.team_short if team is lit else opponent_alias(team.name)


def _result_and_points(won: bool, ending: str | None) -> tuple[str, int]:
    """Stejné pravidlo jako league_stats._result_and_points (duplikováno
    záměrně, jiný datový model – TeamSheet.penalties/goals místo LeaguePenalty/
    LeagueGoal, viz PROJECT.MD)."""
    if ending:
        return ("VP", 2) if won else ("PP", 1)
    return ("V", 3) if won else ("P", 0)


def _team_row(
    game: Game,
    team: TeamSheet,
    opponent: TeamSheet,
    short: str,
    opponent_short: str,
    *,
    is_home: bool,
) -> list:
    """Výsledek, body, přesilovky/oslabení z pohledu `team` – composite pravidlo
    s časovým párováním trestů (stejné jako league_stats.team_perspective_rows),
    proto Python, ne vzorec (viz PROJECT.MD)."""
    score_for, score_against = (
        (game.home_score, game.away_score) if is_home else (game.away_score, game.home_score)
    )
    result, points = _result_and_points(score_for > score_against, game.ending)

    pp = power_plays(team.penalties, opponent.penalties)
    team_goals = goal_situation_counts(team.goals)
    opponent_goals = goal_situation_counts(opponent.goals)
    penalties = penalty_totals(team.penalties)

    return [
        game.number, short, opponent_short, "doma" if is_home else "venku",
        score_for, score_against, result, points,
        pp.home_power_plays, team_goals.pp_goals,
        pp.away_power_plays, opponent_goals.pp_goals, team_goals.sh_goals,
        penalties.count, penalties.minutes,
    ]


def build_seznamy_rows(game: Game, config: Config) -> dict[str, list[list]]:
    """Čistá funkce (bez sítě): rozloží naparsovaný zápas na řádky pro 5 syrových
    listů Seznamy DB, symetricky pro oba týmy. Identita hráče (jméno, registrace)
    je soběstačná v rámci jednoho PDF – nepotřebuje Seznam hráčů, ten se používá
    jen pro zápis do produkční tabulky Seznamy (viz importer.build_import)."""
    lit, _opponent = identify_lit(game, config)
    date = _format_date(game.date)
    home_short = _short_name(game.home, lit, config)
    away_short = _short_name(game.away, lit, config)

    zapasy_row = [
        game.number, date, home_short, away_short, game.home_score, game.away_score,
        note(game), *_period_score_cells(game),
    ]
    zapasy_tym_rows = [
        _team_row(game, game.home, game.away, home_short, away_short, is_home=True),
        _team_row(game, game.away, game.home, away_short, home_short, is_home=False),
    ]

    goly_rows: list[list] = []
    vylouceni_rows: list[list] = []
    bruslari_rows: list[list] = []
    brankari_rows: list[list] = []

    for team, short, goals_against in (
        (game.home, home_short, game.away_score),
        (game.away, away_short, game.home_score),
    ):
        for g in team.goals:
            third, rel_time = third_and_relative_time(g.time)
            goly_rows.append([
                game.number, short, third, rel_time,
                _player_name(team, g.scorer_number),
                _player_name(team, g.assist1_number) if g.assist1_number else "",
                _player_name(team, g.assist2_number) if g.assist2_number else "",
                g.situation,
            ])
        for p in team.penalties:
            third, rel_time = third_and_relative_time(p.time)
            vylouceni_rows.append([
                game.number, short, third, rel_time,
                _player_name(team, p.player_number), p.minutes, p.reason, p.start, p.end,
            ])

        goals_by_number = Counter(g.scorer_number for g in team.goals)
        assists_by_number: Counter[str] = Counter()
        for g in team.goals:
            if g.assist1_number:
                assists_by_number[g.assist1_number] += 1
            if g.assist2_number:
                assists_by_number[g.assist2_number] += 1
        tm_by_number: Counter[str] = Counter()
        for p in team.penalties:
            tm_by_number[p.player_number] += p.minutes

        for player in team.roster:
            goals = goals_by_number.get(player.number, 0)
            assists = assists_by_number.get(player.number, 0)
            tm = tm_by_number.get(player.number, 0)
            name = f"{player.last_name} {player.first_name}".strip()
            if player.is_goalkeeper:
                brankari_rows.append([
                    game.number, short, player.number, name, player.registration_number,
                    1 if player.played else 0,
                    goals_against if player.played else "",
                    goals, assists, tm,
                ])
            else:
                bruslari_rows.append([
                    game.number, short, player.number, name, player.registration_number,
                    player.position, 1 if player.played else 0,
                    goals, assists, goals + assists, tm,
                ])

    return {
        SEZNAMY_ZAPASY_SHEET: [zapasy_row],
        SEZNAMY_ZAPASY_TYM_SHEET: zapasy_tym_rows,
        SEZNAMY_GOLY_SHEET: goly_rows,
        SEZNAMY_VYLOUCENI_SHEET: vylouceni_rows,
        SEZNAMY_SKATERS_LOG_SHEET: bruslari_rows,
        SEZNAMY_GOALIES_LOG_SHEET: brankari_rows,
    }


def append_game(config: Config, spreadsheet_id: str, game: Game) -> None:
    """Zapíše zápas do syrových listů Seznamy DB (append), pokud tam ještě
    není (dedup podle čísla zápisu) – bezpečné volat opakovaně při re-importu
    stejného PDF."""
    ensure_seznamy_sheets(config, spreadsheet_id)
    if game.number in read_known_game_numbers(config, spreadsheet_id):
        return
    rows_by_sheet = build_seznamy_rows(game, config)
    for sheet, rows in rows_by_sheet.items():
        _append_rows(config, spreadsheet_id, sheet, rows)

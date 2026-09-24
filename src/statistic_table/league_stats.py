from __future__ import annotations

from collections import Counter

from statistic_table.league_model import LeagueGame, LeagueGoal, LeaguePenalty
from statistic_table.stats import situation_result


def _unmatched_minor_count(
    penalties: list[LeaguePenalty], opponent_penalties: list[LeaguePenalty]
) -> int:
    """Stejné pravidlo jako stats._unmatched_minor_count, jen nad LeaguePenalty
    (má jen `time`, ne pár start/end – pro párování stačí čas začátku)."""
    own_starts = Counter(p.time for p in penalties if p.minutes == 2)
    opponent_starts = Counter(p.time for p in opponent_penalties if p.minutes == 2)
    return sum(max(0, count - opponent_starts.get(start, 0)) for start, count in own_starts.items())


def _result_and_points(won: bool, ending: str | None) -> tuple[str, int]:
    if ending:
        return ("VP", 2) if won else ("PP", 1)
    return ("V", 3) if won else ("P", 0)


def _period_score(periods: list[tuple[int, int]], index: int, *, is_home: bool) -> str:
    if index >= len(periods):
        return ""
    home, away = periods[index]
    return str(home if is_home else away)


def _team_row(
    game: LeagueGame,
    goals: list[LeagueGoal],
    penalties: list[LeaguePenalty],
    *,
    team: str,
    opponent: str,
    is_home: bool,
) -> list:
    score_for, score_against = (
        (game.home_score, game.away_score) if is_home else (game.away_score, game.home_score)
    )
    won = score_for > score_against
    result, points = _result_and_points(won, game.ending)

    team_penalties = [p for p in penalties if p.team == team]
    opponent_penalties = [p for p in penalties if p.team == opponent]
    power_plays = _unmatched_minor_count(opponent_penalties, team_penalties)
    penalty_kills = _unmatched_minor_count(team_penalties, opponent_penalties)

    team_goal_situations = [situation_result(g.situation) for g in goals if g.team == team]
    opponent_goal_situations = [situation_result(g.situation) for g in goals if g.team == opponent]
    pp_goals_for = team_goal_situations.count("pp")
    sh_goals_for = team_goal_situations.count("sh")
    pk_goals_against = opponent_goal_situations.count("pp")

    return [
        game.game_id,
        team,
        opponent,
        game.date,
        "doma" if is_home else "venku",
        score_for,
        score_against,
        result,
        points,
        _period_score(game.period_scores, 0, is_home=is_home),
        _period_score(game.period_scores, 1, is_home=is_home),
        _period_score(game.period_scores, 2, is_home=is_home),
        power_plays,
        pp_goals_for,
        penalty_kills,
        pk_goals_against,
        sh_goals_for,
        len(team_penalties),
        sum(p.minutes for p in team_penalties),
        game.round if game.round is not None else "",
    ]


def team_perspective_rows(
    game: LeagueGame, goals: list[LeagueGoal], penalties: list[LeaguePenalty]
) -> list[list]:
    """Dva řádky (domácí a hosté) s výsledkem už z pohledu daného týmu – stejná
    data, jaká pro LIT dnes počítá list Tým ze sloupců Zápasy!AR:BA, jen bez
    vazby na jeden konkrétní tým (viz šablona per-tým listu, PLAN.MD)."""
    return [
        _team_row(
            game, goals, penalties, team=game.home_team, opponent=game.away_team, is_home=True
        ),
        _team_row(
            game, goals, penalties, team=game.away_team, opponent=game.home_team, is_home=False
        ),
    ]

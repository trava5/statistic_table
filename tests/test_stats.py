from pathlib import Path

import pytest

from statistic_table.model import GamePlayer, Penalty, RosterPlayer, TeamSheet
from statistic_table.pdf_parser import parse_game
from statistic_table.stats import (
    GoalSituationCounts,
    PenaltyTotals,
    PowerPlayStats,
    average_age,
    goal_situation_counts,
    note,
    opponent_birth_years,
    penalty_breakdown,
    penalty_totals,
    power_plays,
    situation_result,
)

PDF_DIR = Path(__file__).parent / "fixtures" / "pdf"
SEASON_YEAR = 2026


def _penalty(start: str, end: str, minutes: int = 2, player_number: str = "1") -> Penalty:
    return Penalty(
        time=start, player_number=player_number, minutes=minutes, reason="X", start=start, end=end
    )


# --- Regresní testy na oba referenční zápasy (hodnoty z PROJECT.MD) ------------


@pytest.fixture(scope="module")
def game_4002():
    return parse_game(PDF_DIR / "4002_lit_pribram.pdf")


@pytest.fixture(scope="module")
def game_4012():
    return parse_game(PDF_DIR / "4012_chomutov_lit.pdf")


def test_power_plays_4002(game_4002):
    assert power_plays(game_4002.home.penalties, game_4002.away.penalties) == PowerPlayStats(6, 7)


def test_power_plays_4012(game_4012):
    assert power_plays(game_4012.home.penalties, game_4012.away.penalties) == PowerPlayStats(8, 6)


def test_goal_situation_counts_4002(game_4002):
    assert goal_situation_counts(game_4002.home.goals) == GoalSituationCounts(1, 0)
    assert goal_situation_counts(game_4002.away.goals) == GoalSituationCounts(0, 1)


def test_goal_situation_counts_4012(game_4012):
    assert goal_situation_counts(game_4012.home.goals) == GoalSituationCounts(2, 0)
    assert goal_situation_counts(game_4012.away.goals) == GoalSituationCounts(1, 0)


def test_penalty_totals_4002(game_4002):
    assert penalty_totals(game_4002.home.penalties) == PenaltyTotals(9, 26)
    assert penalty_totals(game_4002.away.penalties) == PenaltyTotals(7, 14)


def test_penalty_totals_4012(game_4012):
    assert penalty_totals(game_4012.home.penalties) == PenaltyTotals(7, 14)
    assert penalty_totals(game_4012.away.penalties) == PenaltyTotals(9, 18)


def test_opponent_birth_years_4002(game_4002):
    result = opponent_birth_years(game_4002.away)
    assert result.counts == {2006: 1, 2007: 13, 2008: 5}
    assert result.warnings == []


def test_opponent_birth_years_4012(game_4012):
    result = opponent_birth_years(game_4012.home)
    assert result.counts == {2006: 2, 2007: 4, 2008: 11}
    assert result.warnings == []


def test_average_age_4002(game_4002):
    assert round(average_age(game_4002.home, SEASON_YEAR), 2) == 18.79
    assert round(average_age(game_4002.away, SEASON_YEAR), 2) == 18.79


def test_average_age_4012(game_4012):
    assert round(average_age(game_4012.away, SEASON_YEAR), 2) == 18.70
    assert round(average_age(game_4012.home, SEASON_YEAR), 2) == 18.47


def test_note_regulation_game_is_empty(game_4002):
    assert note(game_4002) == ""


# --- situation_result -----------------------------------------------------


@pytest.mark.parametrize(
    ("situation", "expected"),
    [("5/3", "pp"), ("5/4", "pp"), ("4/5", "sh"), ("3/5", "sh"), ("5/5", None), ("", None)],
)
def test_situation_result(situation, expected):
    assert situation_result(situation) == expected


# --- Okrajové případy přesilovek (PLAN.MD Krok 4 – hotovo) -----------------


def test_power_plays_coincidental_minors_fully_offset():
    home = [_penalty("10:00", "12:00")]
    away = [_penalty("10:00", "12:00")]
    assert power_plays(home, away) == PowerPlayStats(0, 0)


def test_power_plays_double_minor_leaves_one_unmatched():
    # Dvojitý menší trest domácích proti jednomu trestu hostů ve stejný čas:
    # jeden pár se vyrovná, zbylý trest je přesilovka hostů.
    home = [
        _penalty("10:00", "12:00", player_number="5"),
        _penalty("10:00", "12:00", player_number="6"),
    ]
    away = [_penalty("10:00", "12:00", player_number="7")]
    assert power_plays(home, away) == PowerPlayStats(0, 1)


def test_power_plays_excludes_ten_minute_penalties():
    home = [_penalty("10:00", "20:00", minutes=10)]
    away: list[Penalty] = []
    assert power_plays(home, away) == PowerPlayStats(0, 0)


def test_power_plays_penalty_served_by_teammate_still_counts():
    home = [
        Penalty(
            time="10:00", player_number="16", minutes=2, reason="DRZP",
            start="10:00", end="12:00", served_by_number="18",
        )
    ]
    away: list[Penalty] = []
    assert power_plays(home, away) == PowerPlayStats(0, 1)


def test_power_plays_different_start_times_do_not_offset():
    home = [_penalty("10:00", "12:00")]
    away = [_penalty("10:05", "12:05")]
    assert power_plays(home, away) == PowerPlayStats(1, 1)


# --- penalty_breakdown ------------------------------------------------------


def _roster_player(last_name: str, jersey: str, reg: str) -> RosterPlayer:
    return RosterPlayer(
        last_name=last_name,
        first_name="X",
        registration_number=reg,
        jersey_number=jersey,
        position="D",
    )


def _game_player(number: str, last_name: str, reg: str) -> GamePlayer:
    return GamePlayer(
        number=number, last_name=last_name.upper(), first_name="X", registration_number=reg,
        position="D", is_goalkeeper=False, played=True,
    )


def test_penalty_breakdown_uses_penalized_player_not_server():
    club_roster = [
        _roster_player("Novák", "16", "1000000016"),
        _roster_player("Svoboda", "18", "1000000018"),
    ]
    team_roster = [
        _game_player("16", "Novák", "1000000016"),
        _game_player("18", "Svoboda", "1000000018"),
    ]
    penalties = [
        Penalty(
            time="52:25", player_number="16", minutes=2, reason="DRZP",
            start="52:25", end="54:25", served_by_number="18",
        )
    ]

    names, minutes = penalty_breakdown(penalties, team_roster, club_roster)

    assert names == ["Novák"]
    assert minutes == [2]


def test_penalty_breakdown_preserves_order():
    club_roster = [
        _roster_player("Novák", "16", "1000000016"),
        _roster_player("Svoboda", "18", "1000000018"),
    ]
    team_roster = [
        _game_player("16", "Novák", "1000000016"),
        _game_player("18", "Svoboda", "1000000018"),
    ]
    penalties = [
        _penalty("05:00", "07:00", player_number="18"),
        _penalty("10:00", "12:00", player_number="16"),
    ]

    names, minutes = penalty_breakdown(penalties, team_roster, club_roster)

    assert names == ["Svoboda", "Novák"]
    assert minutes == [2, 2]


# --- opponent_birth_years okrajové případy ---------------------------------


def test_opponent_birth_years_warns_on_out_of_range_year():
    team = TeamSheet(
        name="Soupeř",
        roster=[_game_player("9", "Starý", "1000002001")],  # rocnik 2001
        goals=[],
        penalties=[],
    )
    result = opponent_birth_years(team)
    assert result.counts == {2001: 1}
    assert len(result.warnings) == 1
    assert "2001" in result.warnings[0]


def test_opponent_birth_years_warns_on_missing_registration():
    team = TeamSheet(
        name="Soupeř", roster=[_game_player("9", "Bezregistrace", "")], goals=[], penalties=[]
    )
    result = opponent_birth_years(team)
    assert result.counts == {}
    assert len(result.warnings) == 1

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from statistic_table.pdf_parser import parse_game

FIXTURES = Path(__file__).parent / "fixtures"
PDF_DIR = FIXTURES / "pdf"

CASES = [
    ("4002_lit_pribram.pdf", "4002_expected.json"),
    ("4012_chomutov_lit.pdf", "4012_expected.json"),
]


def _goal_dict(goal) -> dict:
    return {
        "time": goal.time,
        "scorer_number": goal.scorer_number,
        "assist1_number": goal.assist1_number,
        "assist2_number": goal.assist2_number,
        "situation": goal.situation,
    }


@pytest.mark.parametrize(("pdf_name", "expected_name"), CASES)
def test_parse_game_matches_expected(pdf_name, expected_name):
    expected = json.loads((FIXTURES / expected_name).read_text(encoding="utf-8"))
    game = parse_game(PDF_DIR / pdf_name)

    assert game.number == expected["number"]
    assert game.date == expected["date"]
    assert game.home.name == expected["home_name"]
    assert game.away.name == expected["away_name"]
    assert game.home_score == expected["home_score"]
    assert game.away_score == expected["away_score"]
    assert [list(p) for p in game.period_scores] == expected["period_scores"]
    assert game.ending == expected["ending"]

    assert len(game.home.roster) == expected["home_roster_count"]
    assert len(game.away.roster) == expected["away_roster_count"]
    assert game.home.goalie_number == expected["home_goalie"]
    assert game.away.goalie_number == expected["away_goalie"]

    assert [_goal_dict(g) for g in game.home.goals] == expected["home_goals"]
    assert [_goal_dict(g) for g in game.away.goals] == expected["away_goals"]

    assert len(game.home.penalties) == expected["home_penalties_count"]
    assert sum(p.minutes for p in game.home.penalties) == expected["home_penalties_minutes"]
    assert len(game.away.penalties) == expected["away_penalties_count"]
    assert sum(p.minutes for p in game.away.penalties) == expected["away_penalties_minutes"]


@pytest.mark.parametrize(("pdf_name", "_expected_name"), CASES)
def test_exactly_one_goalkeeper_played_per_team(pdf_name, _expected_name):
    game = parse_game(PDF_DIR / pdf_name)
    for team in (game.home, game.away):
        goalkeepers = [p for p in team.roster if p.is_goalkeeper]
        assert len(goalkeepers) >= 1
        played = [p for p in goalkeepers if p.played]
        assert len(played) == 1
        assert played[0].number == team.goalie_number


def test_asdict_roundtrips_frozen_dataclasses():
    game = parse_game(PDF_DIR / "4002_lit_pribram.pdf")
    assert asdict(game)["number"] == "4002"

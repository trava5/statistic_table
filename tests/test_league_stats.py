from pathlib import Path

from statistic_table.league_scraper import parse_game_detail
from statistic_table.league_stats import team_perspective_rows

FIXTURES = Path(__file__).parent / "fixtures" / "league"
GAME_DETAIL_HTML = (FIXTURES / "game_detail_180718.html").read_text(encoding="utf-8")


def _rows():
    game, goals, penalties, _skaters, _goalies = parse_game_detail(
        GAME_DETAIL_HTML, 180718, round_number=2
    )
    rows = team_perspective_rows(game, goals, penalties)
    by_team = {row[1]: row for row in rows}
    return by_team


# Sloupce (viz LEAGUE_ZAPASY_TYM_HEADER v config.py):
# 0 game_id, 1 tým, 2 soupeř, 3 datum, 4 doma/venku, 5 skóre tým, 6 skóre soupeř,
# 7 výsledek, 8 body, 9 1.P, 10 2.P, 11 3.P, 12 přesilovky, 13 góly v přesilovce,
# 14 oslabení, 15 obdržené góly v oslabení, 16 góly v oslabení (vstřelené),
# 17 vyloučení, 18 trestné minuty, 19 kolo


def test_kolo_propagates_to_team_perspective_rows():
    rows = _rows()
    assert rows["HC Stadion Litoměřice"][19] == 2
    assert rows["Piráti Chomutov"][19] == 2


def test_lit_won_away_in_regulation():
    rows = _rows()
    lit = rows["HC Stadion Litoměřice"]

    assert lit[4] == "venku"
    assert lit[5] == 5  # skóre tým (LIT)
    assert lit[6] == 4  # skóre soupeř (Chomutov)
    assert lit[7] == "V"
    assert lit[8] == 3


def test_chomutov_lost_at_home_in_regulation():
    rows = _rows()
    chm = rows["Piráti Chomutov"]

    assert chm[4] == "doma"
    assert chm[5] == 4
    assert chm[6] == 5
    assert chm[7] == "P"
    assert chm[8] == 0


def test_power_plays_match_project_md_reference():
    # PROJECT.MD, referenční zápas 4012: přesilovky LIT:soupeř = 6:8
    rows = _rows()
    assert rows["HC Stadion Litoměřice"][12] == 6  # přesilovky LIT
    assert rows["Piráti Chomutov"][12] == 8  # přesilovky Chomutov (= oslabení LIT)
    assert rows["HC Stadion Litoměřice"][14] == 8  # oslabení LIT = přesilovky soupeře
    assert rows["Piráti Chomutov"][14] == 6


def test_penalties_and_minutes_match_project_md_reference():
    rows = _rows()
    assert rows["HC Stadion Litoměřice"][17] == 9
    assert rows["HC Stadion Litoměřice"][18] == 18
    assert rows["Piráti Chomutov"][17] == 7
    assert rows["Piráti Chomutov"][18] == 14


def test_period_scores_are_team_perspective():
    rows = _rows()
    lit = rows["HC Stadion Litoměřice"]
    chm = rows["Piráti Chomutov"]

    # Zápis: 2:2, 1:0, 1:3 (domácí Chomutov : hosté LIT)
    assert (chm[9], chm[10], chm[11]) == ("2", "1", "1")
    assert (lit[9], lit[10], lit[11]) == ("2", "0", "3")

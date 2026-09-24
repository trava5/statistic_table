from pathlib import Path

from statistic_table.league_scraper import (
    has_next_page,
    parse_game_detail,
    parse_played_games,
)

FIXTURES = Path(__file__).parent / "fixtures" / "league"
GAMES_LIST_HTML = (FIXTURES / "games_list_page1.html").read_text(encoding="utf-8")
GAME_DETAIL_HTML = (FIXTURES / "game_detail_180718.html").read_text(encoding="utf-8")


def test_parse_played_games_only_returns_played_games_with_round():
    games = parse_played_games(GAMES_LIST_HTML)
    ids = [game_id for _round, game_id in games]

    # Piráti Chomutov - HC Stadion Litoměřice, 20.9.2026, odehráno, 2. kolo
    assert (2, 180718) in games
    assert 180753 not in ids  # IHC Králové Písek - HC Příbram, 9.10.2026, 0:0 = nerozehráno
    assert len(ids) == len(set(ids))  # bez duplicit


def test_has_next_page_true_when_dalsi_link_present():
    assert has_next_page(GAMES_LIST_HTML) is True


# --- parse_game_detail: zápas 4012 Chomutov-LIT, referenční hodnoty PROJECT.MD ----

def test_parse_game_detail_game_summary():
    game, _goals, _penalties, _skaters, _goalies = parse_game_detail(
        GAME_DETAIL_HTML, 180718, round_number=2
    )

    assert game.round == 2
    assert game.game_number == "4012"
    assert game.date == "20. 09. 2026, 10:30"
    assert game.home_team == "Piráti Chomutov"
    assert game.away_team == "HC Stadion Litoměřice"
    assert game.home_score == 4
    assert game.away_score == 5
    assert game.period_scores == [(2, 2), (1, 0), (1, 3)]
    assert game.ending is None
    assert game.attendance == 85
    assert game.referees == "Alexandr Kapitanov, Tomáš Kučera (PE95), Jakub Teršíp"


def test_parse_game_detail_goals_and_situations():
    game, goals, _penalties, _skaters, _goalies = parse_game_detail(GAME_DETAIL_HTML, 180718)

    assert len(goals) == game.home_score + game.away_score
    first_goal = goals[0]
    assert first_goal.team == "Piráti Chomutov"
    assert first_goal.period == 1
    assert first_goal.time == "03:49"
    assert first_goal.scorer == "Jaroslav Pospíšil"
    assert first_goal.assist1 == "Šimon Kříž"
    assert first_goal.assist2 == "Josef Chládek"
    assert first_goal.situation == "5/4"


def test_parse_game_detail_penalties_totals_match_project_md():
    _game, _goals, penalties, _skaters, _goalies = parse_game_detail(GAME_DETAIL_HTML, 180718)

    chm_penalties = [p for p in penalties if p.team == "Piráti Chomutov"]
    lit_penalties = [p for p in penalties if p.team == "HC Stadion Litoměřice"]

    # PROJECT.MD: vyloučení 9:7 (LIT:soupeř), TM 18:14 (LIT:soupeř)
    assert len(lit_penalties) == 9
    assert len(chm_penalties) == 7
    assert sum(p.minutes for p in lit_penalties) == 18
    assert sum(p.minutes for p in chm_penalties) == 14


def test_parse_game_detail_skater_and_goalie_rosters():
    _game, _goals, _penalties, skaters, goalies = parse_game_detail(GAME_DETAIL_HTML, 180718)

    lit_skaters = [s for s in skaters if s.team == "HC Stadion Litoměřice"]
    chm_skaters = [s for s in skaters if s.team == "Piráti Chomutov"]
    assert lit_skaters and chm_skaters

    pospisil = next(s for s in chm_skaters if s.name == "Jaroslav Pospíšil")
    assert pospisil.goals == 1
    assert pospisil.assists == 2
    assert pospisil.points == 3

    lit_goalie = next(g for g in goalies if g.team == "HC Stadion Litoměřice")
    assert lit_goalie.name == "Jáchym Krátký"

    chm_goalie = next(g for g in goalies if g.team == "Piráti Chomutov")
    assert chm_goalie.name == "Petr Kašpar"
    assert chm_goalie.goals_against == 5
    assert chm_goalie.time_on_ice == "59:05"

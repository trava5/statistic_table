from pathlib import Path

import pytest

from statistic_table.config import (
    SEZNAMY_GOALIES_LOG_SHEET,
    SEZNAMY_GOLY_SHEET,
    SEZNAMY_SKATERS_LOG_SHEET,
    SEZNAMY_VYLOUCENI_SHEET,
    SEZNAMY_ZAPASY_SHEET,
    Config,
)
from statistic_table.pdf_parser import parse_game
from statistic_table.seznamy_sheets import build_seznamy_rows

FIXTURES = Path(__file__).parent / "fixtures"
PDF_DIR = FIXTURES / "pdf"


def _config() -> Config:
    return Config(
        google_auth_mode="service_account",
        google_service_account_file=None,
        drive_folder_id="x",
        spreadsheet_id="x",
        team_name_in_pdf="HC Stadion Litoměřice",
        team_short="LIT",
        season_start_year=2026,
    )


@pytest.fixture(scope="module")
def game_4002():
    return parse_game(PDF_DIR / "4002_lit_pribram.pdf")


@pytest.fixture(scope="module")
def game_4012():
    return parse_game(PDF_DIR / "4012_chomutov_lit.pdf")


# Referenční čísla z PROJECT.MD („Zapsané zápasy“): vyloučení a TM v pohledu
# LIT:soupeř, ověřené i v tests/test_importer.py na produkčním zápisu.


def test_zapasy_row_4002(game_4002):
    rows = build_seznamy_rows(game_4002, _config())
    assert rows[SEZNAMY_ZAPASY_SHEET] == [
        ["4002", "18.9.2026", "LIT", "Příbram", 1, 3, "", "0:2", "1:0", "0:1", ""]
    ]


def test_zapasy_row_4012(game_4012):
    rows = build_seznamy_rows(game_4012, _config())
    assert rows[SEZNAMY_ZAPASY_SHEET] == [
        ["4012", "20.9.2026", "Chomutov", "LIT", 4, 5, "", "2:2", "1:0", "1:3", ""]
    ]


def test_goly_total_matches_score(game_4002, game_4012):
    rows_4002 = build_seznamy_rows(game_4002, _config())[SEZNAMY_GOLY_SHEET]
    assert len(rows_4002) == 1 + 3  # home_score + away_score

    rows_4012 = build_seznamy_rows(game_4012, _config())[SEZNAMY_GOLY_SHEET]
    assert len(rows_4012) == 4 + 5


def test_vylouceni_counts_and_tm_4002(game_4002):
    rows = build_seznamy_rows(game_4002, _config())[SEZNAMY_VYLOUCENI_SHEET]
    lit_rows = [r for r in rows if r[1] == "LIT"]
    opp_rows = [r for r in rows if r[1] == "Příbram"]
    assert len(lit_rows) == 9
    assert len(opp_rows) == 7
    assert sum(r[5] for r in lit_rows) == 26
    assert sum(r[5] for r in opp_rows) == 14


def test_vylouceni_counts_and_tm_4012(game_4012):
    rows = build_seznamy_rows(game_4012, _config())[SEZNAMY_VYLOUCENI_SHEET]
    lit_rows = [r for r in rows if r[1] == "LIT"]
    opp_rows = [r for r in rows if r[1] == "Chomutov"]
    assert len(lit_rows) == 9
    assert len(opp_rows) == 7
    assert sum(r[5] for r in lit_rows) == 18
    assert sum(r[5] for r in opp_rows) == 14


def test_vylouceni_third_within_valid_range(game_4002, game_4012):
    for game in (game_4002, game_4012):
        rows = build_seznamy_rows(game, _config())[SEZNAMY_VYLOUCENI_SHEET]
        assert all(1 <= r[2] <= 4 for r in rows)


def test_skater_and_goalie_roster_counts_4002(game_4002):
    rows = build_seznamy_rows(game_4002, _config())
    skaters = rows[SEZNAMY_SKATERS_LOG_SHEET]
    goalies = rows[SEZNAMY_GOALIES_LOG_SHEET]
    assert len(skaters) == 36  # 18 hráčů v poli na tým, oba týmy
    assert len(goalies) == 4  # 2 brankáři v soupisce na tým, oba týmy

    lit_goalies = {r[3]: r for r in goalies if r[1] == "LIT"}
    assert lit_goalies["WEBER Jiří"][5] == 1  # chytal
    assert lit_goalies["WEBER Jiří"][6] == 3  # obdržené góly = away_score
    assert lit_goalies["KRÁTKÝ Jáchym"][5] == 0  # nechytal
    assert lit_goalies["KRÁTKÝ Jáchym"][6] == ""


def test_skater_goals_and_assists_tracked_4002(game_4002):
    rows = build_seznamy_rows(game_4002, _config())[SEZNAMY_SKATERS_LOG_SHEET]
    scorer = next(r for r in rows if r[3] == "HLADÍK Šimon")
    assert scorer[7] == 1  # G (jediný gól LIT v zápase)
    assert scorer[8] == 0  # A
    assert scorer[9] == 1  # B
    assert scorer[10] == 2  # TM

    assist = next(r for r in rows if r[3] == "PROKŮPEK Tomáš")
    assert assist[7] == 0  # G
    assert assist[8] == 1  # A (asistence u gólu Hladíka)
    assert assist[9] == 1  # B

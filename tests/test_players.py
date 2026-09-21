import json
from pathlib import Path

import pytest

from statistic_table.config import Config
from statistic_table.model import GamePlayer, RosterPlayer
from statistic_table.pdf_parser import parse_game
from statistic_table.players import (
    PlayerMatchError,
    TeamIdentificationError,
    identify_lit,
    match_lineup,
    match_player,
    opponent_alias,
)

FIXTURES = Path(__file__).parent / "fixtures"
PDF_DIR = FIXTURES / "pdf"

LIT_LINEUP_4002 = [
    "Beránek", "Chlouda", "Drahorád", "Gois", "Hendrych", "Hladík", "Holčák", "Hurst",
    "Husák", "Kalla", "Kurnat", "Novotný D", "Novotný T", "Prokůpek", "Walter V",
    "Weber", "Čellenyuk", "Šilhavý", "Šustík",
]

LIT_LINEUP_4012 = [
    "Beránek", "Chlouda", "Drahorád", "Gois", "Hendrych", "Hladík", "Hodek", "Holčák",
    "Hurst", "Husák", "Kalla", "Krátký", "Kurnat", "Novotný D", "Novotný T", "Prokůpek",
    "Walter V", "Čellenyuk", "Šilhavý", "Šustík",
]


def _config(team_name: str) -> Config:
    return Config(
        google_auth_mode="service_account",
        google_service_account_file=None,
        drive_folder_id="x",
        spreadsheet_id="x",
        team_name_in_pdf=team_name,
        team_short="LIT",
        season_start_year=2026,
    )


@pytest.fixture
def roster() -> list[RosterPlayer]:
    rows = json.loads((FIXTURES / "seznam_hracu.json").read_text(encoding="utf-8"))
    return [RosterPlayer(**row) for row in rows]


@pytest.mark.parametrize(
    ("pdf_name", "expected_lineup"),
    [
        ("4002_lit_pribram.pdf", LIT_LINEUP_4002),
        ("4012_chomutov_lit.pdf", LIT_LINEUP_4012),
    ],
)
def test_lit_lineup_matches_saved_sestavy(pdf_name, expected_lineup, roster):
    config = _config("HC Stadion Litoměřice")
    game = parse_game(PDF_DIR / pdf_name)
    lit, _opponent = identify_lit(game, config)

    matched = match_lineup(lit, roster)

    assert sorted(r.last_name for r in matched.values()) == sorted(expected_lineup)


def test_identify_lit_picks_away_side_when_lit_is_hosts(roster):
    config = _config("HC Stadion Litoměřice")
    game = parse_game(PDF_DIR / "4012_chomutov_lit.pdf")

    lit, opponent = identify_lit(game, config)

    assert lit.name == "HC Stadion Litoměřice"
    assert opponent.name == "Piráti Chomutov"


def test_identify_lit_raises_when_team_name_not_in_game(roster):
    config = _config("Nesedící název týmu")
    game = parse_game(PDF_DIR / "4002_lit_pribram.pdf")

    with pytest.raises(TeamIdentificationError):
        identify_lit(game, config)


def test_opponent_alias_known_teams():
    assert opponent_alias("HC Příbram") == "Příbram"
    assert opponent_alias("Piráti Chomutov") == "Chomutov"


def test_opponent_alias_unknown_team_raises():
    with pytest.raises(TeamIdentificationError):
        opponent_alias("SK Nikdy Neviděný")


def _game_player(
    number: str, last_name: str, first_name: str, registration_number: str
) -> GamePlayer:
    return GamePlayer(
        number=number,
        last_name=last_name,
        first_name=first_name,
        registration_number=registration_number,
        position="D",
        is_goalkeeper=False,
        played=True,
    )


def test_match_by_registration_number(roster):
    player = match_player(_game_player("22", "NOVOTNÝ", "Daniel", "1158652007"), roster)
    assert player.last_name == "Novotný D"


def test_match_duplicate_jersey_number_resolved_by_registration(roster):
    adelt = match_player(_game_player("15", "ADELT", "Ondřej", "1105512006"), roster)
    hodek = match_player(_game_player("15", "HODEK", "Richard", "1189912009"), roster)
    assert adelt.last_name == "Adelt"
    assert hodek.last_name == "Hodek"


def test_match_missing_registration_falls_back_to_surname(roster):
    player = match_player(_game_player("", "KOTMAN", "Tomáš", ""), roster)
    assert player.last_name == "Kotman"


def test_match_unknown_player_raises(roster):
    with pytest.raises(PlayerMatchError):
        match_player(_game_player("99", "NEZNÁMÝ", "Karel", "9999999999"), roster)

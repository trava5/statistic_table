import json
from pathlib import Path

import pytest

from statistic_table.config import Config
from statistic_table.importer import build_import
from statistic_table.model import RosterPlayer
from statistic_table.pdf_parser import parse_game

FIXTURES = Path(__file__).parent / "fixtures"
PDF_DIR = FIXTURES / "pdf"

# Očekávané hodnoty odpovídají přesně tomu, co už je zapsáno v živé tabulce
# (řádky 6 a 7 listu Zápasy/Sestavy) – ověřeno v konverzaci ručním čtením.
EXPECTED_4002 = {
    "Zápasy!A6:E6": ["18.9.2026", "LIT", "Příbram", "1", "3"],
    "Zápasy!F6": [""],
    "Zápasy!J6:T6": ["Hladík", "", "", "", "", "", "", "", "", "", ""],
    "Zápasy!U6:AM6": [
        "Prokůpek", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
    ],
    "Zápasy!AR6:BA6": ["6", "7", "1", "0", "0", "1", "9", "7", "26", "14"],
    "Zápasy!BC6:BN6": [
        "Hendrych", "Prokůpek", "Beránek", "Kalla", "Drahorád", "Hladík",
        "Chlouda", "Chlouda", "Walter V", "", "", "",
    ],
    "Zápasy!BO6:BZ6": ["2", "2", "2", "2", "2", "2", "2", "10", "2", "", "", ""],
    "Zápasy!CJ6:CO6": ["0", "1", "13", "5", "0", "0"],
    "Sestavy!F6:G6": ["2", "Weber"],
}

EXPECTED_4012 = {
    "Zápasy!A7:E7": ["20.9.2026", "Chomutov", "LIT", "4", "5"],
    "Zápasy!F7": [""],
    "Zápasy!J7:T7": ["Kalla", "Kurnat", "Chlouda", "Husák", "Prokůpek", "", "", "", "", "", ""],
    "Zápasy!U7:AM7": [
        "Husák", "Hendrych", "Hurst", "Čellenyuk", "Drahorád", "Beránek", "Hladík",
        "", "", "", "", "", "", "", "", "", "", "", "",
    ],
    "Zápasy!AR7:BA7": ["6", "8", "1", "2", "0", "0", "9", "7", "18", "14"],
    "Zápasy!BC7:BN7": [
        "Beránek", "Gois", "Beránek", "Hurst", "Šilhavý", "Čellenyuk",
        "Chlouda", "Novotný D", "Husák", "", "", "",
    ],
    "Zápasy!BO7:BZ7": ["2", "2", "2", "2", "2", "2", "2", "2", "2", "", "", ""],
    "Zápasy!CJ7:CO7": ["0", "2", "4", "11", "0", "0"],
    "Sestavy!F7:G7": ["2", "Krátký"],
}

# Pořadí H:N/O:AB v živé tabulce neodpovídá žádné odvoditelné konvenci z PDF
# (viz konverzace) – porovnává se jen množina jmen, ne pořadí.
EXPECTED_SESTAVA_SET_4002 = {
    "Sestavy!H6:N6": {"Walter V", "Hladík", "Hurst", "Drahorád", "Novotný D", "Chlouda", "Šilhavý"},
    "Sestavy!O6:AB6": {
        "Beránek", "Prokůpek", "Husák", "Gois", "Kurnat", "Čellenyuk",
        "Novotný T", "Kalla", "Hendrych", "Šustík", "Holčák",
    },
}

EXPECTED_SESTAVA_SET_4012 = {
    "Sestavy!H7:N7": {"Walter V", "Hladík", "Hurst", "Drahorád", "Novotný D", "Chlouda", "Šilhavý"},
    "Sestavy!O7:AB7": {
        "Beránek", "Prokůpek", "Husák", "Gois", "Kurnat", "Čellenyuk", "Novotný T",
        "Kalla", "Hendrych", "Šustík", "Holčák", "Hodek",
    },
}


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
def club_roster() -> list[RosterPlayer]:
    rows = json.loads((FIXTURES / "seznam_hracu.json").read_text(encoding="utf-8"))
    return [RosterPlayer(**row) for row in rows]


@pytest.mark.parametrize(
    ("pdf_name", "row", "expected", "expected_sets"),
    [
        ("4002_lit_pribram.pdf", 6, EXPECTED_4002, EXPECTED_SESTAVA_SET_4002),
        ("4012_chomutov_lit.pdf", 7, EXPECTED_4012, EXPECTED_SESTAVA_SET_4012),
    ],
)
def test_build_import_matches_live_sheet(pdf_name, row, expected, expected_sets, club_roster):
    game = parse_game(PDF_DIR / pdf_name)

    plan = build_import(game, _config(), club_roster, row=row)

    assert plan.row == row
    assert plan.game_number == game.number
    for range_, values in expected.items():
        assert plan.cells[range_] == values, range_
    for range_, names in expected_sets.items():
        assert set(v for v in plan.cells[range_] if v) == names, range_


def test_build_import_pads_unused_slots_with_empty_strings(club_roster):
    game = parse_game(PDF_DIR / "4002_lit_pribram.pdf")
    plan = build_import(game, _config(), club_roster, row=6)

    branky = plan.cells["Zápasy!J6:T6"]
    assert len(branky) == 11
    assert branky.count("") == 10

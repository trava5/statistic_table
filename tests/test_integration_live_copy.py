"""Integrační test: import obou referenčních PDF do TESTOVACÍ KOPIE tabulky
(viz PLAN.MD Krok 5/8). Nikdy neběží proti ostré tabulce.

Spuštění: udělej kopii Google Tabulky "Seznamy", nasdílej ji servisnímu účtu
(edit) a nastav TEST_SPREADSHEET_ID na její ID, např.:

    TEST_SPREADSHEET_ID=... pytest tests/test_integration_live_copy.py

Bez TEST_SPREADSHEET_ID se celý soubor přeskočí.
"""

import json
import os
from pathlib import Path

import pytest

from statistic_table.config import Config
from statistic_table.importer import import_pdf
from statistic_table.model import RosterPlayer
from statistic_table.sheets import read_range

FIXTURES = Path(__file__).parent / "fixtures"
PDF_DIR = FIXTURES / "pdf"
TEST_SPREADSHEET_ID = os.environ.get("TEST_SPREADSHEET_ID")

pytestmark = pytest.mark.skipif(
    not TEST_SPREADSHEET_ID,
    reason="TEST_SPREADSHEET_ID není nastaven – integrační test na kopii tabulky se přeskakuje.",
)


def _config() -> Config:
    return Config(
        google_auth_mode="service_account",
        google_service_account_file=os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/service_account.json"
        ),
        drive_folder_id="",
        spreadsheet_id=TEST_SPREADSHEET_ID or "",
        team_name_in_pdf="HC Stadion Litoměřice",
        team_short="LIT",
        season_start_year=2026,
    )


@pytest.fixture(scope="module")
def club_roster() -> list[RosterPlayer]:
    rows = json.loads((FIXTURES / "seznam_hracu.json").read_text(encoding="utf-8"))
    return [RosterPlayer(**row) for row in rows]


def test_import_both_reference_games_into_copy(club_roster):
    config = _config()

    plan1 = import_pdf(PDF_DIR / "4002_lit_pribram.pdf", config, club_roster, dry_run=False)
    plan2 = import_pdf(PDF_DIR / "4012_chomutov_lit.pdf", config, club_roster, dry_run=False)

    assert plan1.row == 6
    assert plan2.row == 7

    assert read_range(config, "Zápasy!J6:T6")[0][0] == "Hladík"
    assert read_range(config, "Zápasy!AR6:BA6")[0] == [
        "6", "7", "1", "0", "0", "1", "9", "7", "26", "14",
    ]
    assert read_range(config, "Zápasy!AR7:BA7")[0] == [
        "6", "8", "1", "2", "0", "0", "9", "7", "18", "14",
    ]

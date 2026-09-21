import json
from pathlib import Path

from statistic_table.config import (
    SESTAVY_COLUMNS,
    SESTAVY_HEADER_ROW,
    SESTAVY_SHEET,
    ZAPASY_COLUMNS,
    ZAPASY_HEADER_ROW,
    ZAPASY_SHEET,
)
from statistic_table.sheets import header_mismatches

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list[str]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_zapasy_header_matches_saved_copy():
    row = _load("zapasy_header_row5.json")
    assert header_mismatches(ZAPASY_SHEET, row, ZAPASY_COLUMNS, ZAPASY_HEADER_ROW) == []


def test_sestavy_header_matches_saved_copy():
    row = _load("sestavy_header_row5.json")
    assert header_mismatches(SESTAVY_SHEET, row, SESTAVY_COLUMNS, SESTAVY_HEADER_ROW) == []


def test_header_mismatch_is_reported_with_position():
    row = _load("zapasy_header_row5.json")
    row[8] = "neco jineho"  # sloupec I, dřív vložený "pořadí po kole"

    mismatches = header_mismatches(ZAPASY_SHEET, row, ZAPASY_COLUMNS, ZAPASY_HEADER_ROW)

    assert len(mismatches) == 1
    assert "Zápasy!I5" in mismatches[0]
    assert "pořadí po kole" in mismatches[0]

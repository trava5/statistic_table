from pathlib import Path

from statistic_table.standings import (
    Record,
    TeamStanding,
    arithmetic_issues,
    compute_record_from_rows,
    cross_check_issues,
    find_team,
    parse_standings,
)

FIXTURES = Path(__file__).parent / "fixtures"
STANDINGS_HTML = (FIXTURES / "standings_page.html").read_text(encoding="utf-8")


def test_parse_standings_finds_both_groups():
    standings = parse_standings(STANDINGS_HTML)
    assert len(standings) >= 16  # dvě skupiny po ~8 týmech


def test_parse_standings_lit_row():
    standings = parse_standings(STANDINGS_HTML)
    lit = find_team(standings, "HC Stadion Litoměřice")

    assert lit is not None
    assert lit.position == 4
    assert lit.games == 2
    assert lit.wins == 1
    assert lit.ot_wins == 0
    assert lit.ot_losses == 0
    assert lit.losses == 1
    assert lit.goals_for == 6
    assert lit.goals_against == 7
    assert lit.points == 3


def test_find_team_not_present_returns_none():
    standings = parse_standings(STANDINGS_HTML)
    assert find_team(standings, "Neexistující Tým") is None


def test_arithmetic_issues_clean_standing():
    standing = TeamStanding(4, "HC Stadion Litoměřice", 2, 1, 0, 0, 1, 6, 7, 3)
    assert arithmetic_issues(standing) == []


def test_arithmetic_issues_detects_bad_games_count():
    standing = TeamStanding(
        4, "X", games=5, wins=1, ot_wins=0, ot_losses=0, losses=1,
        goals_for=6, goals_against=7, points=3,
    )
    issues = arithmetic_issues(standing)
    assert len(issues) == 1
    assert "Z=5" in issues[0]


def test_arithmetic_issues_detects_bad_points():
    standing = TeamStanding(
        4, "X", games=2, wins=1, ot_wins=0, ot_losses=0, losses=1,
        goals_for=6, goals_against=7, points=99,
    )
    issues = arithmetic_issues(standing)
    assert len(issues) == 1
    assert "B=99" in issues[0]


# --- compute_record_from_rows / cross_check_issues -------------------------

ZAPASY_ROWS = [
    ["18.9.2026", "LIT", "Příbram", "1", "3", ""],
    ["20.9.2026", "Chomutov", "LIT", "4", "5", ""],
]


def test_compute_record_from_rows_matches_reference():
    record = compute_record_from_rows(ZAPASY_ROWS, "LIT")
    assert record == Record(
        games=2, wins=1, ot_wins=0, ot_losses=0, losses=1, goals_for=6, goals_against=7, points=3
    )


def test_compute_record_ignores_other_teams_and_unplayed_rows():
    rows = [*ZAPASY_ROWS, ["25.9.2026", "Kladno", "Sparta", "", "", ""]]
    record = compute_record_from_rows(rows, "LIT")
    assert record.games == 2


def test_compute_record_handles_overtime_win_and_loss():
    rows = [
        ["1.10.2026", "LIT", "X", "2", "1", "pp"],  # výhra po prodloužení = 2 body
        ["8.10.2026", "Y", "LIT", "5", "4", "sn"],  # LIT prohrála po nájezdech = 1 bod
    ]
    record = compute_record_from_rows(rows, "LIT")
    assert record.ot_wins == 1
    assert record.ot_losses == 1
    assert record.wins == 0
    assert record.losses == 0
    assert record.points == 3


def test_cross_check_issues_matches_live_data():
    standings = parse_standings(STANDINGS_HTML)
    lit = find_team(standings, "HC Stadion Litoměřice")
    record = compute_record_from_rows(ZAPASY_ROWS, "LIT")

    assert cross_check_issues(lit, record) == []


def test_cross_check_issues_detects_mismatch():
    standing = TeamStanding(4, "X", 2, 1, 0, 0, 1, 6, 7, 3)
    record = Record(
        games=2, wins=0, ot_wins=0, ot_losses=0, losses=2, goals_for=1, goals_against=9, points=0
    )

    issues = cross_check_issues(standing, record)

    assert len(issues) == 2  # body i skóre nesedí (Z sedí)

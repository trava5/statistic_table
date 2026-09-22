from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pdfplumber

from statistic_table.model import Game, GamePlayer, Goal, Penalty, TeamSheet

# Pořadí sloupců v tabulce soupiska+góly+tresty na 1. straně zápisu ČSLH.
# "čas" a "č." se v hlavičce objevují dvakrát (góly, pak tresty) – hledáme je
# postupně zleva doprava, takže druhý výskyt se správně napojí na tresty.
TEAM_TABLE_FIELDS = [
    "č.", "Příjmení, jméno C/A", "č. registrace", "post", "čas",
    "S", "A1", "A2", "HS", "čas", "č.", "Min.", "důvod", "Od", "Do",
]

SUMMARY_TABLE_FIELDS = ["GÓLY\nA:B", "BA", "Min", "OB", "BB", "min", "OB"]


class ParseError(Exception):
    """Zápis nemá očekávaný formát – import se má zastavit, ne hádat."""


def _sequential_column_map(header_row: list, fields: list[str]) -> list[int]:
    mapping = []
    search_start = 0
    for field_name in fields:
        idx = None
        for i in range(search_start, len(header_row)):
            if header_row[i] == field_name:
                idx = i
                break
        if idx is None:
            raise ParseError(f"Hlavička tabulky neobsahuje očekávaný sloupec {field_name!r}")
        mapping.append(idx)
        search_start = idx + 1
    return mapping


def _find_marker_row(table: list[list], marker: str) -> int:
    for i, row in enumerate(table):
        if row and row[0] == marker:
            return i
    raise ParseError(f"V zápise chybí očekávaný oddíl {marker!r}")


def _team_name(marker_row: list) -> str:
    for cell in marker_row[1:]:
        if cell:
            return cell.split("\n")[0].strip()
    raise ParseError("Nepodařilo se najít název týmu")


def _label_value(row: list, label: str) -> str:
    idx = row.index(label)
    for cell in row[idx + 1 :]:
        if cell:
            return cell
    raise ParseError(f"Chybí hodnota pro {label!r}")


def _parse_team_block(table: list[list], marker: str) -> TeamSheet:
    marker_idx = _find_marker_row(table, marker)
    name = _team_name(table[marker_idx])
    header_row = table[marker_idx + 1]
    (
        num_col,
        name_col,
        reg_col,
        post_col,
        goal_time_col,
        s_col,
        a1_col,
        a2_col,
        hs_col,
        pen_time_col,
        pen_player_col,
        min_col,
        reason_col,
        od_col,
        do_col,
    ) = _sequential_column_map(header_row, TEAM_TABLE_FIELDS)
    served_by_col = do_col + 1

    roster: list[GamePlayer] = []
    goals: list[Goal] = []
    penalties: list[Penalty] = []

    for row in table[marker_idx + 2 :]:
        if row[0] and "před utkáním" in row[0]:
            break

        number, full_name = row[num_col], row[name_col]
        if number and full_name:
            last_name, _, first_name = full_name.partition(" ")
            roster.append(
                GamePlayer(
                    number=number,
                    last_name=last_name,
                    first_name=first_name,
                    registration_number=row[reg_col] or "",
                    position=row[post_col] or "",
                    is_goalkeeper=row[post_col] == "GK",
                    played=True,
                )
            )

        if row[goal_time_col]:
            goals.append(
                Goal(
                    time=row[goal_time_col],
                    scorer_number=row[s_col] or "",
                    assist1_number=row[a1_col] or "",
                    assist2_number=row[a2_col] or "",
                    situation=row[hs_col] or "",
                )
            )

        if row[pen_time_col]:
            served_by = None
            if len(row) > served_by_col and row[served_by_col]:
                served_by = row[served_by_col].strip("() ") or None
            penalties.append(
                Penalty(
                    time=row[pen_time_col],
                    player_number=row[pen_player_col] or "",
                    minutes=int(row[min_col]),
                    reason=row[reason_col] or "",
                    start=row[od_col] or "",
                    end=row[do_col] or "",
                    served_by_number=served_by,
                )
            )

    return TeamSheet(name=name, roster=roster, goals=goals, penalties=penalties)


def _with_goalie(team: TeamSheet, goalie_number: str | None) -> TeamSheet:
    roster = [
        replace(p, played=(not p.is_goalkeeper) or p.number == goalie_number)
        for p in team.roster
    ]
    return replace(team, roster=roster, goalie_number=goalie_number)


def _parse_summary(table: list[list]) -> dict:
    goal_col, ba_col, ba_min_col, ba_ob_col, bb_col, bb_min_col, bb_ob_col = (
        _sequential_column_map(table[0], SUMMARY_TABLE_FIELDS)
    )

    period_scores: list[tuple[int, int]] = []
    ot_score: tuple[int, int] | None = None
    ending: str | None = None
    home_goalie = away_goalie = None
    home_score = away_score = None

    for row in table[1:]:
        label = row[0]
        if label in ("1", "2", "3") and row[goal_col]:
            h, a = row[goal_col].split(":")
            period_scores.append((int(h), int(a)))
        elif label == "P" and row[goal_col]:
            ending = "pp"
            h, a = row[goal_col].split(":")
            ot_score = (int(h), int(a))
        elif label == "SN" and row[goal_col]:
            ending = "sn"
        elif label == "CELKEM" and row[goal_col]:
            h, a = row[goal_col].split(":")
            home_score, away_score = int(h), int(a)

        if label == "1":
            home_goalie = row[ba_col] or None
            away_goalie = row[bb_col] or None

    if home_score is None or away_score is None:
        raise ParseError("V souhrnu utkání chybí celkové skóre (CELKEM)")

    return {
        "period_scores": period_scores,
        "ot_score": ot_score,
        "ending": ending,
        "home_goalie": home_goalie,
        "away_goalie": away_goalie,
        "home_score": home_score,
        "away_score": away_score,
    }


def parse_game(path: str | Path) -> Game:
    with pdfplumber.open(path) as pdf:
        tables = pdf.pages[0].extract_tables()

    if len(tables) < 2:
        raise ParseError(f"Neočekávaný počet tabulek na 1. straně zápisu: {len(tables)}")
    main_table, summary_table = tables[0], tables[1]

    number_col = main_table[0].index("Číslo utkání")
    number = main_table[1][number_col]
    if not number:
        raise ParseError("Chybí číslo utkání")
    date = _label_value(main_table[2], "Datum")

    home = _parse_team_block(main_table, "Domácí tým (A)")
    away = _parse_team_block(main_table, "Hostující tým (B)")

    summary = _parse_summary(summary_table)
    home = _with_goalie(home, summary["home_goalie"])
    away = _with_goalie(away, summary["away_goalie"])

    return Game(
        number=number,
        date=date,
        home=home,
        away=away,
        home_score=summary["home_score"],
        away_score=summary["away_score"],
        period_scores=summary["period_scores"],
        ending=summary["ending"],
        ot_score=summary["ot_score"],
    )

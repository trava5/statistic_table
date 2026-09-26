from __future__ import annotations

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from statistic_table.config import STANDINGS_URL


@dataclass(frozen=True)
class TeamStanding:
    position: int
    team: str
    games: int
    wins: int
    ot_wins: int
    ot_losses: int
    losses: int
    goals_for: int
    goals_against: int
    points: int
    group: int = 0  # pořadí tabulky (skupiny) na stránce, 1 = první, 2 = druhá…


@dataclass(frozen=True)
class Record:
    """Bilance dopočítaná z vlastní tabulky Zápasy – reference pro kontrolu
    věrohodnosti dat ze stránky Ligy juniorů (viz PROJECT.MD, pravidlo bodů)."""

    games: int
    wins: int
    ot_wins: int
    ot_losses: int
    losses: int
    goals_for: int
    goals_against: int
    points: int


def fetch_standings_html(url: str = STANDINGS_URL) -> str:
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.text


def parse_standings(html: str) -> list[TeamStanding]:
    """Čistá funkce: rozparsuje tabulky pořadí (obě skupiny) ze stránky."""
    soup = BeautifulSoup(html, "html.parser")
    standings = []
    for group_index, table in enumerate(soup.select("table.table-count"), start=1):
        for row in table.select("tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 9:
                continue
            position = int(cells[0].get_text(strip=True).rstrip("."))
            team = cells[1].get_text(strip=True)
            games, wins, ot_wins, ot_losses, losses = (
                int(cells[i].get_text(strip=True)) for i in range(2, 7)
            )
            goals_for, goals_against = (
                int(part) for part in cells[7].get_text(strip=True).split(":")
            )
            points = int(cells[8].get_text(strip=True))
            standings.append(
                TeamStanding(
                    position=position,
                    team=team,
                    games=games,
                    wins=wins,
                    ot_wins=ot_wins,
                    ot_losses=ot_losses,
                    losses=losses,
                    goals_for=goals_for,
                    goals_against=goals_against,
                    points=points,
                    group=group_index,
                )
            )
    return standings


def find_team(standings: list[TeamStanding], team_name: str) -> TeamStanding | None:
    for standing in standings:
        if standing.team == team_name:
            return standing
    return None


def arithmetic_issues(standing: TeamStanding) -> list[str]:
    """Ověří, že Z, B na stránce odpovídají V/VP/PP/P (viz PLAN.MD Krok 7, bod 3)."""
    issues = []
    played = standing.wins + standing.ot_wins + standing.ot_losses + standing.losses
    if standing.games != played:
        issues.append(
            f"{standing.team}: Z={standing.games} neodpovídá součtu V+VP+PP+P={played}"
        )
    expected_points = standing.wins * 3 + standing.ot_wins * 2 + standing.ot_losses
    if standing.points != expected_points:
        issues.append(
            f"{standing.team}: B={standing.points} neodpovídá výpočtu {expected_points} z V/VP/PP"
        )
    return issues


def compute_record_from_rows(rows: list[list[str]], team_short: str) -> Record:
    """Bilance týmu team_short z odehraných řádků listu Zápasy (A:F)."""
    games = wins = ot_wins = ot_losses = losses = goals_for = goals_against = points = 0
    for row in rows:
        if len(row) < 5:
            continue
        date, home, away, hg, ag = row[0], row[1], row[2], row[3], row[4]
        if not (date and hg and ag) or team_short not in (home, away):
            continue
        note = row[5] if len(row) > 5 else ""
        home_goals, away_goals = int(hg), int(ag)
        is_home = home == team_short
        gf, ga = (home_goals, away_goals) if is_home else (away_goals, home_goals)

        games += 1
        goals_for += gf
        goals_against += ga
        won = gf > ga
        if note in ("pp", "sn"):
            if won:
                ot_wins += 1
                points += 2
            else:
                ot_losses += 1
                points += 1
        elif won:
            wins += 1
            points += 3
        else:
            losses += 1

    return Record(games, wins, ot_wins, ot_losses, losses, goals_for, goals_against, points)


def cross_check_issues(standing: TeamStanding, record: Record) -> list[str]:
    """Porovná stránku s vlastní tabulkou – dřívější chybné čtení stránky je
    důvod, proč se výsledky nikdy neberou jen z webu (viz PLAN.MD Krok 7)."""
    issues = []
    if standing.games != record.games:
        issues.append(f"Z: stránka {standing.games}, tabulka {record.games}")
    if standing.points != record.points:
        issues.append(f"B: stránka {standing.points}, tabulka {record.points}")
    if (standing.goals_for, standing.goals_against) != (record.goals_for, record.goals_against):
        issues.append(
            f"skóre: stránka {standing.goals_for}:{standing.goals_against}, "
            f"tabulka {record.goals_for}:{record.goals_against}"
        )
    return issues



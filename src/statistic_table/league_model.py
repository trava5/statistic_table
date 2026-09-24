from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeagueGame:
    """Jeden odehraný zápas Ligy juniorů (libovolné dva týmy), z /game/detail/<id>."""

    game_id: int
    game_number: str
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    period_scores: list[tuple[int, int]]
    ending: str | None = None  # "pp" (prodloužení), "sn" (nájezdy), nebo None
    ot_score: tuple[int, int] | None = None
    attendance: int | None = None
    referees: str | None = None
    round: int | None = None  # kolo, ze seznamu zápasů (detail zápasu ho neuvádí)


@dataclass(frozen=True)
class LeagueGoal:
    """Jeden gól ze zápisu o utkání – tým je vždy tým střelce."""

    game_id: int
    team: str
    period: int
    time: str
    scorer: str
    assist1: str
    assist2: str
    situation: str  # HS, např. "5/4"


@dataclass(frozen=True)
class LeaguePenalty:
    """Jedno vyloučení – tým je tým potrestaného hráče."""

    game_id: int
    team: str
    period: int
    time: str
    player: str
    minutes: int
    reason: str


@dataclass(frozen=True)
class LeagueSkaterStat:
    """Řádek bruslaře v soupisce k zápasu (list SESTAVY) – i bez bodu, kvůli počtu
    odehraných zápasů. Body/TM/+- bere web přímo spočítané, nepočítá se z Goal/Penalty."""

    game_id: int
    team: str
    jersey_number: str
    name: str
    position: str  # "O" obránce, "Ú" útočník
    goals: int
    assists: int
    points: int
    penalty_minutes: int
    plus_minus: int


@dataclass(frozen=True)
class LeagueGoalieStat:
    """Řádek brankáře v soupisce k zápasu (list SESTAVY)."""

    game_id: int
    team: str
    jersey_number: str
    name: str
    time_on_ice: str
    saves: int
    goals_against: int
    save_percentage: str
    goals: int
    assists: int
    penalty_minutes: int

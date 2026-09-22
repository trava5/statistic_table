from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RosterPlayer:
    last_name: str
    first_name: str
    registration_number: str
    jersey_number: str
    position: str

    @property
    def birth_year(self) -> int | None:
        if len(self.registration_number) < 4:
            return None
        return int(self.registration_number[-4:])


@dataclass(frozen=True)
class GamePlayer:
    """Jeden řádek soupisky týmu v zápise o utkání (PDF)."""

    number: str
    last_name: str
    first_name: str
    registration_number: str
    position: str
    is_goalkeeper: bool
    played: bool

    @property
    def birth_year(self) -> int | None:
        if len(self.registration_number) < 4:
            return None
        return int(self.registration_number[-4:])


@dataclass(frozen=True)
class Goal:
    time: str
    scorer_number: str
    assist1_number: str
    assist2_number: str
    situation: str  # HS, např. "5/3"


@dataclass(frozen=True)
class Penalty:
    time: str
    player_number: str
    minutes: int
    reason: str
    start: str
    end: str
    served_by_number: str | None = None


@dataclass(frozen=True)
class TeamSheet:
    name: str
    roster: list[GamePlayer]
    goals: list[Goal]
    penalties: list[Penalty]
    goalie_number: str | None = None


@dataclass(frozen=True)
class Game:
    number: str
    date: str
    home: TeamSheet
    away: TeamSheet
    home_score: int
    away_score: int
    period_scores: list[tuple[int, int]]
    ending: str | None = None  # "pp" (prodloužení), "sn" (nájezdy), nebo None
    ot_score: tuple[int, int] | None = None  # skóre v prodloužení (řádek "P" v souhrnu)


@dataclass(frozen=True)
class ImportLogEntry:
    """Jeden záznam na skrytém listu Import log – evidence importovaných PDF."""

    file_id: str
    checksum: str
    game_number: str
    imported_at: str
    result: str

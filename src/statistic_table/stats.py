from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from statistic_table.model import Game, GamePlayer, Penalty, RosterPlayer, TeamSheet
from statistic_table.players import match_player

MIN_VALID_BIRTH_YEAR = 2005
MAX_VALID_BIRTH_YEAR = 2010


def _unmatched_minor_count(
    penalties: list[Penalty], opponent_penalties: list[Penalty]
) -> int:
    """Počet 2min menších trestů týmu, které nebyly vyrovnány soupeřovým trestem
    se stejným časem začátku (10min tresty se do přesilovek nepočítají). Každý
    zbylý trest je jedna přesilovka soupeře – viz PROJECT.MD."""
    own_starts = Counter(p.start for p in penalties if p.minutes == 2)
    opponent_starts = Counter(p.start for p in opponent_penalties if p.minutes == 2)
    return sum(max(0, count - opponent_starts.get(start, 0)) for start, count in own_starts.items())


@dataclass(frozen=True)
class PowerPlayStats:
    home_power_plays: int
    away_power_plays: int


def power_plays(home_penalties: list[Penalty], away_penalties: list[Penalty]) -> PowerPlayStats:
    """Počet přesilovek. Oslabení jednoho týmu = přesilovka druhého (viz PROJECT.MD)."""
    return PowerPlayStats(
        home_power_plays=_unmatched_minor_count(away_penalties, home_penalties),
        away_power_plays=_unmatched_minor_count(home_penalties, away_penalties),
    )


def situation_result(situation: str) -> str | None:
    """'pp' (přesilovkový gól), 'sh' (gól v oslabení), nebo None (jiná situace)."""
    own, _, opp = situation.partition("/")
    if not own or not opp:
        return None
    own_n, opp_n = int(own), int(opp)
    if own_n > opp_n:
        return "pp"
    if own_n < opp_n:
        return "sh"
    return None


@dataclass(frozen=True)
class GoalSituationCounts:
    pp_goals: int
    sh_goals: int


def goal_situation_counts(goals: list) -> GoalSituationCounts:
    results = [situation_result(g.situation) for g in goals]
    return GoalSituationCounts(pp_goals=results.count("pp"), sh_goals=results.count("sh"))


@dataclass(frozen=True)
class PenaltyTotals:
    count: int
    minutes: int


def penalty_totals(penalties: list[Penalty]) -> PenaltyTotals:
    return PenaltyTotals(count=len(penalties), minutes=sum(p.minutes for p in penalties))


def penalty_breakdown(
    penalties: list[Penalty],
    team_roster: list[GamePlayer],
    club_roster: list[RosterPlayer],
) -> tuple[list[str], list[int]]:
    """Jména (ve tvaru ze Seznamu hráčů) a minuty vyloučených hráčů LIT ve stejném
    pořadí, v jakém se zapisují do sloupců BC:BN / BO:BZ. Trest se vždy připisuje
    hráči, který ho dostal, i když ho odsedí spoluhráč (served_by_number)."""
    by_number = {p.number: p for p in team_roster}
    names: list[str] = []
    minutes: list[int] = []
    for penalty in penalties:
        game_player = by_number[penalty.player_number]
        roster_player = match_player(game_player, club_roster)
        names.append(roster_player.last_name)
        minutes.append(penalty.minutes)
    return names, minutes


@dataclass(frozen=True)
class BirthYearStats:
    counts: dict[int, int]
    warnings: list[str]


def _counted_players(team: TeamSheet) -> list[GamePlayer]:
    """Bruslaři z listiny + brankář, který skutečně chytal (viz PROJECT.MD)."""
    skaters = [p for p in team.roster if not p.is_goalkeeper]
    goalies = [p for p in team.roster if p.is_goalkeeper and p.played]
    return skaters + goalies


def opponent_birth_years(team: TeamSheet) -> BirthYearStats:
    counts: Counter[int] = Counter()
    warnings: list[str] = []
    for player in _counted_players(team):
        year = player.birth_year
        if year is None:
            warnings.append(
                f"Hráč č. {player.number} {player.last_name} nemá platné číslo registrace "
                "pro určení ročníku"
            )
            continue
        if not (MIN_VALID_BIRTH_YEAR <= year <= MAX_VALID_BIRTH_YEAR):
            warnings.append(
                f"Hráč č. {player.number} {player.last_name} má ročník {year} mimo rozsah "
                f"{MIN_VALID_BIRTH_YEAR}–{MAX_VALID_BIRTH_YEAR} – rozšiř tabulku"
            )
        counts[year] += 1
    return BirthYearStats(counts=dict(counts), warnings=warnings)


def average_age(team: TeamSheet, season_year: int) -> float:
    years = [p.birth_year for p in _counted_players(team) if p.birth_year is not None]
    if not years:
        raise ValueError(f"Tým {team.name}: žádný hráč s platným ročníkem pro výpočet věku")
    return sum(season_year - y for y in years) / len(years)


def note(game: Game) -> str:
    """Hodnota pro sloupec Zápasy!F (pozn.): 'pp', 'sn', nebo prázdný řetězec."""
    return game.ending or ""

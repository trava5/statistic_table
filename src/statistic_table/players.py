from __future__ import annotations

from statistic_table.config import TEAM_ALIASES, Config
from statistic_table.model import Game, GamePlayer, RosterPlayer, TeamSheet


class PlayerMatchError(Exception):
    """Hráče se nepodařilo spárovat jednoznačně – import zápasu se má zastavit."""


class TeamIdentificationError(Exception):
    """Tým LIT nebo soupeře se nepodařilo v zápise rozpoznat."""


def _surname_matches(roster_last_name: str, pdf_last_name: str) -> bool:
    # Seznam hráčů může mít rozlišovač navíc ("Novotný D"), PDF ho nemá ("NOVOTNÝ").
    roster_surname = roster_last_name.split(" ")[0]
    return roster_surname.upper() == pdf_last_name.upper()


def match_player(game_player: GamePlayer, roster: list[RosterPlayer]) -> RosterPlayer:
    if game_player.registration_number:
        by_registration = [
            r for r in roster if r.registration_number == game_player.registration_number
        ]
        if len(by_registration) == 1:
            return by_registration[0]
        if len(by_registration) > 1:
            raise PlayerMatchError(
                f"Číslo registrace {game_player.registration_number} má v Seznamu hráčů "
                f"více řádků ({', '.join(r.last_name for r in by_registration)}) – oprav duplicitu."
            )

    by_surname = [r for r in roster if _surname_matches(r.last_name, game_player.last_name)]
    if game_player.number:
        by_number = [r for r in by_surname if r.jersey_number == game_player.number]
        if by_number:
            by_surname = by_number

    if len(by_surname) == 1:
        return by_surname[0]

    reg = game_player.registration_number or "chybí"
    if not by_surname:
        raise PlayerMatchError(
            f"Neznámý hráč: č. {game_player.number} {game_player.last_name} "
            f"{game_player.first_name} (č. registrace {reg}) není v Seznamu hráčů – doplň ho tam."
        )
    raise PlayerMatchError(
        f"Nejednoznačné párování hráče: č. {game_player.number} {game_player.last_name} "
        f"{game_player.first_name} (č. registrace {reg}) odpovídá více řádkům Seznamu hráčů "
        f"({', '.join(f'{r.last_name} {r.first_name}' for r in by_surname)})."
    )


def match_lineup(team: TeamSheet, roster: list[RosterPlayer]) -> dict[GamePlayer, RosterPlayer]:
    """Spáruje jen hráče, kteří v zápase skutečně nastoupili (viz GamePlayer.played)."""
    return {player: match_player(player, roster) for player in team.roster if player.played}


def identify_lit(game: Game, config: Config) -> tuple[TeamSheet, TeamSheet]:
    """Vrátí (tým LIT, tým soupeře) podle TEAM_NAME_IN_PDF."""
    if game.home.name == config.team_name_in_pdf:
        return game.home, game.away
    if game.away.name == config.team_name_in_pdf:
        return game.away, game.home
    raise TeamIdentificationError(
        f"Ani domácí ({game.home.name!r}), ani hosté ({game.away.name!r}) neodpovídají "
        f"TEAM_NAME_IN_PDF={config.team_name_in_pdf!r} – zápas se netýká LIT, nebo je "
        "TEAM_NAME_IN_PDF špatně nastavené."
    )


def opponent_alias(opponent_name: str) -> str:
    try:
        return TEAM_ALIASES[opponent_name]
    except KeyError as exc:
        raise TeamIdentificationError(
            f"Soupeř {opponent_name!r} nemá v TEAM_ALIASES zkratku pro tabulku Zápasy – doplň ji."
        ) from exc

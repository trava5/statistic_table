"""Kontrola počtu zápasů hráčů se statusem "střídavé" (střídavý start) v
`Seznam hráčů` – u takových hráčů ČSLH limituje počet startů za jejich
"klub" (sloupec `klub`) ve vyšší soutěži (Extraliga juniorů) za sezónu,
trenér to musí hlídat. Scraper ceskyhokej.cz (`/competition/teams/1` pro
seznam týmů soutěže, `/competition/player-stats/1?...filter[club]=<id>`
pro tabulku statistik s odehranými zápasy, sloupec "Z") – jiná část webu
než `league_scraper.py` (ten čte `/competition/games/...`/`/game/detail/
...`, tohle čte souhrnné sezónní statistiky hráčů podle klubu).

Zapisuje přímo do sloupce "z nahoře" (`COL_Z_NAHORE`), přesně jak zadal
uživatel – i když u všech současných řádků se statusem "střídavé" ta
buňka dnes nese pevnou kvótu "22" (konzistentně s "zbývá" = "z nahoře" −
"Z"), potvrzeno s uživatelem 20. 11. 2026, že se má přepsat (ne zapisovat
jinam), viz PLAN.MD."""

from __future__ import annotations

import re
import unicodedata

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from statistic_table.config import (
    SEZNAM_HRACU_DATA_START_ROW,
    SEZNAM_HRACU_SHEET,
    Config,
    require_seznamy_private_spreadsheet_id,
)
from statistic_table.sheets import read_range, write_batch

HEADERS = {"User-Agent": "Mozilla/5.0"}
EXTRALIGA_JUNIORU_COMPETITION_ID = "1"
TEAMS_URL = "https://ceskyhokej.cz/competition/teams/{competition_id}"
PLAYER_STATS_URL = "https://ceskyhokej.cz/competition/player-stats/{competition_id}"

STATUS_STRIDAVE = "střídavé"

# Sloupce `Seznam hráčů` (0-based index v řádku čteném od A, ověřeno živě
# 20. 11. 2026 – viz PLAN.MD): 0 pořadí, 1 příjmení, 2 jméno, 3 č. reg.,
# 4 číslo, 5 post, 6 Z, 7 ročník, 8 klub, 9 status, 10 datum, 11 z nahoře,
# 12 zbývá.
COL_PRIJMENI = 1
COL_JMENO = 2
COL_POST = 5
COL_KLUB = 8
COL_STATUS = 9
COL_Z_NAHORE = "L"

# `post` hodnota pro brankáře v `Seznam hráčů` – jiná tabulka statistik na
# ceskyhokej.cz (viz `fetch_player_stats_html(goalie=True)`).
POST_GOALIE = "G"


# ── ceskyhokej.cz ────────────────────────────────────────────────────────────

def fetch_teams_html(competition_id: str = EXTRALIGA_JUNIORU_COMPETITION_ID) -> str:
    response = requests.get(
        TEAMS_URL.format(competition_id=competition_id), headers=HEADERS, timeout=30
    )
    response.raise_for_status()
    return response.text


def parse_teams(html: str) -> list[dict]:
    """[{club_id, name}] týmů soutěže, v pořadí na stránce – `a.team` s
    `href="/club/detail/{id}"` a vnořeným `h4` jménem (ověřeno živě)."""
    soup = BeautifulSoup(html, "html.parser")
    teams = []
    for link in soup.select("a.team"):
        match = re.search(r"/club/detail/(\d+)", link.get("href", ""))
        name_tag = link.find("h4")
        if match and name_tag:
            teams.append({"club_id": match.group(1), "name": name_tag.get_text(strip=True)})
    return teams


def fetch_player_stats_html(
    club_id: str, *, goalie: bool = False, competition_id: str = EXTRALIGA_JUNIORU_COMPETITION_ID
) -> str:
    """Brankáři mají samostatnou tabulku statistik (jiné sloupce – TOI/OG/
    zásky místo G/A/B – ale stejná sloupec "Z", ověřeno živě 20. 11. 2026),
    vybíranou `filter[type]=goalie`, ne vlastní URL."""
    params = {"playerCompetitionStatsWidget-filter[club]": club_id}
    if goalie:
        params["playerCompetitionStatsWidget-filter[type]"] = "goalie"
    response = requests.get(
        PLAYER_STATS_URL.format(competition_id=competition_id),
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _header_index(table: Tag) -> dict[str, int]:
    """Mapa popisek sloupce -> index v <td>, stejný princip jako
    `league_scraper._header_index` – čte se jménem sloupce, ne pevnou
    pozicí, ať další změna webu dá jasnou chybu, ne tiše špatná data."""
    return {th.get_text(strip=True): i for i, th in enumerate(table.select("thead th"))}


def parse_player_stats(html: str) -> list[dict]:
    """[{player_id, name, games}] hráčů klubu z tabulky statistik
    (sloupec "Z" = počet odehraných zápasů v soutěži). Prázdný seznam,
    pokud klub nemá v tabulce žádné hráče."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.table-count")
    if table is None:
        return []
    header_index = _header_index(table)
    if "HRÁČ" not in header_index or "Z" not in header_index:
        raise ValueError(
            f"Tabulka statistik nemá očekávané sloupce (dostupné: {sorted(header_index)}) "
            "– změnil se web, oprav parse_player_stats."
        )
    players = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        link = cells[header_index["HRÁČ"]].find("a")
        if link is None:
            continue
        player_match = re.search(r"/player/detail/(\d+)", link.get("href", ""))
        games_text = cells[header_index["Z"]].get_text(strip=True)
        players.append(
            {
                "player_id": player_match.group(1) if player_match else "",
                "name": link.get_text(strip=True),
                "games": int(games_text) if games_text.isdigit() else 0,
            }
        )
    return players


def normalize(text: str) -> str:
    """Lowercase bez diakritiky, stejný princip jako `prescout.cihtv.
    normalize` – pro case/diakritika-insensitive porovnání jmen/klubů."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def _match_name(first_name: str, last_name: str) -> str:
    """Jméno pro porovnání s ceskyhokej.cz – `Seznam hráčů` může mít za
    příjmením rozlišovač navíc ("Novotný T", stejná past jako `players.
    _surname_matches`/"Novotný D" u PDF importu), web ho nemá ("Tomáš
    Novotný"), proto se při porovnání odřízne."""
    surname = last_name.split(" ")[0]
    return normalize(f"{first_name} {surname}")


def find_club(klub: str, teams: list[dict]) -> dict | None:
    """Najde tým v `teams`, jehož název obsahuje `klub` jako podřetězec
    (case/diakritika insensitive) – "BOLESLAV" -> "BK Mladá Boleslav".
    `None`, pokud klub v soutěži nehraje vůbec, nebo název sedí na víc
    než jeden tým (nejednoznačné se nemá hádat)."""
    needle = normalize(klub)
    if not needle:
        return None
    matches = [t for t in teams if needle in normalize(t["name"])]
    return matches[0] if len(matches) == 1 else None


# ── Orchestrace ───────────────────────────────────────────────────────────────

def _stridave_players(config: Config, spreadsheet_id: str) -> list[dict]:
    rows = read_range(
        config, f"'{SEZNAM_HRACU_SHEET}'!A{SEZNAM_HRACU_DATA_START_ROW}:M1000", spreadsheet_id
    )
    players = []
    for offset, row in enumerate(rows):
        status = row[COL_STATUS] if len(row) > COL_STATUS else ""
        if status != STATUS_STRIDAVE:
            continue
        last_name = row[COL_PRIJMENI] if len(row) > COL_PRIJMENI else ""
        first_name = row[COL_JMENO] if len(row) > COL_JMENO else ""
        klub = row[COL_KLUB] if len(row) > COL_KLUB else ""
        post = row[COL_POST] if len(row) > COL_POST else ""
        if not last_name or not klub:
            continue
        players.append(
            {
                "sheet_row": SEZNAM_HRACU_DATA_START_ROW + offset,
                "last_name": last_name,
                "first_name": first_name,
                "klub": klub,
                "goalie": post == POST_GOALIE,
            }
        )
    return players


def check_alternating_starts(config: Config, *, dry_run: bool = False) -> list[str]:
    """Pro každého hráče se statusem "střídavé" v `Seznam hráčů` dohledá
    počet odehraných zápasů jeho "klubu" v Extralize juniorů a zapíše ho
    do sloupce "z nahoře" (`COL_Z_NAHORE`). Vrací lidsky čitelné řádky
    hlášení (co se zapsalo/přeskočilo/nenašlo) – `dry_run=True` jen
    nahlásí, nic nezapíše."""
    spreadsheet_id = require_seznamy_private_spreadsheet_id(config)
    players = _stridave_players(config, spreadsheet_id)
    if not players:
        return ["Žádný hráč se statusem 'střídavé' v Seznamu hráčů."]

    teams = parse_teams(fetch_teams_html())
    club_rosters: dict[tuple[str, bool], list[dict]] = {}
    report: list[str] = []
    updates: dict[str, list] = {}

    for p in players:
        full_name = f"{p['first_name']} {p['last_name']}"
        club = find_club(p["klub"], teams)
        if club is None:
            report.append(
                f"  {full_name} ({p['klub']}): klub nehraje Extraligu juniorů, nekontroluje se."
            )
            continue

        cache_key = (club["club_id"], p["goalie"])
        if cache_key not in club_rosters:
            club_rosters[cache_key] = parse_player_stats(
                fetch_player_stats_html(club["club_id"], goalie=p["goalie"])
            )
        roster = club_rosters[cache_key]

        needle = _match_name(p["first_name"], p["last_name"])
        matches = [r for r in roster if normalize(r["name"]) == needle]
        if len(matches) != 1:
            report.append(
                f"  ⚠ {full_name} ({club['name']}): nenalezen v tabulce statistik "
                "(0 zápasů, nebo nesedí jméno) – zkontroluj ručně, buňka se nemění."
            )
            continue

        games = matches[0]["games"]
        report.append(f"  ✓ {full_name} ({club['name']}): {games} zápasů")
        updates[f"'{SEZNAM_HRACU_SHEET}'!{COL_Z_NAHORE}{p['sheet_row']}"] = [games]

    if updates and not dry_run:
        write_batch(config, spreadsheet_id, updates)

    return report

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from statistic_table.league_model import (
    LeagueGame,
    LeagueGoal,
    LeagueGoalieStat,
    LeaguePenalty,
    LeagueSkaterStat,
)

GAMES_LIST_URL = "https://ceskyhokej.cz/competition/games/{competition_id}"
GAME_DETAIL_URL = "https://ceskyhokej.cz/game/detail/{game_id}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Písmeno za skóre v <h2> (např. "3:2P") – "P" je ověřené (prodloužení), "S"/"N"
# jsou nájezdy jen odhadem (v dostupných fixture datech se nevyskytl příklad).
# Neznámé písmeno se neignoruje potichu, jen se nepřevede na pp/sn (viz `Game.ending`
# v model.py, kde neznámý stav dřív znamenal zastavit import, ne hádat).
ENDING_SUFFIXES = {"P": "pp", "S": "sn", "N": "sn"}


def fetch_games_list_html(competition_id: str, page: int = 1) -> str:
    url = GAMES_LIST_URL.format(competition_id=competition_id)
    params = None if page == 1 else {"gameListWidget-page": page}
    response = requests.get(url, params=params, timeout=30, headers=HEADERS)
    response.raise_for_status()
    return response.text


def fetch_game_detail_html(game_id: int) -> str:
    response = requests.get(
        GAME_DETAIL_URL.format(game_id=game_id), timeout=30, headers=HEADERS
    )
    response.raise_for_status()
    return response.text


def parse_played_games(html: str) -> list[tuple[int, int]]:
    """(kolo, game_id) odehraných zápasů z listu zápasů, v pořadí na stránce.

    Zápasy jsou na stránce seskupené pod nadpisem „N. kolo – Liga juniorů…“
    (`div.mb-40` obsahující `h4` a `div.games-list` se zápasy toho kola).
    Nerozehrané zápasy mají skóre bez třídy `bg-blue` (viz fixture
    games_list_page1.html, budoucí zápasy mají `<h6 class="score">0</h6>`,
    odehrané `<h6 class="score bg-blue">4</h6>`)."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[int, int]] = []
    seen: set[int] = set()
    for block in soup.select("div.mb-40"):
        heading = block.find("h4")
        if heading is None:
            continue
        match = re.match(r"(\d+)\.\s*kolo", heading.get_text(strip=True))
        if not match:
            continue
        round_number = int(match.group(1))
        for link in block.select("a.game-item"):
            if not link.select_one("h6.score.bg-blue"):
                continue
            game_match = re.search(r"/game/detail/(\d+)", link.get("href", ""))
            if not game_match:
                continue
            game_id = int(game_match.group(1))
            if game_id not in seen:
                seen.add(game_id)
                results.append((round_number, game_id))
    return results


def has_next_page(html: str) -> bool:
    """Stránka zápasů se stránkuje (?gameListWidget-page=N); odkaz DALŠÍ chybí
    na poslední stránce (ověřeno – stránka 1 nemá PŘEDCHOZÍ, další mají obojí)."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href*='gameListWidget-page']"):
        if "DALŠÍ" in link.get_text(strip=True):
            return True
    return False


def _parse_period_scores(text: str) -> tuple[list[tuple[int, int]], tuple[int, int] | None]:
    main_part, _, ot_part = text.partition(" - ")
    periods = []
    for chunk in main_part.split(","):
        home, away = chunk.strip().split(":")
        periods.append((int(home), int(away)))
    ot_score = None
    if ot_part:
        home, away = ot_part.strip().split(":")
        ot_score = (int(home), int(away))
    return periods, ot_score


def _team_abbr_map(header_card: Tag, home_team: str, away_team: str) -> dict[str, str]:
    """Zkratky týmů (CHM, LTM…) použité v tabulkách gólů/trestů, v pořadí
    domácí/hosté podle obrázků v hlavičce skóre (stejné pořadí jako v H4)."""
    imgs = header_card.select("div.d-flex img[alt]")
    if len(imgs) < 2:
        return {}
    return {imgs[0]["alt"]: home_team, imgs[1]["alt"]: away_team}


def _extra_info(soup: BeautifulSoup) -> dict[str, str]:
    heading = soup.find("h4", string=re.compile("další údaje", re.IGNORECASE))
    if heading is None:
        return {}
    container = heading.find_parent("div")
    info = {}
    for li in container.select("ul.list-view li"):
        strong = li.find("strong")
        span = li.find("span")
        if strong and span:
            info[strong.get_text(strip=True).rstrip(":")] = span.get_text(strip=True)
    return info


def _period_event_tables(soup: BeautifulSoup) -> dict[int, list[Tag]]:
    """Seskupí tabulky pod ZÁPIS O UTKÁNÍ podle třetiny (h5 „N. třetina“ nadpisů,
    které jsou sourozenci tabulek ve stejném obalovém divu)."""
    heading = soup.find("h4", string=re.compile("ZÁPIS O UTKÁNÍ"))
    container = heading.find_parent("div")
    tables_by_period: dict[int, list[Tag]] = {}
    period = None
    for child in container.find_all(["h5", "div"], recursive=False):
        if child.name == "h5":
            match = re.match(r"(\d+)\.", child.get_text(strip=True))
            period = int(match.group(1)) if match else None
        elif period is not None and "table-responsive" in (child.get("class") or []):
            tables_by_period.setdefault(period, []).append(child)
    return tables_by_period


def _parse_goals_table(
    table: Tag, game_id: int, period: int, abbr_map: dict[str, str]
) -> list[LeagueGoal]:
    goals = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        time = cells[0].get_text(strip=True)
        team_abbr = cells[1].select_one("span").get_text(strip=True)
        scorer = cells[3].get_text(strip=True)
        assist_links = cells[4].select("a")
        assist1 = assist_links[0].get_text(strip=True) if len(assist_links) > 0 else ""
        assist2 = assist_links[1].get_text(strip=True) if len(assist_links) > 1 else ""
        situation = cells[5].get_text(strip=True)
        goals.append(
            LeagueGoal(
                game_id=game_id,
                team=abbr_map.get(team_abbr, team_abbr),
                period=period,
                time=time,
                scorer=scorer,
                assist1=assist1,
                assist2=assist2,
                situation=situation,
            )
        )
    return goals


def _parse_penalties_table(
    table: Tag, game_id: int, period: int, abbr_map: dict[str, str]
) -> list[LeaguePenalty]:
    penalties = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        time = cells[0].get_text(strip=True)
        team_abbr = cells[1].select_one("span").get_text(strip=True)
        minutes_match = re.search(r"\d+", cells[2].get_text(strip=True))
        minutes = int(minutes_match.group()) if minutes_match else 0
        player = cells[3].get_text(strip=True)
        reason = cells[4].get_text(strip=True)
        penalties.append(
            LeaguePenalty(
                game_id=game_id,
                team=abbr_map.get(team_abbr, team_abbr),
                period=period,
                time=time,
                player=player,
                minutes=minutes,
                reason=reason,
            )
        )
    return penalties


def _table_kind(table: Tag) -> str | None:
    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    if "BRANKY" in headers:
        return "goals"
    if "VYLOUČENÍ" in headers:
        return "penalties"
    return None


def _parse_skater_row(row: Tag, game_id: int, team: str) -> LeagueSkaterStat:
    cells = row.find_all("td")
    return LeagueSkaterStat(
        game_id=game_id,
        team=team,
        jersey_number=cells[0].get_text(strip=True),
        name=cells[2].get_text(strip=True),
        position=cells[1].get_text(strip=True),
        goals=int(cells[3].get_text(strip=True)),
        assists=int(cells[4].get_text(strip=True)),
        points=int(cells[5].get_text(strip=True)),
        penalty_minutes=int(cells[6].get_text(strip=True)),
        plus_minus=int(cells[7].get_text(strip=True)),
    )


def _parse_goalie_row(row: Tag, game_id: int, team: str) -> LeagueGoalieStat:
    cells = row.find_all("td")
    return LeagueGoalieStat(
        game_id=game_id,
        team=team,
        jersey_number=cells[0].get_text(strip=True),
        name=cells[2].get_text(strip=True),
        time_on_ice=cells[3].get_text(strip=True),
        saves=int(cells[4].get_text(strip=True)),
        goals_against=int(cells[5].get_text(strip=True)),
        save_percentage=cells[6].get_text(strip=True),
        goals=int(cells[7].get_text(strip=True)),
        assists=int(cells[8].get_text(strip=True)),
        penalty_minutes=int(cells[9].get_text(strip=True)),
    )


GameDetail = tuple[
    LeagueGame,
    list[LeagueGoal],
    list[LeaguePenalty],
    list[LeagueSkaterStat],
    list[LeagueGoalieStat],
]


def parse_game_detail(html: str, game_id: int, round_number: int | None = None) -> GameDetail:
    """Čistá funkce: rozparsuje jednu stránku /game/detail/<id>."""
    soup = BeautifulSoup(html, "html.parser")

    score_h2 = soup.select_one("h2.mb-0")
    header_card = score_h2.find_parent("div", class_="card-body")
    teams_text = header_card.select_one("h4.mb-4").get_text(strip=True)
    home_team, away_team = (part.strip() for part in teams_text.split("–", maxsplit=1))
    date = header_card.find_all("p")[0].get_text(strip=True)
    periods_text = header_card.find_all("p")[-1].get_text(strip=True)
    period_scores, ot_score = _parse_period_scores(periods_text)

    score_match = re.match(r"(\d+):(\d+)([A-Z]?)$", score_h2.get_text(strip=True))
    home_score, away_score, suffix = score_match.groups()
    ending = ENDING_SUFFIXES.get(suffix) if suffix else None

    info = _extra_info(soup)
    referees = ", ".join(v for k, v in info.items() if "rozhodčí" in k.lower())

    game = LeagueGame(
        game_id=game_id,
        game_number=info.get("Číslo utkání", ""),
        date=date,
        home_team=home_team,
        away_team=away_team,
        home_score=int(home_score),
        away_score=int(away_score),
        period_scores=period_scores,
        ending=ending,
        ot_score=ot_score,
        round=round_number,
        attendance=int(info["Diváků"]) if info.get("Diváků", "").isdigit() else None,
        referees=referees or None,
    )

    abbr_map = _team_abbr_map(header_card, home_team, away_team)
    goals: list[LeagueGoal] = []
    penalties: list[LeaguePenalty] = []
    for period, tables in _period_event_tables(soup).items():
        for table_div in tables:
            table = table_div.find("table")
            kind = _table_kind(table)
            if kind == "goals":
                goals.extend(_parse_goals_table(table, game_id, period, abbr_map))
            elif kind == "penalties":
                penalties.extend(_parse_penalties_table(table, game_id, period, abbr_map))

    skaters: list[LeagueSkaterStat] = []
    goalies: list[LeagueGoalieStat] = []
    sestavy_heading = soup.find("h4", string=re.compile("SESTAVY"))
    sestavy_container = sestavy_heading.find_parent("div")
    for team_block in sestavy_container.find_all("div", class_="mb-40", recursive=False):
        team_name = team_block.select_one("h5").get_text(strip=True)
        tables = team_block.find_all("table", class_="table-sort")
        if len(tables) >= 1:
            for row in tables[0].select("tbody tr"):
                skaters.append(_parse_skater_row(row, game_id, team_name))
        if len(tables) >= 2:
            for row in tables[1].select("tbody tr"):
                goalies.append(_parse_goalie_row(row, game_id, team_name))

    return game, goals, penalties, skaters, goalies

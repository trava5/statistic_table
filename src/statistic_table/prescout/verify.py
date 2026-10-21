"""Ověří góly a vyloučení z czechicehockey.tv (zdroj klipů, `event_clips.py`)
proti Liga DB (`league_scraper.py` – oficiální scrape PDF ze svazu). Dva
nezávislé zdroje stejného zápasu, czechicehockey.tv občas eventy
zaznamená nepřesně (chybějící/duplicitní trest, pozdní gól), což by jinak
nikdo nepoznal, dokud by si klip neprohlédl – tahle kontrola to odhalí
hned při stažení, než se klipy použijí ke scoutingu. Jen informativní,
nic neblokuje – zápas v Liga DB může chybět (jiná soutěž/skupina) nebo
API Liga DB může být momentálně nedostupné."""

from __future__ import annotations

import re
from datetime import date

from statistic_table.config import (
    LEAGUE_ZAPASY_SHEET,
    LEAGUE_ZAPASY_TYM_SHEET,
    Config,
    require_league_db_spreadsheet_id,
)
from statistic_table.sheets import read_range

from . import cihtv

ROWS = 5000
_DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")


def _parse_date(text: str) -> date | None:
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    return date(year, month, day)


def _find_game(config: Config, match: dict) -> dict | None:
    """Najde řádek v `Zápasy - liga` pro `match` (shoda domácí/hosté + datum).

    Jméno týmu je mezi czechicehockey.tv a Liga DB stejné (ověřeno živě u
    všech 16 týmů, viz PLAN.MD 20. 10. 2026), stačí tedy `cihtv.normalize`
    (case/diakritika) bez dalšího mapování aliasů."""
    spreadsheet_id = require_league_db_spreadsheet_id(config)
    rows = read_range(config, f"'{LEAGUE_ZAPASY_SHEET}'!A2:O{ROWS}", spreadsheet_id)
    home = cihtv.normalize(match["homeTeam"]["name"])
    away = cihtv.normalize(match["awayTeam"]["name"])
    match_date = cihtv.match_start(match).date()
    for row in rows:
        if len(row) < 7:
            continue
        game_id, _cislo, datum, domaci, hoste, skore_d, skore_h, *_ = row
        if (
            cihtv.normalize(domaci) == home
            and cihtv.normalize(hoste) == away
            and _parse_date(datum) == match_date
        ):
            return {"game_id": game_id, "skore_domaci": skore_d, "skore_hoste": skore_h}
    return None


def _penalty_counts_by_side(config: Config, game_id: str) -> dict[str, int]:
    """{"doma": počet vyloučení domácího týmu, "venku": hostujícího} pro
    `game_id` z `Zápasy - liga (tým)` (sloupec "vyloučení" = `len(team_
    penalties)` v `league_stats._team_row` – počítá VŠECHNA vyloučení,
    ne jen ta kratší než `event_clips.MAX_PP_PENALTY_SEC`, co se použijí
    pro přesilovkové klipy)."""
    spreadsheet_id = require_league_db_spreadsheet_id(config)
    rows = read_range(config, f"'{LEAGUE_ZAPASY_TYM_SHEET}'!A2:T{ROWS}", spreadsheet_id)
    counts: dict[str, int] = {}
    for row in rows:
        if len(row) < 18 or row[0] != game_id:
            continue
        side, vylouceni = row[4], row[17]
        counts[side] = int(vylouceni) if str(vylouceni).strip().lstrip("-").isdigit() else 0
    return counts


def verify_events(config: Config, match: dict, events: list[dict]) -> list[str]:
    """Vrátí lidsky čitelné řádky nesrovnalostí (prázdný seznam = všechno
    sedí, nebo zápas v Liga DB nejde dohledat – jiná soutěž/skupina, žádná
    chyba)."""
    try:
        game = _find_game(config, match)
    except Exception as exc:  # noqa: BLE001 - verifikace nemá zastavit stahování klipů
        return [f"Liga DB: verifikace selhala ({exc})."]
    if not game:
        return ["Liga DB: zápas nenalezen (jiná soutěž/skupina?), góly/vyloučení neověřeny."]

    lines = []
    cihtv_home_goals = sum(
        1 for e in events if e.get("eventType") == "GOAL" and e["teamType"] == "HOME"
    )
    cihtv_away_goals = sum(
        1 for e in events if e.get("eventType") == "GOAL" and e["teamType"] == "AWAY"
    )
    try:
        db_home_goals = int(game["skore_domaci"])
        db_away_goals = int(game["skore_hoste"])
    except (TypeError, ValueError):
        db_home_goals = db_away_goals = None

    if db_home_goals is not None and (cihtv_home_goals, cihtv_away_goals) != (
        db_home_goals,
        db_away_goals,
    ):
        lines.append(
            f"Góly nesedí: czechicehockey.tv {cihtv_home_goals}:{cihtv_away_goals}, "
            f"Liga DB {db_home_goals}:{db_away_goals}."
        )

    try:
        penalty_counts = _penalty_counts_by_side(config, game["game_id"])
    except Exception as exc:  # noqa: BLE001 - viz výš
        lines.append(f"Liga DB: vyloučení nejde ověřit ({exc}).")
        return lines

    cihtv_home_pen = sum(
        1 for e in events if e.get("eventType") == "PENALTY" and e["teamType"] == "HOME"
    )
    cihtv_away_pen = sum(
        1 for e in events if e.get("eventType") == "PENALTY" and e["teamType"] == "AWAY"
    )
    db_home_pen = penalty_counts.get("doma")
    db_away_pen = penalty_counts.get("venku")
    if db_home_pen is not None and cihtv_home_pen != db_home_pen:
        lines.append(
            f"Vyloučení {match['homeTeam']['name']} nesedí: "
            f"czechicehockey.tv {cihtv_home_pen}, Liga DB {db_home_pen}."
        )
    if db_away_pen is not None and cihtv_away_pen != db_away_pen:
        lines.append(
            f"Vyloučení {match['awayTeam']['name']} nesedí: "
            f"czechicehockey.tv {cihtv_away_pen}, Liga DB {db_away_pen}."
        )

    return lines

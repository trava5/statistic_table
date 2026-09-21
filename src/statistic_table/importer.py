from __future__ import annotations

import hashlib
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from statistic_table import stats
from statistic_table.config import (
    SESTAVY_COLUMNS,
    SESTAVY_SHEET,
    ZAPASY_COLUMNS,
    ZAPASY_SHEET,
    ColumnGroup,
    Config,
    check_capacity,
)
from statistic_table.drive import download_file, list_pdf_files
from statistic_table.model import Game, ImportLogEntry, RosterPlayer, TeamSheet
from statistic_table.pdf_parser import ParseError, parse_game
from statistic_table.players import (
    PlayerMatchError,
    TeamIdentificationError,
    identify_lit,
    match_lineup,
    opponent_alias,
)
from statistic_table.sheets import (
    append_import_log,
    ensure_import_log_sheet,
    find_or_create_row,
    read_import_log,
    write_batch,
)

BIRTH_YEARS = range(2005, 2011)

# Chyby, které se mají vztahovat jen k jednomu zápasu/souboru – ostatní
# soubory ve složce se mají importovat dál (viz PLAN.MD Krok 6, bod 6).
IMPORT_ERRORS = (ParseError, PlayerMatchError, TeamIdentificationError, ValueError, KeyError)


@dataclass(frozen=True)
class ImportPlan:
    row: int
    game_number: str
    cells: dict[str, list[str]]


def _format_date(pdf_date: str) -> str:
    day, month, year = pdf_date.split(".")
    return f"{int(day)}.{int(month)}.{year}"


def _short_name(team: TeamSheet, lit: TeamSheet, config: Config) -> str:
    return config.team_short if team is lit else opponent_alias(team.name)


def _padded(values: list[str], group: ColumnGroup, context: str) -> list[str]:
    check_capacity(group, values, context)
    return values + [""] * (group.capacity - len(values))


def _number_to_name(lit: TeamSheet, club_roster: list[RosterPlayer]) -> dict[str, str]:
    lineup = match_lineup(lit, club_roster)
    return {gp.number: rp.last_name for gp, rp in lineup.items()}


def _name_for(number_to_name: dict[str, str], number: str, context: str) -> str:
    try:
        return number_to_name[number]
    except KeyError as exc:
        raise ValueError(f"{context}: hráč č. {number} není v sestavě LIT, která hrála") from exc


def _lineup_names(lit: TeamSheet, club_roster: list[RosterPlayer], position: str) -> list[str]:
    lineup = match_lineup(lit, club_roster)
    return [lineup[p].last_name for p in lit.roster if p in lineup and p.position == position]


def build_import(
    game: Game,
    config: Config,
    club_roster: list[RosterPlayer],
    *,
    row: int | None = None,
) -> ImportPlan:
    """Sestaví plán zápisu (buňka -> hodnoty). Bez zadaného `row` dohledá řádek
    v tabulce přes síť; s `row` je funkce čistá a jde testovat bez sítě."""
    lit, opponent = identify_lit(game, config)
    context = f"zápas {game.number}"

    home_short = _short_name(game.home, lit, config)
    away_short = _short_name(game.away, lit, config)
    date = _format_date(game.date)
    if row is None:
        row = find_or_create_row(config, date, home_short, away_short)

    number_to_name = _number_to_name(lit, club_roster)
    scorer_names = [
        _name_for(number_to_name, g.scorer_number, context) for g in lit.goals
    ]
    assist_names: list[str] = []
    for g in lit.goals:
        if g.assist1_number:
            assist_names.append(_name_for(number_to_name, g.assist1_number, context))
        if g.assist2_number:
            assist_names.append(_name_for(number_to_name, g.assist2_number, context))

    pp = stats.power_plays(game.home.penalties, game.away.penalties)
    lit_pp, opp_pp = (
        (pp.home_power_plays, pp.away_power_plays)
        if lit is game.home
        else (pp.away_power_plays, pp.home_power_plays)
    )
    lit_goals = stats.goal_situation_counts(lit.goals)
    opp_goals = stats.goal_situation_counts(opponent.goals)
    lit_penalties = stats.penalty_totals(lit.penalties)
    opp_penalties = stats.penalty_totals(opponent.penalties)
    penalty_names, penalty_minutes = stats.penalty_breakdown(
        lit.penalties, lit.roster, club_roster
    )
    birth_years = stats.opponent_birth_years(opponent)
    birth_year_counts = [birth_years.counts.get(year, 0) for year in BIRTH_YEARS]

    special = [
        lit_pp, opp_pp,
        lit_goals.pp_goals, opp_goals.pp_goals,
        lit_goals.sh_goals, opp_goals.sh_goals,
        lit_penalties.count, opp_penalties.count,
        lit_penalties.minutes, opp_penalties.minutes,
    ]

    cells: dict[str, list[str]] = {
        f"{ZAPASY_SHEET}!A{row}:E{row}": [
            date, home_short, away_short, str(game.home_score), str(game.away_score),
        ],
        f"{ZAPASY_SHEET}!F{row}": [stats.note(game)],
        f"{ZAPASY_SHEET}!J{row}:T{row}": _padded(
            scorer_names, ZAPASY_COLUMNS["branky"], context
        ),
        f"{ZAPASY_SHEET}!U{row}:AM{row}": _padded(
            assist_names, ZAPASY_COLUMNS["prihravky"], context
        ),
        f"{ZAPASY_SHEET}!AR{row}:BA{row}": [str(v) for v in special],
        f"{ZAPASY_SHEET}!BC{row}:BN{row}": _padded(
            penalty_names, ZAPASY_COLUMNS["vylouceni_jmena"], context
        ),
        f"{ZAPASY_SHEET}!BO{row}:BZ{row}": _padded(
            [str(m) for m in penalty_minutes], ZAPASY_COLUMNS["vylouceni_minuty"], context
        ),
        f"{ZAPASY_SHEET}!CJ{row}:CO{row}": [str(c) for c in birth_year_counts],
        f"{SESTAVY_SHEET}!F{row}:G{row}": [
            str(sum(1 for p in lit.roster if p.is_goalkeeper)),
            number_to_name.get(lit.goalie_number or "", ""),
        ],
        f"{SESTAVY_SHEET}!H{row}:N{row}": _padded(
            _lineup_names(lit, club_roster, "D"), SESTAVY_COLUMNS["obranci"], context
        ),
        f"{SESTAVY_SHEET}!O{row}:AB{row}": _padded(
            _lineup_names(lit, club_roster, "F"), SESTAVY_COLUMNS["utocnici"], context
        ),
    }

    return ImportPlan(row=row, game_number=game.number, cells=cells)


def import_pdf(
    path: str | Path, config: Config, club_roster: list[RosterPlayer], *, dry_run: bool
) -> ImportPlan:
    game = parse_game(path)
    plan = build_import(game, config, club_roster)
    if not dry_run:
        write_batch(config, plan.cells)
    return plan


def print_plan(plan: ImportPlan) -> None:
    print(f"Zápas {plan.game_number} -> řádek {plan.row}")
    for range_, values in plan.cells.items():
        print(f"  {range_} = {values}")


@dataclass(frozen=True)
class FileOutcome:
    file_name: str
    status: str  # "imported", "skipped", "warning", "error"
    detail: str


def file_checksum(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _date_sort_key(pdf_date: str) -> tuple[int, int, int]:
    day, month, year = pdf_date.split(".")
    return (int(year), int(month), int(day))


def _classify(
    game_number: str,
    file_id: str,
    checksum: str,
    log_by_game_number: dict[str, ImportLogEntry],
) -> tuple[str, str]:
    """Čistá funkce: rozhodne, jestli je soubor nový, už importovaný,
    změněný (bod 3), nebo duplicitní zápis (bod 4)."""
    existing = log_by_game_number.get(game_number)
    if existing is None:
        return "new", ""
    if existing.file_id == file_id and existing.checksum == checksum:
        return "skipped", "již importováno"
    if existing.file_id == file_id and existing.checksum != checksum:
        return (
            "warning",
            f"soubor s číslem zápisu {game_number} byl od importu změněn – "
            "přepis spusť ručně (python -m statistic_table.cli import <pdf>)",
        )
    return (
        "error",
        f"duplicitní zápis: číslo utkání {game_number} už bylo importováno "
        f"z jiného souboru (ID {existing.file_id})",
    )


def import_folder(
    config: Config, club_roster: list[RosterPlayer], *, dry_run: bool = False
) -> list[FileOutcome]:
    """Projde PDF ve složce Zápisy, přeskočí už importované/duplicitní/změněné
    a nové zapíše (pokud dry_run=False), v pořadí podle data zápasu."""
    ensure_import_log_sheet(config)
    log_by_game_number = {entry.game_number: entry for entry in read_import_log(config)}

    files = list_pdf_files(config)
    outcomes: list[FileOutcome] = []
    new_log_entries: list[ImportLogEntry] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        candidates: list[tuple[Game, dict, str]] = []
        for f in files:
            local_path = Path(tmp_dir) / f["name"]
            download_file(config, f["id"], local_path)
            try:
                game = parse_game(local_path)
            except IMPORT_ERRORS as exc:
                outcomes.append(FileOutcome(f["name"], "error", f"Nelze načíst PDF: {exc}"))
                continue
            candidates.append((game, f, file_checksum(local_path)))

        candidates.sort(key=lambda c: _date_sort_key(c[0].date))

        for game, f, checksum in candidates:
            status, detail = _classify(game.number, f["id"], checksum, log_by_game_number)
            if status != "new":
                outcomes.append(FileOutcome(f["name"], status, detail))
                continue

            try:
                plan = build_import(game, config, club_roster)
            except IMPORT_ERRORS as exc:
                outcomes.append(FileOutcome(f["name"], "error", str(exc)))
                continue

            if not dry_run:
                write_batch(config, plan.cells)
                new_log_entries.append(
                    ImportLogEntry(
                        file_id=f["id"],
                        checksum=checksum,
                        game_number=game.number,
                        imported_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                        result=f"řádek {plan.row}",
                    )
                )
            outcomes.append(FileOutcome(f["name"], "imported", f"řádek {plan.row}"))

    if new_log_entries:
        append_import_log(config, new_log_entries)

    return outcomes


def print_outcomes(outcomes: list[FileOutcome]) -> None:
    for o in outcomes:
        print(f"[{o.status}] {o.file_name}: {o.detail}")
    counts = Counter(o.status for o in outcomes)
    print(
        f"Shrnutí: importováno {counts.get('imported', 0)}, "
        f"přeskočeno {counts.get('skipped', 0)}, "
        f"varování {counts.get('warning', 0)}, "
        f"chyba {counts.get('error', 0)}"
    )

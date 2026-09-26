from __future__ import annotations

import argparse
import sys

from statistic_table.config import (
    LEAGUE_COMPETITION_ID,
    SEZNAMY_PORADI_PO_KOLE_COLUMN,
    SEZNAMY_ZAPASY_SHEET,
    load_config,
    require_league_db_spreadsheet_id,
    require_league_v2_spreadsheet_id,
    require_seznamy_db_spreadsheet_id,
)
from statistic_table.drive import list_pdf_files
from statistic_table.importer import (
    IMPORT_ERRORS,
    import_folder,
    import_pdf,
    print_outcomes,
)
from statistic_table.league_scraper import (
    fetch_game_detail_html,
    fetch_games_list_html,
    has_next_page,
    parse_game_detail,
    parse_played_games,
)
from statistic_table.league_sheets import (
    append_game,
    ensure_league_sheets,
    ensure_team_sheet,
    read_known_game_ids,
    read_known_teams,
    recompute_standings_history,
    refresh_group_membership,
    team_sheet_title,
)
from statistic_table.logging_config import setup_logging
from statistic_table.seznamy_sheets import build_seznamy_rows, last_game_row, write_poradi
from statistic_table.sheets import check_headers, read_player_registry, read_range
from statistic_table.standings import (
    arithmetic_issues,
    compute_record_from_rows,
    cross_check_issues,
    fetch_standings_html,
    find_team,
    parse_standings,
)


def cmd_check(_args: argparse.Namespace) -> int:
    config = load_config()

    print(f"Složka Zápisy (DRIVE_FOLDER_ID={config.drive_folder_id}):")
    files = list_pdf_files(config)
    if not files:
        print("  (žádné PDF nenalezeny)")
    for f in files:
        print(f"  - {f['name']} ({f['id']})")

    values = read_range(config, "Zápasy!A6")
    cell = values[0][0] if values and values[0] else ""
    print(f"Zápasy!A6 = {cell!r}")

    try:
        check_headers(config)
    except RuntimeError as exc:
        print(f"Rozložení tabulky: CHYBA\n{exc}")
        return 1
    print("Rozložení tabulky: OK")

    players = read_player_registry(config)
    print(f"Seznam hráčů: {len(players)} hráčů")

    return 0


def cmd_import(args: argparse.Namespace) -> int:
    config = load_config()

    if args.pdf:
        try:
            game = import_pdf(args.pdf, config, dry_run=args.dry_run)
        except IMPORT_ERRORS as exc:
            print(f"Import se nezdařil: {exc}")
            return 1
        print(
            f"Zápas {game.number}: {game.date}  {game.home.name} "
            f"{game.home_score}:{game.away_score} {game.away.name}"
        )
        if args.dry_run:
            try:
                rows_by_sheet = build_seznamy_rows(game, config)
            except IMPORT_ERRORS as exc:
                print(f"Import se nezdařil: {exc}")
                return 1
            for sheet, rows in rows_by_sheet.items():
                print(f"  {sheet} ({len(rows)}):")
                for row in rows:
                    print(f"    {row}")
            print("(--dry-run: nic se nezapsalo)")
            return 0
        print(f"Zápas {game.number} zapsán do Seznamy DB.")
        return 0

    outcomes = import_folder(config, dry_run=args.dry_run)
    print_outcomes(outcomes)
    if args.dry_run:
        print("(--dry-run: nic se nezapsalo)")
    return 0


def cmd_standings(args: argparse.Namespace) -> int:
    config = load_config()

    try:
        html = fetch_standings_html()
    except Exception as exc:  # noqa: BLE001 – volitelný modul nesmí spadnout import
        print(f"Stránku Ligy juniorů se nepodařilo stáhnout: {exc}")
        return 1

    standings = parse_standings(html)
    standing = find_team(standings, config.team_name_in_pdf)
    if standing is None:
        print(f"{config.team_name_in_pdf} nebyl na stránce nalezen.")
        return 1

    print(
        f"{standing.team}: pozice {standing.position}. "
        f"(Z={standing.games} V={standing.wins} VP={standing.ot_wins} PP={standing.ot_losses} "
        f"P={standing.losses} skóre {standing.goals_for}:{standing.goals_against} "
        f"B={standing.points})"
    )

    issues = arithmetic_issues(standing)
    # Bilance i zápis pořadí jdou od cutoveru na Seznamy DB (viz PLAN.MD) –
    # produkční `Zápasy` už nové zápasy nedostává. Sloupce B:G (datum, domácí,
    # hosté, skóre domácí, skóre hosté, pozn.) mají stejný tvar jako dřív A:F
    # v produkční tabulce, `compute_record_from_rows` beze změny.
    seznamy_db_id = require_seznamy_db_spreadsheet_id(config)
    rows = read_range(
        config, f"{SEZNAMY_ZAPASY_SHEET}!B2:G100000", spreadsheet_id=seznamy_db_id
    )
    record = compute_record_from_rows(rows, config.team_short)
    issues += cross_check_issues(standing, record)

    if issues:
        print("Nevěrohodné – nesouhlasí s vlastní tabulkou, pořadí se nezapíše:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    row = last_game_row(config, seznamy_db_id)
    if row is None:
        print("V Seznamy DB zatím není žádný odehraný zápas.")
        return 1

    current = read_range(
        config,
        f"{SEZNAMY_ZAPASY_SHEET}!{SEZNAMY_PORADI_PO_KOLE_COLUMN}{row}",
        spreadsheet_id=seznamy_db_id,
    )
    current_value = current[0][0] if current and current[0] else ""
    print(
        f"Navrhovaný zápis: {SEZNAMY_ZAPASY_SHEET}!{SEZNAMY_PORADI_PO_KOLE_COLUMN}{row} = "
        f"{standing.position} (nyní: {current_value!r})"
    )

    if args.dry_run:
        print("(--dry-run: nic se nezapsalo)")
        return 0

    if not args.yes:
        answer = input("Zapsat? [y/N] ").strip().lower()
        if answer != "y":
            print("Zrušeno.")
            return 0

    write_poradi(config, seznamy_db_id, row, standing.position)
    print("Zapsáno.")
    return 0


def cmd_league_sync_games(args: argparse.Namespace) -> int:
    config = load_config()
    spreadsheet_id = require_league_db_spreadsheet_id(config)

    if not args.dry_run:
        ensure_league_sheets(config, spreadsheet_id)
    try:
        known_ids = read_known_game_ids(config, spreadsheet_id)
    except Exception:  # noqa: BLE001 – list ještě nemusí existovat (první běh, --dry-run)
        known_ids = set()

    played_games: list[tuple[int, int]] = []  # (kolo, game_id)
    page = 1
    while True:
        try:
            html = fetch_games_list_html(LEAGUE_COMPETITION_ID, page=page)
        except Exception as exc:  # noqa: BLE001
            print(f"Seznam zápasů se nepodařilo stáhnout (stránka {page}): {exc}")
            return 1
        played_games.extend(parse_played_games(html))
        if not has_next_page(html):
            break
        page += 1

    played_games = list(dict.fromkeys(played_games))
    new_games = [(kolo, gid) for kolo, gid in played_games if gid not in known_ids]
    print(f"Odehraných zápasů na webu: {len(played_games)}, nových k zápisu: {len(new_games)}")

    for round_number, game_id in new_games:
        try:
            detail_html = fetch_game_detail_html(game_id)
            game, goals, penalties, skaters, goalies = parse_game_detail(
                detail_html, game_id, round_number
            )
        except Exception as exc:  # noqa: BLE001 – jeden vadný zápas nesmí zastavit zbytek
            print(f"  zápas {game_id}: chyba při zpracování – {exc}")
            continue
        print(
            f"  kolo {round_number}: {game.date}  {game.home_team} "
            f"{game.home_score}:{game.away_score} {game.away_team}  "
            f"(#{game.game_number}, id {game_id})"
        )
        if not args.dry_run:
            try:
                append_game(config, spreadsheet_id, game, goals, penalties, skaters, goalies)
            except Exception as exc:  # noqa: BLE001 – jeden vadný zápas nesmí zastavit zbytek
                print(f"  zápas {game_id}: zápis do DB selhal – {exc}")
                continue

    if new_games and not args.dry_run:
        # Sezónní bodování a brankářské statistiky se dopočítají samy vzorcem
        # (viz Bruslaři/Brankáři - liga, postavené scripts/build_league_aggregate_sheets.py).
        refresh_group_membership(config, spreadsheet_id)
        recompute_standings_history(config, spreadsheet_id)
        print("Pořadí po kolech přepočítáno.")

    if args.dry_run:
        print("(--dry-run: nic se nezapsalo)")
    return 0


def cmd_league_sync_teams(args: argparse.Namespace) -> int:
    config = load_config()
    db_spreadsheet_id = require_league_db_spreadsheet_id(config)
    view_spreadsheet_id = require_league_v2_spreadsheet_id(config)

    teams = read_known_teams(config, db_spreadsheet_id)
    print(f"Týmů v syrových datech: {len(teams)}")

    for team in sorted(teams):
        needs_sheet = ensure_team_sheet(config, view_spreadsheet_id, team, dry_run=args.dry_run)
        if needs_sheet:
            action = "chybí list" if args.dry_run else "založen list"
            print(f"  {team}: {action} '{team_sheet_title(team)}'")

    if args.dry_run:
        print("(--dry-run: nic se nezapsalo)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="statistic_table")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Ověří přístup k Disku a Tabulce")
    check.set_defaults(func=cmd_check)

    import_cmd = subparsers.add_parser(
        "import",
        help="Naimportuje zápas(y) – z lokálního PDF, nebo (bez cesty) celou složku Zápisy",
    )
    import_cmd.add_argument(
        "pdf",
        nargs="?",
        default=None,
        help="Cesta k PDF zápisu (bez ní se projde celá složka Zápisy)",
    )
    import_cmd.add_argument(
        "--dry-run", action="store_true", help="Jen vypsat, co by se zapsalo"
    )
    import_cmd.set_defaults(func=cmd_import)

    standings_cmd = subparsers.add_parser(
        "standings", help="Zjistí pořadí LIT na stránce Ligy juniorů a nabídne zápis"
    )
    standings_cmd.add_argument(
        "--dry-run", action="store_true", help="Jen vypsat, co by se zapsalo"
    )
    standings_cmd.add_argument(
        "-y", "--yes", action="store_true", help="Nezobrazovat potvrzovací dotaz"
    )
    standings_cmd.set_defaults(func=cmd_standings)

    league_cmd = subparsers.add_parser(
        "league", help="Statistiky všech týmů Ligy juniorů (samostatná tabulka)"
    )
    league_sub = league_cmd.add_subparsers(dest="league_command", required=True)

    sync_games_cmd = league_sub.add_parser(
        "sync-games", help="Stáhne nové odehrané zápasy celé ligy a zapíše je do syrových listů"
    )
    sync_games_cmd.add_argument(
        "--dry-run", action="store_true", help="Jen vypsat, co by se zapsalo"
    )
    sync_games_cmd.set_defaults(func=cmd_league_sync_games)

    sync_teams_cmd = league_sub.add_parser(
        "sync-teams", help="Založí list pro každý tým nalezený v syrových datech"
    )
    sync_teams_cmd.add_argument(
        "--dry-run", action="store_true", help="Jen vypsat, které listy chybí"
    )
    sync_teams_cmd.set_defaults(func=cmd_league_sync_teams)

    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

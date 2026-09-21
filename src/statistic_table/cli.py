from __future__ import annotations

import argparse
import sys

from statistic_table.config import ZAPASY_DATA_START_ROW, ZAPASY_SHEET, load_config
from statistic_table.drive import list_pdf_files
from statistic_table.importer import (
    IMPORT_ERRORS,
    import_folder,
    import_pdf,
    print_outcomes,
    print_plan,
)
from statistic_table.logging_config import setup_logging
from statistic_table.sheets import check_headers, read_checks, read_player_registry, read_range
from statistic_table.standings import (
    arithmetic_issues,
    compute_record_from_rows,
    cross_check_issues,
    fetch_standings_html,
    find_team,
    last_played_row,
    parse_standings,
    write_position,
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
    club_roster = read_player_registry(config)

    if args.pdf:
        try:
            plan = import_pdf(args.pdf, config, club_roster, dry_run=args.dry_run)
        except IMPORT_ERRORS as exc:
            print(f"Import se nezdařil: {exc}")
            return 1
        print_plan(plan)
        if args.dry_run:
            print("(--dry-run: nic se nezapsalo)")
            return 0
        for label, value in read_checks(config, plan.row).items():
            print(f"{label}: {value!r}")
        return 0

    outcomes = import_folder(config, club_roster, dry_run=args.dry_run)
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
    rows = read_range(config, f"{ZAPASY_SHEET}!A{ZAPASY_DATA_START_ROW}:F1000")
    record = compute_record_from_rows(rows, config.team_short)
    issues += cross_check_issues(standing, record)

    if issues:
        print("Nevěrohodné – nesouhlasí s vlastní tabulkou, pořadí se nezapíše:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    row = last_played_row(config)
    if row is None:
        print("V tabulce zatím není žádný odehraný zápas.")
        return 1

    current = read_range(config, f"{ZAPASY_SHEET}!I{row}")
    current_value = current[0][0] if current and current[0] else ""
    print(
        f"Navrhovaný zápis: {ZAPASY_SHEET}!I{row} = {standing.position} "
        f"(nyní: {current_value!r})"
    )

    if args.dry_run:
        print("(--dry-run: nic se nezapsalo)")
        return 0

    if not args.yes:
        answer = input("Zapsat? [y/N] ").strip().lower()
        if answer != "y":
            print("Zrušeno.")
            return 0

    write_position(config, row, standing.position)
    print("Zapsáno.")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

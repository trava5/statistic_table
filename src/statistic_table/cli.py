from __future__ import annotations

import argparse
import sys

from statistic_table.config import load_config
from statistic_table.drive import list_pdf_files
from statistic_table.sheets import check_headers, read_player_registry, read_range


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="statistic_table")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Ověří přístup k Disku a Tabulce")
    check.set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

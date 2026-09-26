"""Jednoduché textové menu nad `python -m statistic_table.cli` – pro spouštění
na produkčním počítači bez nutnosti pamatovat si příkazy a přepínače."""

from __future__ import annotations

from collections.abc import Callable

from statistic_table.cli import main as cli_main


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def _confirm(prompt: str, *, default_yes: bool) -> bool:
    hint = "[A/n]" if default_yes else "[a/N]"
    answer = _ask(f"{prompt} {hint} ").lower()
    if not answer:
        return default_yes
    return answer in ("a", "ano", "y", "yes")


def _run(argv: list[str]) -> None:
    print(f"> statistic_table {' '.join(argv)}")
    cli_main(argv)


def menu_check() -> None:
    _run(["check"])


def menu_import_pdf() -> None:
    if _confirm("Celá složka Zápisy (ne jen jeden konkrétní soubor)?", default_yes=True):
        argv_base = ["import"]
    else:
        path = _ask("Cesta k PDF zápisu: ")
        if not path:
            print("Cesta nebyla zadána.")
            return
        argv_base = ["import", path]

    if _confirm("Nejdřív jen dry-run?", default_yes=True):
        _run([*argv_base, "--dry-run"])
        if not _confirm("Zapsat doopravdy?", default_yes=False):
            return
    _run(argv_base)


def menu_standings() -> None:
    if _confirm("Nejdřív jen dry-run?", default_yes=True):
        _run(["standings", "--dry-run"])
        if not _confirm("Pokračovat k zápisu?", default_yes=False):
            return
    _run(["standings"])


def menu_league_sync_games() -> None:
    if _confirm("Nejdřív jen dry-run?", default_yes=True):
        _run(["league", "sync-games", "--dry-run"])
        if not _confirm("Pokračovat k zápisu?", default_yes=False):
            return
    _run(["league", "sync-games"])


def menu_league_sync_teams() -> None:
    if _confirm("Nejdřív jen dry-run?", default_yes=True):
        _run(["league", "sync-teams", "--dry-run"])
        if not _confirm("Pokračovat k zápisu?", default_yes=False):
            return
    _run(["league", "sync-teams"])


MENU: dict[str, tuple[str, Callable[[], None] | None]] = {
    "1": ("Ověřit přístup k Disku a Tabulce", menu_check),
    "2": ("Import z PDF (Zápisy)", menu_import_pdf),
    "3": ("Zjistit a zapsat pořadí po kole", menu_standings),
    "4": ("Import z webu (Liga: nové odehrané zápasy)", menu_league_sync_games),
    "5": ("Liga: založit listy pro nové týmy", menu_league_sync_teams),
    "0": ("Konec", None),
}


def main() -> None:
    while True:
        print("\n=== statistic_table ===")
        for key, (label, _action) in MENU.items():
            print(f"  {key}) {label}")

        choice = _ask("Volba: ")
        if choice == "0":
            return

        entry = MENU.get(choice)
        if entry is None:
            print("Neplatná volba.")
            continue

        _, action = entry
        try:
            action()
        except KeyboardInterrupt:
            print("\nPřerušeno.")
        except Exception as exc:  # noqa: BLE001 – menu nesmí spadnout, jen ukáže chybu
            print(f"Chyba: {exc}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUkončeno.")

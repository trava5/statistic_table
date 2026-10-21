"""Orchestrace pre-scout: napojí `pre_scout_lt` (czechicehockey.tv, klipy)
na výběr příštího soupeře.

Soupeř pro list `Příští soupeř` v „HC LIT jun 2026/27“ se od 21. 10. 2026
vybírá ručně přes rozbalovací seznam přímo v tabulce (`B1`, data
validation – viz `scripts/build_seznamy_next_opponent_sheet.py`), ne
odsud – `run_pre_scout` řeší jen stahování klipů a (od 21. 10. 2026) jejich
nahrání na Disk, do Sheets nezapisuje (viz PLAN.MD)."""

from __future__ import annotations

from pathlib import Path

from statistic_table.config import Config, require_pre_scout_drive_folder_id
from statistic_table.drive import find_or_create_folder, upload_file

from .pre_scout_lt import ask_team, save_team_clips

OUTPUT_DIR = Path("./output/pre_scout")


def run_pre_scout(config: Config, query: str, output_dir: Path = OUTPUT_DIR) -> Path | None:
    """Zeptá se (pokud `query` nejde napárovat jednoznačně) na soupeře a
    stáhne klipy z jeho posledního odehraného zápasu. Klipy se zároveň
    nahrají na Disk do `Pre-scout/<tým>/` (OAuth za reálného uživatele,
    viz `drive.py`). Vrací lokální adresář s klipy, nebo None, pokud zápas
    nemá žádné góly ani přesilovky."""
    team = ask_team(query)
    run_dir = save_team_clips(team, config, output_dir)
    if run_dir is not None:
        upload_team_clips(config, team["name"], run_dir)
    return run_dir


def upload_team_clips(config: Config, team_name: str, run_dir: Path) -> None:
    """Nahraje všechny `.mp4`/`prehled.txt` z `run_dir` do `Pre-scout/<tým>/`
    na Disku. Jedna chyba u jednoho klipu (např. výpadek sítě) nezastaví
    nahrávání zbylých – každý soubor se nahrává samostatně a chyba se jen
    vypíše, lokální klipy v `run_dir` zůstávají jako záloha."""
    parent_id = require_pre_scout_drive_folder_id(config)
    folder_id = find_or_create_folder(config, parent_id, team_name)
    files = sorted(run_dir.glob("*.mp4")) + sorted(run_dir.glob("prehled.txt"))
    print(f"\nNahrávám {len(files)} souborů na Disk do 'Pre-scout/{team_name}/'...")
    for local_path in files:
        mime_type = "video/mp4" if local_path.suffix == ".mp4" else "text/plain"
        try:
            upload_file(config, folder_id, local_path, mime_type)
            print(f"  ✓ {local_path.name}")
        except Exception as exc:  # noqa: BLE001 - jeden neúspěšný upload nemá zastavit zbytek
            print(f"  ✗ {local_path.name}: {exc}")

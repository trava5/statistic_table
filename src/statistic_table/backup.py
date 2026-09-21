from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from statistic_table.config import SESTAVY_SHEET, ZAPASY_SHEET, Config
from statistic_table.sheets import read_range

BACKUP_DIR = Path("backups")


def write_backup(
    row: int, zapasy_row: list[str], sestavy_row: list[str], backup_dir: Path = BACKUP_DIR
) -> Path:
    """Čistá I/O funkce (jen disk, žádná síť) – uloží obsah řádku do JSON."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    payload = {"row": row, "timestamp": timestamp, "zapasy": zapasy_row, "sestavy": sestavy_row}
    slug = timestamp.replace(":", "-").replace(" ", "_")
    path = backup_dir / f"{slug}_radek{row}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def backup_row(config: Config, row: int, backup_dir: Path = BACKUP_DIR) -> Path:
    """Zálohuje aktuální obsah řádku (Zápasy i Sestavy) před přepsáním."""
    zapasy = read_range(config, f"{ZAPASY_SHEET}!A{row}:CO{row}")
    sestavy = read_range(config, f"{SESTAVY_SHEET}!A{row}:AB{row}")
    return write_backup(row, zapasy[0] if zapasy else [], sestavy[0] if sestavy else [], backup_dir)

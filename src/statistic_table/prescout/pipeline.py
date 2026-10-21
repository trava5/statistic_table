"""Orchestrace pre-scout: napojí `pre_scout_lt` (czechicehockey.tv, klipy)
na výběr příštího soupeře.

Soupeř pro list `Příští soupeř` v „HC LIT jun 2026/27“ se od 21. 10. 2026
vybírá ručně přes rozbalovací seznam přímo v tabulce (`B1`, data
validation – viz `scripts/build_seznamy_next_opponent_sheet.py`), ne
odsud – `run_pre_scout` řeší jen stahování klipů, do Sheets nezapisuje
(viz PLAN.MD)."""

from __future__ import annotations

from pathlib import Path

from statistic_table.config import Config

from .pre_scout_lt import ask_team, save_team_clips

OUTPUT_DIR = Path("./output/pre_scout")


def run_pre_scout(config: Config, query: str, output_dir: Path = OUTPUT_DIR) -> Path | None:
    """Zeptá se (pokud `query` nejde napárovat jednoznačně) na soupeře a
    stáhne klipy z jeho posledního odehraného zápasu. Vrací adresář s
    klipy, nebo None, pokud zápas nemá žádné góly ani přesilovky."""
    team = ask_team(query)
    return save_team_clips(team, config, output_dir)

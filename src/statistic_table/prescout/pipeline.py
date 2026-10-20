"""Orchestrace pre-scout: napojí `pre_scout_lt` (czechicehockey.tv, klipy)
na list `Příští soupeř` v „HC LIT jun 2026/27“ (viz PLAN.MD, 20. 10. 2026).

Název týmu vrácený `cihtv.find_teams` (czechicehockey.tv) se píše přímo do
`B1` – u všech 16 týmů Ligy juniorů ověřeno živě, že je identický s názvem
listu v Liga 2.0 (stejný svaz/registr, jen jiný web), takže žádné
dodatečné mapování není potřeba.
"""

from __future__ import annotations

from pathlib import Path

from statistic_table.config import (
    SEZNAMY_NEXT_OPPONENT_SHEET,
    SEZNAMY_NEXT_OPPONENT_TEAM_CELL,
    Config,
    require_seznamy_v2_spreadsheet_id,
)
from statistic_table.sheets import write_batch

from .pre_scout_lt import ask_team, save_team_clips

OUTPUT_DIR = Path("./output/pre_scout")


def write_next_opponent(config: Config, team_name: str) -> None:
    """Zapíše název soupeře do `B1` listu „Příští soupeř“ – IMPORTRANGE se
    podle toho sám přepočítá na kartu daného týmu z Liga 2.0."""
    spreadsheet_id = require_seznamy_v2_spreadsheet_id(config)
    cell = f"'{SEZNAMY_NEXT_OPPONENT_SHEET}'!{SEZNAMY_NEXT_OPPONENT_TEAM_CELL}"
    write_batch(config, spreadsheet_id, {cell: [team_name]})


def run_pre_scout(config: Config, query: str, output_dir: Path = OUTPUT_DIR) -> Path | None:
    """Zeptá se (pokud `query` nejde napárovat jednoznačně) na příštího
    soupeře, zapíše ho do „Příští soupeř“ a stáhne klipy z jeho posledního
    odehraného zápasu. Vrací adresář s klipy, nebo None, pokud zápas nemá
    žádné góly ani přesilovky."""
    team = ask_team(query)
    print(f"\nPříští soupeř: {team['name']}")
    write_next_opponent(config, team["name"])
    print(f"List „{SEZNAMY_NEXT_OPPONENT_SHEET}“ aktualizován.")
    return save_team_clips(team, config, output_dir)

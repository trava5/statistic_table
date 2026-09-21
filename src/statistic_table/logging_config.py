from __future__ import annotations

import logging
from pathlib import Path

LOG_FILE = Path("logs") / "statistic_table.log"


def setup_logging(log_file: Path = LOG_FILE) -> logging.Logger:
    """Nastaví logování do souboru (mimo git – viz .gitignore). Bezpečné volat
    opakovaně, handler se přidá jen jednou."""
    logger = logging.getLogger("statistic_table")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(handler)
    return logger

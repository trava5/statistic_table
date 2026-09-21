from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_VARS = (
    "GOOGLE_AUTH_MODE",
    "DRIVE_FOLDER_ID",
    "SPREADSHEET_ID",
    "TEAM_NAME_IN_PDF",
    "TEAM_SHORT",
    "SEASON_START_YEAR",
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


@dataclass(frozen=True)
class Config:
    google_auth_mode: str
    google_service_account_file: str | None
    drive_folder_id: str
    spreadsheet_id: str
    team_name_in_pdf: str
    team_short: str
    season_start_year: int


def load_config(env_file: str | Path = ".env") -> Config:
    load_dotenv(env_file, override=True)

    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Chybí proměnné v .env: {', '.join(missing)}")

    return Config(
        google_auth_mode=os.environ["GOOGLE_AUTH_MODE"],
        google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        drive_folder_id=os.environ["DRIVE_FOLDER_ID"],
        spreadsheet_id=os.environ["SPREADSHEET_ID"],
        team_name_in_pdf=os.environ["TEAM_NAME_IN_PDF"],
        team_short=os.environ["TEAM_SHORT"],
        season_start_year=int(os.environ["SEASON_START_YEAR"]),
    )


def get_credentials(config: Config):
    from google.oauth2 import service_account

    if config.google_auth_mode != "service_account":
        raise NotImplementedError("Zatím je podporován jen GOOGLE_AUTH_MODE=service_account")
    if not config.google_service_account_file:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE není v .env nastaven")
    return service_account.Credentials.from_service_account_file(
        config.google_service_account_file, scopes=SCOPES
    )


def col_to_index(letter: str) -> int:
    """Převede písmeno sloupce (A, ..., Z, AA, ...) na index od 0."""
    result = 0
    for ch in letter:
        result = result * 26 + (ord(ch.upper()) - ord("A") + 1)
    return result - 1


@dataclass(frozen=True)
class ColumnGroup:
    """Blok vstupních sloupců na listu, s volitelnou kontrolou záhlaví v `start`."""

    name: str
    start: str
    end: str
    header: str | None = None

    @property
    def capacity(self) -> int:
        return col_to_index(self.end) - col_to_index(self.start) + 1


def check_capacity(group: ColumnGroup, values: list, context: str) -> None:
    if len(values) > group.capacity:
        raise ValueError(
            f"{context}: sloupec '{group.name}' přesahuje kapacitu {group.capacity} "
            f"(zapisuje se {len(values)} hodnot)"
        )


# Písmena sloupců odpovídají stavu tabulky k 21. 9. 2026 (viz PROJECT.MD).
ZAPASY_SHEET = "Zápasy"
ZAPASY_HEADER_ROW = 5
ZAPASY_DATA_START_ROW = 6

ZAPASY_COLUMNS = {
    "zaklad": ColumnGroup("zaklad", "A", "E"),  # datum, home, away, HG, AG
    "poznamka": ColumnGroup("poznamka", "F", "F", header="pozn."),
    "poradi_po_kole": ColumnGroup("poradi_po_kole", "I", "I", header="pořadí po kole"),
    "branky": ColumnGroup("branky", "J", "T", header="Branky"),
    "prihravky": ColumnGroup("prihravky", "U", "AM", header="Přihrávky"),
    "specialni_cinnosti": ColumnGroup("specialni_cinnosti", "AR", "BA", header="přesilovky LIT"),
    "vylouceni_jmena": ColumnGroup("vylouceni_jmena", "BC", "BN", header="Vyloučení"),
    "vylouceni_minuty": ColumnGroup("vylouceni_minuty", "BO", "BZ", header="Minuty"),
    "rocniky_souper": ColumnGroup("rocniky_souper", "CJ", "CO", header="2005"),
}

SESTAVY_SHEET = "Sestavy"
SESTAVY_HEADER_ROW = 5
SESTAVY_DATA_START_ROW = 6

SESTAVY_COLUMNS = {
    "info": ColumnGroup("info", "F", "G", header="goalies"),
    "obranci": ColumnGroup("obranci", "H", "N", header="Defence"),
    "utocnici": ColumnGroup("utocnici", "O", "AB", header="Attack"),
}

SEZNAM_HRACU_SHEET = "Seznam hráčů"
SEZNAM_HRACU_HEADER_ROW = 2
SEZNAM_HRACU_DATA_START_ROW = 3

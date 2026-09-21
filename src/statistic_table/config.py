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

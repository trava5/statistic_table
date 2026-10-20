from __future__ import annotations

import json
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

# Zůstává "drive.readonly" – nahrávání MP4 klipů na Disk (pre-scout) je
# zatím odloženo (20. 10. 2026): servisní účet nemá vlastní úložiště
# ("Service Accounts do not have storage quota"), na běžném (ne Workspace)
# Google účtu nejde obejít ani plným scope "drive" bez Shared Drive nebo
# OAuth přihlášení za reálného uživatele – viz PLAN.MD. `drive.
# find_or_create_folder`/`upload_file` jsou připravené a funkční (založení
# složky ověřeno živě), jen se zatím nikde nevolají.
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
    league_spreadsheet_id: str | None = None
    league_db_spreadsheet_id: str | None = None
    league_v2_spreadsheet_id: str | None = None
    seznamy_db_spreadsheet_id: str | None = None
    seznamy_v2_spreadsheet_id: str | None = None
    seznamy_private_spreadsheet_id: str | None = None
    web_login: str | None = None
    web_passwd: str | None = None
    pre_scout_drive_folder_id: str | None = None


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
        league_spreadsheet_id=os.getenv("LEAGUE_SPREADSHEET_ID"),
        league_db_spreadsheet_id=os.getenv("LEAGUE_DB_SPREADSHEET_ID"),
        league_v2_spreadsheet_id=os.getenv("LEAGUE_V2_SPREADSHEET_ID"),
        seznamy_db_spreadsheet_id=os.getenv("SEZNAMY_DB_SPREADSHEET_ID"),
        seznamy_v2_spreadsheet_id=os.getenv("SEZNAMY_V2_SPREADSHEET_ID"),
        seznamy_private_spreadsheet_id=os.getenv("SEZNAMY_PRIVATE_SPREADSHEET_ID"),
        web_login=os.getenv("WEB_LOGIN"),
        web_passwd=os.getenv("WEB_PASSWD"),
        pre_scout_drive_folder_id=os.getenv("PRE_SCOUT_DRIVE_FOLDER_ID"),
    )


def require_league_spreadsheet_id(config: Config) -> str:
    if not config.league_spreadsheet_id:
        raise RuntimeError("Chybí LEAGUE_SPREADSHEET_ID v .env (viz README, sekce Liga)")
    return config.league_spreadsheet_id


def require_league_db_spreadsheet_id(config: Config) -> str:
    """DB tabulka – jediný zdroj pravdy pro ligová data, zapisuje jen Python
    (`league sync-games`). Prezentační listy (Liga, časem i Seznamy) do ní
    nezapisují, jen z ní čtou přes IMPORTRANGE – viz PLAN.MD."""
    if not config.league_db_spreadsheet_id:
        raise RuntimeError("Chybí LEAGUE_DB_SPREADSHEET_ID v .env (viz README, sekce Liga)")
    return config.league_db_spreadsheet_id


def require_league_v2_spreadsheet_id(config: Config) -> str:
    """„Liga 2.0“ – nová prezentační tabulka, čte z DB přes IMPORTRANGE
    (nahrazuje zamrzlou LEAGUE_SPREADSHEET_ID) – viz PLAN.MD."""
    if not config.league_v2_spreadsheet_id:
        raise RuntimeError("Chybí LEAGUE_V2_SPREADSHEET_ID v .env (viz README, sekce Liga)")
    return config.league_v2_spreadsheet_id


def require_seznamy_db_spreadsheet_id(config: Config) -> str:
    """DB tabulka – jediný zdroj pravdy pro data zápasů LIT z PDF (Zápasy,
    Góly, Vyloučení, Bruslaři/Brankáři (zápasy), oba týmy). Produkční
    `SPREADSHEET_ID` („Seznamy“) do ní zatím nezapisuje ani nečte, běží
    paralelně, dokud Seznamy 2.0 není hotová – viz PLAN.MD."""
    if not config.seznamy_db_spreadsheet_id:
        raise RuntimeError("Chybí SEZNAMY_DB_SPREADSHEET_ID v .env (viz README, sekce Seznamy)")
    return config.seznamy_db_spreadsheet_id


def require_seznamy_v2_spreadsheet_id(config: Config) -> str:
    """„Seznamy 2.0“ – nová prezentační tabulka, čte z DB přes IMPORTRANGE
    (rozpracováno, viz PLAN.MD)."""
    if not config.seznamy_v2_spreadsheet_id:
        raise RuntimeError("Chybí SEZNAMY_V2_SPREADSHEET_ID v .env (viz README, sekce Seznamy)")
    return config.seznamy_v2_spreadsheet_id


def require_seznamy_private_spreadsheet_id(config: Config) -> str:
    """Čistě soukromá tabulka pro `Seznam hráčů`/`Trenéři` (citlivé osobní
    údaje – rodné číslo, pojišťovna, telefon, e-mail, PIN trenérů), oddělená
    i od produkční `Seznamy` i od Seznamy DB. Servisní účet k ní má jen
    Prohlížeč – nikdy se do ní nezapisuje přes API, viz PLAN.MD (2. 10. 2026)."""
    if not config.seznamy_private_spreadsheet_id:
        raise RuntimeError(
            "Chybí SEZNAMY_PRIVATE_SPREADSHEET_ID v .env (viz README, sekce Seznamy)"
        )
    return config.seznamy_private_spreadsheet_id


def require_pre_scout_drive_folder_id(config: Config) -> str:
    """Složka na Disku (servisní účet má Editor), do které pre-scout vytváří
    podsložku pro každého soupeře a nahrává tam MP4 klipy – viz PLAN.MD,
    20. 10. 2026. Založená a nasdílená ručně, stejně jako DRIVE_FOLDER_ID."""
    if not config.pre_scout_drive_folder_id:
        raise RuntimeError(
            "Chybí PRE_SCOUT_DRIVE_FOLDER_ID v .env (viz README, sekce pre-scout)"
        )
    return config.pre_scout_drive_folder_id


def require_web_credentials(config: Config) -> tuple[str, str]:
    """Přihlašovací údaje pro czechicehockey.tv (pre-scout – stahování videí),
    ne Google. Nikam se neukládá, drží se jen v paměti běžícího procesu."""
    if not config.web_login or not config.web_passwd:
        raise RuntimeError("Chybí WEB_LOGIN/WEB_PASSWD v .env (viz README, sekce pre-scout)")
    return config.web_login, config.web_passwd


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
    # Skóre po třetinách (home:away) + prodloužení; přidáno 22. 9. 2026 na konec
    # tabulky (za CS), aby se neposunuly žádné stávající sloupce.
    "skore_treti": ColumnGroup("skore_treti", "CT", "CW", header="1.P"),
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

# Název soupeře, jak je uveden v PDF zápisu (Piráti Chomutov), na zkratku
# používanou v tabulce Zápasy (Chomutov). Nový soupeř = nová položka zde,
# nikdy se neodvozuje automaticky (různé kluby mají různé předpony).
TEAM_ALIASES = {
    "HC Příbram": "Příbram",
    "Piráti Chomutov": "Chomutov",
    "HC Olomouc": "Olomouc",
    "HK MD Šumperk": "Šumperk",
    "HC Hvězda Praha": "Hvězda",
    "SC Retia Kolín": "Kolín",
    "BK Havlíčkův Brod": "H.BR",
    "HC Tábor": "Tábor",
}

# Zkratky doplněné interaktivně při importu (viz importer.call_with_alias_
# prompt, PLAN.MD 11. 10. 2026) – oddělené od hardcoded TEAM_ALIASES výš,
# ať nový soupeř během importu nevyžaduje zásah do zdrojového kódu. Soubor
# je v gitu (ne .gitignore), takže doplnění přežije i po `git pull` na
# jiném stroji, ale je potřeba ho pak commitnout.
_TEAM_ALIASES_EXTRA_FILE = Path(__file__).parent / "team_aliases_extra.json"


def _load_extra_team_aliases() -> None:
    if not _TEAM_ALIASES_EXTRA_FILE.exists():
        return
    extra = json.loads(_TEAM_ALIASES_EXTRA_FILE.read_text(encoding="utf-8"))
    TEAM_ALIASES.update(extra)


_load_extra_team_aliases()


def add_team_alias(name: str, alias: str) -> None:
    """Trvale přidá dvojici (název soupeře -> zkratka pro tabulku Zápasy).
    Zapíše do `team_aliases_extra.json` (ne přímo do TEAM_ALIASES v kódu)
    a rovnou doplní i do běžícího `TEAM_ALIASES`, ať pokračuje i aktuální
    import bez restartu."""
    name = name.strip()
    alias = alias.strip()
    if not name or not alias:
        raise ValueError("Název soupeře i zkratka musí být nprázdné.")
    existing: dict[str, str] = {}
    if _TEAM_ALIASES_EXTRA_FILE.exists():
        existing = json.loads(_TEAM_ALIASES_EXTRA_FILE.read_text(encoding="utf-8"))
    existing[name] = alias
    _TEAM_ALIASES_EXTRA_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    TEAM_ALIASES[name] = alias

IMPORT_LOG_SHEET = "Import log"
IMPORT_LOG_HEADER_ROW = 1
IMPORT_LOG_DATA_START_ROW = 2
IMPORT_LOG_HEADER = ["soubor_id", "kontrolní součet", "číslo zápisu", "datum importu", "výsledek"]

STANDINGS_URL = "https://ceskyhokej.cz/souteze-juniori/liga-junioru"

# Liga juniorů 2026/27, id soutěže z URL https://ceskyhokej.cz/competition/games/19
LEAGUE_COMPETITION_ID = "19"

# Listy v DB tabulce (LEAGUE_DB_SPREADSHEET_ID) – jediný zdroj pravdy pro
# ligová data, zapisuje jen Python (`league sync-games`). Nikdo je needituje
# ručně, prezentační tabulky (Liga, časem Seznamy) z nich jen čtou.
LEAGUE_ZAPASY_SHEET = "Zápasy - liga"
LEAGUE_ZAPASY_TYM_SHEET = "Zápasy - liga (tým)"
LEAGUE_GOLY_SHEET = "Góly - liga"
LEAGUE_VYLOUCENI_SHEET = "Vyloučení - liga"
LEAGUE_PORADI_SHEET = "Pořadí - liga"
LEAGUE_SKUPINY_SHEET = "Skupiny - liga"

# Syrový log (skript sem jen přidává řádky, jeden řádek = jeden hráč v jednom
# zápase) – zdroj dat pro vzorce sezónních součtů níže.
LEAGUE_SKATERS_LOG_SHEET = "Bruslaři - liga (zápasy)"
LEAGUE_GOALIES_LOG_SHEET = "Brankáři - liga (zápasy)"

# Sezónní bodování/brankářské statistiky celé ligy – jeden řádek na hráče.
# Toto NEJSOU listy v DB – žijí v prezentační tabulce LEAGUE_SPREADSHEET_ID
# (Liga) jako vzorec (QUERY group by nad *_LOG_SHEET), postavené jednorázově
# scripts/build_league_aggregate_sheets.py. Python do nich nikdy nezapisuje.
LEAGUE_SKATERS_SHEET = "Bruslaři - liga"
LEAGUE_GOALIES_SHEET = "Brankáři - liga"

# Šablona per-tým prezentačního listu (vzorce QUERY/FILTER, skript ji jen kopíruje).
LEAGUE_TEAM_TEMPLATE_SHEET = "Tým – šablona"
LEAGUE_TEAM_NAME_CELL = "B1"

# Souhrnná tabulka obou skupin vedle sebe (vzorce nad Zápasy - liga (tým)/
# Skupiny - liga, žije jen v Liga 2.0, žádný list v DB) – postaveno
# jednorázově scripts/build_league_tabulka_sheet.py, správnost se
# kontroluje ručně proti STANDINGS_URL (viz PLAN.MD, 12. 10. 2026).
LEAGUE_TABULKA_SHEET = "Tabulka"

LEAGUE_ZAPASY_HEADER = [
    "game_id", "číslo utkání", "datum", "domácí", "hosté",
    "skóre domácí", "skóre hosté", "1.P", "2.P", "3.P", "OT", "pozn.", "diváci", "rozhodčí",
    "kolo",
]
LEAGUE_ZAPASY_TYM_HEADER = [
    "game_id", "tým", "soupeř", "datum", "doma/venku", "skóre tým", "skóre soupeř",
    "výsledek", "body", "1.P", "2.P", "3.P",
    "přesilovky", "góly v přesilovce", "oslabení", "obdržené góly v oslabení",
    "góly v oslabení (vstřelené)", "vyloučení", "trestné minuty", "kolo",
]
LEAGUE_GOLY_HEADER = [
    "game_id", "tým", "třetina", "čas", "střelec", "asistence 1", "asistence 2", "situace",
]
LEAGUE_VYLOUCENI_HEADER = ["game_id", "tým", "třetina", "čas", "hráč", "minuty", "důvod"]

LEAGUE_SKATERS_LOG_HEADER = [
    "game_id", "tým", "číslo", "hráč", "post", "G", "A", "B", "TM", "+/-",
]
LEAGUE_GOALIES_LOG_HEADER = [
    "game_id", "tým", "číslo", "hráč", "TOI", "zákroky", "obdržené góly", "%Z", "G", "A", "TM",
    "výsledek týmu",
]

# Sezónní součty (jeden řádek na hráče) – viz LEAGUE_SKATERS_SHEET výše.
LEAGUE_SKATERS_HEADER = ["tým", "číslo", "hráč", "post", "Z", "G", "A", "B", "TM", "+/-"]
LEAGUE_GOALIES_HEADER = [
    "tým", "číslo", "hráč", "Z", "obdržené góly", "obdržené góly/zápas",
    "G", "A", "TM", "výhry", "shutouty",
]

LEAGUE_PORADI_HEADER = ["kolo", "datum", "tým", "pořadí"]

# Členství ve skupině (1/2), obnovuje se scrapem oficiální tabulky při
# každém `league sync-games` – uložené jako fakt, aby `recompute_standings_
# history` nemusela scrapovat znovu a aby to šlo použít i odjinud.
LEAGUE_SKUPINY_HEADER = ["tým", "skupina"]

# Listy v DB tabulce (SEZNAMY_DB_SPREADSHEET_ID) – jediný zdroj pravdy pro
# zápasy LIT z PDF, zapisuje jen Python (`import`/`seznamy sync`). Symetricky
# pro oba týmy (domácí i hosté) – PDF je parsuje pro oba, dřív se soupeřova
# strana po naparsování zahazovala (viz PLAN.MD). Žádné vzorce, žádné
# citlivé osobní údaje (jen registrační číslo jako identifikátor).
SEZNAMY_ZAPASY_SHEET = "Zápasy"
SEZNAMY_ZAPASY_TYM_SHEET = "Zápasy (tým)"
SEZNAMY_GOLY_SHEET = "Góly"
SEZNAMY_VYLOUCENI_SHEET = "Vyloučení"
SEZNAMY_SKATERS_LOG_SHEET = "Bruslaři (zápasy)"
SEZNAMY_GOALIES_LOG_SHEET = "Brankáři (zápasy)"

SEZNAMY_ZAPASY_HEADER = [
    "číslo zápisu", "datum", "domácí", "hosté", "skóre domácí", "skóre hosté",
    "pozn.", "1.P", "2.P", "3.P", "OT", "pořadí po kole",
]
# "pořadí po kole" (sloupec L) se na rozdíl od zbytku řádku nezapisuje při
# importu zápasu (standings.py ho zjišťuje až dodatečně, scrapem stránky Ligy
# juniorů) – zapisuje ho samostatně cli.cmd_standings do posledního řádku.
SEZNAMY_PORADI_PO_KOLE_COLUMN = "L"
# Výsledek z pohledu daného týmu (přesilovky/oslabení, výsledek, body) – composite
# pravidlo s časovým párováním trestů, stejný důvod jako LEAGUE_ZAPASY_TYM_HEADER
# proč to zůstává v Pythonu (stats.py), ne ve vzorci. Bez "kolo" (LIT hraje jen
# svůj rozpis, ne celou soutěž).
SEZNAMY_ZAPASY_TYM_HEADER = [
    "číslo zápisu", "tým", "soupeř", "doma/venku", "skóre tým", "skóre soupeř",
    "výsledek", "body", "přesilovky", "góly v přesilovce", "oslabení",
    "obdržené góly v oslabení", "góly v oslabení (vstřelené)", "vyloučení", "trestné minuty",
]
SEZNAMY_GOLY_HEADER = [
    "číslo zápisu", "tým", "třetina", "čas", "střelec", "asistence 1", "asistence 2", "situace",
]
SEZNAMY_VYLOUCENI_HEADER = [
    "číslo zápisu", "tým", "třetina", "čas", "hráč", "minuty", "důvod", "od", "do",
]
SEZNAMY_SKATERS_LOG_HEADER = [
    "číslo zápisu", "tým", "číslo", "jméno", "registrace", "post", "nastoupil",
    "G", "A", "B", "TM",
]
SEZNAMY_GOALIES_LOG_HEADER = [
    # PDF nedává TOI ani počet zákroků (jen jméno brankáře, co chytal) – na
    # rozdíl od webu Ligy tyhle dva sloupce v Seznamy DB chybí.
    "číslo zápisu", "tým", "číslo", "jméno", "registrace", "chytal",
    "obdržené góly", "G", "A", "TM",
]

# Sezónní bodování/brankářské statistiky LIT – jeden řádek na hráče. Toto
# NEJSOU listy v DB – žijí v prezentační tabulce SEZNAMY_V2_SPREADSHEET_ID
# (Seznamy 2.0) jako vzorec (QUERY group by nad SEZNAMY_*_LOG_SHEET,
# filtrované na tým = LIT), postavené jednorázově scripts/build_seznamy_
# aggregate_sheets.py. Python do nich nikdy nezapisuje.
SEZNAMY_BODOVANI_SHEET = "Bodování"
SEZNAMY_BRANKARI_SHEET = "Brankáři"

# Týmový přehled (sezónní součty LIT:soupeř) – vzorec nad SEZNAMY_ZAPASY_TYM_SHEET
# a SEZNAMY_ZAPASY_SHEET, postavený jednorázově scripts/build_seznamy_tym_sheet.py.
SEZNAMY_TYM_SHEET = "Tým"

# Přehledový list pro trenérský štáb – vzorec nad Tým/Zápasy (tým)/Zápasy/
# Bodování/Brankáři, postavený jednorázově scripts/build_seznamy_dashboard.py.
SEZNAMY_DASHBOARD_SHEET = "Dashboard"

# Stejné kategorie jako Tým (sezónní přehled/přesilovky-oslabení/vyloučení-TM),
# jen počítané z posledních 5 odehraných zápasů LIT – aktuální forma týmu.
# Vzorec nad SEZNAMY_ZAPASY_TYM_SHEET, postavený jednorázově
# scripts/build_seznamy_last5_sheet.py.
SEZNAMY_LAST5_SHEET = "Last 5"

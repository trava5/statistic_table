# statistic_table

Import zápisů o utkání ČSLH (PDF) do evidenční tabulky HC Stadion Litoměřice U20
v Google Tabulkách. Účel, datový kontrakt a pravidla logiky jsou popsané v
[PROJECT.MD](PROJECT.MD), plán vývoje po krocích v [PLAN.MD](PLAN.MD).

## Instalace

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Přístup ke Google API

Skript potřebuje servisní účet s přístupem k Disku (čtení složky „Zápisy") a
k cílové tabulce (úpravy):

1. V Google Cloud Console založ projekt, zapni **Google Drive API** a
   **Google Sheets API**.
2. Vytvoř servisní účet, stáhni JSON klíč a ulož ho do `secrets/service_account.json`
   (složka `secrets/` je v `.gitignore`, klíč se nikdy nepushuje).
3. Nasdílej e-mail servisního účtu (`client_email` v JSON klíči):
   - složku „Zápisy" na Disku – stačí role Prohlížeč,
   - cílovou tabulku „Seznamy" – role Editor.
4. Tabulka „Seznamy" musí být **nativní Google Tabulka**, ne `.xlsx` soubor
   nahraný na Disk – Sheets API do `.xlsx` neumí zapisovat (Soubor → Uložit
   jako Google Tabulky).

## Konfigurace

Zkopíruj `.env.example` do `.env` a doplň:

```
GOOGLE_AUTH_MODE=service_account
GOOGLE_SERVICE_ACCOUNT_FILE=./secrets/service_account.json
DRIVE_FOLDER_ID=<ID složky Zápisy>
SPREADSHEET_ID=<ID nativní Google Tabulky Seznamy>
TEAM_NAME_IN_PDF=HC Stadion Litoměřice
TEAM_SHORT=LIT
SEASON_START_YEAR=2026
```

`DRIVE_FOLDER_ID` a `SPREADSHEET_ID` jsou **holá ID** (řetězec z URL), ne
celé sdílecí odkazy – např. z `.../folders/1k364.../` jen `1k364...`.

## Použití

```powershell
# Ověří přístup k Disku i Tabulce a rozložení sloupců
.venv\Scripts\python.exe -m statistic_table.cli check

# Naimportuje jeden lokální PDF (pro test/ladění)
.venv\Scripts\python.exe -m statistic_table.cli import cesta/k/zapisu.pdf --dry-run
.venv\Scripts\python.exe -m statistic_table.cli import cesta/k/zapisu.pdf

# Projde celou složku Zápisy, přeskočí už importované, zapíše nové
.venv\Scripts\python.exe -m statistic_table.cli import
.venv\Scripts\python.exe -m statistic_table.cli import --dry-run

# Zjistí pořadí LIT na stránce Ligy juniorů a po potvrzení ho zapíše
.venv\Scripts\python.exe -m statistic_table.cli standings
.venv\Scripts\python.exe -m statistic_table.cli standings --dry-run
.venv\Scripts\python.exe -m statistic_table.cli standings --yes   # bez dotazu

# Liga: stáhne nové odehrané zápasy VŠECH týmů (ne jen LIT) do DB tabulky
# LEAGUE_DB_SPREADSHEET_ID a založí chybějící listy jednotlivých týmů
# v prezentační tabulce LEAGUE_V2_SPREADSHEET_ID (Liga 2.0)
.venv\Scripts\python.exe -m statistic_table.cli league sync-games --dry-run
.venv\Scripts\python.exe -m statistic_table.cli league sync-games
.venv\Scripts\python.exe -m statistic_table.cli league sync-teams --dry-run
.venv\Scripts\python.exe -m statistic_table.cli league sync-teams
```

### Liga: statistiky všech týmů

Kromě evidence LIT z PDF zápisů umí skript stáhnout statistiky **všech**
týmů Ligy juniorů přímo z `ceskyhokej.cz` (stránky jednotlivých zápasů mají
kompletní zápis o utkání – soupisky, střelce, asistence, vyloučení – pro oba
týmy, ne jen pro LIT). Jsou na tom **dvě samostatné** Google Tabulky, ne
produkční tabulka „Seznamy“:

- **DB** (`LEAGUE_DB_SPREADSHEET_ID`) – jediný zdroj pravdy, zapisuje jen
  `league sync-games`. Žádné vzorce, jen syrová/dopočítaná data.
- **Liga 2.0** (`LEAGUE_V2_SPREADSHEET_ID`) – prezentační tabulka (Tým –
  šablona, per-tým listy, sezónní součty). Data nekopíruje – syrové listy
  jsou v ní jen `IMPORTRANGE` mirror nad DB (`scripts/build_league_v2_
  mirrors.py`), takže veškerá logika zůstává ve vzorcích a jediný zápis
  Pythonem je pořád do DB.

Stará tabulka `LEAGUE_SPREADSHEET_ID` (Liga) je zamrzlá/nahrazená Liga 2.0
a `.env` proměnná zůstává jen kvůli historii, nepoužívá se v žádném novém
kódu.

Postup nastavení:

1. Založ dvě nové nativní Google Tabulky (DB, Liga 2.0), obě nasdílej
   servisnímu účtu (role Editor), ID vlož do `LEAGUE_DB_SPREADSHEET_ID` a
   `LEAGUE_V2_SPREADSHEET_ID` v `.env`.
2. Syrové listy v DB (`Zápasy - liga`, `Zápasy - liga (tým)`, `Góly - liga`,
   `Vyloučení - liga`, `Pořadí - liga`, `Skupiny - liga`,
   `Bruslaři/Brankáři - liga (zápasy)` – per-zápas log) založí skript sám
   při prvním `league sync-games`.
3. `scripts/build_league_v2_mirrors.py` (spustit jednou, cíl Liga 2.0)
   postaví v Liga 2.0 pro každý syrový list z DB stejnojmenný list
   s jediným vzorcem `IMPORTRANGE`. Po prvním spuštění je nutné v prohlížeči
   ručně kliknout „Povolit přístup“ (Google to vyžaduje jednou za dvojici
   tabulek, nejde přes API) – do potvrzení mirror listy ukazují chybu.
4. `scripts/build_league_aggregate_sheets.py` (spustit jednou, cíl Liga 2.0)
   postaví listy **`Bruslaři - liga`** a **`Brankáři - liga`** –
   sezónní součty (jeden řádek na hráče za celou ligu) jako `QUERY` vzorec
   nad mirror listem `*-liga (zápasy)`. Python do těchto dvou listů nikdy
   nezapisuje.
5. `scripts/build_league_team_template.py` (spustit jednou, cíl Liga 2.0)
   postaví list **„Tým – šablona”** (Sezónní přehled, Přesilovky/oslabení,
   Vyloučení a TM, grafy Skóre po zápasech/po třetinách/Pořadí v tabulce,
   a dole vedle sebe Odehrané zápasy, Bodování (vč. sloupce Číslo) a
   Brankáři – vše přes `QUERY`/`SUMIF` parametrizované jménem týmu v buňce
   `B1`).
6. `league sync-games` – projde stránkovaný seznam zápasů ligy, přeskočí
   zápasy, které ještě neproběhly, i ty, které už jsou v DB, nové zapíše do
   DB, obnoví `Skupiny - liga` a přepočítá `Pořadí - liga` (viz PROJECT.MD,
   „Co je záměrně v Pythonu, co ve vzorcích“).
7. `league sync-teams` – přečte seznam týmů z DB a pro každý nalezený tým
   naklonuje „Tým – šablona“ (list `<název klubu>`) v Liga 2.0, pokud ještě
   neexistuje.

Skript do listu „Tým – šablona“ ani do jeho kopií nikdy nezapisuje vzorce,
jen buňku se jménem týmu – stejný princip jako u zbytku projektu (skript
zapisuje syrová data, tabulka počítá a prezentuje vzorci; výjimky, kde
Python počítá i něco navíc, jsou vysvětlené a zdůvodněné v PROJECT.MD).

`import` bez zápisu vyžaduje `--dry-run`, aby šlo předem zkontrolovat, co by
se zapsalo, beze změny tabulky.

### LIT Seznamy 2.0 (rozpracováno)

Produkční tabulka „Seznamy“ (`SPREADSHEET_ID`) běží dál beze změny. Vedle ní
`cli import` (soubor i celá složka) navíc **dual-write** zapisuje totéž do
`SEZNAMY_DB_SPREADSHEET_ID` – 5 syrových listů (`Zápasy`, `Góly`,
`Vyloučení`, `Bruslaři (zápasy)`, `Brankáři (zápasy)`), symetricky pro oba
týmy, viz PROJECT.MD/PLAN.MD. Bez nastavené `SEZNAMY_DB_SPREADSHEET_ID`
v `.env` se tenhle krok tiše přeskočí; pokud je nastavená, ale zápis selže,
je to jen varování v logu, produkční import to nezastaví.
`SEZNAMY_V2_SPREADSHEET_ID` (prezentační Seznamy 2.0) je zatím jen založená
prázdná tabulka bez napojení.

### Textové menu

Pro spouštění bez pamatování si příkazů a přepínačů (např. na produkčním
počítači) stačí:

```powershell
.venv\Scripts\python.exe main.py
```

Nabídne stejné čtyři akce (`check`, import jednoho PDF, import celé složky,
`standings`), u zápisu se vždy nejdřív zeptá na dry-run a pak na potvrzení.

## Co skript dělá a co ne

- Skript zapisuje **jen vstupní buňky** (soupisky, góly, přihrávky, tresty,
  ročníky soupeře – viz PROJECT.MD). Veškeré výpočty (body, průměry, listy
  Bodování/Brankáři/Tým) zůstávají ve vzorcích tabulky a skript se jich
  nedotýká.
- Před každým zápisem se aktuální obsah řádku (Zápasy i Sestavy) uloží do
  `backups/*.json` (mimo git). Při problému lze hodnoty ručně vrátit.
- Evidence importovaných souborů je na skrytém listu **Import log** v
  samotné tabulce – přežije změnu počítače. Druhé spuštění `import` nad
  stejnou složkou nic nezmění (soubory se stejným obsahem se přeskočí).
- Log běhu se ukládá do `logs/statistic_table.log` (mimo git).

## Řešení typických chyb

**„Neznámý hráč … není v Seznamu hráčů"** – hráč z PDF se nepodařilo
spárovat (podle čísla registrace, nebo podle příjmení a čísla dresu, pokud
registrace chybí). Doplň hráče do listu Seznam hráčů (příjmení, jméno,
číslo registrace, číslo dresu, post) a import spusť znovu.

**„Nejednoznačné párování hráče"** – více řádků v Seznamu hráčů odpovídá
stejnému příjmení bez jasného rozlišení (např. chybí číslo registrace u
duplicitního příjmení). Zkontroluj Seznam hráčů, případně dopiš rozlišovač
za příjmení (např. „Novotný D").

**„Rozložení tabulky neodpovídá očekávání"** (`check`) – záhlaví sloupců na
listu Zápasy/Sestavy se posunulo (např. po vložení nového sloupce). Uprav
mapu sloupců v `config.py` (`ZAPASY_COLUMNS`, `SESTAVY_COLUMNS`) podle
nového stavu tabulky.

**„… přesahuje kapacitu …"** – v jednom zápase je víc gólů/trestů/hráčů, než
kolik má odpovídající rozsah sloupců slotů (viz PROJECT.MD). Buď je to
chyba v PDF, nebo je potřeba rozšířit rozsah sloupců v tabulce i v
`config.py`.

**„Duplicitní zápis"** – dva různé soubory ve složce Zápisy mají stejné
číslo utkání. Zkontroluj, jestli nejde o omylem dvakrát nahraný zápis.

**„Soubor … byl od importu změněn"** – varování, ne chyba: soubor ve
složce má stejné ID jako už dříve importovaný, ale jiný obsah (např. oprava
překlepu v PDF). Skript ho automaticky nepřepíše; po ověření spusť import
ručně na ten konkrétní soubor: `cli import <cesta>`.

**Soupeř nemá zkratku (`TeamIdentificationError`)** – nový soupeř ještě
není v `TEAM_ALIASES` v `config.py` (např. `"HC Nový Klub": "Nový Klub"`).
Zkratky se nikdy neodvozují automaticky, protože kluby mají různé předpony.

**`standings` hlásí „Nevěrohodné"** – data ze stránky Ligy juniorů
nesouhlasí s vlastní tabulkou Zápasy (dřív se to jednou stalo). Pořadí se
v tom případě nezapíše; zkontroluj ručně na webu i v tabulce.

## Testy

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
```

Většina testů je čistá logika bez sítě (fixture kopie PDF, hlaviček tabulky
a stránky Ligy juniorů v `tests/fixtures/`). Integrační test zápisu do
Google Tabulky (`tests/test_integration_live_copy.py`) se bez nastaveného
`TEST_SPREADSHEET_ID` (kopie tabulky Seznamy nasdílená servisnímu účtu)
automaticky přeskočí – nikdy neběží proti ostré tabulce.

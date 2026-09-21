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
```

`import` bez zápisu vyžaduje `--dry-run`, aby šlo předem zkontrolovat, co by
se zapsalo, beze změny tabulky.

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

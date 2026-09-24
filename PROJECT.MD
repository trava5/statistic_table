# PROJECT – Statistic table (HC Stadion Litoměřice U20)

## Účel aplikace

Aplikace automaticky přenáší data z oficiálních zápisů o utkání ČSLH (PDF „Zápis o utkání“) do evidenční tabulky týmu HC Stadion Litoměřice U20 (Liga juniorů, ročník 2026/27, v tabulce zkráceně „LIT“) v Google Tabulkách.

Dosud se zápisy do tabulky přepisovaly ručně (nebo s asistencí Claude v konverzaci). Cílem je jeden Python skript, který se po spuštění:

1. připojí k Disku Google a načte obsah složky **Zápisy**,
2. zjistí, které PDF ještě nebyly importovány,
3. z každého nového zápisu vyčte data a spočítá odvozené statistiky podle pravidel níže,
4. zapíše vstupní hodnoty do listů **Zápasy** a **Sestavy** v Google Tabulce,
5. ověří kontrolní sloupce v tabulce a vypíše výsledek importu (co se zapsalo, co je potřeba doplnit ručně).

Uživatelé: realizační tým (asistent trenéra Michal), malý interní tým. Skript se spouští ručně (později případně plánovaně), není to veřejná služba.

## Rozdělení odpovědnosti

- **Python skript** = import: čtení PDF, párování hráčů, výpočet přesilovek/oslabení/trestů/ročníků, zápis vstupních buněk.
- **Google Tabulka** = výpočty a prezentace: statistiky hráčů (Bodování), brankářů (Brankáři), týmu (Tým) a body, průměry, kontroly zůstávají ve vzorcích tabulky. Skript do buněk se vzorci nikdy nezapisuje.

Důsledek: změna vzhledu nebo vzorců statistik se dělá v tabulce, změna způsobu čtení zápisu ve skriptu.

## Tabulka „Seznamy“

Listy: Zápasy, Sestavy, Bodování, Brankáři, Tým, Seznam hráčů, Trenéři.

Statistiky na listech Bodování a Brankáři se tvoří z listů Zápasy, Sestavy a Seznam hráčů.

### Vstupní buňky (zapisuje skript)

Písmena sloupců odpovídají stavu k 21. 9. 2026 (po vložení sloupce „pořadí po kole“). Ve skriptu budou v konfiguraci, ne natvrdo v kódu, a při startu se ověří záhlaví.

**Zápasy** (jeden řádek = jeden zápas, od řádku 6):

| Sloupce | Obsah |
|---|---|
| A:E | datum, home, away, HG, AG |
| F | pozn. (`pp` = po prodloužení, `sn` = po nájezdech, jinak prázdné) |
| I | pořadí LIT v tabulce po kole (ze stránky ceskyhokej.cz, viz níže) |
| J:T | Branky: příjmení střelců v pořadí gólů (jen LIT) |
| U:AM | Přihrávky: příjmení asistentů v pořadí gólů, za sebou (jen LIT) |
| AR:BA | přesilovky LIT/soupeř, góly v přesilovce LIT/soupeř, góly v oslabení LIT/soupeř, vyloučení LIT/soupeř, TM LIT/soupeř |
| BC:BN | příjmení vyloučených hráčů LIT |
| BO:BZ | trestné minuty těchto hráčů (stejné pořadí) |
| CJ:CO | počty hráčů soupeře podle ročníku 2005–2010 |
| CT:CW | skóre po třetinách a v prodloužení: `1.P`, `2.P`, `3.P`, `OT` (tvar `home:away`, stejná konvence jako HG/AG; `OT` prázdné mimo zápasy s prodloužením). Přidáno 22. 9. 2026 na konec tabulky (za CS), aby se neposunuly ostatní sloupce. |

**Sestavy** (stejné řádky jako Zápasy): F = počet brankářů v soupisce, G = brankář, který skutečně chytal, H:N obránci, O:AB útočníci (příjmení).

**Seznam hráčů**: soupiska týmu (příjmení, jméno, číslo registrace, číslo dresu, post). Slouží jako číselník pro párování. Ročník hráče = poslední čtyři číslice čísla registrace.

Vše ostatní jsou vzorce (body P, doma/venku, vstřelené/obdržené, kontroly jmen/trestů/ročníků, ročníky LIT CC:CI, věkové průměry CR:CS, listy Bodování, Brankáři, Tým).

## Pravidla logiky

**Klíč hráče.** Páruje se podle příjmení ze sloupce B listu Seznam hráčů. Shodná příjmení jsou rozlišena písmenem: Novotný D / Novotný T, Walter F / Walter V. Hráč se z PDF určí přes číslo registrace, případně přes dvojici číslo dresu + jméno (čísla dresů nejsou jednoznačná, Adelt a Hodek mají oba 15). Neznámý hráč znamená zastavení importu daného zápasu, nikdy hádání.

**Body.** Výhra 3, výhra po prodloužení/nájezdech 2, prohra po prodloužení/nájezdech 1, prohra 0 (počítá vzorec v tabulce z HG, AG a pozn.).

**Zápas se počítá** až po zadání HG i AG. Statistiky jsou v pohledu LIT : soupeř, ne domácí : hosté.

**Přesilovka** = každý 2min trest soupeře, který nebyl vyrovnán stejným trestem druhého týmu (stejný čas začátku, např. 4 na 4). Při dvojitém menším trestu jedné strany a jednom trestu druhé strany se jeden pár vyrovná a zbylý trest je přesilovka. 10min osobní tresty přesilovku nedávají. Oslabení týmu = přesilovky soupeře. Trest odsedělý spoluhráčem (číslo v závorce v zápise) se počítá jako přesilovka soupeře a připisuje se hráči, který ho dostal.

**Góly v přesilovce a v oslabení** se berou z herní situace (HS) u gólu: 5/3 a 5/4 je gól v přesilovce střelce, 4/5 a 3/5 gól v oslabení střelce.

**Vyloučení** = počet zapsaných trestů (2min menší trest plus 10min osobní trest téhož hráče jsou dvě vyloučení). **Trestné minuty** = součet minut.

**Ročníky.** Počítají se všichni bruslaři z listiny týmu a brankář, který skutečně chytal (přeškrtnutý brankář nehrál). Za LIT z Seznamu hráčů, za soupeře z čísel registrace v zápise (poslední čtyři číslice). Věkový průměr týmu = průměr z (rok zápasu − ročník), tedy věk v celých letech, skutečný je v průměru o půl roku nižší.

**Brankář** ve statistice je ten, kdo skutečně chytal.

**Střely** se neevidují (v zápise nejsou).

**Pořadí po kole.** Po každém odehraném kole se do sloupce I zapíše místo LIT v tabulce Ligy juniorů (https://ceskyhokej.cz/souteze-juniori/liga-junioru). Liga má dvě skupiny, LIT je ve Skupině 1 (Západní), bere se pořadí v ní. Stránka nezveřejňuje historii tabulky, takže pořadí se musí zjistit po odehrání kola, zpětně jen dopočtem z výsledků.

## Omezení Google Tabulek, která ovlivňují návrh

- COUNTIFS a SUMIFS neumí párovat rozsahy z různých listů (různý počet řádků). Proto listy Sestavy používají pomocné sloupce AD:AF. Skript nesmí tyto sloupce ani jejich vzorce měnit.
- Google Sheets API neumí zapisovat do souboru `.xlsx` uloženého na Disku. Skript proto vyžaduje tabulku ve formátu **nativních Google Tabulek** (viz PLAN.MD, krok 0).

## Zdroje dat a přístup

- Složka **Zápisy** na Disku Google: PDF zápisy ČSLH, jeden soubor = jeden zápas. Uživatelé nahrávají nové soubory.
- Cílová tabulka „Seznamy“ v Google Tabulkách, identifikovaná ID v konfiguraci.
- Účet s daty týmu: hc.lit.juniori@gmail.com. Přístup skriptu přes servisní účet nebo OAuth (viz PLAN.MD). Přihlášení heslem k Google API není možné, proto se stávající `.env.example` (gmail + password) nahradí.
- Tajné údaje (klíče, ID) patří pouze do `.env` a souboru klíče, oba mimo git (`.gitignore` už obsahuje `.env` a `.venv`).

## Zapsané zápasy (referenční data pro testy)

| Zápas | Výsledek | Přesilovky LIT:soupeř | Góly v PP | Góly v SH | Vyloučení | TM | Ročníky LIT 2006/07/08/09 | Ročníky soupeře | Věk Ø LIT:soupeř |
|---|---|---|---|---|---|---|---|---|---|
| 18. 9. 2026 LIT–Příbram (zápis č. 4002) | 1:3 | 6:7 | 1:0 | 0:1 | 9:7 | 26:14 | 3/9/7/0 | 2006/07/08 = 1/13/5 | 18,79 : 18,79 |
| 20. 9. 2026 Chomutov–LIT (zápis č. 4012) | 4:5 | 6:8 | 1:2 | 0:0 | 9:7 | 18:14 | 3/9/7/1 | 2006/07/08 = 2/4/11 | 18,70 : 18,47 |

Tyto dva zápasy (PDF + očekávané hodnoty) jsou základ regresních testů: import musí dát přesně stejné hodnoty, jaké jsou nyní v tabulce.

## Známé otevřené věci

- Šilhavý má v soupisce post A, v zápise D (rozhoduje zápis pro sestavu, Seznam hráčů zůstává).
- Adelt a Hodek mají shodné číslo dresu 15.
- Kotman a Nádemlenjský nemají číslo registrace (nelze párovat přes registraci).
- Ročníky 2005–2010 jsou v tabulce pevně dané, pro novou sezónu se musí rozšířit.

## Statistiky všech týmů ligy

Kromě evidence LIT z PDF (výše) umí skript (`cli league sync-games` /
`sync-teams`) stáhnout statistiky **všech** týmů Ligy juniorů přímo ze
stránek jednotlivých zápasů na `ceskyhokej.cz` (`/game/detail/<id>`) – ty
jsou server-renderované a obsahují pro oba týmy kompletní zápis o utkání
(soupisky, střelce, asistence s časem a herní situací, vyloučení s
minutáží a druhem trestu, skóre po třetinách). Data jdou do **samostatné**
Google Tabulky (`LEAGUE_SPREADSHEET_ID`), ne do „Seznamy“, ve stejném duchu
jako zbytek projektu: skript zapisuje jen syrová data. Listy `Zápasy - liga`,
`Zápasy - liga (tým)`, `Góly - liga`, `Vyloučení - liga` jsou normalizované
(jeden řádek = jedna událost). Bodování a brankářské statistiky mají navíc
dvě vrstvy: syrový log `Bruslaři/Brankáři - liga (zápasy)` (jeden řádek =
jeden hráč v jednom zápase, skript do něj jen přidává) a **sezónní součty**
`Bruslaři - liga` / `Brankáři - liga` (jeden řádek na hráče za celou
sezónu) – to už ale Python nezapisuje, je to `QUERY` vzorec nad logem,
jednorázově postavený `scripts/build_league_aggregate_sheets.py` (viz níže
„Co je (záměrně) v Pythonu, co ve vzorcích“). Prezentaci a součty za tým
dělá list „Tým – šablona“ vzorci `QUERY`/`SUMIF` nad sezónními součty
(Sezónní přehled,
Přesilovky/oslabení, Vyloučení a TM, grafy, a dole vedle sebe Odehrané
zápasy/Bodování s kompletní soupiskou/Brankáři), naklonovaný skriptem pro
každý tým zvlášť (`league sync-teams`). Šablonu samotnou staví jednorázově
`scripts/build_league_team_template.py`. Použití viz README, sekce „Liga:
statistiky všech týmů“; moduly: `league_model.py`, `league_scraper.py`,
`league_stats.py` (přesilovky/oslabení z pohledu libovolného týmu, stejné
pravidlo jako `stats.py`), `league_sheets.py`.

### Co je (záměrně) v Pythonu, co ve vzorcích

Princip zůstává „skript zapisuje jen vstupní data, výpočty a prezentaci dělá
tabulka vzorci“ – ale ne úplně bezvýjimečně. Tři místa v ligové části stojí
za vysvětlení, protože počítají víc než jen přepis naškrábaných čísel:

- **`Zápasy - liga (tým)`** (výsledek, body, přesilovky/oslabení za zápas) –
  počítá se v Pythonu (`league_stats.py`), protože jde o pravidlo s časovým
  párováním trestů (koincidenční menší tresty se ruší) a klasifikací herní
  situace u gólu – stejné pravidlo a stejný důvod, proč to i pro LIT počítá
  `stats.py` z PDF, ne vzorec v tabulce. Konzistentní s existujícím vzorem.
- **`Bruslaři - liga` / `Brankáři - liga`** (sezónní součty) – **vzorec**
  (`QUERY ... group by` nad `*_LOG_SHEET`), postavený jednorázově
  `scripts/build_league_aggregate_sheets.py`. Python do těchto listů
  nezapisuje vůbec nic, jen do syrového logu.
- **`Pořadí - liga`** (pořadí po každém kole) – zůstává v Pythonu
  (`league_sheets.recompute_standings_history`). Šlo by to postavit i
  vzorcem (kumulativní `SUMIFS` do daného kola + `COUNTIFS`-based pořadí
  v rámci skupiny), ale je to composite pravidlo se třemi úrovněmi
  tie-breaku nad dynamicky filtrovanou skupinou – vědomě ponecháno
  v testovaném Pythonu místo nepřehledného vzorce.

Až se do dat budou napojovat další analytické nástroje, tohle rozdělení
(syrová fakta vs. odvozené pohledy) je i důvod, proč zvažujeme samostatný
Google Sheet jako „databázovou“ vrstvu – viz diskuze v historii projektu.

## Struktura repozitáře

Stav k 21. 9. 2026 (Kroky 0–8 z PLAN.MD hotové, viz tam sekce „Stav“):

```
statistic_table/
  PROJECT.MD          účel a pravidla (tento soubor)
  PLAN.MD             plán migrace + průběžný stav
  README.md           instalace, přístupy, příkazy, řešení chyb
  main.py             textové menu nad cli.py (pro běžné používání)
  .env.example        vzor konfigurace
  src/statistic_table/
    config.py         načtení .env, mapa sloupců tabulky, aliasy soupeřů
    drive.py          Google Drive: složka Zápisy, výpis + stahování PDF
    sheets.py         Google Sheets: čtení/zápis, kontrola záhlaví, Import log
    pdf_parser.py     PDF -> datový model zápasu
    model.py          datové třídy (Game, TeamSheet, GamePlayer, Goal, Penalty,
                       RosterPlayer, ImportLogEntry)
    players.py        párování hráčů, určení týmu LIT/soupeře
    stats.py          přesilovky, góly PP/SH, tresty, ročníky, věk
    importer.py       orchestrace: PDF (jeden nebo celá složka) -> zápis
    standings.py      pořadí po kole z ceskyhokej.cz (volitelné)
    backup.py         záloha řádku před přepsáním (backups/, mimo git)
    logging_config.py logování do logs/ (mimo git)
    league_model.py   datové třídy pro statistiky celé ligy (LeagueGame,
                       LeagueGoal, LeaguePenalty, LeagueSkaterStat, LeagueGoalieStat)
    league_scraper.py rozparsování /game/detail/<id> a seznamu zápasů (ceskyhokej.cz)
    league_stats.py   přesilovky/oslabení/výsledek z pohledu libovolného týmu
    league_sheets.py  zápis do samostatné ligové tabulky, listy per tým
    cli.py            check / import / standings / league sync-games / league sync-teams
  scripts/
    build_league_team_template.py     jednorázové postavení listu „Tým – šablona“
    build_league_aggregate_sheets.py  jednorázové postavení Bruslaři/Brankáři - liga
  tests/
    fixtures/         PDF zápisy, uložené kopie hlaviček a stránky Ligy
    fixtures/league/  uložené stránky ceskyhokej.cz pro testy league_scraper.py
                       juniorů, očekávané hodnoty
    test_*.py         jednotkové testy (bez sítě) + skippable integrační
                       test na kopii tabulky
```

Adresáře `secrets/`, `backups/`, `logs/`, `.venv/` a soubor `.env` jsou
mimo git (obsahují klíče/citlivá data nebo se generují za běhu).

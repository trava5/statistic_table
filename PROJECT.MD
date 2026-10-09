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

## Tabulka „Seznamy“ (produkční, částečně zamrzlá od 26. 9. 2026)

Listy: Zápasy, Sestavy, Bodování, Brankáři, Tým, Seznam hráčů (od 2. 10. 2026
obnovený, viz níže), Import log. **`Trenéři` v produkční tabulce už není** –
přesunut beze zbytku do soukromé tabulky.

Statistiky na listech Bodování a Brankáři se tvoří z listů Zápasy, Sestavy a Seznam hráčů.

**Od cutoveru na Seznamy DB (26. 9. 2026, viz PLAN.MD) skript do listů Zápasy
a Sestavy níže už nezapisuje** – nové zápasy jdou jen do `SEZNAMY_DB_SPREADSHEET_ID`
(sekce „HC LIT jun 2026/27“ níže). Popis vstupních buněk zůstává jako historický
záznam toho, jak byla tabulka naplněná do 26. 9. 2026 (zápasy č. 4002–4026),
a jako reference pro `importer.build_import` (netknutý, ale nevolaný z živé
cesty).

**List `Seznam hráčů`** (a `Trenéři`, ten ale úplně) se 2. 10. 2026 přesunul
do nové, čistě soukromé tabulky (`SEZNAMY_PRIVATE_SPREADSHEET_ID`, viz
PLAN.MD) – citlivé osobní údaje (rodné číslo, pojišťovna, telefon, e-mail,
PIN trenérů) nemají ležet ve sdílené tabulce vedle zápasových dat. Trenér ji
dál edituje ručně, servisní účet k ní má jen roli **Prohlížeč**. Protože
`Bodování`/`Brankáři` v produkční tabulce (viz výš) na `Seznam hráčů`
formulově závisí (INDEX/MATCH), list byl v produkční tabulce znovu
obnoven jako **hybrid**, ne čistý mirror:
- sloupce A:F a H:I (neosobní administrativní údaje – příjmení, jméno,
  č. reg., číslo, post, „Z“-status, poznámka) jsou `IMPORTRANGE` ze soukromé
  tabulky,
- sloupec `G` („Z“ = odehrané zápasy) a pomocné sloupce `P:S` (góly/
  asistence/body/klíč řazení pro řazení v Bodování) jsou **místní vzorce**
  počítané přímo z produkční `Sestavy`/`Zápasy` – tahle část se z definice
  nedá importovat odjinud, musí se počítat proti aktuální (byť zamrzlé)
  produkční tabulce.

Skript k tomu: `scripts/restore_production_seznam_hracu.py` (jednorázový).

**Přidávání nových hráčů** (od 9. 10. 2026) řeší formulář přímo v soukromé
tabulce – `scripts/apps_script/seznam_hracu_pridat_hrace.gs` (Google Apps
Script, ne Python). Servisní účet má k soukromé tabulce jen Prohlížeč,
takže tahle repozitář do ní nemůže zapisovat ani instalovat Apps Script
projekt – kód musí trenér vložit sám do Rozšíření → Apps Script dané
tabulky (návod v hlavičce souboru). Nový hráč se vkládá `insertRowBefore`
na správné místo podle abecedy (příjmení, tie-break jméno, `localeCompare`
s českou lokalizací), sloupec A (pořadové číslo) se při každém přidání
přepíše na vzorec `=ROW()-2&"."` (ať se sám přepočítá při dalších
vloženích/mazáních). Sloupce G a P:S v soukromé tabulce jsou nefunkční
`#REF!` vzorce zděděné z produkční tabulky (odkazují na listy Sestavy/
Zápasy, co soukromá tabulka neobsahuje) – formulář je u nového řádku
nechává prázdné, jen funkční `T` (ročník (pom.)) dopočítá.

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

**Trestné střílení** (kód „TS" ve sloupci „Min." místo počtu minut, potvrzeno s uživatelem 3. 10. 2026) – nemá žádný čas v boxu ani interval Od/Do (PDF tam píše „---"), do TM se tedy nepočítá (`PENALTY_MINUTES_CODES` v `pdf_parser.py` mapuje na 0 minut). Jiný neznámý kód ve sloupci „Min." pořád zastaví import s chybou, nehádá se.

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
minutáží a druhem trestu, skóre po třetinách). Data jsou na **dvou
samostatných** Google Tabulkách, ne v „Seznamy“:

- **DB** (`LEAGUE_DB_SPREADSHEET_ID`) – jediný zdroj pravdy, zapisuje jen
  `league sync-games`. Listy `Zápasy - liga`, `Zápasy - liga (tým)`,
  `Góly - liga`, `Vyloučení - liga` jsou normalizované (jeden řádek =
  jedna událost), `Bruslaři/Brankáři - liga (zápasy)` je stejně normovaný
  log (jeden řádek = jeden hráč v jednom zápase), `Pořadí - liga` a
  `Skupiny - liga` jsou dopočítaná fakta (viz „Co je (záměrně) v Pythonu“
  níže). Žádné vzorce, jen data od Pythonu.
- **Liga 2.0** (`LEAGUE_V2_SPREADSHEET_ID`) – prezentační tabulka, nekopíruje
  žádná data ručně/Pythonem: syrové listy jsou v ní `IMPORTRANGE` mirror nad
  DB (jeden vzorec na list, `scripts/build_league_v2_mirrors.py`), takže
  jediný zápis Pythonem zůstává v DB. **Sezónní součty** `Bruslaři - liga` /
  `Brankáři - liga` (jeden řádek na hráče za celou sezónu) jsou tu `QUERY`
  vzorec nad mirror listem `*-liga (zápasy)`, jednorázově postavený
  `scripts/build_league_aggregate_sheets.py` – Python do nich nezapisuje.
  List „Tým – šablona“ vzorci `QUERY`/`SUMIF` nad sezónními součty (Sezónní
  přehled vč. „Bodového zisku“ – `H5`, `=F5/(A5*3)`, podíl ze zisku
  maximálně možných bodů, od 5. 10. 2026 – Přesilovky/oslabení, Vyloučení
  a TM, grafy, a dole vedle sebe Odehrané zápasy/Bodování s kompletní
  soupiskou vč. čísla dresu/Brankáři), naklonovaný skriptem pro každý tým
  zvlášť (`league sync-teams`). Šablonu samotnou staví jednorázově
  `scripts/build_league_team_template.py` – `sync-teams` klonuje šablonu
  jen pro nové týmy, dodatečná změna šablony (jako „Bodový zisk“) se do
  existujících listů týmů musí doplnit ručním patchem (viz PLAN.MD).
  Stará tabulka `LEAGUE_SPREADSHEET_ID` (Liga) je zamrzlá, nahrazená
  Liga 2.0. Použití viz README, sekce „Liga: statistiky všech týmů“; moduly:
  `league_model.py`, `league_scraper.py`, `league_stats.py`
  (přesilovky/oslabení z pohledu libovolného týmu, stejné pravidlo jako
  `stats.py`), `league_sheets.py`.

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
  v testovaném Pythonu místo nepřehledného vzorce. Členství ve skupině
  (`Skupiny - liga`) obnovuje `league_sheets.refresh_group_membership`
  živým scrapem při každém `league sync-games` – uložené jako fakt v DB,
  aby přepočet pořadí nemusel scrapovat znovu a šlo to použít i odjinud.
  **Známé omezení** (narazilo 2. 10. 2026, viz PLAN.MD): přepočet vychází
  jen z výsledků uložených při prvním stažení zápasu – pokud web výsledek
  dodatečně opraví (např. prodloužení → regulérní výsledek), dedup podle
  `game_id` to nerozpozná a DB zůstane s neplatnými daty, dokud to někdo
  nenahlásí a zápas se ručně nesmaže a znovu nezasynchronizuje.

Až se do dat budou napojovat další analytické nástroje, tohle rozdělení
(syrová fakta vs. odvozené pohledy) je i důvod, proč zvažujeme samostatný
Google Sheet jako „databázovou“ vrstvu – viz diskuze v historii projektu.

## LIT „HC LIT jun 2026/27“ (od 26. 9. 2026 živá architektura, dřívější „Seznamy“ nahradila; tabulka přejmenována z „Seznamy 2.0“ 5. 10. 2026 – jen titulek, ID/obsah beze změny)

Stejný DB → prezentace vzor jako u Ligy, tentokrát nad daty LIT z PDF
(`import_pdf`/`import_folder`), ne z webu. **Cutover dokončen 26. 9. 2026**
(viz PLAN.MD) – `cli import` zapisuje jen do Seznamy DB, přímý zápis do
produkční „Seznamy“ (buňka po buňce přes `Seznam hráčů`) skončil.
`importer.build_import`/`ImportPlan` (mapování na starou produkční tabulku)
zůstávají v kódu netknuté a otestované jako referenční/legacy cesta, jen se
nevolají odnikud za běhu.

- **Seznamy DB** (`SEZNAMY_DB_SPREADSHEET_ID`) – 6 syrových listů (`Zápasy`,
  `Zápasy (tým)`, `Góly`, `Vyloučení`, `Bruslaři (zápasy)`, `Brankáři
  (zápasy)`), **symetricky pro oba týmy** (na rozdíl od bývalého zápisu do
  produkční `Seznamy`, kde se soupeřova strana po naparsování PDF
  zahazovala). Jediný cíl zápisu `cli import` (`seznamy_sheets.append_game`,
  dedup podle čísla zápisu, `_append_all_or_nothing` maže rozepsané řádky
  při chybě uprostřed zápisu – zápas skončí zapsaný celý, nebo vůbec).
  Identita hráče (jméno, registrace) je soběstačná v rámci jednoho PDF,
  nepotřebuje `Seznam hráčů`. `Zápasy` má navíc sloupec `L` „pořadí po
  kole“ – na rozdíl od zbytku řádku (zapisuje `cli import`) ho doplňuje
  `cli league sync-games` (`seznamy_sheets.sync_poradi_from_liga`, viz
  PLAN.MD 3. 10. 2026): Liga DB `Pořadí - liga` je jediný úplný zdroj
  historie pořadí (přepočítává ji pro všechny týmy včetně LIT při každém
  novém zápase), takže se LIT pořadí páruje přes číslo utkání a doplňuje
  pro všechny odehrané zápasy najednou, ne jen pro poslední. `cli
  standings` (scrape aktuální pozice z oficiální stránky) od téhle změny
  nic nezapisuje, slouží jen jako nezávislá kontrola věrohodnosti proti
  vlastnímu záznamu. `Zápasy (tým)` (výsledek, body, přesilovky/oslabení za zápas
  z pohledu daného týmu) počítá Python stejným principem jako `Zápasy -
  liga (tým)` u Ligy – composite pravidlo s časovým párováním trestů, ne
  vzorec (viz „Co je záměrně v Pythonu“ níže).
- **HC LIT jun 2026/27** (`SEZNAMY_V2_SPREADSHEET_ID`, dříve „Seznamy 2.0“) –
  prezentační tabulka, jediné místo, které trenérský štáb sleduje po
  cutoveru. `IMPORTRANGE` mirror
  syrových listů z DB (`scripts/build_seznamy_v2_mirrors.py`, spill `A:L`
  u `Zápasy` – zahrnuje i „pořadí po kole“) + neosobních sloupců B:F
  (Příjmení, Jméno, č. reg., číslo, post) `Seznam hráčů` ze **soukromé**
  tabulky (`SEZNAMY_PRIVATE_SPREADSHEET_ID`, od 2. 10. 2026 – viz výše
  a PLAN.MD; **nikdy** celý `Seznam hráčů`, od sloupce J má citlivé osobní
  údaje). Mirror listu `Zápasy` má navíc mimo spill sloupce `M:N`
  („Góly“/„Asistence“ – střelci/nahrávači LIT za daný zápas, FILTER+TEXTJOIN
  nad `Góly`) a mirror `Brankáři (zápasy)` sloupce `K:L` („výsledek“/
  „vychytaná výhra“, MATCH proti `Zápasy (tým)`), obojí po řádcích, ne jako
  `ARRAYFORMULA` (nespolehlivé se zřetězeným polem jako lookup, viz skript).
  „Vychytaná výhra“ navíc podmíněná sloupcem `F` („chytal“, 0/1) – list má
  pro každý zápas řádek pro oba brankáře v soupisce, i náhradníka, takže
  bez týhle podmínky dostal kredit za výhru i ten, co vůbec nechytal
  (oprava 3. 10. 2026, viz PLAN.MD).
  `Bodování` (nativní Sheets Tabulka, řazení kliknutím na hlavičku) a
  `Brankáři` (vč. „Vychytané výhry“/„% výher“ ze sloupců výše, zatím bez
  shutoutu) jsou `QUERY group by` nad `Bruslaři/Brankáři (zápasy)`
  filtrované na LIT (`scripts/build_seznamy_aggregate_sheets.py`),
  zjednodušené oproti produkční tabulce (jméno přímo z logu, bez INDEX/
  MATCH do `Seznam hráčů`). `Tým` (`scripts/build_seznamy_tym_sheet.py`) je
  sezónní přehled LIT:soupeř (`SUMIF`/`COUNTIF` nad `Zápasy (tým)`) + skóre
  po třetinách (`REGEXEXTRACT` nad `Zápasy`, rozpad podle domácí/hosté) –
  zatím bez sekce Ročníky. `Dashboard` (`scripts/build_seznamy_dashboard.py`)
  je přehled pro trenérský štáb nad `Tým`/`Bodování`/`Brankáři` (žádná
  vlastní syrová data) – sezónní přehled vč. „Pořadí v lize“
  (`INDEX`+`COUNTA` nad mirrored `Zápasy!L`) a „Bodového zisku“ (`I5`,
  `=F5/(A5*3)`, stejná buňka jako na Liga 2.0, posunutá na `I`, protože
  `H` zabírá „Pořadí v lize“), přesilovky/oslabení, vyloučení/TM, grafy
  Skóre po zápasech/po třetinách, a pod tím (od
  5. 10. 2026, stejné rozložení jako Liga 2.0 team template) Odehrané
  zápasy/Bodování/Brankáři vedle sebe – zjednodušený seznam odehraných
  zápasů dohledává „Datum“ přes `VLOOKUP` do `Zápasy` (`Zápasy (tým)`
  nemá sloupec s datem), zbytek z pole skrytého raw helperu `QUERY`.
  `Last 5` (`scripts/build_seznamy_last5_sheet.py`, 3. 10. 2026) má stejné
  tabulkové sekce a rozložení jako Dashboard (sezónní přehled vč.
  „Bodového zisku“ na `H5` – tady `H` volné, žádné „Pořadí v lize“ –
  /přesilovky-oslabení/vyloučení-TM, pod tím Bodování a Brankáři vedle
  sebe), ale spočítané jen z **posledních 5 odehraných zápasů LIT**
  místo celé sezóny – aktuální forma týmu. Bez grafů (vědomě,
  odsouhlaseno s uživatelem).
  `Zápasy (tým)` nemá sloupec s datem, takže „posledních 5“ se vybírá podle
  čísla zápisu (`QUERY ... order by A desc limit 5` do skrytého pomocného
  sloupce N2:N6) – čísla zápisů přiděluje svaz postupně podle termínu,
  takže to dá stejné pořadí jako datum, a `QUERY` sloupec se samými čísly
  automaticky vyhodnotí jako číselný typ (na rozdíl od řazení data jako
  textu u Liga 2.0, viz výš, tu tedy nehrozí problém s různým počtem
  znaků). Týmové součty filtrují `Zápasy (tým)` přes `SUMPRODUCT` s
  `COUNTIF` proti tomuhle seznamu (ne `SUMIF`/`COUNTIFS`, ty neumí podmínku
  „je v seznamu hodnot“); Bodování/Brankáři počítají znovu přímo z
  `Bruslaři/Brankáři (zápasy)` (ne ze sezónních agregátů – ty nejdou
  dodatečně omezit na 5 zápasů) stejným `QUERY group by` vzorem, jen
  s podmínkou na posledních 5 čísel zápisu sestavenou jako dynamický
  řetězec (`QUERY` neumí „hodnota je v rozsahu“ přímo).
- Modul: `seznamy_sheets.py` (`build_seznamy_rows` – čistá funkce, žádná
  síť; `append_game` – I/O, dedup podle čísla zápisu; `sync_poradi_from_liga`
  – zápis pořadí po kole ze sdíleného zdroje Liga DB).
- `stats.third_and_relative_time` – PDF má čas gólu/trestu jako průběžný
  čas zápasu, ne čas od začátku třetiny; tahle funkce ho rozdělí.
- **Otevřené:** Ročníky v `Tým` a shutout v `Brankáři` zatím chybí (viz
  PLAN.MD, „Další krok“).

## Struktura repozitáře

Stav k 26. 9. 2026 (Kroky 0–8 z PLAN.MD hotové + cutover LIT na Seznamy DB
dokončen, viz tam sekce „Stav“):

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
    sheets.py         Google Sheets: čtení/zápis, kontrola záhlaví produkční
                       tabulky (`spreadsheet_id` teď parametr, ne natvrdo)
    pdf_parser.py     PDF -> datový model zápasu
    model.py          datové třídy (Game, TeamSheet, GamePlayer, Goal, Penalty,
                       RosterPlayer, ImportLogEntry)
    players.py        párování hráčů, určení týmu LIT/soupeře
    stats.py          přesilovky, góly PP/SH, tresty, ročníky, věk
    importer.py       orchestrace: PDF (jeden nebo celá složka) -> Seznamy DB;
                       `build_import`/`ImportPlan` (stará produkční cesta)
                       netknuté jako referenční/legacy kód, nevolané za běhu
    standings.py      kontrola věrohodnosti pořadí LIT proti oficiální
                       stránce ceskyhokej.cz (diagnostické, čistá logika)
    backup.py         záloha řádku produkční tabulky před přepsáním
                       (backups/, mimo git) – používá jen legacy `build_import`
    logging_config.py logování do logs/ (mimo git)
    league_model.py   datové třídy pro statistiky celé ligy (LeagueGame,
                       LeagueGoal, LeaguePenalty, LeagueSkaterStat, LeagueGoalieStat)
    league_scraper.py rozparsování /game/detail/<id> a seznamu zápasů (ceskyhokej.cz)
    league_stats.py   přesilovky/oslabení/výsledek z pohledu libovolného týmu
    league_sheets.py  zápis do Liga DB, listy per tým v Liga 2.0
                       (`_append_all_or_nothing` – rollback při chybě uprostřed zápisu)
    seznamy_sheets.py zápis do Seznamy DB (6 syrových listů, oba týmy, z PDF;
                       `sync_poradi_from_liga` doplňuje pořadí po kole z Liga DB)
    cli.py            check / import / standings / league sync-games / league sync-teams
  scripts/
    build_league_team_template.py     jednorázové postavení listu „Tým – šablona“
    build_league_aggregate_sheets.py  jednorázové postavení Bruslaři/Brankáři - liga
    build_league_v2_mirrors.py        jednorázové IMPORTRANGE zrcadlo DB v Liga 2.0
    build_league_poradi_view.py       přehled Skupina 1/2 na listu Pořadí - liga
    build_seznamy_v2_mirrors.py       jednorázové IMPORTRANGE zrcadlo DB v HC LIT jun 2026/27
    build_seznamy_aggregate_sheets.py jednorázové postavení Bodování/Brankáři v HC LIT jun 2026/27
    build_seznamy_tym_sheet.py        jednorázové postavení listu Tým v HC LIT jun 2026/27
    build_seznamy_dashboard.py        jednorázové postavení listu Dashboard v HC LIT jun 2026/27
    build_seznamy_last5_sheet.py      jednorázové postavení listu Last 5 (forma
                                       za posledních 5 zápasů) v HC LIT jun 2026/27
    restore_production_seznam_hracu.py obnova listu Seznam hráčů v produkční
                                       tabulce po přesunu do soukromé tabulky
    apps_script/
      seznam_hracu_pridat_hrace.gs     Google Apps Script (ne Python) - formulář
                                       "Přidat hráče" v soukromé tabulce Seznam
                                       hráčů, vkládá ručně trenér (servisní účet
                                       tam má jen Prohlížeč, viz výš)
  tests/
    fixtures/         PDF zápisy, uložené kopie hlaviček a stránky Ligy
    fixtures/league/  uložené stránky ceskyhokej.cz pro testy league_scraper.py
                       juniorů, očekávané hodnoty
    test_*.py         jednotkové testy (bez sítě) + skippable integrační
                       test na kopii tabulky
```

Adresáře `secrets/`, `backups/`, `logs/`, `.venv/` a soubor `.env` jsou
mimo git (obsahují klíče/citlivá data nebo se generují za běhu).

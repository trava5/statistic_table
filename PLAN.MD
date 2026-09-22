# PLAN – migrace logiky z konverzace do Python skriptu

Popis cíle a pravidel je v [PROJECT.MD](PROJECT.MD). Tento plán rozděluje práci na kroky, které lze dělat a ověřovat postupně v IDE. Každý krok má výstup a kritérium hotovo.

## Stav k 21. 9. 2026

**Kroky 0–8 hotové a pushnuté** na `origin/master` (poslední commit
`3c6124d`, „Přidat main.py"). Oba referenční zápasy (4002 LIT–Příbram,
4012 Chomutov–LIT) jsou reálně zapsané v ostré tabulce, list „Import log"
založen a funguje (druhé spuštění `cli import` nic nezmění). Pořadí LIT
(`Zápasy!I7`) nezávisle ověřeno proti stránce Ligy juniorů. `main.py`
přidává textové menu nad `cli.py` pro běžné používání bez pamatování si
přepínačů. 89 testů zelených (+ 1 skippable integrační bez
`TEST_SPREADSHEET_ID`), ruff bez chyb.

**Co zbývá:**
- **Krok 9 – Přechod**: čeká se na další reálný zápas. Postup: naimportovat
  skriptem (přes `main.py` nebo `cli import <pdf> --dry-run` → `cli import
  <pdf>`), porovnat s ručním výsledkem, po pár úspěšných zápasech ukončit
  ruční asistenci v konverzaci.
- **Automatizace spouštění** (Krok 8, bod 5) vědomě odložena – appka se
  zatím spouští ručně na vývojovém i produkčním PC. Zvažované možnosti:
  Windows Task Scheduler, domácí server/NAS s cronem, GitHub Actions
  (repo je na GitHubu, ale klíč servisního účtu by musel jako secret).
  Rozhodnutí padne, až bude appka nějakou dobu v ručním provozu ověřená.

**Poznatky z implementace (užitečné při dalším ladění):**
- Písmena sloupců v tabulce (viz PROJECT.MD) se od 21. 9. 2026 neposunula,
  ověřeno živě proti hlavičce – kontrola v `config.py`/`sheets.py` na
  budoucí posun hlídá.
- **Algoritmus přesilovek** (`stats.power_plays`): přesilovka = 2min trest,
  který nemá soupeřův trest se stejným časem začátku (`Od`). Časové úseky
  se NEslučují do jedné přesilovky, i když se v čase překrývají – první
  verze to dělala a dávala o 1 méně, než je ve skutečné tabulce (ověřeno
  na zápase 4002, kde oba týmy dostaly koincidenční trest ve stejný čas).
- **Pořadí jmen v Sestavy H:N/O:AB** (obránci/útočníci) v živé tabulce
  neodpovídá žádné odvoditelné konvenci z PDF (zkoušeno: pořadí v zápise,
  pořadí v Seznamu hráčů, číslo dresu – žádné nesedí). `importer.py` proto
  zapisuje v pořadí z PDF soupisky a testy porovnávají množinu jmen, ne
  přesné pořadí.
- **Brankář, který skutečně chytal**, se pozná podle „evidence brankářů"
  v souhrnné tabulce na 1. straně zápisu (sloupce BA/BB), ne přeškrtnutím
  v soupisce – to se ukázalo jednodušší a spolehlivější.
- Seznam hráčů už má rozlišovače rovnou v příjmení („Novotný D", „Walter
  V"), není potřeba je dopočítávat.

**Ruční úpravy tabulky mimo skript (21. 9. 2026):** listy Bodování a
Brankáři používají nativní Sheets „Tabulku" (Table), ne klasický filtr –
proto `setBasicFilter` selže, pokud rozsah částečně protíná tabulku
(potřeba `updateTable`, ne `setBasicFilter`).

- Opraveno rozbité pravidlo ověření dat (vlastní vzorec doslova `=0`,
  které je vždy nepravdivé bez ohledu na obsah buňky – proto hláška
  „Neplatné" u správně načtených hodnot). Bylo na `Bodování!B2:C33`
  a `Brankáři!C2:K5`, smazáno přes `setDataValidation` bez pravidla.
- Bodování: sloupec „vyloučení" (COUNTIF, počet trestů) nahrazen sloupcem
  **TM** (trestné minuty) – použit vzorec, který už dřív fakticky počítal
  TM, jen byl schovaný pod špatným názvem „Jméno a"
  (`SUMPRODUCT(('Zápasy'!$BC$6:$BN$500=$A{row})*('Zápasy'!$BO$6:$BZ$500))`).
  Sloupec „Jméno a" smazán, tabulka zúžená zpět na `A1:I33`, takže
  „Sloupec 1" a „odehrané zápasy" zůstávají mimo tabulku (mimo
  řazení/filtr).
- Nativní tabulka na listu Bodování/Brankáři dává řazení podle sloupce
  přes malou ikonku v záhlaví (jiný mechanismus než klasický „Vytvořit
  filtr", ale stejný výsledek).
- **Otevřené:** `Bodování!C` (post) čte `'Seznam hráčů'!$G` (sloupec „Z"),
  ne `$F` (sloupec „post") – vypadá to jako existující nesoulad v
  původním vzorci, nesouvisí s naším skriptem, zatím neopraveno.

**Skóre po třetinách (22. 9. 2026):** doplněny sloupce `Zápasy!CT:CW`
(`1.P`, `2.P`, `3.P`, `OT`) – přidáno na konec tabulky (za `CS`), aby se
neposunuly žádné stávající sloupce (uživatel to vybral místo umístění
hned za HG/AG, které by vyžadovalo přepsat písmena všech následujících
sloupců). Mřížka listu Zápasy měla limit přesně 97 sloupců (= `CS`), takže
bylo nejdřív potřeba rozšířit `gridProperties.columnCount` přes API, než
šlo do nových sloupců zapisovat. Data (`Game.period_scores`, nově i
`Game.ot_score`) se v PDF četla už od Kroku 2, jen se nezapisovala – parser
uměl skóre po třetinách odjakživa. Formát `home:away`, stejná konvence
jako `HG`/`AG` (ne LIT-relativní jako `AR:BA`). `OT` sloupec je zatím
ověřený jen synteticky (testy s uměle sestavenou tabulkou) – žádný z
referenčních zápasů do prodloužení nešel, chování na skutečném zápase
s `pp`/`sn` je potřeba potvrdit, až nastane.

**Skóre po třetinách promítnuto do listu Tým (22. 9. 2026, ruční úprava
mimo skript):** protože `Zápasy!CT:CW` je text (`"0:2"`), ne číslo, přidány
pomocné sloupce `Zápasy!CX:DE` (1.P/2.P/3.P/OT × LIT/soupeř, po řádcích
6–100 stejně jako existující `AN`/`AO` pattern), které z textu vytáhnou
číslo za LIT/soupeře podle toho, kdo byl `home` (`INDEX(SPLIT(CT6;":");
IF(B6="LIT";1;2))`). List **Tým** dostal novou sekci „Skóre po třetinách"
(A29:C34) se `SUM` přes tyto pomocné sloupce – součet přes všechny 4
třetiny odpovídá řádku „Góly" výše (6:7), ověřeno. Skript se sloupců
`CX:DE` ani sekce na Tým nedotýká, je to čistě vzorcová vrstva.

**Nový list Dashboard (22. 9. 2026, ruční úprava mimo skript):** první
verze přehledového listu pro trenérský štáb, zařazený jako první tab.
Čistě vzorcová vrstva (Python se dashboardu nedotýká, jen importuje data
do Zápasy/Sestavy jako dřív). Obsah:

- **Sezónní přehled** (A4:H5): odehráno, V/VP/PP/P (přes `COUNTIF` na
  `Zápasy!G` – bodová hodnota 3/2/1/0 už kóduje výsledek), body, pořadí
  v lize (`INDEX`+`COUNTA` na poslední vyplněnou hodnotu `Zápasy!I`),
  skóre – většina odkazuje na už existující souhrny v listu **Tým**.
- **Přesilovky/oslabení** a **Vyloučení a TM** (A8:F13): totéž, odkazy na Tým.
- **Skóre po zápasech** (graf, řádek 15+) a **Skóre po třetinách** (graf,
  řádek 32+, zdroj `Tým!A30:C34`).
- **Top 5 – Bodování** (A50:F55): `SORT`+`FILTER` nad `Bodování` podle bodů.
- **Brankáři** (A58:K62): buňka po buňce zkopírované vzorce z `Brankáři`
  (přímé „přelití" rozsahu `='Brankáři'!A1:K5` dávalo `#VALUE!` –
  nevysvětlené, ale rozepsání po jednotlivých buňkách funguje spolehlivě).
- **Podkladová data pro grafy** (`N5:Z100`, skryté sloupce): jeden řádek =
  jeden zápas (stejné řádkování jako `Zápasy`), zdroj pro grafy – datum,
  soupeř, LIT/soupeř góly (z `Zápasy!AN`/`AO`), body, PP, vyloučení, TM.

Otevřené (řešit při ladění): TOP 5 zatím řadí i hráče s 0 body (jen 2
zápasy odehrané, běžné vyrovnání se srovná s dalšími zápasy). Trend
přesilovek/vyloučení po zápasech zatím není jako graf, jen jako sezónní
součet – lze doplnit stejným vzorem jako „Skóre po zápasech", pokud bude
chtít.

**Oprava grafu „Skóre po zápasech" + nový graf „Pořadí v tabulce"
(22. 9. 2026):** graf po vytvoření nešel vidět, protože zdrojová data
(sloupce `N:Z`) jsou schválně skrytá a graf měl výchozí
`hiddenDimensionStrategy: SKIP_HIDDEN_ROWS_AND_COLUMNS` – při uložení
s touto strategií a plně skrytým zdrojem Sheets potichu zahodil i
`series`/druhou osu ze specifikace (ne jen graficky nezobrazil). Oprava:
`updateChartSpec` s `hiddenDimensionStrategy: SHOW_ALL` a znovu kompletní
`series`+`axis`. **Při přidávání dalšího grafu se skrytým zdrojem dat
vždy nastavit `SHOW_ALL` rovnou při vytváření, ne až dodatečně.**

Nový graf „Pořadí v tabulce" vedle „Skóre po zápasech": osa X = číslo
zápasu v sezóně (`Dashboard!AA`, `COUNTA` přes odehrané zápasy), osa Y =
`Zápasy!I` (pořadí po kole), rozsah osy 1–8. Osa Y NENÍ obrácená (1 dole,
8 nahoře je matematicky přirozené pořadí grafu) – Sheets API nemá pro
`BasicChartAxis` přímou možnost obrácení přes API; v UI editoru grafu jde
zaškrtnout „Obrátit pořadí osy", pokud bude chtít mít 1. místo nahoře.

## Potvrzená rozhodnutí (21. 9. 2026)

- Skript **pouze importuje** vstupní data, veškerá logika statistik zůstává ve vzorcích sešitu.
- **Evidence importů** zůstává v tabulce (skrytý list „Import log“).
- **Přístup ke Google API** (servisní účet nebo OAuth) se řeší jako první krok v IDE.
- Aktuální tabulka: Seznamy_v7.xlsx na Disku hc.lit.juniori@gmail.com, ID souboru `1qhdR3uh6rKKsUkF8Im3-P2xozPzLZYZ-`. Je to stále `.xlsx`, před zápisem přes Sheets API se musí převést na nativní Google Tabulku (krok 0.2). Složka „Zápisy“ je zpřístupněná, její ID se doplní do `.env` (`DRIVE_FOLDER_ID`).

Zásady:

- Skript zapisuje **jen vstupní buňky** (seznam v PROJECT.MD), vzorce v tabulce zůstávají.
- Nejdřív čistá logika s testy bez sítě (PDF → model → statistiky), potom napojení na Google.
- Referenční data: dva zápasy z tabulky (18. 9. LIT–Příbram 1:3, 20. 9. Chomutov–LIT 4:5). Import musí reprodukovat hodnoty v tabulce přesně.
- Nejasnost = zastavit import daného zápasu a vypsat důvod, nikdy hádat.

## Krok 0 – Příprava prostředí a přístupů ✅

Výstup: funkční kostra projektu a přístup k Disku/Tabulce.

1. Kostra projektu: `pyproject.toml`, balíček `src/statistic_table/`, `pytest`, `ruff`, `.venv`. Závislosti: `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `python-dotenv`, knihovna pro PDF (`pdfplumber`, případně `pymupdf`), `requests`/`beautifulsoup4` pro stránku ligy.
2. **Převod tabulky na nativní Google Tabulky.** Aktuální „Seznamy“ je `.xlsx` na Disku (soubor Seznamy_v6.xlsx), do kterého Sheets API zapisovat neumí. Otevřít v Google Tabulkách a uložit jako Google Tabulku (Soubor → Uložit jako Google Tabulky), ověřit, že vzorce (zejména ArrayFormula v kontrolách jmen a COUNTIFS v Brankáři) fungují. Zapsat ID nové tabulky.
3. **Přístup k Google API.** Doporučeno servisní účet (Google Cloud projekt, zapnout Drive API a Sheets API, vytvořit servisní účet, klíč JSON uložit mimo repozitář). Složku „Zápisy“ (čtení) a tabulku „Seznamy“ (úpravy) nasdílet e-mailu servisního účtu. Alternativa při zablokovaném vytváření klíčů v organizaci: OAuth pro desktopovou aplikaci s tokenem uloženým lokálně.
4. **Nový `.env.example`** místo stávajícího `gmail`/`password` (heslo API nepřijímá):
   ```
   GOOGLE_AUTH_MODE=service_account        # nebo oauth
   GOOGLE_SERVICE_ACCOUNT_FILE=./secrets/service_account.json
   DRIVE_FOLDER_ID=                        # složka „Zápisy“
   SPREADSHEET_ID=                         # tabulka „Seznamy“ (nativní Google Tabulka)
   TEAM_NAME_IN_PDF=HC Stadion Litoměřice
   TEAM_SHORT=LIT
   SEASON_START_YEAR=2026
   ```
   `secrets/` a `.env` do `.gitignore`.
5. Ověřit přístup malým skriptem: vypsat soubory ve složce Zápisy a přečíst buňku `Zápasy!A6`.

Hotovo: `python -m statistic_table.cli check` vypíše seznam PDF ve složce a hlavičku tabulky.

## Krok 1 – Datový kontrakt tabulky a konfigurace ✅

Výstup: `config.py` s mapou sloupců a kontrolou rozložení.

1. Mapa vstupních sloupců (Zápasy A:E, F, I, J:T, U:AM, AR:BA, BC:BN, BO:BZ, CJ:CO; Sestavy F:AB) jako konfigurace, ne natvrdo v kódu. Uživatel už jednou vložil sloupec (I „pořadí po kole“), takže se písmena mění.
2. Kontrola při startu: záhlaví na očekávaných pozicích (např. `Zápasy!I5 == "pořadí po kole"`, `Zápasy!J5 == "Branky"`, `Zápasy!U5 == "Přihrávky"`, `Zápasy!AR5 == "přesilovky LIT"`). Při neshodě import odmítnout s jasnou zprávou.
3. Přečíst číselník hráčů z listu Seznam hráčů (příjmení, jméno, č. registrace, číslo dresu, post) do datového modelu.
4. Kapacity: Branky J:T (11 slotů), Přihrávky U:AM (19 slotů, asistence se zapisují za sebou), vyloučení BC:BN (12 slotů), Sestavy H:N (7 obránců) a O:AB (14 útočníků). Přetečení kapacity = chyba importu se jménem zápasu.

Hotovo: test načte mapu, ověří záhlaví na živé tabulce (nebo na uložené kopii).

## Krok 2 – Datový model a parser PDF ✅

Výstup: `model.py`, `pdf_parser.py`, testy nad dvěma referenčními PDF.

1. Zjistit, zda mají PDF ČSLH textovou vrstvu (stačí `pdfplumber`), případně přidat fallback (OCR nebo vyčtení obrazu).
2. Datový model `Game`: číslo zápisu, datum, home, away, skóre po třetinách, konečné skóre, příznak prodloužení/nájezdů, soupisky obou týmů (číslo dresu, jméno, číslo registrace, post, příznak brankáře, příznak „přeškrtnut = nehrál“), branky (čas, tým, střelec S, asistenti A1/A2, HS), tresty (čas, tým, číslo dresu, minuty, důvod, případně číslo hráče, který trest odsedí).
3. Parser: hlavička, soupisky, branky, tresty. Přeškrtnutý brankář se pozná v PDF podle přeškrtnutí (grafika/čára přes řádek), nebo podle toho, že není uveden v záznamu o brankářích. Nejistotu neskrývat, ale hlásit.
4. Test: parsuje oba referenční PDF a výstup se porovná s uloženým očekávaným JSON (počty gólů, trestů, sestav).

Hotovo: `parse(pdf) -> Game` vrací pro oba zápisy kompletní data bez ručních zásahů.

## Krok 3 – Párování hráčů ✅

Výstup: `players.py`.

1. Hráč LIT z PDF → řádek v Seznamu hráčů: podle čísla registrace; když chybí (Kotman, Nádemlenjský), podle čísla dresu + příjmení. Shodná čísla dresu (Adelt/Hodek 15) se rozliší jménem.
2. Zápis příjmení do tabulky vždy ve tvaru z Seznamu hráčů včetně rozlišovačů: Novotný D / Novotný T, Walter F / Walter V.
3. Neznámý hráč nebo nejednoznačné párování: zastavit zápas, vypsat číslo dresu, jméno, číslo registrace, a navrhnout doplnění do Seznamu hráčů.
4. Určení týmu LIT v zápise podle názvu (`TEAM_NAME_IN_PDF`), zkratka soupeře (např. „HC Příbram“ → „Příbram“) přes tabulku aliasů v konfiguraci.

Hotovo: všichni hráči obou referenčních zápisů se spárují na stejná příjmení, jaká jsou v listu Sestavy.

## Krok 4 – Statistiky (přesilovky, góly, tresty, ročníky) ✅

Výstup: `stats.py` s čistými funkcemi a testy.

1. **Přesilovky**: z trestů obou týmů (2min menší tresty, dvojité menší tresty, vyrovnání stejným trestem se stejným časem začátku, 10min osobní a ostatní tresty přesilovku nedávají, trest odsedělý spoluhráčem se připisuje hráči, který ho dostal). Oslabení = přesilovky soupeře.
2. **Góly v přesilovce a v oslabení** z HS: 5/3 a 5/4 přesilovkový gól střelce, 4/5 a 3/5 gól v oslabení střelce; všechno v pohledu LIT : soupeř.
3. **Vyloučení a TM**: počet zapsaných trestů a součet minut za tým, po hráčích LIT (jména do BC:BN, minuty do BO:BZ ve stejném pořadí).
4. **Ročníky**: pro soupeře počty nastoupivších podle ročníku 2005–2010 (poslední čtyři číslice čísla registrace; bruslaři z listiny + brankář, který chytal). Ročník mimo rozsah 2005–2010 = varování a nutnost rozšířit tabulku.
5. **Body a pozn.**: `pp`/`sn` podle způsobu ukončení zápasu; body počítá vzorec v tabulce.
6. Regresní test proti referenčním datům z PROJECT.MD (přesilovky 6:7 / 6:8, góly v PP 1:0 / 1:2, góly v SH 0:1 / 0:0, vyloučení 9:7 / 9:7, TM 26:14 / 18:14, ročníky, věkové průměry 18,79:18,79 a 18,70:18,47).

Hotovo: testy `stats` zelené na obou zápasech, včetně ručně vytvořených okrajových případů (dvojitý trest, vyrovnané tresty, trest odsedělý spoluhráčem).

## Krok 5 – Zápis do Google Tabulky ✅

Výstup: `sheets.py`, `importer.py` (bez Drive zatím, vstup z lokálního PDF).

1. Najít řádek zápasu: shoda data + home + away, jinak první volný řádek od 6 (řádek se doplní i na listu Sestavy se stejným číslem řádku, oba listy musí zůstat zarovnané).
2. Zapsat vstupní rozsahy jedním `batchUpdate` (hodnoty, `USER_ENTERED`), vzorce nepřepisovat. Prázdné sloty v rozsahu vyplnit prázdnou hodnotou, aby při opětovném importu nezůstaly zbytky starého zápisu.
3. Po zápisu přečíst kontrolní sloupce: kontrola jmen (Zápasy AP, Sestavy AC), kontrola tresty (Zápasy CA), kontrola ročníky (Zápasy CQ), chyby `#` v oblasti. Výsledek zahrnout do výpisu.
4. Režim `--dry-run`: vypíše, co by se zapsalo (buňka → hodnota), nezapíše nic.
5. Test na kopii tabulky: import obou referenčních PDF do prázdné kopie musí dát totožný obsah jako je v ostrém listu.

Hotovo: import z lokálního PDF do testovací kopie tabulky vytvoří stejný stav jako ručně naplněná tabulka.

## Krok 6 – Napojení na Disk a detekce nových zápisů ✅

Výstup: `drive.py`, orchestrace v `importer.py`, `cli.py`.

1. Vypsat PDF ve složce „Zápisy“, stáhnout do paměti/dočasné složky.
2. **Evidence importovaných souborů** v samotné tabulce na skrytém listu „Import log“ (ID souboru na Disku, kontrolní součet, číslo zápisu, datum importu, výsledek). Důvod: stav přežije změnu počítače a je vidět uživateli. Nový záznam = soubor, jehož ID nebo kontrolní součet ještě v logu není.
3. Změněný soubor (jiný kontrolní součet, stejné číslo zápisu) = nabídnout přepis, standardně jen varování.
4. Duplicitní zápis (stejné číslo zápisu ve dvou souborech) = chyba.
5. Pořadí zpracování podle data zápasu, ne podle času nahrání.
6. Přehled na konci: importováno / přeskočeno / chyba, s důvody.

Hotovo: `python -m statistic_table.cli import` na složce s novým PDF zapíše zápas; druhé spuštění nic nezmění.

## Krok 7 – Pořadí po kole (volitelný modul) ✅

Výstup: `standings.py`.

1. Stáhnout tabulku Skupiny 1 ze stránky Ligy juniorů (https://ceskyhokej.cz/souteze-juniori/liga-junioru) a zjistit místo HC Stadion Litoměřice.
2. Zapsat do `Zápasy!I` v řádku posledního odehraného zápasu, ale jen pokud je kolo dokončené. Stránka neuchovává historii, proto se pořadí nemůže dopočítat zpětně bez zdroje výsledků všech zápasů kola. Zpětné doplnění zůstává ruční.
3. Kontrola věrohodnosti: součet bodů a skóre v tabulce musí odpovídat výsledkům a souhlasit s LIT v tabulce (dřívější čtení stránky nástrojem jednou vrátilo chybný výsledek, proto se výsledky ověřují aritmetikou tabulky).
4. Modul je samostatný a vypínatelný, při selhání se import zápisů neruší.

Hotovo: příkaz `standings` vypíše pořadí a navrhne zápis, zapíše po potvrzení.

## Krok 8 – Kvalita a provoz ✅ (bod 5 vědomě odloženo)

1. Testy: jednotkové (parser, párování, statistiky), integrační na kopii tabulky (může se přeskočit bez přístupů).
2. Logování do souboru a srozumitelné chybové zprávy v češtině (které pole, který zápas, co udělat).
3. Ochrana dat: zálohovat rozsah tabulky před zápisem (kopie listů Zápasy a Sestavy do souboru JSON v `backups/`, mimo git).
4. README s postupem spuštění, nastavením přístupů a řešením typických chyb (neznámý hráč, neshoda kontrol).
5. Volitelně: plánované spouštění (cron nebo plánovač na domácím serveru), notifikace o výsledku importu.

## Krok 9 – Přechod ⏳ (čeká se na další reálný zápas)

1. Paralelní provoz: první dva až tři zápasy importovat skriptem do kopie a porovnat s ručním výsledkem.
2. Přepnout ostrou tabulku na skript, ruční import a asistence v konverzaci ukončit.
3. Sezónní údržba: rozšíření ročníků, nový Seznam hráčů, nová tabulka pro další sezónu (`SEASON_START_YEAR`).

## Rizika a otevřené otázky

- **Formát PDF**: pokud se šablona zápisu ČSLH změní, parser přestane fungovat. Mitigace: testy na uložených PDF a jasné chyby místo tichých špatných hodnot.
- **Přeškrtnutý brankář**: nutno ověřit, jak se v PDF dá spolehlivě poznat (viz krok 2).
- **Google API kvóty a oprávnění**: servisní účet musí mít úpravy tabulky a čtení složky. Účet s daty (hc.lit.juniori@gmail.com) je jiný než účet uživatele, sdílení se musí nastavit z něj.
- **Ruční úpravy tabulky uživatelem**: mění rozložení sloupců (už se stalo). Řeší kontrola záhlaví při startu (krok 1).
- **Všechny výpočty v tabulce, nebo v Pythonu?** Tento plán ponechává statistiky ve vzorcích tabulky a přesouvá do Pythonu jen import a odvozené hodnoty ze zápisu. Případný přesun i agregací (Bodování, Brankáři, Tým) do Pythonu by šel udělat později jako samostatná fáze.
- **Střely** zůstávají mimo, dokud nebudou ve zdroji.
- **Chybějící čísla registrace** (Kotman, Nádemlenjský) a duplicitní číslo dresu 15 (Adelt/Hodek): doplnit v Seznamu hráčů.

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
`Zápasy!I` (pořadí po kole). **Osa Y NENÍ obrácená** (1 dole, 8 nahoře) –
dva pokusy o obrácení přes API se nepovedly:
1. `viewWindowOptions.viewWindowMin` > `viewWindowMax` (`min:8,max:1`) –
   API to přijme a uloží beze změny, ale při vykreslení se to nijak
   neprojeví (ověřeno vizuálně uživatelem, ne jen podle uložené hodnoty).
2. Vykreslit obrácenou pomocnou hodnotu (`9 - pořadí`) a přes
   `series.dataLabel.type=CUSTOM` + `customLabelData` zobrazit skutečné
   pořadí jako popisek bodu – `updateChartSpec` na tuhle kombinaci
   konzistentně (opakovaně) padá na `500 Internal error`. `dataLabel.
   type=DATA` (popisek = vykreslovaná hodnota, žádný jiný zdroj) funguje
   bez problémů.

Graf teď vykresluje skutečné pořadí přímo (bez obrácení), s popiskem
hodnoty u každého bodu (`dataLabel.type=DATA`). Obrácení osy jde jen přes
UI editor grafu (zaškrtávátko „Obrátit pořadí osy" v Přizpůsobit → Svislá
osa) – přes API se to spolehlivě udělat nepodařilo.

## Liga: statistiky všech týmů (22.–24. 9. 2026)

Nová větev vedle PDF importu LIT výše – statistiky **všech** týmů Ligy
juniorů, scrapované z ceskyhokej.cz do samostatné Google Tabulky
(`LEAGUE_SPREADSHEET_ID`, ne „Seznamy“). Princip a datový kontrakt jsou
zdokumentované v PROJECT.MD, sekce „Statistiky všech týmů ligy“ a „Co je
(záměrně) v Pythonu, co ve vzorcích“ – tady jen průběžný stav a co dál.

**Hotovo a ověřeno proti živým datům (16 týmů, 2 odehraná kola):**
- `league_scraper.py` – seznam zápasů (stránkování, číslo kola z nadpisu
  „N. kolo“) a detail zápasu (soupisky, góly s HS, tresty, skóre po
  třetinách, prodloužení) z `/game/detail/<id>`, bez JS/API.
- `league_model.py` + `league_stats.py` – přesilovky/oslabení (stejný
  algoritmus koincidenčních trestů jako `stats.py` pro LIT), výsledek/body
  za zápas z pohledu libovolného týmu (`Zápasy - liga (tým)`).
- `league_sheets.py` + `cli.py` (`league sync-games`, `league sync-teams`)
  – zápis syrových dat a přepočet pořadí po kole
  (`recompute_standings_history`: dopočet z vlastních výsledků + scrapnuté
  členství ve skupině, protože web historii tabulky nezveřejňuje).
- `scripts/build_league_team_template.py` – list „Tým – šablona“ (Sezónní
  přehled, Přesilovky/oslabení, Vyloučení a TM, 3 grafy, dole vedle sebe
  Odehrané zápasy/Bodování/Brankáři), klonovaný pro každý tým.
- `scripts/build_league_aggregate_sheets.py` (24. 9.) – `Bruslaři - liga` /
  `Brankáři - liga` jsou teď **vzorec** (`QUERY group by` nad syrovým
  logem `*-liga (zápasy)`), Python do nich už nezapisuje.
- Kontrola proti realitě: Kamil Drábek (Olomouc) 2Z/2G/3A/5B, LIT pořadí
  kolo 1→8. místo, kolo 2→4. místo (shoda s ručním scrapem stránky Ligy).

**Poznatky/pasti (Sheets API), užitečné při dalším ladění:**
- `addChart` s víc sériemi nespolehlivě zahazuje druhou a další sérii bez
  chybové hlášky – řešení: po vytvoření ověřit počet sérií, při neshodě
  graf smazat a založit znovu (`create_chart_robust`).
- `valueInputOption=USER_ENTERED` bere text začínající na `+-=@` jako
  vzorec (hlavička „+/-“ končila jako `#ERROR!`) – řešeno vodicím
  apostrofem (`league_sheets._protect`).
- `values().clear()` maže obsah, ne formát buněk – nový sloupec může
  zdědit starý formát (např. čas `mm:ss` u sloupce, co teď nese číslo).
- Zbytkový Google Sheets „Table“ objekt na listu tiše přebíjí vzorec
  vlastními hlavičkami „Sloupec N“ – nutné `deleteTable`, než jde na ten
  rozsah znovu psát vzorec.
- `QUERY` s `group by` nebo `headers:1` si vždy vygeneruje vlastní
  záhlavní řádek (nejde potlačit) – vzorec ať začíná rovnou na řádku
  záhlaví, ne vedle ručně psaného.

**Rozhodnuto s uživatelem (24. 9., revize architektury „skript importuje,
tabulka počítá“):**
1. ✅ Sezónní bodování/brankářské statistiky → vzorec (hotovo, viz výše).
2. Přesilovky/výsledek za zápas a pořadí po kole zůstávají v Pythonu
   (zdůvodnění viz PROJECT.MD – composite pravidla, těžko čitelná jako
   vzorec, testovaná v Pythonu).
3. ✅ **DB tabulka jako jediný zdroj pravdy – založena a naplněna (24. 9.):**
   nová samostatná Google Tabulka (`LEAGUE_DB_SPREADSHEET_ID`), do které
   teď `league sync-games` výhradně zapisuje (přepnuto z
   `LEAGUE_SPREADSHEET_ID`). Obsahuje identický tvar listů, jaký měla
   dřív tabulka Liga: `Zápasy - liga`, `Zápasy - liga (tým)`, `Góly - liga`,
   `Vyloučení - liga`, `Bruslaři/Brankáři - liga (zápasy)`, `Pořadí - liga`
   a nově **`Skupiny - liga`** (tým → skupina, `refresh_group_membership`
   ji obnovuje živým scrapem při každém `sync-games` – dřív se skupina
   scrapovala přímo uvnitř `recompute_standings_history`, teď je to
   samostatný uložený fakt). Ověřeno živě: 16 zápasů, 16 týmů ve
   2 skupinách, `Pořadí - liga` pro LIT sedí (kolo 1→8., kolo 2→4.).
4. **Tabulka Liga zamrzla** – `sync-teams`/`Tým – šablona`/sezónní vzorce
   tam zůstávají beze změny a dál čtou ze svých vlastních (už needitovaných)
   listů. Nahrazena Liga 2.0 (viz níže), plán zrušení/archivace zatím
   neurčen.
5. ✅ **Liga 2.0 založena a napojená na DB (25. 9.):** nová prezentační
   tabulka (`LEAGUE_V2_SPREADSHEET_ID`), uživatel ji založil v účtu
   `hc.lit.juniori@gmail.com` a nasdílel servisnímu účtu. Struktura:
   - `scripts/build_league_v2_mirrors.py` (nový skript) – pro každý syrový
     list z DB vytvoří v Liga 2.0 stejnojmenný list s jediným vzorcem
     `=IMPORTRANGE(DB_ID; "'list'!A1:sloupec5000")`. Listy mají záměrně
     **stejná jména** jako v DB, takže na ně `build_league_aggregate_
     sheets.py` a `build_league_team_template.py` odkazují beze změny –
     jen se přepnul jejich cíl z `LEAGUE_SPREADSHEET_ID` na
     `LEAGUE_V2_SPREADSHEET_ID`.
   - `IMPORTRANGE` vyžaduje jednorázové ruční potvrzení „Povolit přístup“
     v prohlížeči (nejde přes API) – uživatel potvrdil, mirror listy žijí.
   - `cmd_league_sync_teams` (cli.py) teď čte seznam týmů z DB
     (`require_league_db_spreadsheet_id`) a klonuje/plní šablonu v Liga 2.0
     (`require_league_v2_spreadsheet_id`) – rozdělené na dvě různé tabulky,
     dřív to byla jedna a tatáž.
   - `Bruslaři - liga`/`Brankáři - liga` (agregáty) i všech 16 týmových listů
     znovu postaveno a ověřeno v Liga 2.0 (Kamil Drábek 2Z/2G/3A/5B, LIT
     sezónní přehled 2 Z/1 V/1 P, bodování se sloupcem **Číslo**, grafy se
     správným počtem sérií).
   - Šablona (`Tým – šablona`) dostala v sekci Bodování nový sloupec
     „Číslo“ hned za „Hráč“ (`I50` vzorec rozšířen o `B` s labelem
     „Číslo“, `bold_ranges` posunuty na `I50:O50`) – jinak stejná struktura
     jako dřív, na přání uživatele.
6. ✅ **Drobné úpravy Liga 2.0 (25. 9.):**
   - Graf „Pořadí v tabulce“ – dvě kola oprav:
     1. Nejdřív graf vykresloval zápornou pomocnou hodnotu (sloupec `X`,
        kvůli pokusu o obrácenou osu Y) a `dataLabel.type=DATA` u bodu
        ukazoval tu zápornou hodnotu misto skutečného pořadí – matoucí
        spolu s názvem osy „Pořadí“. První oprava: graf čte přímo
        skutečnou (kladnou) hodnotu ze sloupce `W`, `X` smazán.
     2. Uživatel ale správně upozornil, že tohle vizuálně obrátí smysl –
        osa Y roste nahoru, takže horší pořadí (vyšší číslo) vychází nahoře
        a lepší dole, opačně než u tabulky pořadí. Finální oprava: `X`
        (záporné pořadí) vrácen zpět jako zdroj grafu (níže na ose = lepší
        pořadí, tedy výš), ale s vlastním formátem buňky **„0;0"** (druhá
        sekce formátu = záporná čísla, bez znaménka), takže popisek bodu
        i osa (obojí čte formát zdrojové buňky) zobrazují kladné skutečné
        číslo, i když je podkladová hodnota záporná. `CUSTOM` dataLabel s
        `customLabelData` (ukázat jinou buňku, než se vykresluje) byl znovu
        vyzkoušený i přes čerstvě vytvořený graf (ne přes `updateChartSpec`)
        a znovu spadl na `500 Internal error` – potvrzeno, že jde o obecné
        omezení API, ne jen chybu `updateChartSpec`.
     3. Uživatel dál chtěl, aby osa Y měla pevný rozsah 1 (nahoře) až 8
        (dole) na každém listu, ne automatické přizpůsobení odehraným
        kolům (na začátku sezóny je rozsah skutečných hodnot úzký, takže
        osa neukazovala celou tabulku). Přidán `viewWindowOptions` na
        `LEFT_AXIS`: `viewWindowMode: EXPLICIT`, `viewWindowMin: -8`,
        `viewWindowMax: -1` (hodnoty jsou záporné jako sloupec `X` výše,
        min/max jsou tedy prohozené oproti zobrazenému 1/8). Na rozdíl od
        dřívějšího pokusu obrátit směr osy (`min > max`, který se tiše
        neprojevil), tohle je běžný rostoucí rozsah s pevnými mezemi –
        funguje spolehlivě přes API, uloženo a ověřeno na živém listu.
        Předpoklad: skupina má 8 týmů (`Skupiny - liga`) – při jiném počtu
        týmů v soutěži je potřeba mez přepočítat.
     Aby se oprava dostala i do už naklonovaných 16 týmových listů, musely
     se smazat a znovu naklonovat (`league sync-teams`) – vlastní data
     v nich nejsou, jen vzorce/graf z šablony, takže je to bezztrátové.
   - `scripts/build_league_poradi_view.py` (nový skript) – na list
     `Pořadí - liga` v Liga 2.0 doplňuje čitelný přehled: pomocný sloupec
     `F` (skupina týmu přes `INDEX/MATCH` proti `Skupiny - liga`) a dvě
     `QUERY` tabulky vedle sebe (Skupina 1 ve sloupcích `H:J`, Skupina 2
     v `L:N`), obě řazené podle kola a pořadí. Nezasahuje do `A1:D5000`
     (vlastní `IMPORTRANGE`) ani do DB. **Past:** `QUERY` s `where sloupec
     <> ''` na číselném sloupci vrátí vždy 0 řádků (porovnání čísla s
     prázdným řetězcem selže potichu) – filtr na hodnotu skupiny (`F = 1`)
     stejně prázdné/nedoimportované řádky vyloučí sám, netřeba přidávat.

✅ **Liga 2.0 uzavřena (25. 9., odsouhlaseno uživatelem)** – IMPORTRANGE
mirror z DB, sezónní agregáty, šablona + 16 týmových listů, graf „Pořadí
v tabulce“ (směr osy i pevný rozsah 1–8) i přehled Skupina 1/2 na listu
„Pořadí - liga“ jsou hotové a vizuálně ověřené uživatelem přímo v tabulce.
Žádné další úpravy zatím nejsou naplánované.

**Probíhá: LIT Seznamy 2.0.** Živě načtena struktura produkční tabulky
„Seznamy“ přes API (ne jen z dokumentace) – 8 listů (`Dashboard`, `Zápasy`,
`Sestavy`, `Bodování`, `Brankáři`, `Tým`, `Seznam hráčů`, `Trenéři`, skrytý
`Import log`), ověřeny živé vzorce v odvozených listech (`INDEX/MATCH` proti
`Seznam hráčů`, `SUMPRODUCT`/`SUMIFS`/`COUNTIFS` proti `Zápasy`/`Sestavy`).

**Rozhodnuto s uživatelem (25. 9.):**
1. ✅ **PDF import pro LIT zůstává.** Web (`ceskyhokej.cz`) nemá registrační
   čísla hráčů (jen číslo dresu + jméno) – **ročníky soupeře** (`Zápasy!
   CJ:CO`, „celkem soupeř“, „věk Ø soupeř“) se dnes počítají výhradně
   z registrací v PDF a nejdou z webu zrekonstruovat. PDF je navíc pro tuhle
   část zralý, otestovaný pipeline s regresními fixtures – nahrazovat ho
   web-scrapem stejně jako u ligy by bylo čistě horší (ztráta dat), ne
   zjednodušení.
2. ✅ **PDF už dnes parsuje víc, než se zapisuje – využijeme to.**
   `model.Game.TeamSheet.goals/penalties` se parsují pro **oba** týmy
   (`_parse_team_block` volané na „Domácí tým (A)“ i „Hostující tým (B)“,
   včetně registračních čísel), ale do `Zápasy` se dnes zapisují jen
   střelci/asistence/vyloučení LIT – soupeřova strana se po naparsování
   zahazuje. Nová DB bude ukládat **oba týmy symetricky** (stejný vzor jako
   `Zápasy - liga (tým)`/`Góly - liga`/`Vyloučení - liga` u Ligy) – Python
   nezačíná scrapovat nic navíc, jen přestane zahazovat, co už umí
   naparsovat. Identita soupeřova hráče (jméno/registrace/číslo) je
   soběstačná v rámci jednoho PDF (`TeamSheet.roster` hostujícího týmu),
   nepotřebuje žádný externí číselník.
3. ✅ **Soupiska k zápasu se rozdělí na dva logy** (stejně jako
   `Bruslaři/Brankáři - liga (zápasy)` u Ligy), ne jeden `Sestavy` list
   s příznakem brankáře – umožní to postavit `Bodování`/`Brankáři` i
   ročníky jako `QUERY group by` formuli nad logem (registrace → rok
   narození vzorcem), místo dnešního INDEX/MATCH + SUMPRODUCT.
4. ✅ **Tvar 5 syrových tabulek DB** (Python zapisuje z PDF, žádné vzorce,
   žádné citlivé údaje – jen registrace jako identifikátor):
   - `Zápasy`: číslo zápisu, datum, home, away, skóre home/away, pozn.
     (pp/sn), 1.P/2.P/3.P/OT.
   - `Góly` (oba týmy): číslo zápisu, tým, třetina, čas, střelec,
     asistence 1/2, situace (HS).
   - `Vyloučení` (oba týmy): číslo zápisu, tým, třetina, čas, hráč, minuty,
     důvod, od, do (od/do navíc oproti Lize – PDF je má, použije se přímo,
     ne jen k dopočtu přesilovek jako dnes).
   - `Bruslaři (zápasy)` (oba týmy): číslo zápisu, tým, číslo, jméno,
     registrace, post, nastoupil, G, A, B, TM.
   - `Brankáři (zápasy)` (oba týmy): číslo zápisu, tým, číslo, jméno,
     registrace, chytal, obdržené góly, G, A, TM. **Upraveno při
     implementaci:** PDF nedává TOI ani počet zákroků (jen jméno brankáře,
     co chytal) – tyhle dva sloupce oproti Lize (web je má) chybí, stejně
     jako v dnešní produkční `Brankáři` (i tam TOI/zákroky nejsou).
5. ✅ **Architektura – tři tabulky vedle sebe, žádný „velký třesk“:**
   - **Seznamy DB** (nová) – Python zapisuje jen těch 5 syrových tabulek.
   - **Seznamy 2.0** (nová) – `IMPORTRANGE` zrcadlo syrových tabulek z DB
     (jako `build_league_v2_mirrors.py`) + `Bodování`/`Brankáři`/`Tým`/
     `Dashboard` jako formule nad nimi. Protože `Seznam hráčů`/`Trenéři`
     zůstávají zatím v produkční `Seznamy` (bod níž), Seznamy 2.0 je
     **dočasně** `IMPORTRANGE`uje odtud – až se později přesunou do
     soukromé netabulky, přepne se jen zdroj `IMPORTRANGE`, formule nad
     tím zůstanou stejné.
   - **Produkční `Seznamy`** zůstává beze změny a v provozu (trenér ji
     používá v sezóně), dokud Seznamy 2.0 není hotová a ověřená.
6. ✅ **`Seznam hráčů`/`Trenéři` přesunuty do soukromé tabulky (2. 10. 2026),
   dokončeno.** Obsahují citlivé osobní údaje (rodné číslo, pojišťovna,
   telefon, e-mail hráčů i rodičů; PIN a kontakty trenérů) – jiná kategorie
   dat než cokoli v Liga 2.0. Uživatel založil novou čistě soukromou
   tabulku (`SEZNAMY_PRIVATE_SPREADSHEET_ID`) a ručně (Sheets „Kopírovat
   do") do ní přesunul oba listy – API ani tenhle skript se k osobním
   údajům při přesunu vůbec nedostaly. Nasdílena servisnímu účtu jen jako
   **Prohlížeč** (na rozdíl od ostatních DB tabulek se do ní nikdy
   nezapisuje – `require_seznamy_private_spreadsheet_id` v `config.py`).
   `build_seznamy_v2_mirrors.py` přepojen, aby odtud (ne z produkční
   Seznamy) četl neosobní sloupce B:F pro Seznamy 2.0. `sheets.
   read_player_registry` dostal parametr `spreadsheet_id`, `cmd_check`
   ho teď volá s touto tabulkou.

   Listy `Seznam hráčů`/`Trenéři` pak byly z produkční Seznamy smazány
   (osobní údaje nemají být na dvou místech zároveň) – to ale rozbilo
   vzorce v **produkční** `Bodování`/`Brankáři` (INDEX/MATCH proti
   `'Seznam hráčů'!...`, které tam pořád existují jako historický záznam
   sezóny, i když se do nich od cutoveru nic nového nezapisuje). Oprava:
   nový `scripts/restore_production_seznam_hracu.py` znovu založí list
   `Seznam hráčů` v produkční tabulce, ale **ne** jako čistý IMPORTRANGE
   mirror – sloupce A:F a H:I (neosobní administrativní údaje) jsou
   `IMPORTRANGE` ze soukromé tabulky, sloupec `G` („Z“ = odehrané zápasy)
   a `P:S` (pomocné sloupce góly/asistence/body/klíč řazení pro řazení
   v Bodování) jsou **místní vzorce** počítané z produkční `Sestavy`/
   `Zápasy` – přesně stejné znění, jaké mělo původní smazané `Seznam
   hráčů` (dohledáno z formulí zachovaných i v soukromé kopii, kde ale
   po přesunu ukazují `#REF!`, protože tam `Sestavy`/`Zápasy` nejsou).
   Osobní sloupce (J+) se do produkční tabulky nevrací.

   **Past:** po obnovení listu stejného jména zůstaly `Bodování`/
   `Brankáři` chvíli ukazovat staré `#REF!`/„Nenalezeno“, i když zdrojová
   data už byla v pořádku a formule správně odkazovaly na obnovený list –
   Sheets evidentně cachuje výsledek array formulí napříč listy a
   znovuzaložení listu stejného jména ho samo nepřepočítá. Řešení: přepsat
   dotčené buňky přes API stejným textem vzorce (`values().update` s
   formulí přečtenou přes `valueRenderOption=FORMULA` a zapsanou beze
   změny) – to recalculaci "postrčí". Při podobném zásahu příště počítat
   s tímhle krokem navíc, ne jen s obnovením zdrojového listu.

✅ **Seznamy DB naplněná a ověřená (25. 9.):** uživatel založil `Seznamy DB`
(`19YrbX36JG3dpv-_Deqaf9TZlopw1cxAJKpZbjhSqGo8`) a `Seznamy 2.0`
(`1xUieynl0ubjMzyabPGwuleLuI2qwKsA8om_noShvc4M`) v účtu
`hc.lit.juniori@gmail.com`, nasdílel servisnímu účtu, ID v `.env`
(`SEZNAMY_DB_SPREADSHEET_ID`, `SEZNAMY_V2_SPREADSHEET_ID`; helpery
`require_seznamy_db_spreadsheet_id`/`require_seznamy_v2_spreadsheet_id`
v `config.py`).

**Rozhodnuto s uživatelem: zápis do DB je dual-write od teď** (ne oddělený
jednorázový běh) – `cli import` (jak `import_pdf`, tak `import_folder`) po
úspěšném zápisu do produkční `Seznamy` navíc (best-effort, nesmí shodit
produkční import) zapíše i do Seznamy DB přes nový modul
`seznamy_sheets.py`:
- `build_seznamy_rows(game, config)` – čistá funkce (bez sítě), rozloží
  `model.Game` na řádky pro 5 syrových listů, **symetricky pro oba týmy**.
  Na rozdíl od produkčního zápisu (jen LIT) nepotřebuje `club_roster`/
  `Seznam hráčů` vůbec – identita hráče (jméno, registrace) je soběstačná
  v rámci jednoho PDF (`TeamSheet.roster`), stejně u LIT jako u soupeře.
  Otestováno na obou referenčních zápasech (`tests/test_seznamy_sheets.py`,
  8 testů) – počty gólů/vyloučení/TM/bruslařů/brankářů přesně odpovídají
  PROJECT.MD.
- **Nová derivace `stats.third_and_relative_time`:** PDF má čas gólu/trestu
  jako průběžný čas zápasu (`"40:14"`), ne čas od začátku třetiny jako web
  Ligy – rozdělí ho na (třetina 1–4, čas od začátku třetiny). Chování ve
  4. „třetině“ (OT) je zatím neověřené na reálném zápase, stejně jako
  zbytek OT logiky v projektu.
- `append_game` má dedup podle čísla zápisu (bezpečné opakovaně volat
  `cli import` na stejné PDF, nevytvoří duplicity).
- **Past nalezená při backfillu:** `valueInputOption=USER_ENTERED` u
  sloupců „od“/„do“ (čas trestu jako text `"29:06"`) Sheets samo
  přeformátovalo na `"29:06:00"` (nesprávně si to vyložilo jako čas) –
  stejná třída chyby jako dřívější TOI/„0:00:00“ u Ligy. Řešení tentokrát
  jinačí: `seznamy_sheets.py` píše přes **`RAW`** input mode (ne
  `USER_ENTERED`) – DB listy stejně nikdy neobsahují vzorce, takže není
  potřeba ani apostrofový trik (`_protect`) proti `+-=@` na začátku textu,
  RAW navíc nechá čísla/časy přesně tak, jak jsou.
- Oba referenční zápasy (4002, 4012) zpětně dopočítané do DB přes
  `cli import <pdf>` (idempotentní i pro produkci – najde existující
  řádek, přepíše stejnými daty) – ověřeno živě: 2 zápasy, 8 gólů,
  32 vyloučení (16+16), 72 bruslařů, 8 brankářů, hodnoty sedí.

✅ **Seznamy 2.0 – mirror + Bodování/Brankáři hotové (25. 9.):**
- `scripts/build_seznamy_v2_mirrors.py` (nový skript) – zrcadlí 5 syrových
  listů ze Seznamy DB (stejná jména jako v DB). Navíc zrcadlí `Seznam
  hráčů` z **produkční** `Seznamy` (`SPREADSHEET_ID`), ale **jen neosobní
  sloupce B:F** (Příjmení, Jméno, č. reg., číslo, post) – od sloupce J má
  produkční `Seznam hráčů` citlivé osobní údaje (pojišťovna, rodné číslo,
  telefon, e-mail hráčů i rodičů), ty se do Seznamy 2.0 zapisovat nesmí
  (viz bod 6 výše). `Trenéři` se nezrcadlí vůbec – žádná formule ho
  nepotřebuje a je celý citlivý. Dvě samostatná ruční povolení IMPORTRANGE
  potřeba (DB → Seznamy 2.0, produkční Seznamy → Seznamy 2.0 – jiná
  dvojice tabulek, i když cíl je stejný).
- `scripts/build_seznamy_aggregate_sheets.py` (nový skript) – `Bodování`
  a `Brankáři` jako `QUERY group by` nad `Bruslaři/Brankáři (zápasy)`
  (`where tým = 'LIT'`), stejný vzor jako Liga. **Zjednodušeno oproti
  produkční tabulce** (rozhodnuto s uživatelem): jméno je jeden sloupec
  „Hráč“ přímo z logu (z PDF, např. „HLADÍK Šimon“), ne INDEX/MATCH do
  `Seznam hráčů` s rozpadem na Příjmení/Jméno; `Brankáři` zatím bez
  výher/pct výher/shutoutu (vyžaduje spojit log s výsledkem zápasu ze
  `Zápasy` – doplní se v dalším kroku). Ověřeno živě proti sezónním
  hodnotám z produkčního Dashboardu (Krátký 1Z/4G, Weber 1Z/3G, Hladík/
  Husák/Prokůpek 2Z/1G/1A/2B) – sedí přesně.

✅ **6. tabulka `Zápasy (tým)` doplněna do Seznamy DB (25. 9., odsouhlaseno
uživatelem):** chybějící dílek pro `Tým`/`Dashboard` – přesilovky/oslabení/
vyloučení/TM **za zápas** vyžadují composite pravidlo s časovým párováním
trestů (stejný důvod jako `Zápasy - liga (tým)` u Ligy, zůstává v Pythonu,
ne ve vzorci). `seznamy_sheets.py` teď počítá symetricky pro oba týmy přes
existující `stats.power_plays`/`goal_situation_counts`/`penalty_totals`
(stejné funkce, jaké `build_import` už používal jen pro LIT) –
`číslo zápisu, tým, soupeř, doma/venku, skóre tým, skóre soupeř, výsledek,
body, přesilovky, góly v přesilovce, oslabení, obdržené góly v oslabení,
góly v oslabení (vstřelené), vyloučení, trestné minuty`. Ročníky naopak
zůstávají jako plán na vzorec (registrace je v `Bruslaři/Brankáři
(zápasy)` pro oba týmy) – `Zápasy (tým)` je nemá, nejsou tam potřeba.
Zrcadleno do Seznamy 2.0 (`build_seznamy_v2_mirrors.py` rozšířen), oba
referenční zápasy zpětně dopočítané, hodnoty sedí přesně na PROJECT.MD
(LIT 4002: P/0 bodů/6 PP/1 PP gól/7 PK/0 obdržených v PK/0 SH gólů/9
vyloučení/26 TM; symetricky i pro Příbram/Chomutov).

✅ **List `Tým` postaven (25. 9.), rozsah odsouhlasený s uživatelem:**
„nejdřív připravit strukturu dat pro dashboard, dashboard sestavit ve
druhém kroku“ – `Tým` je ta datová vrstva, `scripts/build_seznamy_tym_
sheet.py` (nový skript):
- **Sezónní přehled + Přesilovky/oslabení + Vyloučení a TM** – `SUMIF`/
  `COUNTIF` nad `Zápasy (tým)` (LIT řádky vs. řádky ostatních týmů =
  "soupeř"). **Past:** `COUNTIF(range;"<>LIT")` počítá i prázdné buňky
  pod daty jako „různé od LIT" (997 místo 2 zápasů) – opraveno
  `COUNTIFS(range;"<>";range;"<>LIT")` (druhá podmínka = neprázdné).
  `SUMIF` se stejnou vadou netrpí (prázdné řádky přispívají nulou, součet
  vyjde správně i bez opravy).
- **Skóre po třetinách** – pomocné sloupce `F:M` (skryté) přes
  `REGEXEXTRACT` rozparsují text `"h:a"` ze `Zápasy!H:K` (1.P/2.P/3.P/OT)
  na LIT/soupeř podle toho, kdo byl domácí (`REGEXEXTRACT` zvoleno místo
  `SPLIT`+`INDEX` z produkční tabulky – vektorizuje se čistě pod
  `ARRAYFORMULA`, `SPLIT` ne).
- **Bez sekce Ročníky** (vědomě odloženo) – vyžaduje dopočítat rok
  narození z registrace v `Bruslaři/Brankáři (zápasy)` a zprůměrovat počty
  hráčů na zápas podle ročníku, řeší se v dalším kroku.
- Ověřeno živě proti produkční tabulce Tým – sedí přesně (Odehráno 2/2,
  Góly 6/7, PP 12/15, PP góly 2/2, využití PP 16,67%/13,33%, PK 15/12,
  obdržené v PK 2/2, úspěšnost PK 86,67%/83,33%, SH góly 0/1, vyloučení
  18/14, TM 44/28, TM/zápas 22/14, skóre po třetinách 2:4/1:1/3:2/0:0).

✅ **List `Dashboard` postaven (25. 9.):** `scripts/build_seznamy_dashboard.py`
(nový skript) – přehled pro trenérský štáb, čistě nad už hotovými listy
(`Tým`, `Zápasy (tým)`, `Zápasy`, `Bodování`, `Brankáři`), Python nikdy
nezapisuje syrová data, jen vzorce:
- **Sezónní přehled / Přesilovky-oslabení / Vyloučení a TM** – přímé
  odkazy na `Tým` (V/VP/PP/P dopočítané `COUNTIFS` nad `Zápasy (tým)`,
  protože `Tým` sám nemá rozpad podle výsledku, jen body/skóre).
  **Vědomě chybí „Pořadí v lize“** – to zapisuje samostatný příkaz
  `standings` přímo do produkční tabulky, Seznamy DB tuhle hodnotu zatím
  nemá (rozšíření `standings` na zápis do DB je samostatný krok).
- **Skóre po zápasech** (graf) – skrytý datový blok `N:P` spojuje
  `Zápasy (tým)` (LIT řádky přes `FILTER`) s `Zápasy` (datum přes
  `VLOOKUP`). Skryté sloupce → graf musí mít `hiddenDimensionStrategy:
  SHOW_ALL` rovnou při vytváření, jinak by API tiše zahodilo `series`
  (stejná past jako u League Dashboardu, viz výše).
- **Skóre po třetinách** (graf) – zdroj přímo `Tým!A19:C23`, žádná
  duplikace dat na Dashboardu (na rozdíl od produkční tabulky, kde je
  kopie v `N:Z`).
- **Top 5 – Bodování** – `QUERY` nad `Bodování` (Hráč/Z/G/A/B, `limit 5`).
- **Brankáři** – `QUERY … select *` nad celým listem `Brankáři` (přímá
  kopie rozsahu `='Brankáři'!A1:...` dávala v produkční tabulce `#VALUE!`
  z nevysvětlených důvodů – `QUERY select *` je spolehlivá náhrada).
- Ověřeno živě proti produkční tabulce – sedí přesně (Odehráno 2, V/VP/
  PP/P = 1/0/0/1, Body 3, skóre 6:7, PP 12/16,67%, PK 15/86,67%, Vyloučení
  18/14, TM 44/28/22,0/14,0; oba grafy 2/2 sérií na první pokus).

**Další krok:** doplnit Ročníky do `Tým`, výhry/shutout do `Brankáři` a
rozšířit `standings` o zápis „Pořadí v lize“ do Seznamy DB (pak doplnit
i do Dashboardu).

Osud staré tabulky Liga (`LEAGUE_SPREADSHEET_ID`) po přechodu na Liga 2.0
zatím neřešen (smazat / nechat ladem / archivovat) – rozhodnout až bude
Liga 2.0 nějakou dobu v provozu ověřená uživatelem.

✅ **Cutover `cli import` na Seznamy DB (26. 9. 2026, odsouhlaseno uživatelem
– „přepnout hned, mezery doladit potom“):** architektura LIT je teď stejná
jako Liga – `cli import` (`import_pdf` i `import_folder`) zapisuje **jen**
do Seznamy DB, přímý zápis do produkční tabulky Seznamy (buňka po buňce,
se jménem hráče přes Seznam hráčů) skončil. Souběžně s cutoverem doplněny
dva nové soupeři do `TEAM_ALIASES` (HC Olomouc → Olomouc, HK MD Šumperk →
Šumperk) a naimportovány první dva ostré zápasy po cutoveru (4018 Olomouc–LIT
6:1, 4026 Šumperk–LIT 10:2) – ověřeno živě proti Seznamy DB (žádné duplicity,
kontrolní součty vyloučení/TM sedí, shodná sestava LIT v obou zápasech
nezávisle ověřená přímo ze dvou různých PDF, jde o dvoudenní turnaj).

Co se změnilo v kódu:
- `importer.build_import`/`ImportPlan`/`print_plan` (mapování na starou
  produkční tabulku) zůstávají netknuté a otestované (`test_importer.py`) jako
  referenční/legacy kód – jen se přestaly volat z `import_pdf`/`import_folder`.
  Ty teď nepotřebují `club_roster` vůbec (identita hráče je soběstačná
  v PDF, stejně jako zbytek DB zápisu).
- `import_pdf`/`import_folder` vrací/pracují přímo s `Game`, ne s `ImportPlan`
  – žádný „řádek“ v produkční tabulce už neexistuje, `--dry-run` u
  jednotlivého PDF teď ukazuje skutečné řádky přes `seznamy_sheets.
  build_seznamy_rows` místo starého `print_plan`.
- **Import log (evidence zpracovaných souborů z Drive) se přestěhoval do
  Seznamy DB** (nový skrytý list tam, ne v produkční tabulce) – `sheets.
  write_batch`/`ensure_import_log_sheet`/`read_import_log`/`append_import_log`/
  `read_range` teď berou `spreadsheet_id` jako parametr místo natvrdo
  `config.spreadsheet_id` (used i `standings.write_position`, který dál píše
  do produkce – to je jediné zbylé místo). Protože je to nový list, první
  běh po cutoveru označil všechny 4 dosavadní zápasy jako „nové“ (log byl
  prázdný) – neškodné, protože `seznamy_sheets.append_game` má vlastní dedup
  podle čísla zápisu (ověřeno: žádné duplicitní řádky v DB), jen se do
  nového logu zapsaly hned při prvním běhu.
- **`cmd_standings` přepnutý na čtení bilance ze Seznamy DB** (sloupce
  `Zápasy!B:G`, stejný tvar jako dřív produkční `A:F`) – jinak by cross-check
  proti produkční tabulce po cutoveru začal padat na každém dalším zápase
  (produkce už nové zápasy nedostává).

✅ **Zápis „Pořadí v lize“ přepnutý na Seznamy DB (26. 9. 2026) – poslední
otevřený bod z cutoveru uzavřen.** `standings` (`cmd_standings`) teď píše
pozici přímo do Seznamy DB, ne do produkční tabulky:
- `SEZNAMY_ZAPASY_HEADER` rozšířen o 12. sloupec `L` „pořadí po kole“
  (`SEZNAMY_PORADI_PO_KOLE_COLUMN`) – na rozdíl od zbytku řádku (zapisuje
  `cli import`) ho vyplňuje až `cli standings` dodatečně, po dohrání kola.
  Živý list měl hlavičku jen do `K` (OT), doplněno jednorázovým ručním
  zápisem `L1` (`ensure_seznamy_sheets` retroaktivně needituje hlavičku
  existujícího listu, řeší jen nově vznikající listy – záměrně, ať běžný
  import nedělá kvůli tomu 6 zbytečných extra API čtení na každý zápas).
- `seznamy_sheets.last_game_row`/`write_poradi` (append-only list Zápasy,
  poslední řádek = poslední naimportovaný = poslední odehraný zápas).
  `standings.last_played_row`/`write_position` (produkční varianta) smazány
  beze zbytku – všechny nové zápasy jdou od cutoveru jen do DB, takže
  produkční verze už neměla žádné realistické použití.
- **Kolize v Seznamy 2.0:** rozšíření IMPORTRANGE spillu `Zápasy` z `A:K` na
  `A:L` narazilo na starý vzorec „Góly“ ve sloupci `L` (leftover z dřívějšího
  běhu `build_seznamy_v2_mirrors.py`, viz níže) – spill do už obsazené buňky
  skončil na `#REF!` („array result was not expanded because it would
  overwrite data“). `build_seznamy_v2_mirrors.py` teď před zápisem nové
  formule vždy vyčistí starou pozici (`Zápasy!L1:L101`), sloupce „Góly“/
  „Asistence“ posunuty na `M:N`. Ověřeno živě: mirror i Dashboard („Pořadí
  v lize“ = 6, `INDEX+COUNTA` nad `Zápasy!L`) sedí přesně na hodnotu
  zapsanou `cli standings`.

## Ladění po prvním ostrém provozu (26. 9. – 3. 10. 2026)

Cutover byl hotový, ale první skutečné použití po pár dnech v provozu
odhalilo několik věcí, které žádný test nezachytí (síťová volání, živá
data z webu, ruční obsluha menu):

- **Web import se dva týdny vůbec nezapisoval.** `cli league sync-games`
  se přes `main.py` spouští tak, že se nejdřív zeptá na dry-run a pak na
  „Pokračovat k zápisu?“ s **výchozí odpovědí Ne** – stačí prázdný Enter
  a zápis se tiše neprovede, i když dry-run proběhl v pořádku a vypadá to,
  že import proběhl. Liga DB tak zůstala 2 kola pozadu (16 zápasů místo
  31), než se to odhalilo kontrolou stavu tabulky. Menu samo neupravováno
  (UX riziko zůstává, pro vědomí při příštím ladění).
- **Oprava parsování skóre s nájezdy:** zápas s textem skóre `"1:2SN"`
  (nájezdy) spadl na `AttributeError` – starší regex počítal jen s 0–1
  písmenem přípony (`"S"`/`"N"` zvlášť byl jen odhad, bez živého příkladu
  v datech). Skutečná přípona má obě písmena dohromady. Opraveno
  (`[A-Z]{0,2}`, `ENDING_SUFFIXES = {"P": "pp", "SN": "sn"}`), regresní test
  s uloženým fixture HTML. Důležité: chyba u jednoho zápasu **nezastavila**
  zbytek dávky (14 z 15 nových zápasů se zapsalo i tak) – potvrdilo to
  smysl dřívější opravy izolace chyb na zápas v `cmd_league_sync_games`.
- **Bug v mirror skriptech přepsal reálný list:** `build_league_v2_mirrors.py`
  i `build_seznamy_v2_mirrors.py` měly logiku „přejmenuj první list
  v tabulce, pokud chybí náš mirror“ – platilo jen při úplně prvním běhu
  na prázdné tabulce. Při doplňování chybějícího mirroru do už rozjeté
  Liga 2.0 to omylem přejmenovalo a přepsalo buňku A1 reálného týmového
  listu „Valašský hokejový klub“. Napraveno ručně (list přejmenován zpět,
  A1 obnoveno na „Tým:“, nový mirror list založen čistě) a opraveno v kódu
  (podmínka vyžaduje `len(sheets) == 1`, ne jen „náš list chybí“).
- **Graf „Pořadí po kole“ doplněn do Seznamy 2.0 Dashboardu** – produkční
  Dashboard ho měl, do `build_seznamy_dashboard.py` se ale nikdy nedostal.
  Stejný vzor jako Liga 2.0 (záporná hodnota + formát buňky „0;0“ pro
  obrácenou osu). Zatím řídký (jeden bod po posledním zápase), protože
  `cli standings` doplňuje pořadí jen k poslednímu řádku, ne zpětně.
- **Zápasy v Liga 2.0 ve špatném pořadí:** dvě `QUERY` formule v
  `build_league_team_template.py` (zdroj grafu „Skóre po zápasech“ i
  tabulka „Odehrané zápasy“ pod ním) neměly `order by D` – řádky
  v `Zápasy - liga (tým)` jsou v pořadí, v jakém je scraper zapsal (podle
  kola a pořadí na webové stránce), ne chronologicky. Graf proto spojoval
  body napřeskáčku. Opraveno (`order by D`) ve skriptu i naživo ve všech
  16 už existujících týmových listech (ne jen v šabloně pro budoucí
  klony). **Pozn.:** `QUERY` řadí datum jako text – funguje jen díky
  dvoumístnému zápisu dne na webu, nepotvrzeno pro jednociferné dny
  (říjnové zápasy teprve ukážou, jestli je to problém).
- **Data na webu se mohou dodatečně opravit – naše DB to nezachytí.**
  Zápas #181018 (Valašský–IHC Královo Písek) jsme naimportovali jako
  rozhodnutý v prodloužení (`"7:2P"` nebo podobně), web si ale výsledek
  později opravil na čisté `"7:2"` (bez prodloužení). Naše `Pořadí - liga`
  (vlastní přepočet z uložených výsledků) tak počítalo s jiným bodovým
  ziskem, než je teď oficiálně platný – LIT kvůli tomu vycházelo 8. místo
  místo správného 7. (ověřeno proti živé oficiální stránce, kterou čte
  `cli standings` pro Seznamy DB – ta měla správně). Oprava: smazat
  všechny řádky daného zápasu napříč syrovými listy a znovu zasynchronizovat
  (`league sync-games` ho pak stáhne čerstvě). **Dedup `league sync-games`
  (podle přítomnosti `game_id` v `Zápasy - liga`) nerozpozná, že se
  už-synchronizovaný zápas na webu později změnil** – žádný mechanismus na
  to zatím neupozorní, jde jen o ruční nápravu po nahlášení nesrovnalosti.
  Otevřené riziko do budoucna, neřešeno systémově.
- **Stejný druh chyby podruhé – zápas #180736 (LIT–Hvězda Praha, 3. 10.):**
  web u detailu tohoto zápasu ukazoval skóre po třetinách `5:0, 1:3, 0:1`
  (to už samo dává přesně konečné skóre 6:4) a navíc ještě přilepený
  segment „- 0:0“ (prodloužení) a příponu „P“ – vnitřně rozporné (zápas byl
  jasně rozhodnutý v řádné hrací době, žádné prodloužení dávalo smysl).
  Potvrzeno proti dvěma nezávislým zdrojům (PDF zápisu i oficiální
  přehledové stránce ligy, kterou čte `cli standings` – obě correctly
  ukazovaly V/3 body, ne VP/2). Narozdíl od #181018 tentokrát web
  nesrovnalost sám neopravil (ověřeno opakovaně), takže oprava proběhla
  rovnou: `parse_game_detail` výstup přepsaný přes `dataclasses.replace`
  (`ending=None, ot_score=None`), staré řádky smazány napříč syrovými listy
  a zápas zapsán znovu přes `league_sheets.append_game` (ne ruční patch
  jednotlivých buněk – zajistí, že i odvozené hodnoty jako „výsledek týmu“
  u brankářů v logu zůstanou konzistentní). Pořadí po přepočtu sedí na
  oficiální stránku (6. místo).
- **Nový typ trestu v PDF – „TS“ (trestné střílení):** `_parse_team_block`
  dřív dělalo `int(row[min_col])` bez ošetření – trestné střílení nemá
  počet minut (ani časový interval Od/Do, PDF tam píše „---“), takže
  sloupec „Min.“ obsahuje text „TS“ místo čísla a import spadl na
  `ValueError`. Potvrzeno s uživatelem (ne odhad): `PENALTY_MINUTES_CODES =
  {"TS": 0}` v `pdf_parser.py`, neznámý kód jinak pořád zastaví import
  s chybou (nehádat). Zároveň `_normalize_dash` převádí „---“ v Od/Do na
  prázdný řetězec, ne na doslovné pomlčky v DB.
- Při obou nálezech potvrzeno i doplnění `TEAM_ALIASES` o nového soupeře
  (HC Hvězda Praha → Hvězda) – rutinní krok při každém novém soupeři,
  stejně jako u Olomouce/Šumperku dřív.

✅ **„Pořadí po kole" sjednoceno na jeden zdroj pravdy (3. 10. 2026).**
Uživatel si všiml, že graf v Seznamy 2.0 ukazoval jen poslední 2 kola,
zatímco Liga 2.0 měl kompletní historii – zkoumání odhalilo, že to
**nebyl jeden zdroj dat, jak se předpokládalo**, ale dva nezávislé
mechanismy:
- Seznamy DB: `cli standings` scrapoval **aktuální** pozici z oficiální
  stránky a zapisoval ji jen do **posledního** řádku – stránka historii
  nezveřejňuje, takže starší kola zůstávala navždy prázdná.
- Liga DB: `league sync-games` → `recompute_standings_history` po každém
  novém zápase **přepočítá kompletní historii** (všechna kola, všechny
  týmy) ze surových výsledků + členství ve skupině – a LIT je v tom jen
  jeden z 16 týmů, takže historie pro LIT tam **už existovala správně**.

Rozhodnuto s uživatelem: přepojit vše, co dává smysl, na tenhle jediný
úplný zdroj (Liga DB), Seznamy DB nechat jen pro data, která Liga DB
nemá (registrační čísla, Od/Do u trestů – PDF je pořád jediný zdroj pro
vlastní zápasová data LIT, to se neruší, viz bod 1 výše z 25. 9.). Pro
pořadí po kole to šlo udělat, protože obě DB sdílí stejné „číslo
utkání"/„číslo zápisu".

Implementace:
- `seznamy_sheets.sync_poradi_from_liga(config, seznamy_db_id,
  league_db_id)` – pro každý zápas LIT v Seznamy DB najde podle čísla
  utkání odpovídající řádek v Liga DB `Zápasy - liga` (sloupec „kolo"),
  pak podle kola dohledá pozici LIT v `Pořadí - liga`, a zapíše ji do
  `Zápasy!L` – pro **všechny** řádky najednou (backfill), ne jen poslední.
  Nahrazuje `last_game_row`/`write_poradi` (smazány, byly to jediní
  volající).
- `cmd_league_sync_games` volá `sync_poradi_from_liga` automaticky po
  každém přepočtu Liga pořadí (jen když byly nové zápasy, best-effort –
  chybí-li `SEZNAMY_DB_SPREADSHEET_ID`, krok se přeskočí, nesmí shodit
  Liga sync). Seznamy DB tak zůstává v synchronu s Liga DB bez ručního
  kroku navíc.
- `cmd_standings` zjednodušen na čistě diagnostický příkaz – porovná
  oficiální stránku s vlastním záznamem (`arithmetic_issues`/
  `cross_check_issues`), nic už nezapisuje. `--dry-run`/`-y` přepínače
  odstraněny (byly jen pro zápis). `main.py` menu upraveno (bez
  dry-run/potvrzovací otázky, přejmenováno na „Zkontrolovat pořadí LIT
  proti oficiální stránce").
- Zpětně doplněno pro všech 5 dosavadních zápasů LIT (8, 4, 6, 7, 6) –
  ověřeno živě, Seznamy 2.0 Dashboard teď ukazuje kompletní historii
  shodnou s Liga 2.0.

✅ **Oprava „vychytaných výher“ u brankářů v Seznamy 2.0 (3. 10. 2026).**
Uživatel si všiml, že Krátký měl v listu `Brankáři` nesmyslně vysoký počet
výher. Příčina: `Brankáři (zápasy)` má pro každý zápas řádek pro **oba**
brankáře v soupisce (i náhradníka, co vůbec nechytal – `seznamy_sheets.
build_seznamy_rows` zapisuje sloupec „chytal“ 0/1, ale pořád vytvoří
řádek), zatímco vzorec „vychytaná výhra“ v `build_seznamy_v2_mirrors.py`
kontroloval jen výsledek týmu v daném zápase (`K{row}="V"/"VP"`), ne
jestli ten konkrétní brankář opravdu chytal. Výsledek: oba brankáři (ten,
co hrál, i náhradník na lavičce) dostali kredit za každou výhru týmu –
Krátký i Weber tak měli dvojnásobek skutečných výher (2 místo 1 u obou,
celkem 4 místo skutečných 2 výher LIT v sezóně). Oprava: podmínka
rozšířena o `F{row}=1` (sloupec „chytal“) – `AND(F{row}=1;OR(K{row}="V";
K{row}="VP"))`. Ověřeno živě: Weber 1/3 (33,3 %), Krátký 1/2 (50 %),
součet přesně odpovídá 2 skutečným výhrám LIT v sezóně.

✅ **List `Last 5` v Seznamy 2.0 (3. 10. 2026).** Nový list s aktuální
formou týmu – stejné tabulkové sekce a rozložení jako Dashboard (sezónní
přehled, přesilovky/oslabení, vyloučení a TM, pod tím Bodování a Brankáři
vedle sebe), ale spočítané jen z **posledních 5 odehraných zápasů LIT**,
ne z celé sezóny. Odsouhlaseno s uživatelem: bez grafů.

`scripts/build_seznamy_last5_sheet.py`:
- `Zápasy (tým)` nemá sloupec s datem (viz `SEZNAMY_ZAPASY_TYM_HEADER`) –
  „posledních 5“ se vybírá podle sloupce A („číslo zápisu“), ne podle
  data. Čísla zápisů přiděluje svaz postupně podle termínu utkání, takže
  `order by A desc limit 5` dá stejné pořadí jako chronologicky – a `QUERY`
  sloupec se samými čísly automaticky vyhodnotí jako číselný typ, takže na
  rozdíl od řazení data jako textu (past u Liga 2.0, viz výš) tu nehrozí
  problém s různým počtem znaků mezi měsíci. Posledních 5 čísel zápisů je
  skrytý pomocný sloupec `N2:N6`.
- Všechny součty filtrují `Zápasy (tým)` přes `SUMPRODUCT` s `COUNTIF`
  proti `N2:N6` jako „je toto číslo zápisu mezi posledními pěti“ – `SUMIF`/
  `COUNTIFS` neumí podmínku „je v seznamu hodnot“, jen jednu rovnost.
- **Dvě pasti nalezené při psaní (obě opravené před commitem):**
  1. `QUERY({ZT}!A2:A5000;"select A where B = 'LIT'...")` dávalo `#VALUE!`
     – rozsah předaný do `QUERY` obsahoval jen sloupec A (co se vybírá),
     ale filtrovalo se podle sloupce B, který v tom rozsahu vůbec nebyl.
     Oprava: rozsah `A2:B5000` (oba sloupce).
  2. Uvnitř `QUERY` jazyka je textový literál v **jednoduchých** uvozovkách
     (`'LIT'`), ne v dvojitých – ty uzavírají celý query string. `LIT_CRIT`
     (`'"LIT"'`, pro přímé `SUMIF`/`SUMPRODUCT` podmínky mimo `QUERY`) se
     sem nehodí, byl by to vnořený řetězec se třemi páry uvozovek místo
     jednoho stringu.
- Ověřeno živě: protože LIT má zatím odehraných přesně 5 zápasů, „Last 5“
  teď sedí do posledního čísla na sezónní součty v listu `Tým` (Odehráno 5,
  V2/P3, body 6, skóre 15:27, přesilovky 29/13,79 %, oslabení 36/80,56 %,
  vyloučení 42:34, TM 90:76/18,0:15,2) – až se odehraje 6. zápas, začnou se
  rozcházet, jak se očekává.

✅ **Doplněno Bodování/Brankáři do `Last 5` (3. 10. 2026).** Pod týmové
souhrny přibyly hráčské statistiky za posledních 5 zápasů, vedle sebe
stejně jako na Dashboardu (Bodování vlevo bez sloupce Post/TM – stejná
redukce jako Dashboard vlastní embed, Brankáři vpravo kompletní vč. „%
výher“). Nečtou ze sezónních agregátů `Bodování`/`Brankáři` (ty nejdou
dodatečně omezit na 5 zápasů) – počítají znovu přímo z `Bruslaři/Brankáři
(zápasy)` stejným `QUERY group by` vzorem, jen s navíc podmínkou na
posledních 5 čísel zápisu. `QUERY` ale neumí "hodnota je v rozsahu N2:N6"
přímo, proto se podmínka sestavuje jako **dynamický řetězec** zřetězením
`"(A='"&N2&"' or A='"&N3&"' or ... or A='"&N6&"')"` přímo ve vzorci (stejný
princip jako `'" & $B$1 & "'` u Liga 2.0 team template, jen s pěti
proměnnými místo jedné). Ověřeno živě proti sezónním hodnotám (5
odehraných = celá dosavadní sezóna): Bodování i Brankáři (Weber 1/3 =
33,33 %, Krátký 1/2 = 50,00 %) sedí přesně.

✅ **Chybějící alias soupeře při PDF importu (5. 10. 2026).** Import
zápisu 06 (4. 10. 2026, LIT–Kolín 4:3) spadl na chybu „Soupeř 'SC Retia
Kolín' nemá v `TEAM_ALIASES` zkratku pro tabulku Zápasy“ – `TEAM_ALIASES`
je záměrně bez automatického odvození (různé kluby mají různé předpony,
viz komentář u slovníku), nový soupeř tedy vždy znamená novou ruční
položku. Doplněno `"SC Retia Kolín": "Kolín"`. Ověřeno živě: `cli import
--dry-run` i ostrý běh teď zápis 06 zapíší bez chyby, řádek v Seznamy DB
`Zápasy` (4044, 4.10.2026, LIT–Kolín 4:3) sedí.

✅ **„Seznamy 2.0“ přejmenována na „HC LIT jun 2026/27“ (5. 10. 2026).**
Uživatel přejmenoval prezentační tabulku (`SEZNAMY_V2_SPREADSHEET_ID`) v
Google Tabulkách – jen titulek souboru, ID i obsah beze změny, žádný
zásah do kódu nebo `.env` potřeba (tabulka se v kódu adresuje jen přes
ID, ne přes název). PROJECT.MD/README.md/`.env.example` aktualizované na
nový název (PLAN.MD jako chronologický log si historické zápisy pod
starým názvem „Seznamy 2.0“ záměrně ponechává beze změny). **Aktuální
seznam tabulek, které se používají v provozu:**
- **„HC LIT jun 2026/27“** (`SEZNAMY_V2_SPREADSHEET_ID`) – prezentační
  tabulka pro LIT, sleduje trenérský štáb.
- **„Liga 2.0“** (`LEAGUE_V2_SPREADSHEET_ID`) – prezentační tabulka pro
  celou ligu.
- **„Seznam hráčů“** (`SEZNAMY_PRIVATE_SPREADSHEET_ID`) – soukromá
  tabulka s osobními údaji hráčů/trenérů, edituje se ručně.

Zbylé tabulky (Seznamy DB, Liga DB, produkční „Seznamy“) zůstávají jen
jako datová/historická vrstva, nikdo je běžně neotevírá (viz rozhodnutí
2. 10. 2026 výše).

✅ **Pořadí po kole se po PDF importu nezapsalo (5. 10. 2026).** Uživatel
nahlásil, že zápis 06 (LIT–Kolín) se v „HC LIT jun 2026/27“ objevil bez
pořadí po kole. Příčina: `cmd_league_sync_games` volal
`sync_poradi_from_liga` jen v bloku `if new_games and not args.dry_run`
– tedy jen když web sync najde NOVÉ odehrané zápasy. Zápas Kolín se do
Seznamy DB dostal přes `cli import` (PDF), ne přes web, **po** tom, co
web sync kola 6 už doběhl – další běh `league sync-games` proto nenašel
žádný nový zápas (`new_games` prázdné) a backfill se vůbec nespustil,
i když Liga DB `Pořadí - liga` už pro kolo 6 hodnotu pro LIT měla.
Oprava: `sync_poradi_from_liga` se teď spouští při **každém** běhu
`league sync-games` (jen ne při `--dry-run`), nezávisle na `new_games` –
je to idempotentní úplný backfill přes všechny řádky Seznamy DB, takže
nijak nevadí, že se spustí i „zbytečně“. `refresh_group_membership`/
`recompute_standings_history` zůstávají gatované na `new_games` (nemá
smysl je přepočítávat, když se nic nezměnilo). Ověřeno živě: po opravě
`cli league sync-games` (0 nových zápasů) přesto napsal „Pořadí LIT
promítnuto do Seznamy DB (6 zápasů)“ a řádek 4044 má teď `L`=4, stejně
v mirroru „HC LIT jun 2026/27“.

✅ **Dashboard v „HC LIT jun 2026/27“ sjednocený s formátem Liga 2.0
(5. 10. 2026).** Uživatel chtěl pod týmové statistiky doplnit
zjednodušený seznam odehraných zápasů a posunout Bodování/Brankáři
doprava, ať je rozložení stejné jako u Liga 2.0 team template
(`build_league_team_template.py`, sekce ODEHRANÉ ZÁPASY/BODOVÁNÍ/
BRANKÁŘI vedle sebe). `build_seznamy_dashboard.py` upraven:
- **ODEHRANÉ ZÁPASY** (A:G, nově) – Datum, Soupeř, D/V, Skóre LIT, Skóre
  soupeř, Výsledek, Body. `Zápasy (tým)` nemá sloupec s datem (viz
  PROJECT.MD), takže Datum dohledává `ARRAYFORMULA(VLOOKUP(...))` do
  `Zápasy` podle čísla zápisu ze skrytého raw helperu ve sloupcích
  `AA:AG` (`QUERY` nad `Zápasy (tým)`, `order by A` = chronologicky,
  stejný princip jako u Liga). Zbylé sloupce jsou prostá kopie
  odpovídajícího sloupce helperu – jednoduché kritérium ve `VLOOKUP`
  (ne zřetězený klíč jako u `MATCH` v `build_seznamy_v2_mirrors.py`) je
  přes pole ověřeně spolehlivé, stejný vzor jako existující `N5` výš.
- **BODOVÁNÍ** přesunuto z `A49` na `I49` (I:M), **BRANKÁŘI** z `I49` na
  `T49` (T:Y) – formule beze změny, jen nové umístění.
- List měl jen výchozích 26 sloupců (A:Z), skrytý helper `AA:AG` je
  mimo tenhle rozsah – skript teď na začátku nastaví `gridProperties.
  columnCount` na 35, než začne zapisovat (past nalezená live: API
  vrátilo 400 „Range (Dashboard!AA51) exceeds grid limits“).
Ověřeno živě: `ODEHRANÉ ZÁPASY` sedí na známé výsledky (18. 9. LIT–
Příbram 1:3 P, 20. 9. Chomutov–LIT 5:4 V pro LIT, … 4. 10. LIT–Kolín
4:3 V), `BRANKÁŘI` ukazuje Krátký 2/3 = 66,67 % (vychytal i nově
přidaný zápas Kolín) – grafy (Skóre po zápasech/Pořadí po kole/Skóre po
třetinách) po přesunu beze změny, všechny 3 série ověřené skriptem OK.

✅ **„Bodový zisk“ doplněn do Liga 2.0, Dashboardu a Last 5 (5. 10. 2026).**
Nová buňka `=F5/(A5*3)` (zisk bodů jako podíl z maximálně možných, 3 za
zápas), zobrazená jako procento:
- **Liga 2.0 team template** – `H4`/`H5`, header „Bodový zisk“.
  `league sync-teams` klonuje šablonu jen pro nové týmy, existující
  listy nepřepisuje (stejná past jako u dřívějšího „order by D“ fixu) –
  proto krom úpravy `build_league_team_template.py` (a jeho přeběhnutí,
  což přepsalo i samotnou šablonu) proběhl i jednorázový patch přímo na
  všech 16 už existujících listů týmů (transientní skript, nebyl
  commitnutý do repa – stejný přístup jako u „order by D“).
- **„HC LIT jun 2026/27“, Dashboard** – `I5` (ne `H5`, to už zabírá
  „Pořadí v lize“), header „Bodový zisk“ v `I4`.
- **„HC LIT jun 2026/27“, Last 5** – `H5` (tady je `H` volné, žádné
  „Pořadí v lize“), přes stejné okno posledních 5 zápasů jako zbytek
  listu.

Ověřeno živě: LIT na Liga 2.0 (9 bodů / 18 = 50,00 %) sedí přesně na
Dashboard `I5` (taky 50,00 %, stejná sezóna, nezávislý výpočet nad
Seznamy daty) – dobrá vzájemná kontrola. Last 5 `H5` = 60,00 % (9/15,
5 zápasů v okně). Příbram na Liga 2.0 8/18 = 44,44 % pro orientaci.

✅ **Formulář „Přidat hráče“ pro soukromou tabulku Seznam hráčů
(9. 10. 2026).** Uživatel chtěl do listu „Seznam hráčů" přidat formulář
pro zápis nových hráčů, který je automaticky zařadí abecedně podle
příjmení a seznam prodlouží. **Nejde o Python skript téhle repozitáře**
– servisní účet má k soukromé tabulce (`SEZNAMY_PRIVATE_SPREADSHEET_ID`)
záměrně jen roli Prohlížeč (viz 2. 10. 2026 výše), takže přes API do ní
nejde zapisovat vůbec, ani založit Apps Script projekt. Řešení je
`scripts/apps_script/seznam_hracu_pridat_hrace.gs` – kód pro Google Apps
Script, který musí trenér (majitel/editor tabulky) sám vložit do
Rozšíření → Apps Script přímo v té tabulce (návod je v hlavičce
souboru). Po instalaci přidá do tabulky menu „Seznam hráčů“ → „Přidat
hráče…“ s formulářem (HTML dialog, žádný druhý Google Form) pro
všechna pole listu (jméno/příjmení/registrace/dres/post/status/
poznámka + citlivé údaje – pojišťovna/rodné číslo/telefon/e-mail
hráče i rodiče).
- Nový řádek se vkládá `insertRowBefore` na správné místo (ne přepis
  celého rozsahu) – ostatní řádky a jejich vzorce se jen posunou, nic
  se nepřepisuje.
- Pořadí určuje `localeCompare(..., "cs", {sensitivity:"base"})` nad
  „příjmení jméno“ (tedy s rozlišením diakritiky a tie-breakem podle
  jména při shodném příjmení, např. „Novotný D“/„Novotný T“ – tahle
  dvě existující jména mají ruční rozlišovač přímo v textu příjmení
  ze staré konvence trenéra, nový formulář na to konvenci nevyžaduje,
  tie-break řeší automaticky přes jméno).
- Sloupec A (pořadové číslo) se při každém přidání přepíše na vzorec
  `=ROW()-2&"."` pro všechny řádky (idempotentní) – u existujících
  řádků to byl pevný text, který by se při vložení uprostřed seznamu
  neposunul správně; jako vzorec se přepočítá sám i při budoucích
  vloženích/mazáních, bez nutnosti cokoli ve skriptu dál řešit.
- Sloupce G a P–S (`Z`, góly/asistence/body/klíč řazení (pom.)) jsou
  u existujících řádků nefunkční `#REF!` vzorce (odkazují na listy
  Sestavy/Zápasy, co tahle soukromá tabulka vůbec neobsahuje – zděděné
  z produkční Seznamy při přesunu listu 2. 10. 2026) – nový řádek je
  nechává prázdné, ne další zkopírovaný `#REF!`. Sloupec T (ročník
  (pom.)) funguje (počítá jen z vlastního `D`), takže se pro nový
  řádek dopočítá stejným vzorcem jako u ostatních.
Ověřeno: syntaxe přes `node --check`, logika vkládání (abecední pořadí
vč. diakritiky a tie-breaku) samostatným testem nad reálným seznamem
39 příjmení (Beránek Petr správně za Beránek Jakub, Žák až na konec,
Aaa až na začátek). **Živé spuštění v Google Sheets UI (otevření
formuláře, skutečný zápis) jsem neověřil** – nejde to samo o sobě
spustit bez Apps Script editoru a lidské autorizace, trenér by si měl
po instalaci vyzkoušet přidání jednoho zkušebního hráče.

Živé ladění (9. 10. 2026): po vložení kódu se menu „Seznam hráčů“
neobjevilo ani po manuálním spuštění `onOpen` v Apps Script editoru
(proběhlo bez chyby) – důvod je, že změna menu z editoru se nepromítne
do už otevřené záložky s tabulkou samo, je potřeba záložku s tabulkou
samostatně znovu načíst (F5). Po reloadu menu funguje. **Mazání hráčů**:
uživatel potvrdil, že stačí nativní Sheets (pravý klik na řádek →
Odstranit řádek), žádný další formulář/skript k tomu nepřibude – díky
`fixRowNumbers()` (vzorec `=ROW()-2&"."` ve sloupci A) se pořadová
čísla po smazání řádku sama přepočítají správně, ostatní vzorce (T –
ročník) se váží jen na vlastní řádek, takže smazání jednoho řádku nic
jiného nerozbije.

✅ **Import zápisu 07 spadl na dvou chybách (10. 10. 2026).** Uživatel
nahlásil, že poslední import neproběhl správně:
1. **`OSError` dřív, než se PDF vůbec začalo parsovat.** Soubor na Disku
   se jmenuje `07 - 9.10.2026 - Havl. Brod 4::5P` – název souboru je
   libovolný text, který zadá ten, kdo PDF nahrává, a `importer.
   import_folder` ho dřív použil přímo jako jméno LOKÁLNÍHO temp souboru
   (`Path(tmp_dir) / f["name"]`). `::` je na Windows neplatná sekvence
   ve jméně souboru → `OSError: [Errno 22] Invalid argument`, import
   spadl úplně, ani se nedostal k parsování obsahu. Oprava: lokální
   jméno je teď Drive ID souboru (vždy bezpečné, jen alfanumerické znaky
   a `-`/`_`), ne `f["name"]` – ten se dál používá jen ve výpisech pro
   uživatele. Obecná oprava, ne jen pro `::` – chrání proti libovolnému
   znaku nepřípustnému v cestě k souboru, který by někdo do názvu na
   Disku zadal (uvozovky, `|`, `?`, `*`...).
2. **`cli import --dry-run` u celé složky hlásil "imported" u souboru,
   který ostrý běh vzápětí odmítl** (`TEAM_ALIASES` nemá zkratku pro
   „BK Havlíčkův Brod“, stejná past jako u „SC Retia Kolín“ 5. 10. 2026
   – nový soupeř = nová ruční položka, bez automatického odvození).
   Příčina: `import_folder`'s dry-run větev jen simulovala zápis bez
   reálného volání `append_game` (a tedy bez `build_seznamy_rows`, kde
   `TEAM_ALIASES` lookup žije) – stejná validace, co run-mode hlásila
   přes chybu, se v dry-run větvi vůbec neprováděla, takže dry-run mohl
   lhát o tom, co by se skutečně stalo. Oprava: dry-run teď taky volá
   `build_seznamy_rows` (čistá funkce, beze zápisu) a report "error"
   místo "imported", pokud by zápis skutečně skončil chybou – dry-run
   jako skutečná nápoveda, ne jen echo vstupu. Doplněn alias
   `"BK Havlíčkův Brod": "H.BR"` (uživatel upřesnil zkratku dodatečně –
   původně jsem doplnil plné `"Havlíčkův Brod"` podle vzoru „Příbram“/
   „Chomutov“, ale u dvouslovného názvu klubu dala přednost krátké
   zkratce jako u ostatních sloupců tabulky Zápasy, ne úplnému názvu).
   Zápas 07 byl v tu dobu už naimportovaný se starým aliasem – oprava
   proto přepsala i živá data: 29 buněk přes 6 listů Seznamy DB
   (`Zápasy` C8, `Zápasy (tým)` B14/C15, `Góly` B51:B54, `Vyloučení`
   B89:B93, `Bruslaři (zápasy)` B216:B230, `Brankáři (zápasy)` B26:B27)
   – ne nový import, přímý přepis přes `sheets.write_batch` (stejná
   celá sada buněk, jen hodnota se mění, žádná jiná data se nedotkla).
Ověřeno živě: `cli import --dry-run` i ostrý běh teď zápis 07 zapíší bez
chyby, řádek v Seznamy DB `Zápasy` (4050, 9.10.2026, H.BR–LIT 4:5pp,
periody 0:3/2:1/2:0, OT 0:1) sedí na výsledek z PDF (LIT vyhrálo v
prodloužení venku) a žádná z dřívějších 29 buněk se starým plným
názvem už v DB ani v mirroru „HC LIT jun 2026/27“ nezůstala.

✅ **Interaktivní doplnění chybějícího TEAM_ALIASES při importu PDF
(11. 10. 2026).** Doteď každý nový soupeř (Kolín, H.BR, Tábor – viz
výš) znamenal tvrdý pád importu a ruční zásah do `config.py` od
vývojáře. Uživatel chtěl další stupeň ochrany: import se nemá zastavit
chybou, ale nabídnout doplnění dvojice přímo.
- **`players.MissingTeamAliasError`** – nová podtřída `TeamIdentificationError`
  (jen pro chybějící alias, ne pro hlubší problém s identifikací zápasu
  jako špatně nastavené `TEAM_NAME_IN_PDF`), nese `opponent_name`.
- **`config.add_team_alias(name, alias)`** – zapíše dvojici do nového
  `src/statistic_table/team_aliases_extra.json` (prázdný `{}` při
  prvním běhu, v gitu, ne `.gitignore`) a rovnou ji doplní do běžícího
  `TEAM_ALIASES`, ať pokračuje i aktuální import bez restartu. `config.
  TEAM_ALIASES` se při startu merguje s obsahem tohohle souboru
  (`_load_extra_team_aliases`) – hardcoded dvojice v `config.py` zůstávají
  jediný zdroj pravdy pro běžný vývoj/review, extra soubor je jen pro
  runtime doplnění z terminálu.
- **`importer.call_with_alias_prompt(fn, *args, **kwargs)`** – zavolá
  `fn`; při `MissingTeamAliasError` (a jen interaktivně, `sys.stdin.
  isatty()`) nabídne `input()` na zkratku, při zadání doplní alias a
  zkusí `fn` znovu; jinak (neinteraktivně, nebo prázdná odpověď) chybu
  propustí jako dřív. Použito na všech 3 místech, kde se volá `append_
  game`/`build_seznamy_rows`: `import_pdf`, obě větve `import_folder`
  (dry-run i ostrý zápis) a `cli.cmd_import`'s dry-run větev pro jeden
  konkrétní PDF.
- **Past nalezená živě**: `sys.stdin.isatty()` v týhle shellové
  obálce (Bash tool) vrátilo `True`, i když žádný skutečný terminál
  nebyl k dispozici – `input()` pak spadlo na `EOFError`, ne na
  očekávané zadání. Oprava: `EOFError`/`KeyboardInterrupt` kolem
  `input()` se chovají jako prázdná odpověď (přeskočit), ne jako pád –
  `isatty()` je tedy jen první, ne jediná pojistka.
Ověřeno: 11 nových testů (`test_config.py` – persistence/merge/validace
prázdného vstupu, `test_players.py` – `MissingTeamAliasError.
opponent_name`, `test_importer.py` – neinteraktivní re-raise, úspěšný
retry po zadání aliasu, prázdná odpověď re-raise, `EOFError` re-raise),
138 passed. Živě na reálném novém soupeři: PDF 08 (11. 10. 2026,
LIT–Tábor 1:4) spadl na chybějící alias pro „HC Tábor“ přesně podle
očekávání (bez pádu, čistý `[error]` výpis), doplněno `"HC Tábor":
"Tábor"` (rovnou do `config.py`, ne do extra JSON – ten zůstává
vyhrazený pro budoucí skutečné interaktivní použití z terminálu, ne
pro mé vlastní úpravy), zápas 4059 (LIT–Tábor 1:4, periody
0:0/1:1/0:3) se pak zapsal bez chyby.

✅ **Web ceskyhokej.cz přidal sloupce do tabulky hráčů, scraper pevné
pozici sloupců spadl na všech 6 zápasech kola 8 (11. 10. 2026).** Při
ověřování výše (`league sync-games` po importu zápasu LIT–Tábor) selhaly
VŠECHNY nové zápasy kola 8 (ne jen LIT) na `ValueError: invalid literal
for int() with base 10: '00:00'`. Příčina: web mezi tabulku hráčů
(ne brankářů – ta je beze změny) vložil nové sloupce `TOI`/`PP TOI`/
`SH TOI` hned za `HRÁČ` a `S`/`BL`/`BULY` na konec (8 → 14 sloupců
celkem) – `_parse_skater_row` četla sloupec „góly“ podle pevné pozice
`cells[3]`, což je teď `TOI` (čas na ledě, vždy `"00:00"`), ne góly.
Ověřeno živě, že nové sloupce nikdy nenesou reálná data (`TOI`/`PP TOI`/
`SH TOI` = `"00:00"` u všech hráčů, `S`/`BL` = `"0"`, `BULY` = prázdné) –
jen kosmetická změna šablony webu, žádná ztráta informace.

Oprava: `_parse_skater_row`/`_parse_goalie_row` čtou sloupce podle
**názvu** z `<thead th>` (`_header_index`), ne podle pevné pozice –
robustní i proti dalším podobným změnám webu v budoucnu (chybějící
sloupec teď dá jasnou `ValueError` s názvem a dostupnými sloupci, ne
tiché čtení špatné hodnoty). Goalie tabulka se touhle změnou chránit
nemusela (sloupce beze změny), ale přepsána stejně pro konzistenci.
Nová fixtura `tests/fixtures/league/game_detail_180758.html` (reálná
stránka se širší tabulkou) + test, co ověřuje nejen „neshodí výjimku“,
ale že součet gólů hráčů sedí na skutečné skóre zápasu (7:5).
Ověřeno živě: `parse_game_detail` nad zápasem #180758 teď vrátí správné
hodnoty (suma gólů hráčů 7:5 = skóre zápasu), `league sync-games` doběhl
bez chyby a kolo 8 (6 zápasů) se zapsalo do Liga DB.

✅ **List „Tabulka“ v Liga 2.0 – tabulky obou skupin vedle sebe
(12. 10. 2026).** Uživatel chtěl klasickou tabulku (Pořadí, Tým, Z, V,
VP, PP, P, Skóre, Body) pro obě skupiny vedle sebe, počítanou z dat
Liga DB, správnost kontrolovat ručně proti `STANDINGS_URL`.
`scripts/build_league_tabulka_sheet.py`:
- **Stage 1** (skrytý, `U:AD`) – jedna `QUERY ... group by` dá Tým/Z/
  GF/GA/Body za všech 16 týmů najednou; `ARRAYFORMULA`+`COUNTIFS` (pole
  týmů jako kritérium, stejný vzor jako Výhry/Shutouty brankářů v
  `build_league_aggregate_sheets.py`) doplní V/VP/PP/P; skupina z
  `Skupiny - liga` přes `VLOOKUP`.
- **Stage 2** (skrytý, `AF:AN`/`AP:AX`) – druhá `QUERY` nad stage 1,
  filtr na skupinu + `order by Body desc, (GF-GA) desc, GF desc` –
  stejné pravidlo jako `league_sheets.recompute_standings_history`
  (Python, pro `Pořadí - liga`), ale počítané **nezávisle** vlastním
  vzorcem nad týmiž syrovými daty, ne čtením `Pořadí - liga` – druhý,
  nezávislý výpočet pro porovnání s webem.
- **Viditelné tabulky** (`A:I`/`K:S`) – jen odkaz na stage 2 po
  sloupcích (`ARRAYFORMULA` s hlídáním prázdna), stejný princip jako
  „Odehrané zápasy“ v `build_seznamy_dashboard.py`. Pořadí je prostě
  pořadí řádku v už seřazeném stage 2, ne vzorec s `RANK`.

**Dvě pasti nalezené živě při stavbě:**
1. `QUERY` s agregací (`sum`/`count`/`group by`) vždy vypíše vlastní
   syntetický hlavičkový řádek (popisky typu „sum F“) bez ohledu na
   parametr `headers` – ten řeší jen kolik řádků VSTUPU se přeskočí, ne
   jestli VÝSTUP má hlavičku. S `headers=0` se navíc nepřeskočí ani
   skutečná hlavička vstupního listu („tým“ v `Zápasy - liga (tým)!B1`),
   takže vznikl fantomový 17. „tým“ s názvem „tým“. Oprava: `headers=1`
   (přeskočí vstupní hlavičku) + počítat s tím, že výstup má vlastní
   hlavičkový řádek navíc (data o řádek níž, stejný vzor jako
   `build_league_aggregate_sheets.py`).
2. **`INDEX(rozsah;MATCH(pole;...))` pod `ARRAYFORMULA` nebroadcastuje
   správně** – vrátí jednu hodnotu (zjevně první/poslední match) pro
   všechny řádky pole, ne výsledek pro každý řádek zvlášť. Objeveno při
   debugu, proč sloupec „skupina“ vycházel „2“ pro úplně všechny týmy
   (i skupinu 1). **Při kontrole se ukázalo, že stejnou chybu má už
   hotový `build_league_poradi_view.py`** (5. 10. 2026) – SKUPINA 1 na
   listu `Pořadí - liga` byla od začátku prázdná a SKUPINA 2 ukazovala
   obě skupiny zamíchané, nikdo si toho nevšiml, protože čísla pořadí
   samotná (Python, `recompute_standings_history`) byla pořád správná,
   jen tahle vedlejší view-vrstva rozdělení na skupiny byla rozbitá.
   Oprava na obou místech: `VLOOKUP` místo `INDEX`/`MATCH` (stejný vzor
   jako Dashboard/Last 5 „Datum“, ověřeně spolehlivý pod `ARRAYFORMULA`
   s polem).
Ověřeno živě: oba sloupce „Tabulka“ (SKUPINA 1 i SKUPINA 2) sedí přesně,
řádek po řádku, na živě stažená data z `STANDINGS_URL` (pořadí, Z, V,
VP, PP, P, skóre, body – všech 16 týmů). Oprava `build_league_poradi_
view.py` ověřena stejně (SKUPINA 1/2 teď správně rozdělené, dřív SKUPINA
1 prázdná).

## Pre-scout příštího soupeře (od 20. 10. 2026, probíhá)

Uživatel nakopíroval do `src/ready_to_move/` hotový kód z jiného projektu
(`hockey_analyzer`) – konzolová aplikace, co z **czechicehockey.tv**
(Live Arena Sports, NE ceskyhokej.cz) stáhne poslední odehraný zápas
zadaného soupeře a vystřihne MP4 klipy (góly vstřelené/obdržené,
přesilovky vlastní/soupeřovy) z oficiálních událostí zápasu (žádná AI
analýza obrazu). Cíl: nové menu „pre-scout“ v `main.py` – zadá se název
příštího soupeře, zobrazí se jeho karta z Liga 2.0 na listu „Příští
soupeř“ v „HC LIT jun 2026/27“ a (později) se MP4 klipy nahrají na Disk
do `Pre-scout/<tým>/`. **Řízená, postupná implementace** – každý krok
zvlášť, ověřený živě, než se jde dál.

✅ **Krok 1 – kód přesunutý do balíčku (20. 10. 2026).**
`src/ready_to_move/{cihtv,event_clips,pre_scout_lt}.py` →
`src/statistic_table/prescout/` – relativní importy, `WEB_LOGIN`/
`WEB_PASSWD` čtené přes `Config`/`require_web_credentials` (ne vlastní
`load_dotenv()` v modulu). Logika (přihlášení, hledání zápasu, plánování
klipů podle offsetů eventů, střih ffmpeg) beze změny. `drive.py` dostal
`find_or_create_folder`/`upload_file` (připraveno na krok s Diskem).
`src/ready_to_move/` smazáno (nahrazeno).

❌→✅ **Past: servisní účet nemá úložiště na Disku.** Živý test nahrání
souboru do sdílené složky „Pre-scout“ (`PRE_SCOUT_DRIVE_FOLDER_ID`,
nasdílená Editor servisnímu účtu) spadl na `403 storageQuotaExceeded`:
„Service Accounts do not have storage quota. Leverage shared drives,
or use OAuth delegation instead.“ Založení SLOŽKY (metadata, 0 bajtů)
proběhlo bez problému – jen vlastní OBSAH souboru (MP4) servisní účet
nemůže vlastnit na běžném (ne Workspace) Google účtu. Shared Drive
vyžaduje Workspace předplatné (hc.lit.juniori@gmail.com je běžný Gmail),
OAuth delegace vyžaduje Workspace admin. **Rozhodnuto s uživatelem:
nahrávání na Disk se odkládá** – klipy se zatím ukládají jen lokálně.
`SCOPES` vrácen zpět na `drive.readonly` (`find_or_create_folder`/
`upload_file` zůstávají v kódu připravené, nepoužité).

✅ **Krok 2 – list „Příští soupeř“ v „HC LIT jun 2026/27“ (20. 10. 2026).**
`scripts/build_seznamy_next_opponent_sheet.py` – `IMPORTRANGE` celého
listu soupeře z Liga 2.0, druhý argument sestavený jako dynamický
řetězec (`"'" & B1 & "'!A1:X120"`) podle názvu týmu v `B1` (tu buňku
bude přepisovat menu „pre-scout“ v dalším kroku). `IMPORTRANGE` kopíruje
jen vypočítané HODNOTY, ne grafy (vlastní objekty) – 3 grafy z karty
týmu (Skóre po zápasech/po třetinách, Pořadí v tabulce) se proto
nezobrazí, jen číselné přehledy (Sezónní přehled, Přesilovky/oslabení,
Vyloučení a TM, Odehrané zápasy, Bodování, Brankáři). Vědomý kompromis
oproti `copyTo` (ten by grafy zachoval, ale QUERY/SUMIF vzorce uvnitř by
ukazovaly `#REF!` – odkazují na listy, co v „HC LIT jun 2026/27“
neexistují).
- **Past #1 (stejná jako jinde v projektu):** IMPORTRANGE mezi
  spreadsheety vyžaduje jednorázové ruční „Povolit přístup“ v
  **desktopovém prohlížeči** (ne mobilní appka) – do té doby vrací
  `#REF! "Please use a desktop web browser to connect this sheet."`,
  což `IFERROR` nezachytí (tenhle typ chyby proleze skrz).
- **Past #2 (vlastní, při testování):** testovací vzorec zapsaný omylem
  doprostřed spill rozsahu hlavního vzorce (`A20`, uvnitř `A3:X122`)
  způsobil `#REF! "Array result was not expanded because it would
  overwrite data in A20."` – smazání testovací buňky to opravilo.
- IMPORTRANGE nekopíruje FORMÁT buňky, jen hodnotu – datum (sériové
  číslo, např. „46283,81“) a „Bodový zisk“ (syrový podíl „0,54…“) bez
  vlastního formátu v cílové tabulce byly nečitelné. Opraveno vlastním
  `numberFormat` (`DATE`/`PERCENT`) na odpovídajících buňkách/sloupci v
  „Příští soupeř“ (řádky posunuté o +2 oproti šabloně týmu, protože
  import začíná na řádku 3, ne 1).
Ověřeno živě: `B1` = „HC Příbram“ → „Příští soupeř“ ukazuje přesně
tatáž data, co dřív ověřená „Tabulka“ (8 Z, 3V/1VP/2PP/2P, 13 bodů,
23:23, 54,17 % bodový zisk) + kompletní Odehrané zápasy/Bodování/
Brankáři se správně naformátovaným datem.

✅ **Krok 3 – menu „pre-scout“ v main.py/cli.py (20. 10. 2026).**
`prescout/pipeline.py` (`run_pre_scout`) – zeptá se na soupeře
(`pre_scout_lt.ask_team`, přes `cihtv.find_teams`), zapíše `team["name"]`
přímo do `B1` listu „Příští soupeř“ (`write_next_opponent`) a spustí
`save_team_clips` (lokální klipy). **Žádné dodatečné napárování názvu
nebylo potřeba** – živě ověřeno u všech 16 týmů Ligy juniorů, že název
vrácený `cihtv.find_teams` (czechicehockey.tv) je identický s názvem
listu v Liga 2.0 (ceskyhokej.cz) – stejný svaz/registr, jen jiný web.
Nový příkaz `cli pre-scout [tým]` (`cmd_pre_scout`) a položka „6“ v menu
`main.py`.

Ověřeno živě naplno (ne jen suchý běh): `cli pre-scout pribram` →
přihlášení na czechicehockey.tv, nalezení posledního zápasu (HC
Příbram – HC Hvězda Praha, 11. 10. 2026, 5:3), zápis „HC Příbram“ do
„Příští soupeř“!B1, stažení a střih **15 reálných MP4 klipů**
(5 vlastních gólů, 3 obdržené, 3 vlastní přesilovky, 4 oslabení;
~1,1 GB, `ffmpeg` bez překódování) do `output/pre_scout/
pre_scout_lt_hc_pribram_20261011/` + `prehled.txt`. `output/` doplněno
do `.gitignore` (gigabajty videa), testovací klipy po ověření smazány.

**Pre-scout je tím funkčně hotový vč. Sheets integrace** (list, menu,
klipy) – jediná odložená část je nahrávání klipů na Disk (viz past „krok
1“ výš, Shared Drive/OAuth).

✅ **Doplněny grafy na „Příští soupeř“ (21. 10. 2026).** Uživatel
nahlásil, že se na listu nezobrazují grafy – čekané: `IMPORTRANGE`
kopíruje jen hodnoty buněk, grafy jsou vlastní objekty, ne data, takže
se nikdy nemohly přenést automaticky. Oprava: `build_seznamy_next_
opponent_sheet.py` teď postaví 3 grafy nativně na „Příští soupeř“ (Skóre
po zápasech, Skóre po třetinách, Pořadí v tabulce) – stejné zdrojové
sloupce (N:P, R:T, V:X), co `IMPORTRANGE` přinesl, jen posunuté o +2
řádky (import začíná na řádku 3, šablona na řádku 1). Staré grafy se
před znovupostavením smažou (idempotence – `values().clear()` na grafy
nesahá, opakovaný běh by jinak hromadil duplicity).
- **Past nalezená živě:** graf „Skóre po třetinách“ při prvním běhu
  ztratil jednu ze dvou sérií i po všech 7 pokusech `create_chart_
  robust`. Příčina nebyla flaky API (jako jinde v projektu), ale
  skutečně PRÁZDNÝ zdroj dat – `values().clear()` na začátku skriptu
  smazal i `B1` (soupeř), takže `IMPORTRANGE` v okamžiku stavby grafů
  ukazoval jen chybovou hlášku, ne čísla. Sheets API v takovém případě
  `series` nad prázdným rozsahem tiše zahodí (stejná past jako u
  Dashboardu, viz výš). Oprava: `B1` zůstává po skriptu natrvalo
  vyplněné reálným týmem (`"HC Stadion Litoměřice"`, stejný placeholder
  jako `PLACEHOLDER_TEAM` v `build_league_team_template.py`) – `cli
  pre-scout` ho při výběru soupeře přepíše, ale nikdy nenechá prázdné.
Ověřeno živě: všechny 3 grafy mají po běhu správný počet sérií (2/2/1),
zdrojová data existují a správně se měnila s přepnutím `B1` (ověřeno na
LIT vlastním i HC Příbram – skóre po zápasech/třetinách/pořadí sedí na
dřív ověřená čísla pro oba týmy).

✅ **Výběr soupeře odpojen od stahování videí – rozbalovací seznam na
B1 (21. 10. 2026).** Uživatel chtěl `B1` listu „Příští soupeř“ ovládat
přímo v tabulce (rozbalovací seznam), ne jen jako vedlejší efekt
spuštění celého (pomalého, ~GB) stahování klipů – menu `main.py`/`cli
pre-scout` zůstává jen pro samotné klipy.
- `build_seznamy_next_opponent_sheet.py`: skrytý sloupec `Z` zrcadlí přes
  `IMPORTRANGE` názvy týmů ze `Skupiny - liga` (Liga 2.0) – ne napevno
  vypsaný seznam, ať se sám udrží v souladu, kdyby se složení ligy
  v sezóně změnilo (stejná spreadsheet dvojice jako hlavní import, žádné
  druhé „Povolit přístup“ nebylo potřeba). `B1` dostal `setDataValidation`
  (`ONE_OF_RANGE` nad `Z2:Z50`, `strict: true`, `showCustomUi: true`) –
  rozbalovací šipka v buňce, zápis mimo seznam Sheets samo odmítne (`B1`
  krmí hlavní `IMPORTRANGE`, překlep by ho rozbil beze slova).
- `prescout/pipeline.py` (`run_pre_scout`) už nezapisuje do `B1` –
  `write_next_opponent` smazáno celé (nic jiného ho nevolalo). Zůstává
  jen `ask_team` → `save_team_clips`. `cli pre-scout`/menu „6“ přejmenováno
  na „stáhnout klipy soupeře“, ať je zjevné, že se soupeř pro Sheets
  vybírá jinde.
Ověřeno živě: sloupec `Z` má všech 16 týmů (vč. LIT), `B1` nese platnou
`dataValidation` (`ONE_OF_RANGE` + `strict`), a uživatel dropdown
vyzkoušel sám za běhu (přepnul `B1` na „TECHNIKA HOCKEY BRNO“ zatímco
jsem ověřoval) – „Příští soupeř“ i grafy se podle toho správně
přepočítaly (10 Z, 2V/2VP/0PP/6P, 10 bodů, 25:43, 33,33 % bodový zisk).

✅ **List „Příští soupeř Last 5“ (21. 10. 2026).** Stejné kategorie a
rozložení jako `Last 5` (LIT), ale forma **kteréhokoli soupeře** vybraného
na `Příští soupeř`!`B1` za posledních 5 zápasů. LIT Last 5 počítá
z Seznamy DB (zná jen LIT) – soupeř může být libovolný z 16 týmů ligy,
takže zdroj musí být Liga DB. `scripts/build_seznamy_next_opponent_
last5_sheet.py`:
- Tři skryté `IMPORTRANGE` mirrory z Liga 2.0 (`Zápasy - liga (tým)`
  sloupce AA:AT, `Bruslaři - liga (zápasy)` BA:BJ, `Brankáři - liga
  (zápasy)` CA:CL) + místní pomocný sloupec `CM` („vychytaná výhra“ –
  log má na rozdíl od Seznamy DB jen jeden řádek na brankáře, co v
  zápase skutečně chytal, takže bez potřeby podmínky na „chytal“).
- Tým se filtruje dynamickým odkazem na `'Příští soupeř'!$B$1` (ne
  napevno jako LIT), „posledních 5 zápasů“ podle **kola** (`Zápasy -
  liga (tým)` ho má) – každý tým hraje v lize přesně 1 zápas na kolo,
  bez rizika textového řazení data (past u Liga 2.0 team template, viz
  výš).
**Tři pasti nalezené živě:**
1. Absolutní odkazy na `$5000.` řádek (`$AB$5000` apod.) se po zápisu
   samy přepsaly na `$7014` – mřížka listu měla míň řádků, než
   vyžadovaly vzorce, Sheets ji musela zvětšit a při tom (vložením
   řádků, ne jen změnou `rowCount`) posunula už zapsané absolutní
   odkazy. Oprava: `gridProperties.rowCount` nastavený napevno na
   `ROWS + 100` PŘED zápisem vzorců (stejný princip jako `columnCount`
   u Dashboardu/Tabulky, jen pro řádky).
2. `QUERY` s podmínkou `BA='" & N2 & "'"` (uvozovky kolem `game_id`)
   tiše vrátilo 0 řádků, bez chyby – `game_id` je v Liga DB **číslo**
   (`league_scraper.py` ho parsuje přes `int()`), ne text jako LIT
   „číslo zápisu“, takže textové porovnání proti číselnému sloupci
   v GViz Query nikdy nesedí. Oprava: `_last5_or_tokens` sestavuje
   podmínku bez uvozovek (`BA=181025`, ne `BA='181025'`).
3. (Vedlejší, při ladění) `AND (A OR B)` s uvozovkami i bez nich vracelo
   stejně 0 řádků dokud nebyla opravena past č. 2 – nebyl to problém se
   závorkami samými, jak se zprvu zdálo, jen s typem porovnávané
   hodnoty uvnitř nich.
Ověřeno živě na dvou týmech: „HCM Warriors Brno“ (5 Z, 0V/0VP/1PP/4P,
1 bod, 9:32, oba brankáři 0 % výher – sedí na 0 výher v okně) a „Berani
Zlín“ (5 Z, 4V/1VP/0PP/0P, 14 bodů, 26:10, oba brankáři 100 % výher –
sedí na to, že tým vyhrál všech 5 zápasů v okně).

✅ **Oba listy „Last 5“ doplněny o tabulku samotných zápasů (21. 10.
2026).** Uživatel nahlásil, že se na listech „Last 5“ (LIT) i „Příští
soupeř Last 5“ nezobrazují zápasy, jen souhrnné statistiky – chybělo
vidět, KTERÝCH 5 zápasů se čísla týkají. Oprava na obou listech:
nová tabulka „ODEHRANÉ ZÁPASY (POSLEDNÍCH 5)“ na `A16` (Datum, Soupeř,
D/V, Skóre, Skóre soupeře, Výsledek, Body), Bodování přesunuto na `I16`
a Brankáři na `T16` (dřív `A16`/`I16`), aby byl dost místa.
- `build_seznamy_last5_sheet.py` (LIT): zápasy z `Zápasy - liga (tým)`
  nemají – LIT čerpá ze Seznamy DB (`Zápasy (tým)`), ta nemá vlastní
  datum, takže `A18` je `ARRAYFORMULA(VLOOKUP(...))` do `Zápasy`!A:B
  (stejný hidden-raw-QUERY + VLOOKUP vzor jako Dashboard „Odehrané
  zápasy“), zbytek sloupců (`B`–`G`) čte přímo ze skrytého QUERY
  mirroru na `AA18`.
- `build_seznamy_next_opponent_last5_sheet.py`: Liga 2.0 mirror
  (`Zápasy - liga (tým)`) má vlastní datum (sloupec `AD`), žádný
  VLOOKUP není potřeba – `A18` je přímo `_query_formula` select na
  `ZT_DATUM, ZT_SOUPER, ZT_DOMA_VENKU, ZT_SKORE_TYM, ZT_SKORE_SOUPER,
  ZT_VYSLEDEK, ZT_BODY`, řazeno podle kola vzestupně. Doplněna chybějící
  konstanta `ZT_DOMA_VENKU = "AE"`.
- Na obou listech: `bold_ranges` doplněny o `T16:T16`/`A17:G17`,
  procentní formát Brankářů přesunut z `N18:N50` na `Y18:Y50` (6. sloupec
  výstupu se posunul ze `I`/`N` na `T`/`Y`).
Ověřeno živě na obou listech: LIT (5 zápasů 2.–16. 10. 2026 v chronolo-
gickém pořadí, skóre/výsledky/body přesně sedí na dřív ověřená čísla) i
„Příští soupeř Last 5“ pro „TECHNIKA HOCKEY BRNO“ (5 zápasů 4.–18. 10.
2026, D/V i výsledky logicky navazují na už ověřené souhrnné statistiky
týmu).

✅ **Oprava: sloupec „Z“ v Bodování byl na obou listech „Last 5“ skrytý
(21. 10. 2026).** Uživatel nahlásil, že se počet odehraných zápasů u
hráčů (sloupec „Z“ v BODOVÁNÍ) stále nezobrazuje, i když vzorec v kódu
byl správně (ověřeno `read_range` – data `Z` ve sloupci skutečně byla,
hodnoty 1–5 sedící na počet zápasů v okně). Příčina: oba skripty skrývají
celý sloupec `J` (`hiddenByUser: true`), protože tam dřív býval jen
neviditelný pomocný čitatel `J9` pro „Využití PP“ (přesilovky/oslabení
sekce) – žádná jiná buňka ve sloupci `J` nebyla potřeba. Po přesunu
Bodování z `A16` na `I16` (viz past výš) ale „Z“ sloupec Bodování skončil
právě na `J17` – ve stejném, celoplošně skrytém sloupci. `IFERROR`/
správná data v buňce nic nezmění, pokud je celý sloupec `hiddenByUser`.
Oprava ve dvou krocích: (1) pomocný čitatel přesunut z `J9` na `N9`
(sloupec `N` je už jinak skrytý – nese „posledních 5 game_id“ pomocný
seznam – takže žádný nový skrytý sloupec nepřidává), (2) skript teď
`J` sloupec výslovně ODKRYJE (`hiddenByUser: false`), protože už jednou
běžel se starým kódem a `J` zůstal skrytý i po samotném přesunu dat –
pouhé vynechání hide-requestu by list neopravilo, je potřeba aktivní
unhide.
Ověřeno živě na obou listech: `columnMetadata` z Sheets API po běhu
ukazuje jen `N` (index 13) jako skrytý, `J` (index 9) už ne; „Využití PP“
(`B9`) i nadále počítá správně (LIT 22,22 % = 4/18, soupeř 0,00 % = 0/19)
a Bodování „Z“ je viditelné se stejnými hodnotami jako dřív.

✅ **Nahrávání pre-scout klipů na Disk přes OAuth za reálného uživatele
(21. 10. 2026).**
Navázáno na dřív odloženou past „servisní účet nemá úložiště“ (viz past
výš, krok 1) – řešení č. 1 z nabízených (OAuth jako reálný uživatel,
ne Shared Drive/Workspace, který by stál peníze a chtěl admina).
- `config.py`: `OAUTH_SCOPES = ["...auth/drive"]` (plný, ne `drive.file`
  – potřeba najít i ručně založenou složku `Pre-scout`, ne jen soubory,
  co si OAuth klient sám vytvořil) + `get_oauth_drive_credentials` –
  `InstalledAppFlow.run_local_server` při prvním běhu (otevře prohlížeč,
  jednorázový souhlas za `hc.lit.juniori@gmail.com` – ten vlastní složku
  `Pre-scout`), token (`secrets/oauth_token.json`, v gitu ignorováno jako
  `service_account.json`) se pak jen obnovuje (`Credentials.refresh`),
  beze dalšího otevírání prohlížeče.
- `drive.py`: `find_or_create_folder`/`upload_file` (připravené od
  20. 10. 2026, nikdy nepoužité) teď běží přes `get_oauth_drive_
  credentials`, ne přes servisní účet – `list_pdf_files`/`download_file`
  (import PDF ze „Zápisy“) zůstávají na servisním účtu beze změny.
- `prescout/pipeline.py`: `run_pre_scout` po stažení klipů (`save_team_
  clips`) zavolá nový `upload_team_clips` – najde/založí podsložku podle
  názvu týmu v `PRE_SCOUT_DRIVE_FOLDER_ID`, nahraje všechny `.mp4` +
  `prehled.txt`. Každý soubor se nahrává samostatně v `try/except` – výpadek
  u jednoho klipu (velký soubor, nestabilní síť) nezastaví zbylé, lokální
  klipy v `output/pre_scout/...` zůstávají jako záloha i po uploadu.
- `.env`/`.env.example`: nové `GOOGLE_OAUTH_CLIENT_SECRETS_FILE`
  (`./secrets/oauth_client_secrets.json`) a `GOOGLE_OAUTH_TOKEN_FILE`
  (`./secrets/oauth_token.json`).
**Jednorázové manuální nastavení** (nejde udělat z kódu/CLI, dokončeno
uživatelem): OAuth client ID (typ „Desktop app“) v Google Cloud Console
pro projekt servisního účtu (`storied-key-509309-q8`), „OAuth consent
screen“ (typ „External“) a test user `hc.lit.juniori@gmail.com` (app
není veřejně ověřená, bez testera přihlášení vrací `403 access_denied`).
- **Past nalezená živě:** „Test users“ není na hlavní stránce „OAuth
  consent screen“ – Google přesunul sekci test userů pod samostatnou
  záložku „Audience“ (`console.cloud.google.com/auth/audience`), což na
  staré URL/stránce nejde najít.
- Stažený client secrets JSON má jméno `oauth_client_secrets.json`
  (množné číslo), ne `oauth_client_secret.json`, jak jsem původně
  předpokládal v kódu/`.env.example`/README – opraveno na obou místech
  (`config.py` default i `.env`), ať název souboru sedí na to, co Google
  Cloud Console skutečně nabízí ke stažení.
Ověřeno živě (testovací skript, ne ostrý pre-scout): `get_oauth_drive_
credentials` → prohlížeč → přihlášení za `hc.lit.juniori@gmail.com` →
`find_or_create_folder` založil testovací podsložku v `Pre-scout/` →
`upload_file` nahrál `oauth_test.txt` → `about().get()` potvrdil
přihlášeného uživatele (`hc.lit.juniori@gmail.com`) i vlastníka souboru
(`owners: hc.lit.juniori@gmail.com`, ne servisní účet) → testovací soubor
i podsložka smazány. Token (`secrets/oauth_token.json`) zůstává uložený –
další `cli pre-scout` už prohlížeč neotevře.

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

## Krok 9 – Přechod ✅ (body 1–2 splněny, jinou cestou než plán původně čekal)

1. ✅ Paralelní provoz proběhl, ale ne jako plánovaný „dva až tři zápasy do
   kopie" – zápasy 4002/4012 se rovnou zapisovaly do ostré produkční
   tabulky (Krok 5–8), pak od 25.–26. 9. 2026 souběžně i do nové Seznamy DB
   (dual-write), než se ověřila (viz sekce „LIT Seznamy 2.0" výše).
2. ✅ **Ostrá tabulka přepnuta – ale na Seznamy DB / Seznamy 2.0, ne na
   zůstávající starou produkční „Seznamy"** (26. 9. 2026, cutover). Ruční
   import a asistence v konverzaci skončily už dřív (produkční import
   fungoval samostatně od Kroku 8), tahle poslední změna jen přesunula cíl
   zápisu na novou architekturu sdílenou s Ligou.
3. ⏳ Sezónní údržba (rozšíření ročníků, nový Seznam hráčů, nová tabulka pro
   další sezónu podle `SEASON_START_YEAR`) zůstává otevřená na příští sezónu.

## Rizika a otevřené otázky

- **Formát PDF**: pokud se šablona zápisu ČSLH změní, parser přestane fungovat. Mitigace: testy na uložených PDF a jasné chyby místo tichých špatných hodnot.
- **Přeškrtnutý brankář**: nutno ověřit, jak se v PDF dá spolehlivě poznat (viz krok 2).
- **Google API kvóty a oprávnění**: servisní účet musí mít úpravy tabulky a čtení složky. Účet s daty (hc.lit.juniori@gmail.com) je jiný než účet uživatele, sdílení se musí nastavit z něj.
- **Ruční úpravy tabulky uživatelem**: mění rozložení sloupců (už se stalo). Řeší kontrola záhlaví při startu (krok 1).
- **Všechny výpočty v tabulce, nebo v Pythonu?** Tento plán ponechává statistiky ve vzorcích tabulky a přesouvá do Pythonu jen import a odvozené hodnoty ze zápisu. Případný přesun i agregací (Bodování, Brankáři, Tým) do Pythonu by šel udělat později jako samostatná fáze.
- **Střely** zůstávají mimo, dokud nebudou ve zdroji.
- **Chybějící čísla registrace** (Kotman, Nádemlenjský) a duplicitní číslo dresu 15 (Adelt/Hodek): doplnit v Seznamu hráčů.

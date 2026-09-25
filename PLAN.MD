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
6. **Odloženo na později (po odladění Seznamy 2.0):** `Seznam hráčů`
   a `Trenéři` obsahují citlivé osobní údaje (rodné číslo, pojišťovna,
   telefon, e-mail hráčů i rodičů; PIN a kontakty trenérů) – jiná kategorie
   dat než cokoli v Liga 2.0. Přesunou se do samostatné **nesdílené**
   tabulky, napojené jako DB (analogie k `LEAGUE_DB_SPREADSHEET_ID`), ne do
   veřejně sdílené DB spolu se zápasovými daty.

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

**Další krok:** navrhnout a postavit `Tým`/`Dashboard` v Seznamy 2.0
(sezónní přehled, přesilovky/oslabení, ročníky, skóre po třetinách – ze
`Zápasy` mirror) a později doplnit výhry/shutout do `Brankáři`.

Osud staré tabulky Liga (`LEAGUE_SPREADSHEET_ID`) po přechodu na Liga 2.0
zatím neřešen (smazat / nechat ladem / archivovat) – rozhodnout až bude
Liga 2.0 nějakou dobu v provozu ověřená uživatelem.

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

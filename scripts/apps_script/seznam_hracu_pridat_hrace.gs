/**
 * Google Apps Script pro soukromou tabulku "Seznam hráčů" (SEZNAMY_PRIVATE_
 * SPREADSHEET_ID) – list "Seznam hráčů". Doplňuje formulář "Přidat hráče",
 * který nového hráče vloží na správné místo podle abecedy (příjmení) a
 * seznam prodlouží, bez ručního přepisování pořadí/vzorců.
 *
 * PROČ JE TO APPS SCRIPT, NE PYTHON SKRIPT TÉHLE REPOZITÁŘE:
 * Servisní účet má k téhle tabulce záměrně jen roli Prohlížeč (viz PLAN.MD,
 * 2. 10. 2026) – citlivé osobní údaje hráčů (rodné číslo, pojišťovna,
 * telefon, e-mail) se nikdy nezapisují přes API. Tenhle skript se proto
 * NESPOUŠTÍ odsud, ale vkládá ho ručně trenér (majitel/editor tabulky)
 * přímo do Apps Script editoru té konkrétní tabulky.
 *
 * INSTALACE (provede trenér, jednou):
 *   1. Otevřít tabulku "Seznam hráčů" -> Rozšíření -> Apps Script.
 *   2. Smazat obsah výchozího "Code.gs" a nahradit celým obsahem tohoto
 *      souboru (jeden soubor stačí, formulář je vestavěný jako HTML šablona
 *      v `showAddPlayerDialog`, žádný druhý .html soubor není potřeba).
 *   3. Uložit (Ctrl+S), zavřít editor a znovu načíst tabulku v prohlížeči
 *      (F5 na záložce s tabulkou – jen uložení v editoru menu nepřidá,
 *      záložka s tabulkou se musí sama znovu načíst).
 *   4. Při prvním použití Google vyžádá autorizaci (skript čte/píše jen do
 *      téhle jedné tabulky – "Upravit tabulky Google" je očekávaný rozsah).
 *      Pokud se menu po reloadu stejně neobjeví, spusť funkci `onOpen`
 *      ručně z rozbalovací nabídky funkcí v editoru (tlačítko ▷ Spustit) –
 *      tím proběhne prvotní autorizační dialog, a pak znovu F5 na tabulce.
 *   5. V tabulce se objeví nová nabídka "Seznam hráčů" -> "Přidat hráče…".
 *
 * Sloupce G ("Z"), P–S ("góly/asistence/body/klíč řazení (pom.)") jsou u
 * existujících řádků nefunkční vzorce zděděné z produkční tabulky Seznamy
 * (odkazují na listy Sestavy/Zápasy, které tahle soukromá tabulka vůbec
 * neobsahuje – proto tam je #REF!). Nový řádek je proto nechává prázdné,
 * ne zkopírované jako další #REF!. Sloupec T ("ročník (pom.)") naopak
 * funguje (počítá se jen z vlastního sloupce D), takže se pro nový řádek
 * dopočítá stejným vzorcem jako u ostatních řádků.
 *
 * MAZÁNÍ HRÁČŮ: žádný formulář/skript, prostě nativně v Sheets – pravý
 * klik na číslo řádku -> "Odstranit řádek" (odsouhlaseno s uživatelem
 * 9. 10. 2026). Díky tomu, že `fixRowNumbers()` dole přepisuje sloupec A
 * na vzorec `=ROW()-2&"."`, se pořadová čísla po smazání řádku sama
 * přepočítají – žádná ruční oprava navíc není potřeba.
 */

const SHEET_NAME = "Seznam hráčů";
const DATA_START_ROW = 3; // řádek 1 = sezóna, řádek 2 = hlavička

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Seznam hráčů")
    .addItem("Přidat hráče…", "showAddPlayerDialog")
    .addToUi();
}

function showAddPlayerDialog() {
  const html = HtmlService.createHtmlOutput(FORM_HTML)
    .setWidth(420)
    .setHeight(560);
  SpreadsheetApp.getUi().showModalDialog(html, "Přidat hráče");
}

/** Volá se z formuláře (google.script.run.addPlayer(data)). */
function addPlayer(data) {
  const prijmeni = (data.prijmeni || "").trim();
  const jmeno = (data.jmeno || "").trim();
  if (!prijmeni || !jmeno) {
    throw new Error("Příjmení a jméno jsou povinné.");
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) {
    throw new Error(`List "${SHEET_NAME}" v tabulce chybí.`);
  }

  const lastDataRow = findLastDataRow(sheet);
  const targetRow = findInsertionRow(sheet, lastDataRow, prijmeni, jmeno);

  sheet.insertRowBefore(targetRow);

  const row = [
    "", // A – pořadové číslo, dopočítá fixRowNumbers() níž
    prijmeni,
    jmeno,
    data.cisloReg || "",
    data.cisloDresu || "",
    data.post || "",
    "", // G – nefunkční legacy vzorec, necháváme prázdné (viz komentář výš)
    data.status || "",
    data.poznamka || "",
    data.pojistovna || "",
    data.rc || "",
    data.tel || "",
    data.email || "",
    data.telRodice || "",
    data.emailRodice || "",
  ];
  sheet.getRange(targetRow, 1, 1, row.length).setValues([row]);
  sheet
    .getRange(targetRow, 20) // T – ročník (pom.), stejný vzorec jako ostatní řádky
    .setFormula(`=IF(D${targetRow}="";"";VALUE(RIGHT(D${targetRow};4)))`);

  fixRowNumbers(sheet);
  return `Hráč ${prijmeni} ${jmeno} byl přidán na řádek ${targetRow}.`;
}

/** Poslední řádek se skutečnými daty (sloupec B = příjmení neprázdný). */
function findLastDataRow(sheet) {
  const values = sheet
    .getRange(DATA_START_ROW, 2, sheet.getMaxRows() - DATA_START_ROW + 1, 1)
    .getValues();
  let last = DATA_START_ROW - 1;
  for (let i = 0; i < values.length; i++) {
    if (values[i][0] !== "") {
      last = DATA_START_ROW + i;
    }
  }
  return last;
}

/** Řádek, PŘED který se má nový hráč vložit (abecedně podle příjmení, při
 * shodě podle jména) – `insertRowBefore` ho posune a uvolní místo. Pokud
 * nový hráč patří na konec seznamu, vrátí lastDataRow + 1. */
function findInsertionRow(sheet, lastDataRow, prijmeni, jmeno) {
  if (lastDataRow < DATA_START_ROW) {
    return DATA_START_ROW;
  }
  const existing = sheet
    .getRange(DATA_START_ROW, 2, lastDataRow - DATA_START_ROW + 1, 2)
    .getValues();
  for (let i = 0; i < existing.length; i++) {
    const [existingPrijmeni, existingJmeno] = existing[i];
    const cmp = czechCompare(`${prijmeni} ${jmeno}`, `${existingPrijmeni} ${existingJmeno}`);
    if (cmp < 0) {
      return DATA_START_ROW + i;
    }
  }
  return lastDataRow + 1;
}

/** Lokalizované (české) porovnání – bez něj by diakritika (Č, Š, Ž...)
 * řadila podle Unicode pořadí, ne podle skutečné české abecedy. */
function czechCompare(a, b) {
  return a.localeCompare(b, "cs", { sensitivity: "base" });
}

/** Přepíše sloupec A (pořadové číslo) na `=ROW()-2&"."` pro všechny datové
 * řádky – jde o formuli, ne pevný text, takže při dalším vložení/smazání
 * řádku se čísla sama přepočítají a tahle funkce se dál nemusí volat ručně.
 * Běží při každém addPlayer() znovu (idempotentní, levné), takže funguje
 * i na starší řádky, které ještě mají číslo jako pevný text ("1.", "2."...). */
function fixRowNumbers(sheet) {
  const lastDataRow = findLastDataRow(sheet);
  if (lastDataRow < DATA_START_ROW) return;
  const count = lastDataRow - DATA_START_ROW + 1;
  const formulas = [];
  for (let i = 0; i < count; i++) {
    formulas.push([`=ROW()-2&"."`]);
  }
  sheet.getRange(DATA_START_ROW, 1, count, 1).setFormulas(formulas);
}

const FORM_HTML = `
<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <style>
    body { font-family: Arial, sans-serif; font-size: 13px; }
    label { display: block; margin-top: 8px; font-weight: bold; }
    input, select { width: 100%; box-sizing: border-box; padding: 4px; margin-top: 2px; }
    .row { display: flex; gap: 8px; }
    .row > div { flex: 1; }
    .hint { color: #666; font-weight: normal; font-size: 11px; }
    #submit { margin-top: 14px; padding: 8px 16px; }
    #msg { margin-top: 10px; font-weight: bold; }
    #msg.error { color: #c00; }
    #msg.ok { color: #080; }
  </style>
</head>
<body>
  <form id="form">
    <div class="row">
      <div>
        <label>Příjmení *</label>
        <input type="text" id="prijmeni" required>
      </div>
      <div>
        <label>Jméno *</label>
        <input type="text" id="jmeno" required>
      </div>
    </div>
    <div class="row">
      <div>
        <label>Č. registrace <span class="hint">(10místné)</span></label>
        <input type="text" id="cisloReg">
      </div>
      <div>
        <label>Číslo dresu</label>
        <input type="text" id="cisloDresu">
      </div>
    </div>
    <div class="row">
      <div>
        <label>Post</label>
        <select id="post">
          <option value=""></option>
          <option value="D">D – obránce</option>
          <option value="A">A – útočník</option>
          <option value="G">G – brankář</option>
        </select>
      </div>
      <div>
        <label>Status <span class="hint">(např. LIT, KLA)</span></label>
        <input type="text" id="status">
      </div>
    </div>
    <label>Poznámka</label>
    <input type="text" id="poznamka">
    <label>Pojišťovna</label>
    <input type="text" id="pojistovna">
    <label>Rodné číslo</label>
    <input type="text" id="rc">
    <div class="row">
      <div>
        <label>Telefon</label>
        <input type="text" id="tel">
      </div>
      <div>
        <label>E-mail</label>
        <input type="email" id="email">
      </div>
    </div>
    <div class="row">
      <div>
        <label>Telefon rodiče</label>
        <input type="text" id="telRodice">
      </div>
      <div>
        <label>E-mail rodiče</label>
        <input type="email" id="emailRodice">
      </div>
    </div>
    <button type="submit" id="submit">Přidat hráče</button>
    <div id="msg"></div>
  </form>
  <script>
    document.getElementById("form").addEventListener("submit", function (e) {
      e.preventDefault();
      const msg = document.getElementById("msg");
      const submitBtn = document.getElementById("submit");
      msg.className = "";
      msg.textContent = "";
      submitBtn.disabled = true;
      const data = {
        prijmeni: document.getElementById("prijmeni").value,
        jmeno: document.getElementById("jmeno").value,
        cisloReg: document.getElementById("cisloReg").value,
        cisloDresu: document.getElementById("cisloDresu").value,
        post: document.getElementById("post").value,
        status: document.getElementById("status").value,
        poznamka: document.getElementById("poznamka").value,
        pojistovna: document.getElementById("pojistovna").value,
        rc: document.getElementById("rc").value,
        tel: document.getElementById("tel").value,
        email: document.getElementById("email").value,
        telRodice: document.getElementById("telRodice").value,
        emailRodice: document.getElementById("emailRodice").value,
      };
      google.script.run
        .withSuccessHandler(function (result) {
          msg.className = "ok";
          msg.textContent = result;
          document.getElementById("form").reset();
          submitBtn.disabled = false;
        })
        .withFailureHandler(function (error) {
          msg.className = "error";
          msg.textContent = error.message;
          submitBtn.disabled = false;
        })
        .addPlayer(data);
    });
  </script>
</body>
</html>
`;

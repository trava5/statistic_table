# pre-scout LT — klipy gólů a přesilovek soupeře z czechicehockey.tv

Konzolová aplikace pro přípravu na zápas. Zadáte název **příštího soupeře** z **Ligy juniorů** a aplikace z jeho posledního odehraného zápasu uloží MP4 klipy:

1. `gol` — góly, které tým vstřelil,
2. `obdrzeny_gol` — góly, které tým dostal,
3. `presilovka` — přesilové hry týmu,
4. `oslabeni` — přesilové hry jeho soupeře (tým v oslabení).

Žádná AI analýza obrazu ani placené API, jen oficiální zápis zápasu (timeline) a záznam utkání z czechicehockey.tv.

---

## Obsah složky

| Soubor | Účel |
|---|---|
| `pre_scout_lt.py` | Vstupní bod: dotaz na tým, vyhledání zápasu, uložení klipů a `prehled.txt` |
| `event_clips.py` | Z událostí zápasu (góly, tresty) naplánuje úseky videa, odvodí přesilovky |
| `cihtv.py` | Klient czechicehockey.tv: přihlášení, hledání týmu a zápasů, události, HLS segmenty, střih klipu |
| `requirements.txt` | Python závislosti (jen `python-dotenv`) |
| `.env.example` | Šablona proměnných prostředí |
| `.gitignore` | Chrání `.env` (heslo) a `output/` (gigabajty videa) před commitem |

---

## Požadavky

- **Python 3.10+**
- **ffmpeg** v PATH, používá se jen k přebalení klipů do MP4 bez překódování.
  - Windows: `winget install Gyan.FFmpeg` (pak otevřít nový terminál)
  - macOS: `brew install ffmpeg`, Ubuntu/Debian: `sudo apt install ffmpeg`
- **Účet na czechicehockey.tv** s aktivním předplatným, které zahrnuje záznamy (VOD). Bez přístupu API video nevydá a zápas se přeskočí.
- Připojení k internetu. Jeden zápas zabere na disku zhruba 1–1,5 GB a stáhne se za 3–4 minuty.

---

## Začlenění do projektu

1. Zkopírujte celou složku do cílového projektu (pod libovolným názvem, např. `pre_scout_lt/`).
2. Nainstalujte závislosti: `pip install -r requirements.txt`
3. Do **místního `.env`** cílového projektu přidejte:

   ```env
   WEB_LOGIN=email-uctu@czechicehockey.tv
   WEB_PASSWD=heslo
   ```

   `.env` se hledá od složky s `cihtv.py` směrem nahoru (`python-dotenv`, `load_dotenv()`), takže může ležet přímo v této složce nebo v kterékoli nadřazené, např. v kořeni cílového projektu. Proměnné nastavené přímo v prostředí procesu mají přednost.
4. Pokud cílový projekt má vlastní `.gitignore`, ověřte, že pokrývá `.env` a `output/` této složky. Přiložený `.gitignore` platí jen pro tuto složku.

---

## Použití

Spouštějte z této složky:

```bash
python pre_scout_lt.py              # zeptá se na název týmu
python pre_scout_lt.py technika     # název týmu jako argument
```

- Stačí část názvu, nerozlišují se velká a malá písmena ani diakritika (`pisek` → *IHC Králové Písek*). Při více shodách aplikace nabídne výběr.
- Vybere se poslední odehraný zápas týmu v Lize juniorů, který má video i oficiální události. Zápasy bez nich přeskočí a vypíše je.

### Výstup

```
output/pre_scout_lt_<tým>_<datum zápasu>/
    01_gol_008-52_1-1_11_frimel.mp4
    03_obdrzeny_gol_008-02_0-1_64_skrip.mp4
    09_presilovka_061-34_trest_91_veneny.mp4
    13_oslabeni_065-34_trest_10_sebela_gol.mp4
    ...
    prehled.txt
```

- Název souboru: `NN_<druh>_<začátek klipu ve videu MMM-SS>_<popis>.mp4`.
- Klipy jsou očíslované po druzích v pořadí: góly → obdržené góly → přesilovky → oslabení. V rámci druhu jdou chronologicky.
- `prehled.txt` obsahuje zápas, odkaz na něj na czechicehockey.tv a seznam klipů s délkou a popisem.
- MP4: H.264 720p + AAC. Opakovaný běh pro stejný zápas přepíše klipy ve stejné složce.
- `output/` se vytváří vůči **aktuálnímu adresáři** (`OUTPUT_DIR` v `pre_scout_lt.py`).

### Volání z kódu

```python
import cihtv
from pre_scout_lt import save_team_clips

team = cihtv.find_teams("technika")[0]   # {id, name}
run_dir = save_team_clips(team)           # Path ke složce s klipy, nebo None když nejsou góly/přesilovky
```

`save_team_clips()` vyhodí `RuntimeError`, když tým nemá zápas s videem a událostmi, nebo když selže přihlášení či ffmpeg.

Moduly se importují holými jmény (`import cihtv`), takže adresář musí být na `sys.path`. To platí při spuštění skriptu z této složky. Pokud složku zabalíte jako Python balíček, přepište importy v `pre_scout_lt.py` a `event_clips.py` na relativní (`from . import cihtv`).

---

## Jak to funguje

### Zdroj dat (czechicehockey.tv, platforma Live Arena Sports)

| Údaj | Endpoint | Přihlášení |
|---|---|---|
| Přihlášení → Bearer token (platí 14 dní, drží se jen v paměti) | `POST https://www.czechicehockey.tv/api/user/login` | — |
| Zápasy soutěže | `GET api.livearenasports.com/broadcast/?competition-id=…` | ne (stačí hlavička `site-id: CZE`) |
| Události zápasu (GOAL / PENALTY) | `GET …/match-event/?broadcast-id=…` | ano |
| Začátek záznamu `streamStart` | `GET …/broadcast/{id}` | ano |
| Posun událostí pro soutěž | `GET …/broadcast/rules/match-event-offset?competition-id=…` | ano |
| HLS playlist záznamu | `GET …/broadcast/video/{id}?video-format=HLS` | ano |

Liga juniorů má ID soutěže `617bef438b97052b11740f21` (`LIGA_JUNIORU_ID` v `cihtv.py`), stejné pro všechny sezóny. API neumí filtrovat podle týmu, proto se zápasy soutěže procházejí od nejnovějších a filtrují v aplikaci.

### Časování klipů (`event_clips.py`)

Události nesou jen reálný čas zápisu (`timeStamp`, UTC), ne herní čas. Na čas ve videu se převádí stejně jako ve webovém přehrávači:

```
čas ve videu = timeStamp − streamStart − offset   (Liga juniorů: 90 s u gólu, 60 s u trestu)
```

- **Gól (vstřelený i obdržený):** od 90 s před zápisem do 15 s po něm. Zápis se zpožďuje zhruba o 10–30 s, takže klip obsahuje rozehrávku, gól i grafiku se střelcem.
- **Přesilovka / oslabení:** události ji neoznačují, odvozuje se z trestů.
  - Klip začíná 60 s před zápisem trestu (přestupek) a trvá délku trestu × 1,5, protože hrací čas se zastavuje, ale video běží dál.
  - Když přesilový tým dá gól zapsaný po trestu, klip končí 15 s po něm.
  - Přesilovku nevytváří osobní tresty (10 min a víc) ani vzájemné tresty obou týmů se stejnou délkou zapsané do 30 s od sebe.
  - Trest zapsaný během běžící přesilovky téhož týmu (5 na 3) ji prodlouží místo nového klipu.
- Klipy se skládají z celých 6s segmentů HLS, hranice jsou proto zaokrouhlené ven na ~6 s. Segmenty se spojí do dočasného `.ts` a ffmpeg ho bez překódování přebalí do `.mp4`.

Konstanty (délky, faktor, okna) jsou na začátku `event_clips.py`.

---

## Známá omezení

- **Konec přesilovky je odhad.** Data neobsahují herní čas, klip proto může končit o desítky sekund dřív nebo později.
- **Kvalita zápisu zápasu.** Klipy vycházejí z oficiálních událostí. Chybějící nebo zdvojený zápis (např. skóre 1:3 chybí a 1:4 je dvakrát) se projeví i v klipech.
- **Gól v přesilovce** je dvakrát: jako samostatný gólový klip a uvnitř klipu přesilovky.
- **Jen Liga juniorů.** Jiná soutěž znamená jiné `competition-id` (a jiný posun z API). Kód s tím počítá parametrem `competition_id`, ale ověřený je jen pro Ligu juniorů.
- **Neoficiální API.** Aplikace používá stejné API jako web czechicehockey.tv, které není veřejně dokumentované a může se změnit.

---

## Řešení problémů

| Hláška | Příčina / řešení |
|---|---|
| `Set WEB_LOGIN and WEB_PASSWD in .env` | Proměnné chybí v `.env` nebo `.env` není ve složce či nad ní |
| `czechicehockey.tv login failed (HTTP 400)` | Špatný e-mail nebo heslo |
| `Bez videa, přeskakuji: …` | Zápas nemá záznam nebo ho předplatné účtu nezahrnuje |
| `… nemá žádný odehraný zápas s videem a událostmi` | Tým v Lize juniorů nemá dostupný zápas se záznamem a zápisem |
| `ffmpeg remux to MP4 failed` / `FileNotFoundError: ffmpeg` | ffmpeg není nainstalovaný nebo není v PATH (po instalaci otevřít nový terminál) |
| `Tým „…“ v Lize juniorů nenalezen` | Zkuste kratší nebo jinou část názvu |

---

## Původ

Vyčleněno z projektu `hockey_analyzer` (video analýza s Claude Vision), kde pre-scout LT běží jako volba 3 aplikace `video_analyzer.py`. AI analýza (`analyze` / `pre_scout`) se dál vyvíjí tam a do této exportní složky není zahrnuta.

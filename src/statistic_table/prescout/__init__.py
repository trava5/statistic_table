"""Pre-scout příštího soupeře – klipy gólů a přesilovek z czechicehockey.tv.

Vyčleněno z `ready_to_move/` (projekt `hockey_analyzer`), přepsáno na relativní
importy a napojené na `Config` (žádné vlastní `load_dotenv()`/`os.environ`
čtení v `cihtv.py` – přihlašovací údaje teď chodí přes `Config.web_login`/
`web_passwd`, stejně jako zbytek projektu čte `.env` jen přes `config.py`).

Veřejné rozhraní: `cihtv`, `event_clips`, `pre_scout_lt` (moduly) a
`pipeline.run_pre_scout` (orchestrace: klipy + nahrání na Disk + zápis do
listu „Příští soupeř“), viz PLAN.MD.
"""

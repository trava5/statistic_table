"""
pre-scout LT — clips of the next opponent's goals and power plays from czechicehockey.tv.

Finds the team's last played Liga juniorů match that has a recording and
official match events, and saves MP4 clips of its goals scored, goals
conceded, its power plays and its opponent's power plays into
output_dir/pre_scout_lt_<team>_<match date>/ together with prehled.txt.
No AI analysis is involved.
"""

import re
from datetime import datetime
from pathlib import Path

from statistic_table.config import Config, require_web_credentials

from . import cihtv, event_clips

# ── Console input ─────────────────────────────────────────────────────────────

def ask_choice(question: str, options: list[str]) -> int:
    """Print numbered options and return the 0-based index of the chosen one."""
    print(f"\n{question}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    while True:
        answer = input("Volba: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Zadej číslo 1–{len(options)}.")


def ask_team(query: str = "") -> dict:
    """Resolve a team name (asked for when not given) to a Liga juniorů team."""
    while True:
        query = query or input("\nPříští soupeř (název týmu, stačí část): ").strip()
        if not query:
            continue
        teams = cihtv.find_teams(query)
        if len(teams) == 1:
            return teams[0]
        if teams:
            return teams[ask_choice("Nalezené týmy:", [t["name"] for t in teams])]
        print(f"  Tým „{query}“ v Lize juniorů nenalezen, zkus jiný název.")
        query = ""


# ── Clips ─────────────────────────────────────────────────────────────────────

def slug(text: str) -> str:
    """ASCII-only, underscore-separated name for output directories."""
    return re.sub(r"[^a-z0-9]+", "_", cihtv.normalize(text)).strip("_")


def save_team_clips(team: dict, config: Config, output_dir: Path) -> Path | None:
    """Save clips of the team's goals and power plays from its last played match.

    `team` is {id, name} as returned by cihtv.find_teams(). Returns the
    directory with the clips, or None when the match has no goals or power plays.
    """
    print("\nPřihlašuji se na czechicehockey.tv ...")
    web_login, web_passwd = require_web_credentials(config)
    token = cihtv.login(web_login, web_passwd)

    # Last played match with a recording and official match events
    for match in cihtv.previous_matches(team["id"], datetime.now().astimezone()):
        video_url = cihtv.get_video_url(match, token)
        events = cihtv.get_match_events(match, token) if video_url else []
        if video_url and events:
            break
        missing = "událostí" if video_url else "videa"
        print(f"  Bez {missing}, přeskakuji: {cihtv.match_label(match)}")
    else:
        raise RuntimeError(f"{team['name']} nemá žádný odehraný zápas s videem a událostmi.")

    team_type = "HOME" if match["homeTeam"]["id"] == team["id"] else "AWAY"
    clips = event_clips.plan_clips(
        events, team_type, cihtv.get_stream_start(match, token), cihtv.get_event_offset(token)
    )

    print(f"\npre-scout LT — {team['name']}, poslední zápas: {cihtv.match_label(match)}")
    if not clips:
        print("V zápase nejsou žádné góly ani přesilovky týmu nebo soupeře.")
        return None

    run_name = f"pre_scout_lt_{slug(team['name'])}_{cihtv.match_start(match):%Y%m%d}"
    run_dir = Path(output_dir) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    segments = cihtv.get_segments(video_url)

    overview = [f"{team['name']} — {cihtv.match_label(match)}", cihtv.game_page_url(match), ""]
    for i, clip in enumerate(clips, 1):
        path = run_dir / event_clips.clip_filename(i, clip)
        duration = cihtv.download_clip(segments, clip["start"], clip["end"], str(path))
        line = f"{path.name}  ({duration:.0f} s)  {clip['kind']}: {clip['label']}"
        overview.append(line)
        print(f"  {line}")

    (run_dir / "prehled.txt").write_text("\n".join(overview) + "\n", encoding="utf-8")
    return run_dir

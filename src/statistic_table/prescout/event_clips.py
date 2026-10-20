"""
Event clips for pre-scout LT — cut a team's goals (scored and conceded) and power plays
(its own and its opponent's) out of a match recording.

Uses the official match events from czechicehockey.tv (GOAL / PENALTY with
the wall-clock time they were recorded) and maps them onto the recording
the same way the site's own player does:
    video time = event timeStamp − recording streamStart − offset
No frames are analyzed, so no Claude API calls (and no cost) are involved;
ffmpeg is only used to remux the downloaded segments to MP4.

Power plays are not marked explicitly in the events — they are derived
from penalties:
  - only minor / double minor / major penalties (< 10 min) create a power play,
  - opposite-team penalties of equal length recorded within
    OFFSETTING_WINDOW_SEC of each other cancel out (no power play),
  - a power play clip runs from the penalty's offset point for
    duration × PP_WALL_CLOCK_FACTOR (the game clock stops, the video does not)
    and ends early PP_GOAL_TAIL_SEC after a goal of the team on the power play,
  - a power play goal must be recorded after the penalty,
  - a penalty recorded during the same team's running power play (5 on 3)
    extends that clip instead of starting a new one.
"""

import re
from datetime import datetime

from . import cihtv

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_GOAL_OFFSET_SEC    = 90     # Used when the API returns no offset for the competition
DEFAULT_PENALTY_OFFSET_SEC = 60
GOAL_TAIL_SEC              = 15     # Seconds kept after a goal's timeStamp (scorer graphic)
PP_GOAL_TAIL_SEC           = 15     # Seconds kept after a power-play goal before the clip ends
PP_WALL_CLOCK_FACTOR       = 1.5    # Video seconds per game second during a power play
MAX_PP_PENALTY_SEC         = 300    # Longer penalties (misconducts) don't create a power play
OFFSETTING_WINDOW_SEC      = 30

KIND_GOAL         = "gol"
KIND_GOAL_AGAINST = "obdrzeny_gol"
KIND_PP           = "presilovka"  # power play of the scouted team
KIND_PP_OPPONENT  = "oslabeni"     # power play of its opponent (= scouted team shorthanded)

# Order of clips in the output
KIND_ORDER = [KIND_GOAL, KIND_GOAL_AGAINST, KIND_PP, KIND_PP_OPPONENT]


def _player(event: dict) -> str:
    p = event.get("actionPlayer") or {}
    return f"{p.get('num', '?')} {p.get('lastName', '?')}"


def plan_clips(
    events: list[dict], team_type: str, stream_start: datetime, offsets: dict
) -> list[dict]:
    """Return clips [{kind, start, end, label}] (seconds in the recording).

    Ordered by kind (KIND_ORDER: goals scored, goals conceded, own power
    plays, opponent's power plays), chronologically within each kind.

    `team_type` is "HOME" or "AWAY" — the side of the scouted team in this match.
    """
    goal_offset = offsets.get("goalSec") or DEFAULT_GOAL_OFFSET_SEC
    penalty_offset = offsets.get("penaltySec") or DEFAULT_PENALTY_OFFSET_SEC

    def video_time(event):
        return (datetime.fromisoformat(event["timeStamp"]) - stream_start).total_seconds()

    goals = [e for e in events if e.get("eventType") == "GOAL"]
    penalties = [e for e in events if e.get("eventType") == "PENALTY"
                 and 0 < (e.get("durationInSecs") or 0) <= MAX_PP_PENALTY_SEC]

    # Offsetting penalties: pair opposite-team penalties of equal length recorded close together
    offset_ids = set()
    for a in penalties:
        if a["id"] in offset_ids:
            continue
        for b in penalties:
            if (b["id"] not in offset_ids and b["id"] != a["id"] and b["teamType"] != a["teamType"]
                    and b["durationInSecs"] == a["durationInSecs"]
                    and abs(video_time(a) - video_time(b)) <= OFFSETTING_WINDOW_SEC):
                offset_ids.update((a["id"], b["id"]))
                break

    clips = []
    for g in goals:
        t = video_time(g)
        clips.append({"kind":  KIND_GOAL if g["teamType"] == team_type else KIND_GOAL_AGAINST,
                      "start": t - goal_offset, "end": t + GOAL_TAIL_SEC,
                      "label": f"{g.get('homeGoals', '?')}-{g.get('awayGoals', '?')} {_player(g)}"})

    power_plays = []
    for p in penalties:
        if p["id"] in offset_ids:
            continue
        pp_team = "AWAY" if p["teamType"] == "HOME" else "HOME"
        t = video_time(p)
        start = t - penalty_offset
        end = t + p["durationInSecs"] * PP_WALL_CLOCK_FACTOR
        # A power-play goal is recorded after the penalty (both timeStamps lag the action similarly)
        pp_goal = next(
            (g for g in goals if g["teamType"] == pp_team and t < video_time(g) <= end), None
        )
        if pp_goal:
            end = video_time(pp_goal) + PP_GOAL_TAIL_SEC
        power_plays.append({
            "kind":  KIND_PP if pp_team == team_type else KIND_PP_OPPONENT,
            "start": start, "end": end, "penalty": t,
            "label": f"trest {_player(p)}" + (" gol" if pp_goal else ""),
        })

    # Merge power plays of the same team only when a penalty falls inside the previous
    # power play (5 on 3) — clips merely touching through the pre-roll stay separate
    for pp in sorted(power_plays, key=lambda c: c["start"]):
        prev = next((c for c in reversed(clips) if c["kind"] == pp["kind"]), None)
        if prev and pp["penalty"] < prev["end"]:
            prev["end"] = max(prev["end"], pp["end"])
            prev["label"] += f" + {pp['label']}"
        else:
            clips.append(pp)
    for c in clips:
        c.pop("penalty", None)

    for c in clips:
        c["start"] = max(0.0, c["start"])
    return sorted(clips, key=lambda c: (KIND_ORDER.index(c["kind"]), c["start"]))


def clip_filename(index: int, clip: dict) -> str:
    minutes, seconds = divmod(int(clip["start"]), 60)
    safe = re.sub(r"[^a-z0-9-]+", "_", cihtv.normalize(clip["label"])).strip("_")
    return f"{index:02d}_{clip['kind']}_{minutes:03d}-{seconds:02d}_{safe}.mp4"

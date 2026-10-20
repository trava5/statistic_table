"""
Client for czechicehockey.tv — the video source for pre_scout_lt.py.

The site runs on the Live Arena Sports platform. Match listings come from
its public REST API (only the `site-id` header is required); match events,
recording details and the HLS video URL require a Bearer token obtained by
logging in with WEB_LOGIN / WEB_PASSWD from `.env`. The token is kept in
memory only and never written to disk.
"""

import os
import json
import subprocess
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv

# ── Configuration ─────────────────────────────────────────────────────────────

load_dotenv()

WEB_LOGIN  = os.environ.get("WEB_LOGIN")
WEB_PASSWD = os.environ.get("WEB_PASSWD")

SITE_ID         = "CZE"
LOGIN_URL       = "https://www.czechicehockey.tv/api/user/login"
API_URL         = "https://api.livearenasports.com"
GAME_PAGE_URL   = "https://www.czechicehockey.tv/en/game/{id}"
LIGA_JUNIORU_ID = "617bef438b97052b11740f21"   # competition "Liga juniorů" (same id every season)
PAGE_SIZE       = 50
MAX_PAGES       = 20


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _request(url: str, data: dict = None, token: str = None):
    headers = {"site-id": SITE_ID, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def _iso(dt: datetime) -> str:
    """API expects UTC timestamps with milliseconds, e.g. 2026-10-16T22:00:00.000Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _broadcasts(params: dict) -> list[dict]:
    url = f"{API_URL}/broadcast/?" + urllib.parse.urlencode(params)
    return _request(url) or []


def _is_match(b: dict) -> bool:
    return bool(b.get("homeTeam")) and bool(b.get("awayTeam")) and not b.get("cancelled")


# ── Matches ───────────────────────────────────────────────────────────────────

def match_start(match: dict) -> datetime:
    """Match start as an aware datetime in the local timezone."""
    return datetime.fromisoformat(match["start"]).astimezone()


def match_label(match: dict) -> str:
    return (f"{match_start(match):%d.%m.%Y %H:%M}  "
            f"{match['homeTeam']['name']} – {match['awayTeam']['name']}")


def game_page_url(match: dict) -> str:
    return GAME_PAGE_URL.format(id=match["id"])


def previous_matches(team_id: str, before: datetime,
                     competition_id: str = LIGA_JUNIORU_ID):
    """Yield the team's matches in the competition that started before `before`, newest first.

    The API has no team filter, so the competition's matches are paged
    backwards in time and filtered here.
    """
    for page_index in range(MAX_PAGES):
        page = _broadcasts({
            "competition-id": competition_id,
            "start-to":       _iso(before),
            "include-live":   "false",
            "sort-column":    "start",
            "sort-order":     "Descending",
            "page-size":      PAGE_SIZE,
            "page-index":     page_index,
        })
        for m in page:
            if _is_match(m) and team_id in (m["homeTeam"]["id"], m["awayTeam"]["id"]):
                yield m
        if len(page) < PAGE_SIZE:
            break


def normalize(text: str) -> str:
    """Lowercase without diacritics, for team name search."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def find_teams(query: str, competition_id: str = LIGA_JUNIORU_ID) -> list[dict]:
    """Teams ({id, name}) of the competition's recent matches whose name contains `query`.

    Search ignores case and diacritics ("havirov" finds "HC AZ Havířov").
    """
    needle = normalize(query.strip())
    teams = {}
    now = datetime.now().astimezone()
    for page_index in range(MAX_PAGES):
        page = _broadcasts({
            "competition-id": competition_id,
            "start-to":       _iso(now),
            "include-live":   "false",
            "sort-column":    "start",
            "sort-order":     "Descending",
            "page-size":      PAGE_SIZE,
            "page-index":     page_index,
        })
        for m in page:
            if not _is_match(m):
                continue
            for team in (m["homeTeam"], m["awayTeam"]):
                if needle in normalize(team["name"]) and team["id"] not in teams:
                    teams[team["id"]] = {"id": team["id"], "name": team["name"]}
        if len(page) < PAGE_SIZE:
            break
    return list(teams.values())


# ── Match events ──────────────────────────────────────────────────────────────

def get_match_events(match: dict, token: str) -> list[dict]:
    """Official match events (eventType GOAL / PENALTY), ordered by timeStamp.

    `timeStamp` is the wall-clock time the event was recorded (UTC),
    `teamType` (HOME / AWAY) is the scoring resp. penalized team.
    """
    events = _request(f"{API_URL}/match-event/?" + urllib.parse.urlencode(
        {"broadcast-id": match["id"], "site-id": SITE_ID}), token=token) or []
    return sorted(events, key=lambda e: e["timeStamp"])


def get_stream_start(match: dict, token: str) -> datetime:
    """Wall-clock time of the first second of the match recording."""
    detail = _request(f"{API_URL}/broadcast/{match['id']}", token=token)
    return datetime.fromisoformat(detail["streamStart"])


def get_event_offset(token: str, competition_id: str = LIGA_JUNIORU_ID) -> dict:
    """How many seconds before an event's timeStamp the action starts — {goalSec, penaltySec, ...}.

    Same offsets the site's own player uses when jumping to an event in the timeline.
    """
    return _request(f"{API_URL}/broadcast/rules/match-event-offset?" + urllib.parse.urlencode(
        {"competition-id": competition_id}), token=token) or {}


# ── Video ─────────────────────────────────────────────────────────────────────

def login(user: str = None, password: str = None) -> str:
    """Log in and return the Bearer access token (valid for 14 days, kept in memory only)."""
    user = user or WEB_LOGIN
    password = password or WEB_PASSWD
    if not user or not password:
        raise RuntimeError("Set WEB_LOGIN and WEB_PASSWD in .env")
    try:
        data = _request(LOGIN_URL, data={"userName": user, "password": password})
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"czechicehockey.tv login failed (HTTP {e.code}) — check WEB_LOGIN / WEB_PASSWD") from None
    token = (data or {}).get("accessToken")
    if not token:
        raise RuntimeError(f"czechicehockey.tv login failed: {(data or {}).get('status')}")
    return token


def get_video_url(match: dict, token: str) -> str | None:
    """HLS playlist URL of the match recording, or None if there is no video / no access."""
    data = _request(f"{API_URL}/broadcast/video/{match['id']}?video-format=HLS", token=token) or {}
    if data.get("status") != "OK":
        return None
    return data.get("videoUrl")


def get_segments(video_url: str) -> list[dict]:
    """Segments of an HLS playlist: [{start, duration, url}], start = seconds from the recording start."""
    with urllib.request.urlopen(urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"}),
                                timeout=30) as r:
        lines = r.read().decode("utf-8", "replace").splitlines()
    segments, start = [], 0.0
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF:") and i + 1 < len(lines):
            try:
                duration = float(line[len("#EXTINF:"):].split(",")[0])
            except ValueError:
                continue
            segments.append({"start": start, "duration": duration,
                             "url": urllib.parse.urljoin(video_url, lines[i + 1].strip())})
            start += duration
    return segments


def download_clip(segments: list[dict], start_sec: float, end_sec: float, output_path: str) -> float:
    """Save the part of the recording between start_sec and end_sec as one MP4 file.

    Whole HLS segments covering the interval are downloaded and joined into
    a temporary MPEG-TS file (segments of one stream can be concatenated
    as-is), which ffmpeg then remuxes to MP4 without re-encoding. Clip
    boundaries are rounded outwards to the segment length (~6 s). Returns
    the clip duration in seconds.
    """
    chosen = [s for s in segments if s["start"] + s["duration"] > start_sec and s["start"] < end_sec]
    ts_path = os.path.splitext(output_path)[0] + ".ts"
    with open(ts_path, "wb") as out:
        for s in chosen:
            with urllib.request.urlopen(urllib.request.Request(s["url"], headers={"User-Agent": "Mozilla/5.0"}),
                                        timeout=60) as r:
                out.write(r.read())

    cmd = [
        "ffmpeg", "-i", ts_path,
        "-c", "copy", "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart",
        output_path,
        "-y", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg remux to MP4 failed:\n{result.stderr[:300]}")
    os.remove(ts_path)
    return sum(s["duration"] for s in chosen)

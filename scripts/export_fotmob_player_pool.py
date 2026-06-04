"""Export World Cup player data from public FotMob page JSON.

This uses FotMob's public Next.js page data rather than browser scraping:

1. Read the World Cup league page to get the current build ID and team IDs.
2. Read each qualified team's squad page to collect player IDs.
3. Read each player page JSON to collect club-season minutes, appearances,
   goals, assists, rating, and current club.
4. Write data/fotmob-player-pool.csv for scripts/build_player_pool.py.

FotMob does not publish this as a stable public API, so this script is best
treated as an export helper. It uses normal HTTP requests, light pacing, and no
authentication bypass.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "fotmob-player-pool.csv"
FOTMOB = "https://www.fotmob.com"
WORLD_CUP_URL = f"{FOTMOB}/leagues/77/overview/world-cup"


HEADERS = {
    "User-Agent": "Mozilla/5.0 WorldCup2026Analytics/0.1",
    "Accept": "text/html,application/json",
}


FIELDNAMES = [
    "name",
    "country",
    "role",
    "club",
    "club_minutes",
    "club_apps",
    "goals",
    "assists",
    "xg",
    "xa",
    "shots_created",
    "tackles_interceptions",
    "clearances_blocks",
    "aerials_won",
    "clean_sheets",
    "gk_saves",
    "availability",
    "fotmob_rating",
    "fotmob_player_id",
]


def get_url(url: str, accept_json: bool = False) -> str:
    headers = dict(HEADERS)
    if accept_json:
        headers["Accept"] = "application/json"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def get_next_data(url: str) -> dict:
    text = get_url(url)
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text)
    if not match:
        raise ValueError(f"No Next.js data found at {url}")
    return json.loads(html.unescape(match.group(1)))


def get_build_id(next_data: dict) -> str:
    build_id = next_data.get("buildId")
    if not build_id:
        raise ValueError("Could not find FotMob build ID")
    return build_id


def normalize_role(member: dict) -> str:
    desc = str(member.get("positionIdsDesc") or member.get("role", {}).get("fallback") or "").upper()
    if "GK" in desc or "KEEPER" in desc:
        return "GK"
    if any(token in desc for token in ["CB", "LB", "RB", "LWB", "RWB", "DEF"]):
        return "DEF"
    if any(token in desc for token in ["DM", "CM", "AM", "MID"]):
        return "MID"
    return "FWD"


def stat_value(stats: list[dict], key: str, fallback_title: str = "") -> float:
    fallback_title = fallback_title.lower()
    for stat in stats or []:
        localized = str(stat.get("localizedTitleId", "")).lower()
        title = str(stat.get("title", "")).lower()
        if localized == key or (fallback_title and title == fallback_title):
            value = stat.get("value", 0)
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def collect_world_cup_teams() -> tuple[str, list[dict]]:
    data = get_next_data(WORLD_CUP_URL)
    league = data["props"]["pageProps"]
    teams: dict[int, dict] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if {"name", "id", "pageUrl"}.issubset(value) and str(value.get("pageUrl", "")).startswith("/teams/"):
                teams[int(value["id"])] = {
                    "id": int(value["id"]),
                    "name": value["name"],
                    "page_url": value["pageUrl"],
                }
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(league.get("table", []))
    return get_build_id(data), sorted(teams.values(), key=lambda team: team["name"])


def collect_team_squad(team: dict) -> list[dict]:
    url = f"{FOTMOB}{team['page_url'].replace('/overview/', '/squad/')}"
    data = get_next_data(url)
    fallback = data["props"]["pageProps"]["fallback"]
    team_payload = fallback.get(f"team-{team['id']}")
    if not team_payload:
        return []

    players = []
    for group in team_payload.get("squad", {}).get("squad", []):
        if group.get("title") == "coach":
            continue
        for member in group.get("members", []):
            if member.get("excludeFromRanking") or member.get("role", {}).get("key") == "coach":
                continue
            players.append(
                {
                    "id": int(member["id"]),
                    "name": member.get("name", ""),
                    "country": team["name"],
                    "role": normalize_role(member),
                    "club": member.get("cname", ""),
                }
            )
    return players


def collect_player_stats(build_id: str, player: dict) -> dict:
    url = f"{FOTMOB}/_next/data/{build_id}/en/players/{player['id']}/x.json"
    try:
        data = json.loads(get_url(url, accept_json=True))["pageProps"]["data"]
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        fallback_url = f"{FOTMOB}/players/{player['id']}/x"
        data = get_next_data(fallback_url)["props"]["pageProps"]["data"]
    main_league = data.get("mainLeague") or {}
    stats = main_league.get("stats") or []
    minutes = stat_value(stats, "minutes_played", "minutes played")
    matches = stat_value(stats, "matches_uppercase", "matches")
    starts = stat_value(stats, "started", "started")
    rating = stat_value(stats, "rating", "rating")
    goals = stat_value(stats, "goals", "goals")
    assists = stat_value(stats, "assists", "assists")
    primary_team = data.get("primaryTeam") or {}
    club = primary_team.get("teamName") or player.get("club", "")
    availability = min(max(matches / 25, starts / 20 if starts else 0), 1.0) if matches else 0.0

    return {
        "name": data.get("name") or player["name"],
        "country": player["country"],
        "role": player["role"],
        "club": club,
        "club_minutes": int(minutes),
        "club_apps": int(matches),
        "goals": int(goals),
        "assists": int(assists),
        "xg": "",
        "xa": "",
        "shots_created": "",
        "tackles_interceptions": "",
        "clearances_blocks": "",
        "aerials_won": "",
        "clean_sheets": "",
        "gk_saves": "",
        "availability": round(availability, 3),
        "fotmob_rating": rating or "",
        "fotmob_player_id": player["id"],
    }


def export(limit_teams: int | None, delay: float, workers: int) -> None:
    build_id, teams = collect_world_cup_teams()
    if limit_teams:
        teams = teams[:limit_teams]
    print(f"FotMob build ID: {build_id}")
    print(f"Teams found: {len(teams)}")

    players: dict[int, dict] = {}
    for index, team in enumerate(teams, start=1):
        squad = collect_team_squad(team)
        print(f"[{index:02d}/{len(teams):02d}] {team['name']}: {len(squad)} squad members")
        for player in squad:
            players.setdefault(player["id"], player)
        time.sleep(delay)

    print(f"Unique players found: {len(players)}")
    player_list = list(players.values())
    rows = []

    def fetch_player(player: dict) -> tuple[dict, str | None]:
        try:
            row = collect_player_stats(build_id, player)
            time.sleep(delay)
            return row, None
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            time.sleep(delay)
            return player, str(exc)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_player, player): player for player in player_list}
        for index, future in enumerate(as_completed(futures), start=1):
            row, error = future.result()
            if error:
                print(f"[{index:04d}/{len(player_list):04d}] skipped {row['name']}: {error}")
                continue
            rows.append(row)
            print(f"[{index:04d}/{len(player_list):04d}] {row['name']} - {row['club_minutes']} mins")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-teams", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    export(args.limit_teams, args.delay, args.workers)


if __name__ == "__main__":
    main()

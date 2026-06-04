"""Build the 410-player World Cup impact pool from FotMob-derived data.

Expected input: data/fotmob-player-pool.csv

The CSV should be exported from an approved FotMob workflow or another process
that has already mapped World Cup players to their club-season FotMob stats.
This script filters for World Cup teams, keeps regular club players, computes a
transparent first-pass impact score, and writes the top 410 to the site JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "world-cup-2026.json"
DEFAULT_INPUT = ROOT / "data" / "fotmob-player-pool.csv"

COUNTRY_ALIASES = {
    "Cape Verde": "Cabo Verde",
    "DR Congo": "Congo DR",
    "Iran": "IR Iran",
    "Ivory Coast": "Cote d'Ivoire",
    "South Korea": "Korea Republic",
}


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in ("", None):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    return int(round(as_float(row, key, float(default))))


def per90(value: float, minutes: float) -> float:
    if minutes <= 0:
        return 0.0
    return value * 90 / minutes


def role_code(position: str) -> str:
    normalized = position.strip().upper()
    if normalized in {"GK", "GOALKEEPER"}:
        return "GK"
    if normalized in {"CB", "LB", "RB", "LWB", "RWB", "DEF", "DF", "DEFENDER"}:
        return "DEF"
    if normalized in {"DM", "CM", "AM", "MID", "MF", "MIDFIELDER"}:
        return "MID"
    return "FWD"


def score_player(row: dict[str, str], min_minutes: int) -> dict:
    minutes = as_float(row, "club_minutes")
    role = role_code(row.get("role", ""))
    regularity = min(minutes / min_minutes, 1.0) if min_minutes else 1.0
    rating = as_float(row, "fotmob_rating", 6.6)

    xg90 = per90(as_float(row, "xg"), minutes)
    xa90 = per90(as_float(row, "xa"), minutes)
    goals90 = per90(as_float(row, "goals"), minutes)
    assists90 = per90(as_float(row, "assists"), minutes)
    creation90 = per90(as_float(row, "shots_created"), minutes)
    defensive_actions90 = per90(
        as_float(row, "tackles_interceptions") + as_float(row, "clearances_blocks"),
        minutes,
    )
    aerials90 = per90(as_float(row, "aerials_won"), minutes)
    save_value = per90(as_float(row, "gk_saves"), minutes)

    attack = (xg90 * 1.7) + (xa90 * 1.5) + (goals90 * 0.9) + (assists90 * 0.7) + (creation90 * 0.12)
    defense = (defensive_actions90 * 0.11) + (aerials90 * 0.08)
    if role == "GK":
        attack *= 0.15
        defense = (save_value * 0.26) + (as_float(row, "clean_sheets") * 0.03)
    elif role == "DEF":
        defense *= 1.18
    elif role == "FWD":
        attack *= 1.14

    availability = min(as_float(row, "availability", regularity), 1.0)
    rating_component = (rating - 6.5) * 0.75
    impact_score = attack + defense + rating_component + (regularity * 0.45) + (availability * 0.25)

    return {
        "name": row.get("name", "").strip(),
        "country": COUNTRY_ALIASES.get(row.get("country", "").strip(), row.get("country", "").strip()),
        "role": role,
        "club": row.get("club", "").strip(),
        "club_minutes": int(minutes),
        "regularity": round(regularity, 3),
        "impact_score": round(impact_score, 3),
        "attack": round(attack, 3),
        "defense": round(defense, 3),
        "availability": round(availability, 3),
        "fotmob_rating": round(rating, 2),
        "fotmob_player_id": row.get("fotmob_player_id", "").strip(),
        "source_status": "fotmob-export",
    }


def build_pool(input_path: Path, limit: int, min_minutes: int, min_apps: int) -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    world_cup_teams = {team["country"] for team in data["teams"]}

    with input_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    players = []
    for row in rows:
        country = COUNTRY_ALIASES.get(row.get("country", "").strip(), row.get("country", "").strip())
        row["country"] = country
        if country not in world_cup_teams:
            continue
        if as_int(row, "club_minutes") < min_minutes:
            continue
        if as_int(row, "club_apps") < min_apps:
            continue
        player = score_player(row, min_minutes)
        if player["name"]:
            players.append(player)

    players.sort(key=lambda player: player["impact_score"], reverse=True)
    data["players"] = players[:limit]
    data["meta"]["expected_player_pool"] = limit
    data["meta"]["last_updated"] = datetime.now(timezone.utc).date().isoformat()
    data["meta"]["source"] = "FotMob-derived player export plus current team model"
    data["meta"]["player_pool_rule"] = (
        f"Top {limit} World Cup players with at least {min_minutes} club minutes "
        f"and {min_apps} club appearances, ranked by impact score."
    )
    DATA_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['players'])} players to {DATA_PATH.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--limit", type=int, default=410)
    parser.add_argument("--min-minutes", type=int, default=900)
    parser.add_argument("--min-apps", type=int, default=12)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input CSV not found: {args.input}")

    build_pool(args.input, args.limit, args.min_minutes, args.min_apps)


if __name__ == "__main__":
    main()

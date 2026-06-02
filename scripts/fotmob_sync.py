"""Refresh World Cup data.

FotMob is the preferred source for match stats, lineups, and player context.
Because FotMob does not publish a stable public API contract, this script has a
provider-friendly shape:

- Use approved credentials or a paid API adapter when available.
- Only use unofficial FotMob endpoints when explicitly enabled.
- Keep local sample data intact when live access is unavailable.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "world-cup-2026.json"
FOTMOB_BASE = "https://www.fotmob.com/api"


def fetch_json(url: str, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def load_current_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    data["meta"]["last_updated"] = datetime.now(timezone.utc).date().isoformat()
    DATA_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def sync_with_provider_api(data: dict) -> bool:
    api_url = os.getenv("FOOTBALL_DATA_API_URL")
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_url or not api_key:
        return False

    payload = fetch_json(
        api_url,
        {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "WorldCup2026Analytics/0.1",
        },
    )
    data["raw_provider_payload"] = payload
    data["meta"]["source"] = "approved football data provider"
    return True


def sync_with_unofficial_fotmob(data: dict) -> bool:
    if os.getenv("ALLOW_UNOFFICIAL_FOTMOB") != "1":
        return False

    # League and fixture IDs can change. Set FOTMOB_WORLD_CUP_LEAGUE_ID once
    # verified from FotMob URLs or a maintained ID registry.
    league_id = os.getenv("FOTMOB_WORLD_CUP_LEAGUE_ID", "42")
    url = f"{FOTMOB_BASE}/leagues?id={league_id}&ccode3=USA"
    payload = fetch_json(url, {"User-Agent": "WorldCup2026Analytics/0.1"})
    data["raw_fotmob_payload"] = payload
    data["meta"]["source"] = "unofficial FotMob endpoint"
    return True


def main() -> int:
    data = load_current_data()
    try:
        refreshed = sync_with_provider_api(data) or sync_with_unofficial_fotmob(data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Data refresh failed; keeping existing data: {exc}", file=sys.stderr)
        return 1

    if not refreshed:
        print("No live data credentials configured; keeping sample data.")
        save_data(data)
        return 0

    save_data(data)
    print("Data refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


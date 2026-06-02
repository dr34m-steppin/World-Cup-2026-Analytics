"""Generate model outputs for the World Cup analytics site.

This first version keeps the model intentionally simple and transparent:
team ratings are converted into match probabilities with an Elo-style logistic
curve, then tournament probabilities are normalized from the current rating set.
The interface is ready to be replaced by a richer xG, lineup, and availability
model once live data is connected.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "world-cup-2026.json"


def win_probability(home_rating: float, away_rating: float) -> float:
    return 1 / (1 + 10 ** ((away_rating - home_rating) / 400))


def normalize_title_probabilities(teams: list[dict]) -> None:
    weights = [max(team["rating"] - 1750, 1) ** 1.8 for team in teams]
    total = sum(weights)
    for team, weight in zip(teams, weights):
        title = weight / total
        team["title_probability"] = round(title, 3)
        team["final_probability"] = round(min(title * 1.85, 0.92), 3)
        team["semi_probability"] = round(min(title * 2.9, 0.96), 3)


def update_match_probabilities(data: dict) -> None:
    ratings = {team["country"]: team["rating"] for team in data["teams"]}
    for match in data["matches"]:
        if match["home"] not in ratings or match["away"] not in ratings:
            continue
        raw_home = win_probability(ratings[match["home"]], ratings[match["away"]])
        draw = 0.25 + max(0, 0.08 - abs(raw_home - 0.5) * 0.2)
        decisive = 1 - draw
        match["home_win"] = round(raw_home * decisive, 3)
        match["away_win"] = round((1 - raw_home) * decisive, 3)
        match["draw"] = round(draw, 3)


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    normalize_title_probabilities(data["teams"])
    update_match_probabilities(data)
    DATA_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


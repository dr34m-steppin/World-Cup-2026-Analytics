# World Cup 2026 Analytics

A football analytics site for the 2026 World Cup, focused on tournament predictions, player impact, team analysis, and match intelligence.

## What Is Included

- Tournament prediction dashboard with title probabilities, matchup probabilities, and bracket state.
- Player impact leaderboard with role filters, impact components, and trend signals.
- Team profiles with strengths, weaknesses, and model notes.
- Match analysis cards for previews and post-match writeups.
- A data update pipeline designed for scheduled GitHub Actions refreshes.

## Data Strategy

FotMob is the preferred live data source, but it does not provide a public documented API for broad reuse. The pipeline in `scripts/fotmob_sync.py` supports:

1. A provider API path using `FOTMOB_API_KEY` or another paid/approved data source.
2. A cautious unofficial endpoint path when explicitly enabled with `ALLOW_UNOFFICIAL_FOTMOB=1`.
3. A local sample-data fallback so the site remains deployable while credentials are arranged.

The generated website reads from `data/world-cup-2026.json`.

## Run Locally

This is a static site. Open `index.html` directly, or run a local server:

```powershell
python -m http.server 8000
```

Then visit `http://localhost:8000`.

## Update Data

```powershell
python scripts/fotmob_sync.py
python scripts/model.py
```

## Build The 410-Player Pool

Export FotMob-derived World Cup squad and club-season player data:

```powershell
python scripts/export_fotmob_player_pool.py --delay 0.05 --workers 10
```

Then build the leaderboard:

```powershell
python scripts/build_player_pool.py --limit 410 --min-minutes 900 --min-apps 12
```

This filters for World Cup teams, keeps regular club players, ranks them by the
impact model, and writes the top 410 players to `data/world-cup-2026.json`.

## GitHub Pages

The site is ready for GitHub Pages. Push this repository to:

```text
https://github.com/dr34m-steppin/World-Cup-2026-Analytics
```

Then enable GitHub Pages from the repository settings.

# World Cup 2026 Analytics

A football analytics site for the 2026 World Cup, inspired by the clean intelligence surfaces of STATSWING and impact-model leaderboard products like xGRAPM.

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

## GitHub Pages

The site is ready for GitHub Pages. Push this repository to:

```text
https://github.com/dr34m-steppin/World-Cup-2026-Analytics
```

Then enable GitHub Pages from the repository settings.


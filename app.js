const DATA_URL = "data/world-cup-2026.json";

const percent = (value) => `${Math.round(value * 1000) / 10}%`;

const byProbability = (a, b) => b.title_probability - a.title_probability;
const byImpact = (a, b) => b.impact_score - a.impact_score;

async function loadData() {
  const response = await fetch(DATA_URL);
  if (!response.ok) {
    throw new Error(`Could not load ${DATA_URL}`);
  }
  return response.json();
}

function renderHero(data) {
  document.querySelector("#lastUpdated").textContent = data.meta.last_updated;
  document.querySelector("#trackedMatches").textContent = data.matches.length;
  document.querySelector("#trackedTeams").textContent = data.teams.length;
  document.querySelector("#trackedPlayers").textContent = data.players.length;
  document.querySelector("#modelConfidence").textContent = percent(data.meta.calibration_confidence);

  const topTeams = [...data.teams].sort(byProbability).slice(0, 5);
  document.querySelector("#heroProbabilities").innerHTML = topTeams
    .map(
      (team) => `
        <div class="prob-row">
          <div class="prob-meta">
            <span>${team.country}</span>
            <span>${percent(team.title_probability)}</span>
          </div>
          <div class="bar"><span style="width: ${team.title_probability * 100}%"></span></div>
        </div>
      `,
    )
    .join("");
}

function renderPredictions(data) {
  const rows = [...data.teams].sort(byProbability);
  document.querySelector("#predictionTable").innerHTML = rows
    .map(
      (team, index) => `
        <tr>
          <td>${index + 1}</td>
          <td><strong>${team.country}</strong></td>
          <td>${team.rating}</td>
          <td><span class="pill">${percent(team.title_probability)}</span></td>
          <td>${percent(team.final_probability)}</td>
          <td>${percent(team.semi_probability)}</td>
        </tr>
      `,
    )
    .join("");

  document.querySelector("#bracket").innerHTML = data.bracket_rounds
    .map(
      (round) => `
        <article class="bracket-card">
          <h3>${round.name}</h3>
          ${round.matchups
            .map(
              (matchup) => `
                <div class="match-row">
                  <span>${matchup.home} vs ${matchup.away}</span>
                  <strong>${percent(matchup.home_win)} - ${percent(matchup.away_win)}</strong>
                </div>
              `,
            )
            .join("")}
        </article>
      `,
    )
    .join("");
}

function renderLeaderboard(data) {
  const roleFilter = document.querySelector("#roleFilter");
  const table = document.querySelector("#leaderboardTable");

  const draw = () => {
    const role = roleFilter.value;
    const players = data.players
      .filter((player) => role === "all" || player.role === role)
      .sort(byImpact);

    table.innerHTML = players
      .map(
        (player, index) => `
          <tr>
            <td>${index + 1}</td>
            <td><strong>${player.name}</strong></td>
            <td>${player.country}</td>
            <td>${player.role}</td>
            <td><span class="pill">${player.impact_score.toFixed(2)}</span></td>
            <td>${player.attack.toFixed(2)}</td>
            <td>${player.defense.toFixed(2)}</td>
            <td>${percent(player.availability)}</td>
          </tr>
        `,
      )
      .join("");
  };

  roleFilter.addEventListener("change", draw);
  draw();
}

function renderMatches(data) {
  document.querySelector("#matchGrid").innerHTML = data.matches
    .map(
      (match) => `
        <article class="match-card">
          <p class="card-kicker">${match.stage} · ${match.kickoff_local}</p>
          <h3>${match.home} vs ${match.away}</h3>
          <div class="match-row">
            <span>${match.home}</span>
            <strong>${percent(match.home_win)}</strong>
          </div>
          <div class="match-row">
            <span>Draw</span>
            <strong>${percent(match.draw)}</strong>
          </div>
          <div class="match-row">
            <span>${match.away}</span>
            <strong>${percent(match.away_win)}</strong>
          </div>
          <p class="card-body">${match.analysis}</p>
        </article>
      `,
    )
    .join("");
}

function renderTeams(data) {
  document.querySelector("#teamGrid").innerHTML = [...data.teams]
    .sort(byProbability)
    .slice(0, 9)
    .map(
      (team) => `
        <article class="team-card">
          <p class="card-kicker">Rating ${team.rating} · ${percent(team.title_probability)} title chance</p>
          <h3>${team.country}</h3>
          <p class="card-body">${team.profile}</p>
          <div class="team-tags">
            ${team.tags.map((tag) => `<span class="tag">${tag}</span>`).join("")}
          </div>
        </article>
      `,
    )
    .join("");
}

loadData()
  .then((data) => {
    renderHero(data);
    renderPredictions(data);
    renderLeaderboard(data);
    renderMatches(data);
    renderTeams(data);
  })
  .catch((error) => {
    document.body.insertAdjacentHTML(
      "afterbegin",
      `<div class="error-banner">Data failed to load: ${error.message}</div>`,
    );
  });


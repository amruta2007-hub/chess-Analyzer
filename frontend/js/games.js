/**
 * Chess Analyzer - Games & PGN Upload Module (Decoupled Frontend)
 */

let selectedFile = null;

// Initialize Drag & Drop listeners if on Home page
document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('pgnDropzone');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        processSelectedFile(files[0]);
      }
    });
  }
});

function handleFileSelected(event) {
  const files = event.target.files;
  if (files.length > 0) {
    processSelectedFile(files[0]);
  }
}

function processSelectedFile(file) {
  if (!file.name.toLowerCase().endsWith('.pgn')) {
    ChessUtils.showAlert('homeAlert', 'homeAlertText', 'Please select a valid chess .pgn file.');
    return;
  }
  selectedFile = file;
  const dropText = document.getElementById('dropzoneText');
  const uploadBtn = document.getElementById('btnUploadPGN');
  
  if (dropText) dropText.innerHTML = `Selected: <strong>${escapeHtml(file.name)}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  if (uploadBtn) uploadBtn.disabled = false;
  ChessUtils.hideAlert('homeAlert');
}

// Option A: Handle Chess.com Username Submission
async function handleChesscomSubmit(event) {
  event.preventDefault();
  const input = document.getElementById('chesscomUsername');
  const btn = document.getElementById('btnFetchGames');
  const btnText = document.getElementById('fetchBtnText');
  const username = input.value.trim();

  if (!username) return;

  ChessUtils.hideAlert('homeAlert');
  btn.disabled = true;
  btnText.textContent = 'Fetching Matches...';

  try {
    const url = getApiUrl(`/api/chesscom/${encodeURIComponent(username)}/games`);
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      mode: 'cors'
    });
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to fetch games from Chess.com.');
    }

    // Cache results in sessionStorage and redirect to games selection
    sessionStorage.setItem('chess_games_data', JSON.stringify({
      source: 'chesscom',
      player: data.player,
      games: data.games
    }));

    window.location.href = 'games.html';

  } catch (err) {
    ChessUtils.showAlert('homeAlert', 'homeAlertText', err.message);
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Fetch Latest 20 Games';
  }
}

// Option B: Handle PGN Upload Submission
async function handlePGNUpload() {
  if (!selectedFile) return;

  const btn = document.getElementById('btnUploadPGN');
  const btnText = document.getElementById('uploadBtnText');
  ChessUtils.hideAlert('homeAlert');

  btn.disabled = true;
  btnText.textContent = 'Parsing PGN...';

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const url = getApiUrl('/api/pgn/upload');
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      mode: 'cors'
    });
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to parse PGN file.');
    }

    if (data.games_count === 1) {
      // Direct jump to analysis if single game
      const singleGame = data.games[0];
      sessionStorage.setItem('selected_game_pgn', singleGame.pgn);
      sessionStorage.setItem('selected_game_meta', JSON.stringify(singleGame));
      window.location.href = 'analysis.html';
    } else {
      // Multi-game selection screen
      sessionStorage.setItem('chess_games_data', JSON.stringify({
        source: 'pgn',
        player: { username: selectedFile.name, name: `${data.games_count} Games Archive` },
        games: data.games
      }));
      window.location.href = 'games.html';
    }

  } catch (err) {
    ChessUtils.showAlert('homeAlert', 'homeAlertText', err.message);
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Analyze Game';
  }
}

// Render Games Grid in games.html View
function loadGamesView() {
  const grid = document.getElementById('gamesGrid');
  const empty = document.getElementById('gamesEmpty');
  const metaCard = document.getElementById('playerMetaCard');
  if (!grid) return;

  const rawData = sessionStorage.getItem('chess_games_data');
  if (!rawData) {
    if (empty) empty.style.display = 'block';
    return;
  }

  const parsed = JSON.parse(rawData);
  const games = parsed.games || [];
  const player = parsed.player || {};

  if (player && (player.username || player.name)) {
    if (metaCard) metaCard.style.display = 'flex';
    const nameEl = document.getElementById('playerNameDisplay');
    const subEl = document.getElementById('playerSubDisplay');
    const avatarEl = document.getElementById('playerAvatar');

    if (nameEl) nameEl.textContent = player.name || player.username;
    if (subEl) subEl.textContent = `@${player.username} • ${games.length} Games Available`;
    if (avatarEl && player.avatar) avatarEl.src = player.avatar;
  }

  if (games.length === 0) {
    if (empty) empty.style.display = 'block';
    return;
  }

  grid.innerHTML = '';
  games.forEach((game, idx) => {
    const card = document.createElement('div');
    card.className = 'game-card';

    const whiteName = game.white ? game.white.username : 'White';
    const whiteElo = game.white ? game.white.rating : '?';
    const blackName = game.black ? game.black.username : 'Black';
    const blackElo = game.black ? game.black.rating : '?';

    const timeClass = (game.time_class || 'standard').toLowerCase();
    const resultText = game.outcome || game.result || '*';
    let outcomeClass = 'result-draw';
    if (resultText === 'Win' || resultText === '1-0') outcomeClass = 'result-win';
    if (resultText === 'Loss' || resultText === '0-1') outcomeClass = 'result-loss';

    card.innerHTML = `
      <div>
        <div class="game-meta-top">
          <span class="game-badge ${timeClass}">${game.time_class || game.time_control || 'Chess'}</span>
          <span>${game.date || 'Recent Match'}</span>
        </div>

        <div style="margin-bottom: 1.25rem;">
          <div class="matchup-row">
            <div class="player-label">
              <span class="color-dot white"></span>
              <span>${escapeHtml(whiteName)}</span>
              <span class="player-rating">(${whiteElo})</span>
            </div>
          </div>
          <div class="matchup-row">
            <div class="player-label">
              <span class="color-dot black"></span>
              <span>${escapeHtml(blackName)}</span>
              <span class="player-rating">(${blackElo})</span>
            </div>
            <span class="result-tag ${outcomeClass}">${resultText}</span>
          </div>
        </div>
      </div>

      <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="selectGameForAnalysis(${idx})">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        Analyze Game
      </button>
    `;

    grid.appendChild(card);
  });
}

function selectGameForAnalysis(index) {
  const rawData = sessionStorage.getItem('chess_games_data');
  if (!rawData) return;

  const parsed = JSON.parse(rawData);
  const selected = parsed.games[index];
  if (!selected) return;

  sessionStorage.setItem('selected_game_pgn', selected.pgn);
  sessionStorage.setItem('selected_game_meta', JSON.stringify(selected));
  window.location.href = 'analysis.html';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

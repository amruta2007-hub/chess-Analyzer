/**
 * Chess Analyzer - Interactive Analysis Workspace Module (Decoupled Frontend)
 */

let board = null;
let game = null;
let movesData = [];
let analysisResult = null;
let currentMoveIndex = -1; // -1 represents initial position
let isAutoPlaying = false;
let autoPlayTimer = null;
let boardOrientation = 'white';

const DEFAULT_DEMO_PGN = `[Event "Opera Game"]
[Site "Paris FRA"]
[Date "1858.11.02"]
[White "Paul Morphy"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0`;

document.addEventListener('DOMContentLoaded', () => {
  initWorkspace();
});

function initWorkspace() {
  game = new Chess();

  // Retrieve selected game PGN or fallback to Opera game demo
  let pgnText = sessionStorage.getItem('selected_game_pgn');
  if (!pgnText || !pgnText.trim()) {
    pgnText = DEFAULT_DEMO_PGN;
    sessionStorage.setItem('selected_game_pgn', pgnText);
  }

  // Parse PGN headers and moves using client-side chess.js
  const loaded = game.load_pgn(pgnText);
  if (!loaded) {
    console.error("Failed to load PGN into chess.js, using default demo.");
    game.load_pgn(DEFAULT_DEMO_PGN);
  }

  // Extract game headers for display
  const headers = game.header();
  updateHeaderDisplay(headers);

  // Extract all mainline moves with their FEN positions
  extractMainlineMoves();

  // Initialize Chessboard.js with relative piece theme path
  const boardConfig = {
    draggable: false,
    position: 'start',
    orientation: 'white',
    pieceTheme: 'img/chesspieces/wikipedia/{piece}.png'
  };

  board = Chessboard('chessBoard', boardConfig);
  $(window).resize(board.resize);

  // Bind controls
  document.getElementById('btnFirstMove').addEventListener('click', () => goToMove(-1));
  document.getElementById('btnPrevMove').addEventListener('click', () => goToMove(currentMoveIndex - 1));
  document.getElementById('btnNextMove').addEventListener('click', () => goToMove(currentMoveIndex + 1));
  document.getElementById('btnLastMove').addEventListener('click', () => goToMove(movesData.length - 1));
  document.getElementById('btnPlayPause').addEventListener('click', toggleAutoPlay);
  document.getElementById('btnFlipBoard').addEventListener('click', flipBoard);

  // Bind keyboard navigation
  document.addEventListener('keydown', handleKeyNavigation);

  // Populate initial move history list
  renderMoveList();

  // Start Stockfish Analysis via backend API
  startEngineAnalysis(pgnText);
}

function updateHeaderDisplay(headers) {
  const whiteEl = document.getElementById('whitePlayerLabel');
  const blackEl = document.getElementById('blackPlayerLabel');
  const metaEl = document.getElementById('gameMetaSub');

  const whiteName = headers['White'] || 'White';
  const blackName = headers['Black'] || 'Black';
  const whiteElo = headers['WhiteElo'] ? ` (${headers['WhiteElo']})` : '';
  const blackElo = headers['BlackElo'] ? ` (${headers['BlackElo']})` : '';

  if (whiteEl) whiteEl.textContent = `${whiteName}${whiteElo}`;
  if (blackEl) blackEl.textContent = `${blackName}${blackElo}`;

  const eventName = headers['Event'] || 'Chess Game';
  const dateStr = headers['Date'] || '';
  const resultStr = headers['Result'] || '*';

  if (metaEl) {
    metaEl.textContent = `${eventName} • ${dateStr} • Result: ${resultStr}`;
  }
}

function extractMainlineMoves() {
  movesData = [];
  const history = game.history({ verbose: true });
  
  // Re-run moves to get FENs
  const tempGame = new Chess();
  history.forEach((m, idx) => {
    const fenBefore = tempGame.fen();
    tempGame.move(m);
    const fenAfter = tempGame.fen();

    movesData.push({
      index: idx,
      moveNumber: Math.floor(idx / 2) + 1,
      color: m.color === 'w' ? 'white' : 'black',
      san: m.san,
      from: m.from,
      to: m.to,
      fenBefore: fenBefore,
      fenAfter: fenAfter,
      evalDisplay: '0.0',
      evalLoss: 0,
      classification: null,
      badge: '',
      explanation: 'Analysis in progress...'
    });
  });

  const countSummary = document.getElementById('moveCountSummary');
  if (countSummary) countSummary.textContent = `${movesData.length} moves`;
}

function renderMoveList() {
  const container = document.getElementById('moveHistoryScroll');
  if (!container) return;

  container.innerHTML = '';
  const totalMoves = movesData.length;

  for (let i = 0; i < totalMoves; i += 2) {
    const moveNum = Math.floor(i / 2) + 1;
    const whiteMove = movesData[i];
    const blackMove = (i + 1 < totalMoves) ? movesData[i + 1] : null;

    const row = document.createElement('div');
    row.className = 'move-row';
    row.id = `moveRow-${moveNum}`;

    let whiteBadgeHtml = whiteMove.badge ? `<span style="font-weight: 700; font-size: 0.75rem; color: var(--color-${(whiteMove.classification || 'good').toLowerCase()});">${whiteMove.badge}</span>` : '';
    let blackBadgeHtml = (blackMove && blackMove.badge) ? `<span style="font-weight: 700; font-size: 0.75rem; color: var(--color-${(blackMove.classification || 'good').toLowerCase()});">${blackMove.badge}</span>` : '';

    row.innerHTML = `
      <div class="move-num">${moveNum}.</div>
      <div class="move-item ${currentMoveIndex === i ? 'selected' : ''}" id="moveBtn-${i}" onclick="goToMove(${i})">
        <span>${escapeHtml(whiteMove.san)}</span>
        ${whiteBadgeHtml}
      </div>
      <div class="move-item ${currentMoveIndex === i + 1 ? 'selected' : ''}" id="moveBtn-${i + 1}" ${blackMove ? `onclick="goToMove(${i + 1})"` : ''}>
        ${blackMove ? `<span>${escapeHtml(blackMove.san)}</span> ${blackBadgeHtml}` : ''}
      </div>
    `;

    container.appendChild(row);
  }
}

function goToMove(index) {
  if (index < -1) index = -1;
  if (index >= movesData.length) index = movesData.length - 1;

  currentMoveIndex = index;

  if (index === -1) {
    board.position('start');
    removeSquareHighlights();
    updateMoveIndicator("Start Position");
    updateEvaluationUI(0.0, "0.0", "Book Move", "Starting position. All pieces in standard setup.", "-", "-");
  } else {
    const move = movesData[index];
    board.position(move.fenAfter);
    highlightSquares(move.from, move.to);
    updateMoveIndicator(`${move.moveNumber}. ${move.color === 'white' ? move.san : '... ' + move.san}`);

    // Update insight panel
    const analysisInfo = (analysisResult && analysisResult.moves && analysisResult.moves[index])
      ? analysisResult.moves[index]
      : move;

    updateEvaluationUI(
      analysisInfo.score_white_cp || 0,
      analysisInfo.eval_after || analysisInfo.evalDisplay || "0.0",
      analysisInfo.classification || "In Play",
      analysisInfo.explanation || "Evaluating move...",
      analysisInfo.best_move_san || "-",
      (analysisInfo.continuation || []).join(' ') || "-"
    );
  }

  // Update selected class in move list
  $('.move-item').removeClass('selected');
  if (index >= 0) {
    $(`#moveBtn-${index}`).addClass('selected');
    // Scroll row into view
    const row = document.getElementById(`moveRow-${Math.floor(index / 2) + 1}`);
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

function highlightSquares(from, to) {
  removeSquareHighlights();
  $(`#chessBoard .square-${from}`).css('background-color', 'rgba(16, 185, 129, 0.45)');
  $(`#chessBoard .square-${to}`).css('background-color', 'rgba(16, 185, 129, 0.55)');
}

function removeSquareHighlights() {
  $('#chessBoard .square-55d63').css('background-color', '');
}

function updateMoveIndicator(text) {
  const el = document.getElementById('currentMoveIndicator');
  if (el) el.textContent = text;
}

function updateEvaluationUI(scoreCp, displayEval, classification, explanation, bestMove, continuation) {
  // Update eval display badge
  const evalEl = document.getElementById('moveEvalDisplay');
  if (evalEl) evalEl.textContent = displayEval;

  // Update classification badge
  const badgeContainer = document.getElementById('moveBadgeContainer');
  const classKey = (classification || 'good').toLowerCase();
  if (badgeContainer) {
    badgeContainer.innerHTML = `<span class="badge-classification badge-${classKey}">${escapeHtml(classification)}</span>`;
  }

  // Update recommendation box
  const recMove = document.getElementById('recMoveName');
  const recCont = document.getElementById('recContinuation');
  if (recMove) recMove.textContent = bestMove || '-';
  if (recCont) recCont.textContent = continuation || '-';

  // Update explanation
  const expEl = document.getElementById('moveExplanation');
  if (expEl) expEl.textContent = explanation;

  // Update dynamic vertical evaluation bar
  updateEvalBar(scoreCp, displayEval);
}

function updateEvalBar(scoreCp, displayEval) {
  const whiteBar = document.getElementById('evalBarWhite');
  const blackBar = document.getElementById('evalBarBlack');
  const textEl = document.getElementById('evalBarText');

  if (!whiteBar || !blackBar || !textEl) return;

  textEl.textContent = displayEval;

  // Convert centipawns to percentage (clamped to [-800, +800] cp for bar height)
  let whitePct = 50;
  if (displayEval.includes('M')) {
    // Mate score
    whitePct = displayEval.startsWith('-') ? 2 : 98;
  } else {
    const cp = Math.max(-800, Math.min(800, scoreCp));
    whitePct = 50 + (cp / 800) * 45;
    whitePct = Math.max(4, Math.min(96, whitePct));
  }

  let blackPct = 100 - whitePct;

  if (boardOrientation === 'black') {
    whiteBar.style.height = `${blackPct}%`;
    blackBar.style.height = `${whitePct}%`;
  } else {
    whiteBar.style.height = `${whitePct}%`;
    blackBar.style.height = `${blackPct}%`;
  }
}

function flipBoard() {
  boardOrientation = (boardOrientation === 'white') ? 'black' : 'white';
  board.orientation(boardOrientation);
  if (currentMoveIndex === -1) {
    updateEvalBar(0, "0.0");
  } else if (movesData[currentMoveIndex]) {
    const move = movesData[currentMoveIndex];
    updateEvalBar(move.score_white_cp || 0, move.eval_after || "0.0");
  }
}

function toggleAutoPlay() {
  const btn = document.getElementById('btnPlayPause');
  const playIcon = document.getElementById('playIcon');

  if (isAutoPlaying) {
    clearInterval(autoPlayTimer);
    isAutoPlaying = false;
    if (playIcon) playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
  } else {
    isAutoPlaying = true;
    if (playIcon) playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
    
    autoPlayTimer = setInterval(() => {
      if (currentMoveIndex < movesData.length - 1) {
        goToMove(currentMoveIndex + 1);
      } else {
        toggleAutoPlay();
      }
    }, 1200);
  }
}

function handleKeyNavigation(e) {
  if (['input', 'textarea'].includes(document.activeElement.tagName.toLowerCase())) return;

  if (e.key === 'ArrowLeft') {
    e.preventDefault();
    goToMove(currentMoveIndex - 1);
  } else if (e.key === 'ArrowRight') {
    e.preventDefault();
    goToMove(currentMoveIndex + 1);
  } else if (e.key === 'Home') {
    e.preventDefault();
    goToMove(-1);
  } else if (e.key === 'End') {
    e.preventDefault();
    goToMove(movesData.length - 1);
  } else if (e.key === ' ' || e.code === 'Space') {
    e.preventDefault();
    toggleAutoPlay();
  } else if (e.key === 'f' || e.key === 'F') {
    e.preventDefault();
    flipBoard();
  }
}

// Stockfish Engine Polling & Background Task
async function startEngineAnalysis(pgnText) {
  const progressBar = document.getElementById('analysisProgressBar');
  const progressText = document.getElementById('analysisProgressText');
  const statusNote = document.getElementById('engineStatusNote');
  const btnReport = document.getElementById('btnViewReport');

  try {
    const url = getApiUrl('/api/analyze');
    const response = await fetch(url, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ pgn: pgnText, depth: 12 }),
      mode: 'cors'
    });
    const data = await response.json();

    if (!response.ok || !data.success) {
      if (data.stockfish_missing) {
        if (statusNote) statusNote.innerHTML = '<span style="color: #fbbf24;">⚠️ Stockfish binary missing on backend. See setup guide.</span>';
      }
      throw new Error(data.error || 'Failed to start engine analysis.');
    }

    const analysisId = data.analysis_id;
    if (statusNote) statusNote.textContent = 'Stockfish analyzing moves with deep search...';

    // Poll for completion
    const pollInterval = setInterval(async () => {
      try {
        const pollUrl = getApiUrl(`/api/analyze/result/${analysisId}`);
        const pollResp = await fetch(pollUrl, {
          method: 'GET',
          headers: { 'Accept': 'application/json' },
          mode: 'cors'
        });
        const pollData = await pollResp.json();

        if (pollData.success) {
          const progress = pollData.progress || 0;
          if (progressBar) progressBar.style.width = `${progress}%`;
          if (progressText) progressText.textContent = `${progress}% (${pollData.current_move}/${pollData.total_moves})`;

          if (pollData.status === 'completed' && pollData.result) {
            clearInterval(pollInterval);
            analysisResult = pollData.result;
            sessionStorage.setItem('full_analysis_report', JSON.stringify(analysisResult));

            // Merge analysis classifications into local movesData
            if (analysisResult.moves) {
              analysisResult.moves.forEach((am, idx) => {
                if (movesData[idx]) {
                  movesData[idx].classification = am.classification;
                  movesData[idx].badge = am.badge;
                  movesData[idx].evalDisplay = am.eval_after;
                  movesData[idx].score_white_cp = am.score_white_cp;
                  movesData[idx].best_move_san = am.best_move_san;
                  movesData[idx].continuation = am.continuation;
                  movesData[idx].explanation = am.explanation;
                }
              });
            }

            // Re-render move list with classification badges
            renderMoveList();

            if (statusNote) statusNote.innerHTML = '<span style="color: var(--primary);">✓ Analysis Completed!</span>';
            if (btnReport) btnReport.style.display = 'inline-flex';

            // Refresh current move view
            if (currentMoveIndex >= 0) {
              goToMove(currentMoveIndex);
            }
          } else if (pollData.status === 'error') {
            clearInterval(pollInterval);
            if (statusNote) statusNote.innerHTML = `<span style="color: var(--color-blunder);">${escapeHtml(pollData.error)}</span>`;
          }
        }
      } catch (pollErr) {
        console.error("Polling error:", pollErr);
      }
    }, 700);

  } catch (err) {
    if (statusNote) statusNote.innerHTML = `<span style="color: var(--color-blunder);">${escapeHtml(err.message)}</span>`;
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

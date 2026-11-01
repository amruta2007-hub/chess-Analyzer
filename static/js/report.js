/**
 * Chess Analyzer - Game Report & Chart Visualization Module
 */

document.addEventListener('DOMContentLoaded', () => {
  renderReportView();
});

let evalChartInstance = null;

function renderReportView() {
  const rawReport = sessionStorage.getItem('full_analysis_report');
  if (!rawReport) {
    document.querySelector('.report-container').innerHTML = `
      <div class="card" style="text-align: center; padding: 4rem 2rem;">
        <h3>No Analysis Report Found</h3>
        <p style="color: var(--text-muted); margin: 0.75rem 0 1.5rem;">
          Please select and analyze a game first to view the complete performance report.
        </p>
        <a href="/analysis" class="btn btn-primary">Go to Analysis Workspace</a>
      </div>
    `;
    return;
  }

  const analysis = JSON.parse(rawReport);
  const headers = analysis.headers || {};
  const report = analysis.report || {};
  const evalHistory = analysis.eval_history || [];

  // Populate Player Header info
  const whiteUser = headers['White'] || 'White';
  const blackUser = headers['Black'] || 'Black';
  const whiteElo = headers['WhiteElo'] ? `(${headers['WhiteElo']})` : '';
  const blackElo = headers['BlackElo'] ? `(${headers['BlackElo']})` : '';

  document.getElementById('reportWhiteUser').textContent = `${whiteUser} ${whiteElo}`;
  document.getElementById('reportBlackUser').textContent = `${blackUser} ${blackElo}`;
  document.getElementById('reportSubHeader').textContent = `${headers['Event'] || 'Match'} • ${headers['Date'] || ''} • Result: ${headers['Result'] || '*'}`;

  // Populate Accuracies & ACPL
  document.getElementById('reportWhiteAcc').textContent = `${report.white_accuracy || 0}%`;
  document.getElementById('reportBlackAcc').textContent = `${report.black_accuracy || 0}%`;
  document.getElementById('reportWhiteAcpl').textContent = `${report.acpl_white || 0}`;
  document.getElementById('reportBlackAcpl').textContent = `${report.acpl_black || 0}`;

  // Render Evaluation Chart
  renderEvaluationChart(evalHistory);

  // Render Move Classification Table
  renderClassificationTable(report.white_stats || {}, report.black_stats || {});

  // Render Critical Moments
  renderCriticalMoments(report.critical_moments || []);

  // Render Pedagogical Takeaways
  renderTakeaways(report.key_takeaways || []);
}

function renderEvaluationChart(evalHistory) {
  const canvas = document.getElementById('evalChart');
  if (!canvas || !evalHistory || evalHistory.length === 0) return;

  const labels = evalHistory.map(h => h.label);
  const scores = evalHistory.map(h => h.capped_score);
  
  // Custom point background color depending on move classification
  const pointColors = evalHistory.map(h => {
    const cls = (h.classification || '').toLowerCase();
    if (cls === 'blunder') return '#ef4444';
    if (cls === 'mistake') return '#f97316';
    if (cls === 'brilliant') return '#06b6d4';
    if (cls === 'inaccuracy') return '#eab308';
    return '#10b981';
  });

  const pointRadii = evalHistory.map(h => {
    const cls = (h.classification || '').toLowerCase();
    if (cls === 'blunder' || cls === 'brilliant') return 6;
    if (cls === 'mistake') return 5;
    return 2;
  });

  const ctx = canvas.getContext('2d');
  
  // Create gradient fill for chart
  const gradient = ctx.createLinearGradient(0, 0, 0, 320);
  gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
  gradient.addColorStop(0.5, 'rgba(16, 185, 129, 0.05)');
  gradient.addColorStop(1, 'rgba(239, 68, 68, 0.2)');

  evalChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Evaluation (Pawns)',
        data: scores,
        borderColor: '#10b981',
        borderWidth: 2,
        backgroundColor: gradient,
        fill: true,
        tension: 0.25,
        pointBackgroundColor: pointColors,
        pointBorderColor: '#0f1218',
        pointBorderWidth: 1.5,
        pointRadius: pointRadii,
        pointHoverRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#181d26',
          titleColor: '#f8fafc',
          bodyColor: '#94a3b8',
          borderColor: '#262e3d',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: function(context) {
              const item = evalHistory[context.dataIndex];
              const score = item.display_eval;
              const cls = item.classification ? ` [${item.classification}]` : '';
              return `Eval: ${score}${cls}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', maxTicksLimit: 15 }
        },
        y: {
          min: -8,
          max: 8,
          grid: { color: 'rgba(255, 255, 255, 0.07)' },
          ticks: {
            color: '#64748b',
            callback: function(val) {
              if (val > 0) return `+${val}`;
              return val;
            }
          }
        }
      }
    }
  });
}

function renderClassificationTable(whiteStats, blackStats) {
  const tbody = document.getElementById('qualityTableBody');
  if (!tbody) return;

  const categories = [
    { name: 'Brilliant', badge: '!!', classKey: 'brilliant', impact: 'Tactical sacrifice finding decisive blows' },
    { name: 'Best', badge: '★', classKey: 'best', impact: 'Top engine choice (loss ≤ 12 cp)' },
    { name: 'Excellent', badge: '✓', classKey: 'excellent', impact: 'Strong move preserving core advantage' },
    { name: 'Good', badge: '●', classKey: 'good', impact: 'Solid practical continuation' },
    { name: 'Inaccuracy', badge: '?!', classKey: 'inaccuracy', impact: 'Sub-optimal move, slight initiative loss' },
    { name: 'Mistake', badge: '?', classKey: 'mistake', impact: 'Noticeable error compromising position' },
    { name: 'Blunder', badge: '??', classKey: 'blunder', impact: 'Decisive tactical or material disaster' }
  ];

  tbody.innerHTML = '';
  categories.forEach(cat => {
    const wCount = whiteStats[cat.name] || 0;
    const bCount = blackStats[cat.name] || 0;

    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid rgba(255, 255, 255, 0.04)';
    tr.innerHTML = `
      <td style="padding: 0.75rem 1rem;">
        <span class="badge-classification badge-${cat.classKey}">
          ${cat.badge} ${cat.name}
        </span>
      </td>
      <td style="padding: 0.75rem 1rem; font-weight: 700; color: #ffffff;">
        ${wCount}
      </td>
      <td style="padding: 0.75rem 1rem; font-weight: 700; color: var(--primary-light);">
        ${bCount}
      </td>
      <td style="padding: 0.75rem 1rem; color: var(--text-muted); font-size: 0.85rem;">
        ${cat.impact}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCriticalMoments(moments) {
  const list = document.getElementById('criticalMomentsList');
  if (!list) return;

  if (moments.length === 0) {
    list.innerHTML = `
      <div style="color: var(--text-dim); text-align: center; padding: 1.5rem;">
        No major blunders or decisive tactical turnarounds occurred.
      </div>
    `;
    return;
  }

  list.innerHTML = '';
  moments.forEach(m => {
    const card = document.createElement('div');
    const classKey = (m.classification || 'blunder').toLowerCase();
    card.className = `moment-card moment-${classKey}`;

    card.innerHTML = `
      <div style="flex: 1;">
        <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.35rem;">
          <span style="font-weight: 700; font-size: 0.95rem;">Move ${m.move_number} • ${m.player}</span>
          <span class="badge-classification badge-${classKey}">${m.classification}</span>
        </div>
        <div style="font-size: 0.9rem; color: var(--text-main); margin-bottom: 0.25rem;">
          Played: <strong>${escapeHtml(m.played_move)}</strong> &nbsp;|&nbsp; 
          Engine Preference: <strong style="color: var(--primary-light);">${escapeHtml(m.best_move)}</strong>
        </div>
        <div style="font-size: 0.83rem; color: var(--text-muted);">
          ${escapeHtml(m.explanation)}
        </div>
      </div>

      <div style="text-align: right; min-width: 110px;">
        <div style="font-size: 0.8rem; color: var(--text-dim);">Eval Swing</div>
        <div style="font-weight: 800; font-size: 1.1rem; color: var(--color-${classKey});">
          ${m.eval_loss_pawns > 0 ? `-${m.eval_loss_pawns} pawns` : 'Decisive'}
        </div>
        <div style="font-size: 0.75rem; color: var(--text-dim);">
          ${m.eval_before} &rarr; ${m.eval_after}
        </div>
      </div>
    `;
    list.appendChild(card);
  });
}

function renderTakeaways(takeaways) {
  const list = document.getElementById('learningPointsList');
  if (!list) return;

  list.innerHTML = '';
  takeaways.forEach(point => {
    const div = document.createElement('div');
    div.style.padding = '0.75rem 1rem';
    div.style.backgroundColor = 'var(--bg-input)';
    div.style.borderRadius = 'var(--radius-md)';
    div.style.borderLeft = '3px solid var(--primary)';
    div.innerHTML = point.replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--text-main);">$1</strong>');
    list.appendChild(div);
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

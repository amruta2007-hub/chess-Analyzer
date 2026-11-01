/**
 * Chess Analyzer - Global Helper Utilities & Server Connection Status
 */

const ChessUtils = {
  // Show error or success alert banner
  showAlert: function(elementId, textId, message, type = 'danger') {
    const el = document.getElementById(elementId);
    const textEl = document.getElementById(textId);
    if (!el || !textEl) return;

    el.className = `alert alert-${type}`;
    textEl.textContent = message;
    el.style.display = 'flex';

    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  },

  hideAlert: function(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = 'none';
  },

  formatDate: function(dateStr) {
    if (!dateStr || dateStr.includes('????')) return 'Casual Game';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  }
};

// Check backend connectivity on page load
document.addEventListener('DOMContentLoaded', () => {
  initBackendStatusCheck();
});

async function initBackendStatusCheck() {
  const badge = document.getElementById('backendStatusBadge');
  if (!badge) return;

  const result = await ChessConfig.testConnection();
  if (result.ok) {
    badge.className = 'status-badge connected';
    badge.innerHTML = `<span class="status-dot"></span> API Connected`;
    badge.title = `Backend active at: ${ChessConfig.getApiBaseUrl() || window.location.origin} (${result.latency}ms)`;
    
    // Check if Stockfish is ready
    if (result.data && result.data.stockfish && !result.data.stockfish.available) {
      const banner = document.getElementById('globalStockfishBanner');
      if (banner) banner.style.display = 'flex';
    }
  } else {
    badge.className = 'status-badge disconnected';
    badge.innerHTML = `<span class="status-dot"></span> Backend Offline`;
    badge.title = `Failed to connect to backend: ${result.error}`;
  }
}

function openBackendSettingsModal() {
  const modal = document.getElementById('backendConfigModal');
  const input = document.getElementById('modalApiBaseUrlInput');
  const status = document.getElementById('modalBackendTestResult');
  if (modal) {
    if (input) input.value = ChessConfig.getApiBaseUrl();
    if (status) status.innerHTML = '';
    modal.style.display = 'flex';
  }
}

function closeBackendSettingsModal() {
  const modal = document.getElementById('backendConfigModal');
  if (modal) modal.style.display = 'none';
}

async function testBackendModalConnection() {
  const input = document.getElementById('modalApiBaseUrlInput');
  const status = document.getElementById('modalBackendTestResult');
  const testUrl = input.value.trim().replace(/\/+$/, '');

  status.innerHTML = '<span style="color: var(--text-dim);">Pinging backend /api/health...</span>';

  const prev = localStorage.getItem('API_BASE_URL');
  if (testUrl) {
    localStorage.setItem('API_BASE_URL', testUrl);
  } else {
    localStorage.removeItem('API_BASE_URL');
  }

  const result = await ChessConfig.testConnection();
  if (result.ok) {
    status.innerHTML = `<span style="color: var(--primary);">✓ Connected! Latency: ${result.latency}ms. Stockfish: ${result.data.stockfish?.available ? 'Ready' : 'Not installed'}</span>`;
  } else {
    status.innerHTML = `<span style="color: var(--color-blunder);">✗ Connection failed: ${result.error}. Ensure Render service is running and CORS is enabled.</span>`;
    // Restore
    if (prev) localStorage.setItem('API_BASE_URL', prev);
    else localStorage.removeItem('API_BASE_URL');
  }
}

function saveBackendModalSettings() {
  const input = document.getElementById('modalApiBaseUrlInput');
  const newUrl = input.value.trim();
  ChessConfig.setApiBaseUrl(newUrl);
  closeBackendSettingsModal();
  initBackendStatusCheck();
}

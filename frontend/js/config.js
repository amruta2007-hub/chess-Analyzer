/**
 * Chess Analyzer - Frontend Configuration & API Base URL Management
 */

const ChessConfig = {
  /**
   * Determine the effective backend API base URL using multi-tier resolution:
   * 1. Netlify injected build environment variable (window.ENV.API_BASE_URL)
   * 2. Browser localStorage override (localStorage.getItem('API_BASE_URL'))
   * 3. Fallback: current origin or relative path for local development
   */
  getApiBaseUrl: function() {
    // Check localStorage override first (allows testing different backends in browser)
    const localOverride = localStorage.getItem('API_BASE_URL');
    if (localOverride && localOverride.trim()) {
      return localOverride.trim().replace(/\/+$/, '');
    }

    // Check environment variable injected at Netlify build time
    if (typeof window !== 'undefined' && window.ENV && window.ENV.API_BASE_URL) {
      const envUrl = window.ENV.API_BASE_URL.trim();
      if (envUrl) {
        return envUrl.replace(/\/+$/, '');
      }
    }

    // Fallback: empty string for relative paths
    return '';
  },

  /**
   * Resolve an API endpoint path against the configured base URL.
   * Example: getApiUrl('/api/analyze') -> 'https://chess-api.onrender.com/api/analyze'
   */
  getApiUrl: function(endpoint) {
    const base = this.getApiBaseUrl();
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    if (!base) {
      return cleanEndpoint;
    }
    return `${base}${cleanEndpoint}`;
  },

  /**
   * Set custom API Base URL in localStorage.
   */
  setApiBaseUrl: function(url) {
    if (!url || !url.trim()) {
      localStorage.removeItem('API_BASE_URL');
    } else {
      localStorage.setItem('API_BASE_URL', url.trim().replace(/\/+$/, ''));
    }
  },

  /**
   * Test backend API connectivity and retrieve Stockfish health status.
   */
  testConnection: async function() {
    const targetUrl = this.getApiUrl('/api/health');
    const startTime = performance.now();
    try {
      const response = await fetch(targetUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        mode: 'cors'
      });
      const latency = Math.round(performance.now() - startTime);
      if (!response.ok) {
        return { ok: false, status: response.status, error: `HTTP ${response.status}`, latency };
      }
      const data = await response.json();
      return { ok: true, data, latency };
    } catch (err) {
      return { ok: false, error: err.message, latency: Math.round(performance.now() - startTime) };
    }
  }
};

// Global shorthand for convenience
function getApiUrl(endpoint) {
  return ChessConfig.getApiUrl(endpoint);
}

/**
 * Chess Analyzer - Global Helper Utilities
 */

const ChessUtils = {
  // Show error or success toast/alert
  showAlert: function(elementId, textId, message, type = 'danger') {
    const el = document.getElementById(elementId);
    const textEl = document.getElementById(textId);
    if (!el || !textEl) return;

    el.className = `alert alert-${type}`;
    textEl.textContent = message;
    el.style.display = 'flex';

    // Auto scroll into view
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  },

  hideAlert: function(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = 'none';
  },

  // Format date helper
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

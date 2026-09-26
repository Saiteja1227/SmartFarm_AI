/**
 * SmartFarm AI — API helpers
 * Manages the anonymous user ID and all /api/* calls.
 */
(function (window) {
  'use strict';

  const USER_ID_KEY = 'smartfarm.userId';

  function genUserId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'uid-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function getOrCreateUserId() {
    try {
      let id = localStorage.getItem(USER_ID_KEY);
      if (!id) { id = genUserId(); localStorage.setItem(USER_ID_KEY, id); }
      return id;
    } catch (e) {
      if (!window.__sfUserId) window.__sfUserId = genUserId();
      return window.__sfUserId;
    }
  }

  async function apiFetch(path, options = {}) {
    const headers = Object.assign({ 'X-User-Id': getOrCreateUserId() }, options.headers || {});
    const res = await fetch('/api' + path, Object.assign({}, options, { headers }));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || data.message || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  async function analyzeLeaf(file, cropName, language) {
    const fd = new FormData();
    fd.append('image', file);
    if (cropName && cropName.trim()) fd.append('crop_name', cropName.trim());
    fd.append('language', language || 'en');
    return apiFetch('/analyze', { method: 'POST', body: fd });
  }

  async function fetchHistory() {
    return apiFetch('/history');
  }

  async function fetchScan(id) {
    return apiFetch('/scan/' + id);
  }

  async function deleteScan(id) {
    return apiFetch('/scan/' + id, { method: 'DELETE' });
  }

  async function fetchStats() {
    return apiFetch('/stats');
  }

  // Expose
  window.sfApi = { getOrCreateUserId, analyzeLeaf, fetchHistory, fetchScan, deleteScan, fetchStats };
  // Initialise user ID on load
  window.addEventListener('DOMContentLoaded', () => getOrCreateUserId());

})(window);

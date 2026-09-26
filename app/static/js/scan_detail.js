/**
 * SmartFarm AI — Scan detail page
 * Expects window.SCAN_ID to be set by the template.
 */
(function (window) {
  'use strict';

  async function loadScan() {
    const id = window.SCAN_ID;
    if (!id) return;
    try {
      const scan = await window.sfApi.fetchScan(id);
      document.getElementById('detail-loading').classList.add('d-none');
      const container = document.getElementById('report-container');
      container.classList.remove('d-none');
      window.sfReport.renderReport(scan, 'report-container', null);
    } catch (err) {
      document.getElementById('detail-loading').classList.add('d-none');
      document.getElementById('detail-error').classList.remove('d-none');
    }
  }

  window.addEventListener('DOMContentLoaded', loadScan);

})(window);

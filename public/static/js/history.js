/**
 * SmartFarm AI — History page
 */
(function (window) {
  'use strict';

  function t(key) { return window.i18n ? window.i18n.t(key) : key; }

  const STATUS_CLASS = {
    Healthy:   'sf-badge sf-badge-healthy',
    Unhealthy: 'sf-badge sf-badge-unhealthy',
    Uncertain: 'sf-badge sf-badge-uncertain',
  };

  function buildCard(rawItem) {
    const currentLang = window.i18n ? window.i18n.getLang() : 'en';
    const item = (window.i18n && window.i18n.translateReport)
      ? window.i18n.translateReport(rawItem, currentLang)
      : rawItem;

    const statusCls = STATUS_CLASS[item.plant_health_status] || STATUS_CLASS.Uncertain;
    const date = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
    const thumb = item.thumbnail_base64
      ? `<img src="data:${item.image_mime};base64,${item.thumbnail_base64}" alt="${item.predicted_disease}" class="w-100 h-100 object-fit-cover" />`
      : `<div class="w-100 h-100 d-flex align-items-center justify-content-center"><i class="bi bi-leaf fs-3 text-muted"></i></div>`;

    return `
    <div class="col-sm-6 col-lg-4">
      <div class="sf-card sf-history-card h-100 transition-hover overflow-hidden"
           data-testid="history-card"
           onclick="window.location.href='/scan/${item.id}'">
        <div class="position-relative" style="height:220px;background:var(--sf-secondary)">
          ${thumb}
          <span class="${statusCls} position-absolute top-0 start-0 m-3">
            ${t('status.' + item.plant_health_status)}
          </span>
        </div>
        <div class="p-4">
          <p class="font-serif fs-4 text-primary lh-sm mb-2">${item.predicted_disease}</p>
          <div class="d-flex justify-content-between align-items-center">
            <small class="text-muted d-flex align-items-center gap-1">
              <i class="bi bi-calendar3" aria-hidden="true"></i> ${date}
            </small>
            <span class="font-mono small text-primary">${item.confidence_score}%</span>
          </div>
          ${item.crop_name ? `<p class="small text-muted mt-1 text-truncate">${t('history.crop')}: <code>${item.crop_name}</code></p>` : ''}
          <div class="d-flex gap-2 mt-3 pt-3 border-top border-border">
            <button onclick="handleHistoryDownload('${item.id}', event)"
                    class="sf-btn-outline flex-fill d-flex align-items-center justify-content-center gap-1 py-1" style="font-size:0.8rem">
              <i class="bi bi-download" aria-hidden="true"></i> ${t('history.pdfBtn')}
            </button>
            <button onclick="handleHistoryDelete('${item.id}', event)"
                    data-testid="history-delete-btn"
                    class="sf-btn-outline d-flex align-items-center justify-content-center px-3 py-1"
                    style="color:var(--sf-destructive);font-size:0.8rem"
                    aria-label="${t('history.deleteAria')}">
              <i class="bi bi-trash3" aria-hidden="true"></i>
            </button>
          </div>
        </div>
      </div>
    </div>`;
  }

  async function loadHistory() {
    try {
      const items = await window.sfApi.fetchHistory();
      window._historyItems = items;
      document.getElementById('history-loading').classList.add('d-none');

      if (!items || items.length === 0) {
        document.getElementById('history-empty').classList.remove('d-none');
        return;
      }

      const grid = document.getElementById('history-grid');
      grid.innerHTML = items.map(buildCard).join('');
      grid.classList.remove('d-none');
    } catch (err) {
      document.getElementById('history-loading').classList.add('d-none');
      window.sfApp.showToast(t('history.toast.loadFail'), 'error');
      document.getElementById('history-empty').classList.remove('d-none');
    }
  }

  window.handleHistoryDelete = async function (id, event) {
    event.stopPropagation();
    if (!confirm(t('history.confirmDelete'))) return;
    try {
      await window.sfApi.deleteScan(id);
      window.sfApp.showToast(t('history.toast.deleted'), 'success');
      // Reload grid
      document.getElementById('history-grid').classList.add('d-none');
      document.getElementById('history-loading').classList.remove('d-none');
      loadHistory();
    } catch (err) {
      window.sfApp.showToast(t('history.toast.deleteFail'), 'error');
    }
  };

  window.handleHistoryDownload = async function (id, event) {
    event.stopPropagation();
    try {
      const full = await window.sfApi.fetchScan(id);
      window.downloadReportPdf(full);
    } catch (err) {
      window.sfApp.showToast(t('history.toast.pdfFail'), 'error');
    }
  };

  // Re-render history cards when language changes
  window.addEventListener('sf:languageChanged', function () {
    if (window._historyItems && window._historyItems.length > 0) {
      const grid = document.getElementById('history-grid');
      if (grid && !grid.classList.contains('d-none')) {
        grid.innerHTML = window._historyItems.map(buildCard).join('');
      }
    }
  });

  window.addEventListener('DOMContentLoaded', loadHistory);

})(window);

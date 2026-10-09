/**
 * SmartFarm AI — Result report renderer
 * Builds the bento-grid HTML for a scan report and injects it into #report-container.
 * Supports side-by-side Original vs. Enhanced image comparison when a blurry leaf image was enhanced.
 */
(function (window) {
  'use strict';

  const BCP47_MAP = {
    en: 'en-US',
    hi: 'hi-IN',
    te: 'te-IN',
    ta: 'ta-IN',
    bn: 'bn-IN',
    mr: 'mr-IN',
    kn: 'kn-IN',
    gu: 'gu-IN'
  };

  function stressBars(level) {
    const order = ['Low', 'Moderate', 'High', 'Critical'];
    const idx = Math.max(0, order.indexOf(level));
    return order.map((l, i) => {
      let cls = 'sf-stress-seg';
      if (i <= idx) {
        if (level === 'Critical' || level === 'High') cls += ' active-high';
        else if (level === 'Moderate') cls += ' active-moderate';
        else cls += ' active-low';
      }
      return `<div class="${cls}"></div>`;
    }).join('');
  }

  function statusBadgeCls(status) {
    if (status === 'Healthy') return 'sf-badge sf-badge-healthy';
    if (status === 'Unhealthy') return 'sf-badge sf-badge-unhealthy';
    return 'sf-badge sf-badge-uncertain';
  }

  function listItems(arr, emptyKey) {
    const t = window.i18n ? window.i18n.t : k => k;
    if (!arr || !arr.length) return `<li class="text-muted small">${t(emptyKey)}</li>`;
    return arr.map(a => `<li class="small">${a}</li>`).join('');
  }

  function numberedItems(arr, emptyKey) {
    const t = window.i18n ? window.i18n.t : k => k;
    if (!arr || !arr.length) return `<li class="text-muted small">${t(emptyKey)}</li>`;
    return arr.map((a, i) => `
      <li class="d-flex gap-3 small">
        <span class="font-mono text-muted" style="min-width:1.5rem">0${i + 1}</span>
        <span>${a}</span>
      </li>`).join('');
  }

  // ── Lightbox Modal for Image Inspection ────────────────────────────────────
  function ensureLightboxModal() {
    let modal = document.getElementById('sf-image-lightbox');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'sf-image-lightbox';
    modal.className = 'sf-lightbox d-none';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('data-testid', 'image-lightbox-modal');
    modal.innerHTML = `
      <div class="sf-lightbox-backdrop" onclick="closeImageLightbox()"></div>
      <div class="sf-lightbox-content sf-card p-3">
        <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-border">
          <span id="sf-lightbox-title" class="fw-medium text-primary small"></span>
          <button type="button" class="sf-clear-btn rounded-1 d-flex align-items-center justify-content-center"
                  onclick="closeImageLightbox()" id="sf-lightbox-close" aria-label="Close preview">
            <i class="bi bi-x-lg" aria-hidden="true"></i>
          </button>
        </div>
        <div class="text-center">
          <img id="sf-lightbox-img" src="" alt="" class="img-fluid rounded-1" style="max-height:78vh;object-fit:contain" />
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') window.closeImageLightbox();
    });
    return modal;
  }

  window.openImageLightbox = function (src, title) {
    if (!src) return;
    const t = window.i18n ? window.i18n.t : k => k;
    const modal = ensureLightboxModal();
    const imgEl = document.getElementById('sf-lightbox-img');
    const titleEl = document.getElementById('sf-lightbox-title');
    const closeBtn = document.getElementById('sf-lightbox-close');
    if (imgEl) {
      imgEl.src = src;
      imgEl.alt = title || t('report.leafImgAlt');
    }
    if (titleEl) titleEl.textContent = title || t('report.leafImgAlt');
    if (closeBtn) closeBtn.setAttribute('aria-label', t('report.closePreview'));
    modal.classList.remove('d-none');
  };

  window.closeImageLightbox = function () {
    const modal = document.getElementById('sf-image-lightbox');
    if (modal) modal.classList.add('d-none');
  };

  function renderReport(rawReport, containerId, onNewScan) {
    if (!rawReport) return;
    const t = window.i18n ? window.i18n.t : k => k;
    const container = document.getElementById(containerId);
    if (!container) return;

    window._currentRawReport = rawReport;
    window._currentContainerId = containerId;
    window._currentOnNewScan = onNewScan;

    const currentLang = window.i18n ? window.i18n.getLang() : 'en';
    const report = (window.i18n && window.i18n.translateReport)
      ? window.i18n.translateReport(rawReport, currentLang)
      : rawReport;

    const imgSrc = report.image_base64
      ? `data:${report.image_mime || 'image/jpeg'};base64,${report.image_base64}`
      : null;

    const isEnhanced = Boolean(report.image_enhanced && report.enhanced_image_base64);
    const enhanceFailed = Boolean(report.is_blurry && report.enhancement_status === 'failed');
    const enhancedImgSrc = isEnhanced
      ? `data:${report.enhanced_image_mime || 'image/jpeg'};base64,${report.enhanced_image_base64}`
      : null;

    window._lastOrigImgSrc = imgSrc;
    window._lastEnhancedImgSrc = enhancedImgSrc;

    const speechSupported = window.sfApp ? window.sfApp.isSpeechSupported() : false;

    const notPlantWarning = !report.is_plant_image ? `
      <div class="alert d-flex align-items-start gap-2 mb-4 rounded-1" style="background:color-mix(in srgb,var(--sf-warning) 12%,transparent);border:1px solid color-mix(in srgb,var(--sf-warning) 35%,transparent)">
        <i class="bi bi-exclamation-triangle text-warning mt-1" aria-hidden="true"></i>
        <p class="mb-0 small">${t('report.notPlant')}</p>
      </div>` : '';

    const enhanceFailedWarning = enhanceFailed ? `
      <div data-testid="enhance-failed-banner" class="alert d-flex align-items-start gap-2 mb-4 rounded-1" style="background:color-mix(in srgb,var(--sf-warning) 12%,transparent);border:1px solid color-mix(in srgb,var(--sf-warning) 35%,transparent)">
        <i class="bi bi-exclamation-circle text-warning mt-1" aria-hidden="true"></i>
        <p class="mb-0 small">${t('report.enhanceFailed')}</p>
      </div>` : '';

    // Side-by-side comparison card when blurry image was enhanced, or single image card when sharp
    let imageSectionHtml = '';
    if (isEnhanced && imgSrc && enhancedImgSrc) {
      imageSectionHtml = `
        <div class="sf-card p-4" style="grid-column:1/-1" data-testid="enhanced-image-comparison">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
            <div>
              <span class="sf-badge sf-badge-healthy mb-2" data-testid="blur-enhanced-badge">
                <i class="bi bi-magic" aria-hidden="true"></i>
                <span>${t('report.blurDetectedBadge')}</span>
              </span>
              <p class="small text-muted mb-0" data-testid="blur-enhanced-desc">${t('report.blurEnhancedDesc')}</p>
            </div>
          </div>
          <div class="row g-3">
            <div class="col-md-6" data-testid="original-image-col">
              <div class="sf-compare-frame position-relative rounded-1 overflow-hidden cursor-pointer"
                   onclick="openImageLightbox(window._lastOrigImgSrc, window.i18n ? window.i18n.t('report.originalImage') : 'Original Uploaded Image')">
                <span class="sf-compare-label sf-compare-label-orig" data-testid="original-image-label">
                  <i class="bi bi-image" aria-hidden="true"></i>
                  <span>${t('report.originalImage')}</span>
                </span>
                <span class="sf-compare-zoom">
                  <i class="bi bi-arrows-fullscreen" aria-hidden="true"></i>
                  <span class="d-none d-sm-inline">${t('report.clickToEnlarge')}</span>
                </span>
                <img src="${imgSrc}" alt="${t('report.originalImage')}"
                     data-testid="original-uploaded-image"
                     class="w-100 sf-compare-img" />
              </div>
            </div>
            <div class="col-md-6" data-testid="enhanced-image-col">
              <div class="sf-compare-frame sf-compare-frame-enhanced position-relative rounded-1 overflow-hidden cursor-pointer"
                   onclick="openImageLightbox(window._lastEnhancedImgSrc, window.i18n ? window.i18n.t('report.enhancedImage') : 'Enhanced Image')">
                <span class="sf-compare-label sf-compare-label-enh" data-testid="enhanced-image-label">
                  <i class="bi bi-stars" aria-hidden="true"></i>
                  <span>${t('report.enhancedImage')}</span>
                </span>
                <span class="sf-compare-zoom">
                  <i class="bi bi-arrows-fullscreen" aria-hidden="true"></i>
                  <span class="d-none d-sm-inline">${t('report.clickToEnlarge')}</span>
                </span>
                <img src="${enhancedImgSrc}" alt="${t('report.enhancedImage')}"
                     data-testid="enhanced-image"
                     class="w-100 sf-compare-img sf-compare-img-enhanced" />
              </div>
            </div>
          </div>
        </div>`;
    } else if (imgSrc) {
      imageSectionHtml = `
        <div class="sf-card overflow-hidden sf-report-img position-relative cursor-pointer"
             data-testid="single-uploaded-image-card"
             onclick="openImageLightbox(window._lastOrigImgSrc, window.i18n ? window.i18n.t('report.originalImage') : 'Original Uploaded Image')">
          <span class="sf-compare-zoom">
            <i class="bi bi-arrows-fullscreen" aria-hidden="true"></i>
            <span class="d-none d-sm-inline">${t('report.clickToEnlarge')}</span>
          </span>
          <img src="${imgSrc}" alt="${t('report.leafImgAlt')}"
               data-testid="original-uploaded-image"
               class="w-100 h-100 object-fit-cover" style="max-height:400px" />
        </div>`;
    }

    container.innerHTML = `
      <div data-testid="report-container" class="animate-fade-up">
        <!-- Header row -->
        <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
          <div>
            <p class="sf-overline">${t('report.overline')}</p>
            <h2 class="font-serif display-5 text-primary mt-1">${report.predicted_disease || t('report.dash')}</h2>
            ${report.crop_name ? `<p class="small text-muted mt-1">${t('report.cropHint')}: <code>${report.crop_name}</code></p>` : ''}
          </div>
          <div class="d-flex flex-wrap gap-2">
            ${speechSupported ? `
            <button id="speak-btn" data-testid="report-speak-btn"
                    onclick="handleSpeak()"
                    class="sf-btn-outline d-flex align-items-center gap-2">
              <i class="bi bi-volume-up" id="speak-icon" aria-hidden="true"></i>
              <span id="speak-label">${t('report.speak')}</span>
            </button>` : ''}
            <button onclick="downloadReportPdf(window._currentRawReport || window._currentReport)"
                    data-testid="download-pdf-btn"
                    class="sf-btn-outline d-flex align-items-center gap-2">
              <i class="bi bi-download" aria-hidden="true"></i>
              <span>${t('report.download')}</span>
            </button>
            ${onNewScan ? `
            <button onclick="if(typeof ${onNewScan}==='function'){${onNewScan}();}else if(window.${onNewScan}){window.${onNewScan}();}"
                    data-testid="new-scan-btn"
                    class="sf-btn-primary d-flex align-items-center gap-2">
              <i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i>
              <span>${t('report.newScan')}</span>
            </button>` : `
            <a href="/" data-testid="new-scan-btn"
               class="sf-btn-primary d-flex align-items-center gap-2">
              <i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i>
              <span>${t('report.newScan')}</span>
            </a>`}
          </div>
        </div>

        ${notPlantWarning}
        ${enhanceFailedWarning}

        <!-- Bento grid -->
        <div class="sf-report-bento">

          ${imageSectionHtml}

          <!-- Health status -->
          <div class="sf-card p-4">
            <p class="sf-overline">${t('report.health')}</p>
            <span class="${statusBadgeCls(report.plant_health_status)} mt-2" data-testid="health-status-badge">
              <i class="bi bi-shield-check" aria-hidden="true"></i>
              ${t('status.' + report.plant_health_status)}
            </span>
          </div>

          <!-- Disease -->
          <div class="sf-card p-4">
            <p class="sf-overline">${t('report.disease')}</p>
            <p class="font-serif fs-4 text-primary mt-2 lh-sm" data-testid="predicted-disease">
              ${report.predicted_disease || t('report.dash')}
            </p>
          </div>

          <!-- Confidence -->
          <div class="sf-card p-4" data-testid="confidence-meter">
            <p class="sf-overline">${t('report.confidence')}</p>
            <p class="font-mono display-6 text-primary mt-1" data-testid="confidence-value">
              ${report.confidence_score}<span class="fs-5 text-muted">%</span>
            </p>
            <div class="sf-confidence-bar">
              <div class="sf-confidence-fill" style="width:${Math.max(2, Math.min(100, report.confidence_score))}%"></div>
            </div>
          </div>

          <!-- Water stress -->
          <div class="sf-card p-4" data-testid="water-stress-level">
            <p class="sf-overline">${t('report.water')}</p>
            <div class="d-flex align-items-center gap-2 mt-2">
              <i class="bi bi-droplet ${report.water_stress_level === 'High' || report.water_stress_level === 'Critical' ? 'text-danger' : report.water_stress_level === 'Moderate' ? 'text-warning' : 'text-primary'}" aria-hidden="true"></i>
              <span class="small fw-medium ${report.water_stress_level === 'High' || report.water_stress_level === 'Critical' ? 'text-danger' : report.water_stress_level === 'Moderate' ? 'text-warning' : 'text-primary'}">
                ${t('stress.' + report.water_stress_level)}
              </span>
            </div>
            <div class="sf-stress-bar">${stressBars(report.water_stress_level)}</div>
          </div>

          <!-- Severity -->
          <div class="sf-card p-4" style="grid-column:span 2">
            <p class="sf-overline d-flex align-items-center gap-2">
              <i class="bi bi-activity text-primary" aria-hidden="true"></i>
              ${t('report.severity')}
            </p>
            <p class="small mt-2" data-testid="severity-assessment">${report.severity_assessment || t('report.dash')}</p>
          </div>

          <!-- Symptoms -->
          <div class="sf-card p-4" style="grid-column:span 2">
            <p class="sf-overline d-flex align-items-center gap-2">
              <i class="bi bi-stethoscope text-primary" aria-hidden="true"></i>
              ${t('report.symptoms')}
            </p>
            <ul class="list-unstyled mt-3 d-flex flex-column gap-2" data-testid="symptoms-list">
              ${listItems(report.detected_symptoms, 'report.noSymptoms')}
            </ul>
          </div>

          <!-- Recommended actions -->
          <div class="sf-card p-4" style="grid-column:span 2">
            <p class="sf-overline d-flex align-items-center gap-2">
              <i class="bi bi-list-check text-primary" aria-hidden="true"></i>
              ${t('report.actions')}
            </p>
            <ol class="list-unstyled mt-3 d-flex flex-column gap-2" data-testid="actions-list">
              ${numberedItems(report.recommended_actions, 'report.noActions')}
            </ol>
          </div>

          <!-- Preventive measures -->
          <div class="sf-card p-4" style="grid-column:span 2">
            <p class="sf-overline d-flex align-items-center gap-2">
              <i class="bi bi-shield-check text-primary" aria-hidden="true"></i>
              ${t('report.preventive')}
            </p>
            <ul class="list-unstyled mt-3 d-flex flex-column gap-2" data-testid="preventive-list">
              ${listItems(report.preventive_measures, 'report.dash')}
            </ul>
          </div>

          ${report.notes ? `
          <div class="sf-card p-4" style="grid-column:1/-1;background:color-mix(in srgb,var(--sf-secondary) 50%,var(--sf-card))">
            <p class="sf-overline d-flex align-items-center gap-2">
              <i class="bi bi-journal-text text-primary" aria-hidden="true"></i>
              ${t('report.notes')}
            </p>
            <p class="small mt-2 fst-italic" data-testid="report-notes">${report.notes}</p>
          </div>` : ''}

        </div>
      </div>`;

    // Store translated report for PDF/speech access
    window._currentReport = report;
  }

  // ── Speech toggle ──────────────────────────────────────────────────────────
  let _speaking = false;

  window.handleSpeak = function () {
    const t = window.i18n ? window.i18n.t : k => k;
    const currentLang = window.i18n ? window.i18n.getLang() : 'en';
    const bcp47 = BCP47_MAP[currentLang] || 'en-US';

    if (_speaking) {
      window.sfApp.stopSpeaking();
      _speaking = false;
      _resetSpeakBtn();
      return;
    }

    if (!window._currentReport) return;
    const text = window.sfApp.buildSpeechText(window._currentReport);
    const started = window.sfApp.speak(text, bcp47, {
      onEnd: () => { _speaking = false; _resetSpeakBtn(); },
      onError: () => { _speaking = false; _resetSpeakBtn(); },
    });
    if (started) {
      _speaking = true;
      const btn = document.getElementById('speak-btn');
      if (btn) {
        const icon = document.getElementById('speak-icon');
        const label = document.getElementById('speak-label');
        if (icon) icon.className = 'bi bi-volume-mute';
        if (label) label.textContent = t('report.stop');
      }
    }
  };

  function _resetSpeakBtn() {
    const t = window.i18n ? window.i18n.t : k => k;
    const icon = document.getElementById('speak-icon');
    const label = document.getElementById('speak-label');
    if (icon) icon.className = 'bi bi-volume-up';
    if (label) label.textContent = t('report.speak');
  }

  // Re-render report when language changes
  window.addEventListener('sf:languageChanged', function () {
    if (_speaking) {
      window.sfApp.stopSpeaking();
      _speaking = false;
      _resetSpeakBtn();
    }
    if (window._currentRawReport && window._currentContainerId) {
      const container = document.getElementById(window._currentContainerId);
      if (container && (!container.classList.contains('d-none') || container.children.length > 0)) {
        renderReport(window._currentRawReport, window._currentContainerId, window._currentOnNewScan);
      }
    }
  });

  // Expose
  window.sfReport = { renderReport };

})(window);

/**
 * SmartFarm AI — Image upload & analyze handler
 */
(function (window) {
  'use strict';

  const ACCEPTED_MIME = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  const MAX_BYTES = 8 * 1024 * 1024;

  let _selectedFile = null;
  let _currentErrorKey = null;
  let _isAnalyzing = false;

  function t(key) { return window.i18n ? window.i18n.t(key) : key; }

  function showError(msg, key) {
    _currentErrorKey = key || null;
    const el = document.getElementById('upload-error');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('d-none');
  }

  function clearError() {
    _currentErrorKey = null;
    const el = document.getElementById('upload-error');
    if (el) { el.textContent = ''; el.classList.add('d-none'); }
  }

  function compressImageIfNeeded(file, maxDimension = 1400, quality = 0.88) {
    return new Promise((resolve) => {
      if (file.size <= 2 * 1024 * 1024) {
        return resolve(file);
      }
      const img = new Image();
      const reader = new FileReader();
      reader.onload = (e) => {
        img.onload = () => {
          let width = img.width;
          let height = img.height;
          if (width > maxDimension || height > maxDimension) {
            if (width > height) {
              height = Math.round((height * maxDimension) / width);
              width = maxDimension;
            } else {
              width = Math.round((width * maxDimension) / height);
              height = maxDimension;
            }
          }
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);
          canvas.toBlob((blob) => {
            if (blob && blob.size < file.size) {
              const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, '.jpg'), { type: 'image/jpeg' });
              resolve(compressedFile);
            } else {
              resolve(file);
            }
          }, 'image/jpeg', quality);
        };
        img.onerror = () => resolve(file);
        img.src = e.target.result;
      };
      reader.onerror = () => resolve(file);
      reader.readAsDataURL(file);
    });
  }

  async function setFile(file) {
    clearError();
    if (!file) return;
    if (!ACCEPTED_MIME.includes(file.type)) { showError(t('uploader.err.formats'), 'uploader.err.formats'); return; }
    if (file.size > MAX_BYTES) { showError(t('uploader.err.tooLarge'), 'uploader.err.tooLarge'); return; }
    
    const optimizedFile = await compressImageIfNeeded(file);
    _selectedFile = optimizedFile;
    const reader = new FileReader();
    reader.onload = e => {
      const img = document.getElementById('preview-img');
      if (img) img.src = e.target.result;
      document.getElementById('drop-idle').classList.add('d-none');
      document.getElementById('drop-preview').classList.remove('d-none');
    };
    reader.readAsDataURL(optimizedFile);
    document.getElementById('analyze-btn').disabled = false;
  }

  window.clearUpload = function (event) {
    if (event) event.stopPropagation();
    _selectedFile = null;
    const input = document.getElementById('file-input');
    if (input) input.value = '';
    document.getElementById('drop-idle').classList.remove('d-none');
    document.getElementById('drop-preview').classList.add('d-none');
    document.getElementById('analyze-btn').disabled = true;
    clearError();
    // Hide report
    const reportSection = document.getElementById('report-section');
    if (reportSection) reportSection.classList.add('d-none');
  };

  window.handleAnalyze = async function () {
    const t = window.i18n ? window.i18n.t.bind(window.i18n) : k => k;
    if (!_selectedFile) { showError(t('uploader.err.noFile'), 'uploader.err.noFile'); return; }

    const lang = window.i18n ? window.i18n.getLang() : 'en';
    const crop = (document.getElementById('crop-input') || {}).value || '';

    // Show scanning overlay
    const overlay = document.getElementById('scan-overlay');
    if (overlay) overlay.classList.remove('d-none');
    const btn = document.getElementById('analyze-btn');
    if (btn) {
      btn.disabled = true;
      _isAnalyzing = true;
      document.getElementById('analyze-btn-label').textContent = t('uploader.analyzing');
    }
    clearError();

    try {
      const result = await window.sfApi.analyzeLeaf(_selectedFile, crop, lang);
      window.sfApp.showToast(t('uploader.toast.done'), 'success');

      // Render report
      const reportSection = document.getElementById('report-section');
      if (reportSection) {
        reportSection.classList.remove('d-none');
        window.sfReport.renderReport(result, 'report-container', 'newScan');
        setTimeout(() => reportSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
      }
    } catch (err) {
      showError(err.message || t('uploader.err.generic'), 'uploader.err.generic');
      window.sfApp.showToast(t('uploader.err.generic'), 'error');
    } finally {
      _isAnalyzing = false;
      if (overlay) overlay.classList.add('d-none');
      if (btn) {
        btn.disabled = false;
        document.getElementById('analyze-btn-label').textContent = t('uploader.analyzeBtn');
      }
    }
  };

  // Global new scan function referenced in report buttons
  window.newScan = function () {
    window.clearUpload();
    const section = document.getElementById('analyzer-section');
    if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // React to language change
  window.addEventListener('sf:languageChanged', function () {
    if (_currentErrorKey) {
      showError(t(_currentErrorKey), _currentErrorKey);
    }
    const btnLabel = document.getElementById('analyze-btn-label');
    if (btnLabel) {
      btnLabel.textContent = _isAnalyzing ? t('uploader.analyzing') : t('uploader.analyzeBtn');
    }
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  window.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('file-input');
    if (input) input.addEventListener('change', e => setFile(e.target.files[0]));

    const zone = document.getElementById('upload-dropzone');
    if (zone) {
      zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
      zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
      zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) setFile(file);
      });
      zone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') input && input.click(); });
    }
  });

})(window);

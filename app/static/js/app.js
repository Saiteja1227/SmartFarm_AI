/**
 * SmartFarm AI — Global app utilities (toasts, speech)
 */
(function (window) {
  'use strict';

  // ── Toast ─────────────────────────────────────────────────────────────────
  function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `sf-toast ${type} mb-2 d-flex align-items-center gap-2`;
    const icon = type === 'success' ? '✓' : '✕';
    el.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(el);
    // Fade out
    setTimeout(() => el.style.opacity = '0', 2800);
    setTimeout(() => el.remove(), 3200);
  }

  // ── Speech synthesis ──────────────────────────────────────────────────────
  let _cachedVoices = null;

  function _loadVoices() {
    if (_cachedVoices && _cachedVoices.length) return _cachedVoices;
    if (!window.speechSynthesis) return [];
    _cachedVoices = window.speechSynthesis.getVoices();
    return _cachedVoices;
  }

  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {
      _cachedVoices = window.speechSynthesis.getVoices();
    };
  }

  function isSpeechSupported() { return !!window.speechSynthesis; }

  function stopSpeaking() {
    if (isSpeechSupported()) window.speechSynthesis.cancel();
  }

  function speak(text, bcp47, callbacks) {
    if (!isSpeechSupported() || !text || !text.trim()) return false;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = bcp47 || 'en-US';
    utter.rate = 0.95;
    utter.pitch = 1;

    const voices = _loadVoices();
    const prefix = (bcp47 || '').split('-')[0].toLowerCase();

    // 1. Exact match on language tag (e.g. te-IN, hi-IN, en-US)
    let matchedVoice = voices.find(v => v.lang.toLowerCase() === (bcp47 || '').toLowerCase());

    // 2. Prefix match (e.g. starts with 'te', 'hi', 'en')
    if (!matchedVoice) {
      matchedVoice = voices.find(v => v.lang.toLowerCase().startsWith(prefix));
    }

    // 3. Name match for language keyword
    if (!matchedVoice) {
      const nameKeywords = {
        hi: ['hindi', 'हिन्दी', 'devanagari'],
        te: ['telugu', 'తెలుగు'],
        en: ['english', 'en-']
      };
      const keys = nameKeywords[prefix] || [];
      matchedVoice = voices.find(v => keys.some(k => v.name.toLowerCase().includes(k)));
    }

    if (matchedVoice) utter.voice = matchedVoice;
    if (callbacks && callbacks.onEnd) utter.onend = callbacks.onEnd;
    if (callbacks && callbacks.onError) utter.onerror = callbacks.onError;
    window.speechSynthesis.speak(utter);
    return true;
  }

  function buildSpeechText(report) {
    const currentLang = window.i18n ? window.i18n.getLang() : 'en';
    const rep = (window.i18n && window.i18n.translateReport)
      ? window.i18n.translateReport(report, currentLang)
      : report;
    const t = window.i18n ? window.i18n.t : k => k;

    const parts = [];
    parts.push(`${t('report.health')}: ${t('status.' + rep.plant_health_status)}.`);
    if (rep.predicted_disease) parts.push(`${t('report.disease')}: ${rep.predicted_disease}.`);
    parts.push(`${t('report.confidence')}: ${rep.confidence_score}%.`);
    parts.push(`${t('report.water')}: ${t('stress.' + rep.water_stress_level)}.`);
    if (rep.severity_assessment) parts.push(rep.severity_assessment);
    if (rep.recommended_actions && rep.recommended_actions.length) {
      parts.push(`${t('report.actions')}:`);
      rep.recommended_actions.forEach(a => parts.push(a));
    }
    return parts.join(' ');
  }

  // Stop speaking when user changes language
  window.addEventListener('sf:languageChanged', stopSpeaking);

  // Expose
  window.sfApp = { showToast, isSpeechSupported, speak, stopSpeaking, buildSpeechText };

})(window);

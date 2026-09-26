/**
 * SmartFarm AI — Client-side PDF generation using jsPDF (CDN).
 * Falls back to server-side endpoint if jsPDF is not available.
 */

// Load jsPDF from CDN lazily
(function (window) {
  'use strict';

  let _jsPDFLoaded = false;
  let _loadPromise = null;

  function loadJsPdf() {
    if (_jsPDFLoaded) return Promise.resolve();
    if (_loadPromise) return _loadPromise;
    _loadPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
      script.onload = () => { _jsPDFLoaded = true; resolve(); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return _loadPromise;
  }

  window.downloadReportPdf = async function (rawReport) {
    if (!rawReport) return;
    const currentLang = window.i18n ? window.i18n.getLang() : 'en';
    const report = (window.i18n && window.i18n.translateReport)
      ? window.i18n.translateReport(rawReport, currentLang)
      : rawReport;
    const t = window.i18n ? window.i18n.t : k => k;

    try {
      await loadJsPdf();
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({ unit: 'pt', format: 'a4' });
      const M = 48;
      const W = doc.internal.pageSize.getWidth() - M * 2;
      let y = M;

      // Header
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(18);
      doc.setTextColor(28, 58, 39);
      doc.text(t('pdf.title'), M, y);
      y += 22;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(80, 80, 80);
      const created = report.created_at ? new Date(report.created_at).toLocaleString() : new Date().toLocaleString();
      doc.text(`${t('pdf.generated')} ${created}`, M, y);
      if (report.crop_name) doc.text(`${t('pdf.crop')} ${report.crop_name}`, M + 220, y);
      y += 20;

      // Image
      if (report.image_base64 && report.image_mime) {
        try {
          const dataUrl = `data:${report.image_mime};base64,${report.image_base64}`;
          doc.addImage(dataUrl, 'JPEG', M, y, 200, 200, undefined, 'FAST');
        } catch (e) { /* skip image */ }
        const sx = M + 218;
        let sy = y + 8;
        const pairs = [
          [t('pdf.status'), t('status.' + report.plant_health_status)],
          [t('pdf.disease'), report.predicted_disease],
          [t('pdf.confidence'), `${report.confidence_score ?? 0}%`],
          [t('pdf.water'), t('stress.' + report.water_stress_level)],
        ];
        for (const [lbl, val] of pairs) {
          doc.setFont('helvetica', 'bold'); doc.setFontSize(11); doc.setTextColor(28, 58, 39);
          doc.text(lbl, sx, sy); sy += 14;
          doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.setTextColor(40, 40, 40);
          doc.text(String(val || '—'), sx, sy); sy += 20;
        }
        y += 214;
      }

      function section(title, content) {
        if (y > 720) { doc.addPage(); y = M; }
        doc.setFont('helvetica', 'bold'); doc.setFontSize(11); doc.setTextColor(28, 58, 39);
        doc.text(title, M, y); y += 14;
        doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.setTextColor(40, 40, 40);
        if (Array.isArray(content)) {
          if (!content.length) { doc.text('—', M, y); y += 13; }
          else {
            content.forEach(item => {
              const lines = doc.splitTextToSize(`• ${item}`, W);
              lines.forEach(ln => { if (y > 780) { doc.addPage(); y = M; } doc.text(ln, M, y); y += 12; });
            });
          }
        } else {
          const lines = doc.splitTextToSize(String(content || '—'), W);
          lines.forEach(ln => { if (y > 780) { doc.addPage(); y = M; } doc.text(ln, M, y); y += 12; });
        }
        y += 8;
      }

      section(t('pdf.severity'), report.severity_assessment);
      section(t('pdf.symptoms'), report.detected_symptoms || []);
      section(t('pdf.actions'), report.recommended_actions || []);
      section(t('pdf.preventive'), report.preventive_measures || []);
      if (report.notes) section(t('pdf.notes'), report.notes);

      // Footer
      doc.setFontSize(7); doc.setTextColor(120, 120, 120);
      doc.text(t('pdf.footer'), M, 810);

      const fname = `smartfarm-report-${(report.id || 'scan').slice(0, 8)}.pdf`;
      doc.save(fname);
    } catch (err) {
      // Fallback: server-side PDF
      if (report.id) {
        const userId = window.sfApi ? window.sfApi.getOrCreateUserId() : '';
        window.open(`/api/scan/${report.id}/pdf?uid=${userId}`, '_blank');
      }
    }
  };

})(window);

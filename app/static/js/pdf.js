/**
 * SmartFarm AI — Multilingual Unicode PDF Export (All 8 Languages)
 * Renders the translated Plant Health Report via high-DPI HTML5 2D Canvas
 * (leveraging the browser's native HarfBuzz/CoreText/DirectWrite OpenType
 * Indic shaping engine + Noto Sans Indic fonts) and embeds A4 pages into jsPDF.
 * Also displays side-by-side Original vs. Enhanced leaf images when a blurry image was enhanced.
 */
(function (window) {
  'use strict';

  function loadJsPdf() {
    return new Promise((resolve, reject) => {
      if (window.jspdf && window.jspdf.jsPDF) return resolve(window.jspdf.jsPDF);
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
      s.onload = () => {
        if (window.jspdf && window.jspdf.jsPDF) resolve(window.jspdf.jsPDF);
        else reject(new Error('jsPDF failed to initialize'));
      };
      s.onerror = () => reject(new Error('Could not load jsPDF from CDN'));
      document.head.appendChild(s);
    });
  }

  function loadImageElement(src) {
    return new Promise(resolve => {
      if (!src) return resolve(null);
      const img = new Image();
      img.crossOrigin = 'anonymous';
      const timer = setTimeout(() => resolve(null), 4000);
      img.onload = () => {
        clearTimeout(timer);
        resolve(img);
      };
      img.onerror = () => {
        clearTimeout(timer);
        resolve(null);
      };
      img.src = src;
    });
  }

  // Font stack covering Latin + all 7 Indic scripts supported by SmartFarm AI
  const SANS_FONT_STACK =
    '"Outfit", "Noto Sans Devanagari", "Noto Sans Telugu", "Noto Sans Tamil", ' +
    '"Noto Sans Bengali", "Noto Sans Kannada", "Noto Sans Gujarati", ' +
    'system-ui, -apple-system, BlinkMacSystemFont, sans-serif';

  const SERIF_FONT_STACK =
    '"Cormorant Garamond", "Noto Serif Devanagari", "Noto Serif Telugu", ' +
    '"Noto Sans Tamil", "Noto Sans Bengali", "Noto Sans Kannada", ' +
    '"Noto Sans Gujarati", Georgia, serif';

  function setCanvasFont(ctx, weight, sizePx, isSerif) {
    const family = isSerif ? SERIF_FONT_STACK : SANS_FONT_STACK;
    ctx.font = `${weight} ${sizePx}px ${family}`;
  }

  function wrapLines(ctx, text, maxWidth) {
    if (!text) return [];
    const paragraphs = String(text).split(/\r?\n/);
    const lines = [];
    paragraphs.forEach(para => {
      const words = para.trim().split(/\s+/).filter(Boolean);
      if (!words.length) {
        lines.push('');
        return;
      }
      let currentLine = words[0];
      for (let i = 1; i < words.length; i++) {
        const candidate = currentLine + ' ' + words[i];
        if (ctx.measureText(candidate).width <= maxWidth) {
          currentLine = candidate;
        } else {
          lines.push(currentLine);
          currentLine = words[i];
        }
      }
      lines.push(currentLine);
    });
    return lines;
  }

  function drawCoverFitImage(ctx, img, x, y, w, h) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    const imgRatio = (img.width || 1) / (img.height || 1);
    const boxRatio = w / h;
    let drawW = w;
    let drawH = h;
    let drawX = x;
    let drawY = y;
    if (imgRatio > boxRatio) {
      drawH = h;
      drawW = h * imgRatio;
      drawX = x - (drawW - w) / 2;
    } else {
      drawW = w;
      drawH = w / imgRatio;
      drawY = y - (drawH - h) / 2;
    }
    ctx.drawImage(img, drawX, drawY, drawW, drawH);
    ctx.restore();
  }

  window.downloadReportPdf = async function (rawReport) {
    if (!rawReport) return;

    const currentLang = window.i18n ? window.i18n.getLang() : 'en';
    const report = (window.i18n && window.i18n.translateReport)
      ? window.i18n.translateReport(rawReport, currentLang)
      : rawReport;
    const t = window.i18n ? window.i18n.t : k => k;

    // Wait for web fonts so Indic glyphs shape properly on canvas
    if (document.fonts && document.fonts.ready) {
      try { await document.fonts.ready; } catch (_) {}
    }

    const jsPDF = await loadJsPdf();

    // High-DPI A4 canvas dimensions (1240 x 1754 px = ~150 DPI for 210x297mm)
    const PAGE_W = 1240;
    const PAGE_H = 1754;
    const MARGIN = 84;
    const CONTENT_W = PAGE_W - MARGIN * 2;
    const FOOTER_Y = PAGE_H - 68;

    const pages = [];
    let currentCanvas = null;
    let ctx = null;
    let y = 0;

    function startNewPage(isFirstPage) {
      currentCanvas = document.createElement('canvas');
      currentCanvas.width = PAGE_W;
      currentCanvas.height = PAGE_H;
      ctx = currentCanvas.getContext('2d');
      pages.push(currentCanvas);

      // Warm parchment card background
      ctx.fillStyle = '#FAF8F4';
      ctx.fillRect(0, 0, PAGE_W, PAGE_H);

      if (isFirstPage) {
        // Primary botanical green header banner
        ctx.fillStyle = '#1C3A27';
        ctx.fillRect(0, 0, PAGE_W, 195);

        ctx.fillStyle = '#F4F1EB';
        ctx.textBaseline = 'top';
        setCanvasFont(ctx, '700', 40, true);
        ctx.fillText(t('pdf.title'), MARGIN, 46);

        const dateStr = report.created_at
          ? new Date(report.created_at).toLocaleString()
          : new Date().toLocaleString();
        let metaLine = `${t('pdf.generated')} ${dateStr}`;
        if (report.crop_name) {
          metaLine += `   ·   ${t('pdf.crop')} ${report.crop_name}`;
        }

        ctx.fillStyle = '#C9D6CB';
        setCanvasFont(ctx, '400', 22, false);
        ctx.fillText(metaLine, MARGIN, 114);

        y = 240;
      } else {
        // Compact continuation header on subsequent pages
        ctx.fillStyle = '#1C3A27';
        ctx.fillRect(0, 0, PAGE_W, 92);
        ctx.fillStyle = '#F4F1EB';
        ctx.textBaseline = 'top';
        setCanvasFont(ctx, '600', 26, true);
        ctx.fillText(t('pdf.title'), MARGIN, 30);
        y = 135;
      }
    }

    function ensureSpace(requiredHeight) {
      if (y + requiredHeight > FOOTER_Y - 30) {
        startNewPage(false);
      }
    }

    startNewPage(true);

    // ── Summary 4-Column Metrics Box ─────────────────────────────────────────
    const boxH = 148;
    ctx.fillStyle = '#EFECE4';
    ctx.fillRect(MARGIN, y, CONTENT_W, boxH);
    ctx.strokeStyle = '#D5CFC2';
    ctx.lineWidth = 2;
    ctx.strokeRect(MARGIN, y, CONTENT_W, boxH);

    const summaryCols = [
      { label: t('pdf.status'),     value: t('status.' + (report.plant_health_status || 'Uncertain')) },
      { label: t('pdf.disease'),    value: String(report.predicted_disease || '—') },
      { label: t('pdf.confidence'), value: `${report.confidence_score !== undefined ? report.confidence_score : 0}%` },
      { label: t('pdf.water'),      value: t('stress.' + (report.water_stress_level || 'Low')) }
    ];

    const colW = CONTENT_W / summaryCols.length;
    summaryCols.forEach((col, i) => {
      const colX = MARGIN + i * colW + 24;
      if (i > 0) {
        ctx.beginPath();
        ctx.moveTo(MARGIN + i * colW, y + 20);
        ctx.lineTo(MARGIN + i * colW, y + boxH - 20);
        ctx.strokeStyle = '#D5CFC2';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      ctx.fillStyle = '#6E746B';
      setCanvasFont(ctx, '600', 18, false);
      ctx.fillText(col.label.toUpperCase(), colX, y + 24);

      ctx.fillStyle = '#1C3A27';
      setCanvasFont(ctx, '700', 25, false);
      const valLines = wrapLines(ctx, col.value, colW - 36);
      valLines.slice(0, 2).forEach((ln, idx) => {
        ctx.fillText(ln, colX, y + 62 + idx * 32);
      });
    });

    y += boxH + 36;

    // ── Leaf Image(s) Section (Side-by-Side when Enhanced, Single when Sharp) ─
    const origSrc = report.image_base64
      ? `data:${report.image_mime || 'image/jpeg'};base64,${report.image_base64}`
      : null;
    const isEnhanced = Boolean(report.image_enhanced && report.enhanced_image_base64);
    const enhSrc = isEnhanced
      ? `data:${report.enhanced_image_mime || 'image/jpeg'};base64,${report.enhanced_image_base64}`
      : null;

    const [origImg, enhImg] = await Promise.all([
      loadImageElement(origSrc),
      loadImageElement(enhSrc)
    ]);

    if (isEnhanced && origImg && enhImg) {
      ensureSpace(390);
      // Enhancement note badge
      ctx.fillStyle = '#E3EDE5';
      ctx.fillRect(MARGIN, y, CONTENT_W, 48);
      ctx.strokeStyle = '#8CA38D';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(MARGIN, y, CONTENT_W, 48);
      ctx.fillStyle = '#1C3A27';
      setCanvasFont(ctx, '600', 20, false);
      ctx.fillText(`✦  ${t('pdf.imageEnhancedNote')}`, MARGIN + 18, y + 13);
      y += 64;

      const gap = 28;
      const imgW = (CONTENT_W - gap) / 2;
      const imgH = 290;

      // Left: Original Uploaded Image
      ctx.fillStyle = '#1C3A27';
      setCanvasFont(ctx, '600', 21, false);
      ctx.fillText(t('pdf.originalImage'), MARGIN, y);

      // Right: Enhanced Image
      ctx.fillText(t('pdf.enhancedImage'), MARGIN + imgW + gap, y);
      y += 32;

      drawCoverFitImage(ctx, origImg, MARGIN, y, imgW, imgH);
      ctx.strokeStyle = '#C9C2B2';
      ctx.lineWidth = 2;
      ctx.strokeRect(MARGIN, y, imgW, imgH);

      drawCoverFitImage(ctx, enhImg, MARGIN + imgW + gap, y, imgW, imgH);
      ctx.strokeStyle = '#1C3A27';
      ctx.lineWidth = 3;
      ctx.strokeRect(MARGIN + imgW + gap, y, imgW, imgH);

      y += imgH + 38;
    } else if (origImg) {
      ensureSpace(310);
      const imgW = 460;
      const imgH = 270;
      drawCoverFitImage(ctx, origImg, MARGIN, y, imgW, imgH);
      ctx.strokeStyle = '#C9C2B2';
      ctx.lineWidth = 2;
      ctx.strokeRect(MARGIN, y, imgW, imgH);
      y += imgH + 36;
    }

    // ── Section Helper ───────────────────────────────────────────────────────
    function drawSectionHeading(title) {
      ensureSpace(90);
      ctx.fillStyle = '#1C3A27';
      setCanvasFont(ctx, '700', 26, false);
      ctx.fillText(title, MARGIN, y);
      y += 36;
      ctx.beginPath();
      ctx.moveTo(MARGIN, y);
      ctx.lineTo(MARGIN + CONTENT_W, y);
      ctx.strokeStyle = '#D5CFC2';
      ctx.lineWidth = 2;
      ctx.stroke();
      y += 18;
    }

    function drawParagraphSection(title, text) {
      if (!text) return;
      drawSectionHeading(title);
      ctx.fillStyle = '#2B2E2A';
      setCanvasFont(ctx, '400', 22, false);
      const lines = wrapLines(ctx, text, CONTENT_W);
      lines.forEach(line => {
        ensureSpace(36);
        ctx.fillStyle = '#2B2E2A';
        setCanvasFont(ctx, '400', 22, false);
        ctx.fillText(line, MARGIN, y);
        y += 34;
      });
      y += 22;
    }

    function drawListSection(title, items, numbered) {
      if (!items || !items.length) return;
      drawSectionHeading(title);
      items.forEach((item, idx) => {
        const prefix = numbered ? `${String(idx + 1).padStart(2, '0')}. ` : '•  ';
        setCanvasFont(ctx, '400', 22, false);
        const lines = wrapLines(ctx, prefix + item, CONTENT_W - 18);
        lines.forEach((line, lineIdx) => {
          ensureSpace(36);
          ctx.fillStyle = '#2B2E2A';
          setCanvasFont(ctx, '400', 22, false);
          ctx.fillText(line, MARGIN + (lineIdx === 0 ? 8 : 36), y);
          y += 34;
        });
        y += 6;
      });
      y += 18;
    }

    drawParagraphSection(t('pdf.severity'), report.severity_assessment);
    drawListSection(t('pdf.symptoms'), report.detected_symptoms, false);
    drawListSection(t('pdf.actions'), report.recommended_actions, true);
    drawListSection(t('pdf.preventive'), report.preventive_measures, false);
    drawParagraphSection(t('pdf.notes'), report.notes);

    // ── Footer on All Pages ──────────────────────────────────────────────────
    const totalPages = pages.length;
    pages.forEach((pageCanvas, idx) => {
      const pctx = pageCanvas.getContext('2d');
      pctx.beginPath();
      pctx.moveTo(MARGIN, FOOTER_Y - 14);
      pctx.lineTo(PAGE_W - MARGIN, FOOTER_Y - 14);
      pctx.strokeStyle = '#D5CFC2';
      pctx.lineWidth = 1.5;
      pctx.stroke();

      pctx.fillStyle = '#6E746B';
      pctx.textBaseline = 'top';
      setCanvasFont(pctx, '400', 17, false);
      const footerLines = wrapLines(pctx, t('pdf.footer'), CONTENT_W - 100);
      if (footerLines[0]) {
        pctx.fillText(footerLines[0], MARGIN, FOOTER_Y);
      }
      const pageLabel = `${idx + 1} / ${totalPages}`;
      const pw = pctx.measureText(pageLabel).width;
      pctx.fillText(pageLabel, PAGE_W - MARGIN - pw, FOOTER_Y);
    });

    // ── Assemble A4 PDF via jsPDF ────────────────────────────────────────────
    const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
    if (doc.setProperties) {
      doc.setProperties({
        title: t('pdf.title'),
        subject: `${t('pdf.disease')}: ${report.predicted_disease || ''}`,
        creator: 'SmartFarm AI'
      });
    }

    pages.forEach((pageCanvas, idx) => {
      if (idx > 0) doc.addPage();
      const pageDataUrl = pageCanvas.toDataURL('image/jpeg', 0.94);
      doc.addImage(pageDataUrl, 'JPEG', 0, 0, 210, 297);
    });

    const idSuffix = (report.id || Date.now()).toString().slice(0, 8);
    doc.save(`smartfarm-report-${currentLang}-${idSuffix}.pdf`);
  };

})(window);

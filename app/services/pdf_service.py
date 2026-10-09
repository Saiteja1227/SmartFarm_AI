"""Server-side multilingual Unicode PDF generation for SmartFarm AI scan reports.
Supports all 8 languages: English (en), Hindi (hi), Telugu (te), Tamil (ta),
Bengali (bn), Marathi (mr), Kannada (kn), and Gujarati (gu), as well as
side-by-side Original vs. Enhanced leaf images when a blurry image was enhanced.
"""
import base64
import io
import logging
import os
from datetime import datetime
from typing import Optional, Tuple

from app.translations import SUPPORTED_LANG_CODES, t, translate_report

logger = logging.getLogger(__name__)

# Language-specific TrueType / TrueType-Collection font candidates (macOS + LinuxNoto paths)
_FONT_CANDIDATES = {
    "en": [
        ("/System/Library/Fonts/Supplemental/Arial.ttf", None, "/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", None, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", None),
    ],
    "hi": [
        ("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 0, "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
    "mr": [
        ("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 0, "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
    "te": [
        ("/System/Library/Fonts/Supplemental/Telugu Sangam MN.ttc", 0, "/System/Library/Fonts/Supplemental/Telugu Sangam MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansTelugu-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
    "ta": [
        ("/System/Library/Fonts/Supplemental/Tamil MN.ttc", 0, "/System/Library/Fonts/Supplemental/Tamil MN.ttc", 1),
        ("/System/Library/Fonts/Supplemental/InaiMathi-MN.ttc", 0, "/System/Library/Fonts/Supplemental/InaiMathi-MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
    "bn": [
        ("/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc", 0, "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
    "kn": [
        ("/System/Library/Fonts/NotoSansKannada.ttc", 0, "/System/Library/Fonts/NotoSansKannada.ttc", 1),
        ("/System/Library/Fonts/Supplemental/Kannada Sangam MN.ttc", 0, "/System/Library/Fonts/Supplemental/Kannada Sangam MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansKannada-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
    "gu": [
        ("/System/Library/Fonts/Supplemental/Gujarati Sangam MN.ttc", 0, "/System/Library/Fonts/Supplemental/Gujarati Sangam MN.ttc", 1),
        ("/usr/share/fonts/truetype/noto/NotoSansGujarati-Regular.ttf", None, "/usr/share/fonts/truetype/noto/NotoSansGujarati-Bold.ttf", None),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    ],
}

_REGISTERED_FONTS = {}


def _get_reportlab_fonts(lang: str) -> Tuple[str, str]:
    """Register and return (regular_font_name, bold_font_name) for ReportLab."""
    if lang in _REGISTERED_FONTS:
        return _REGISTERED_FONTS[lang]

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = _FONT_CANDIDATES.get(lang, []) + _FONT_CANDIDATES.get("en", [])
    for reg_path, reg_idx, bold_path, bold_idx in candidates:
        if not os.path.exists(reg_path):
            continue
        try:
            reg_name = f"SF_{lang}_Reg"
            bold_name = f"SF_{lang}_Bold"
            if reg_idx is not None:
                pdfmetrics.registerFont(TTFont(reg_name, reg_path, subfontIndex=reg_idx))
            else:
                pdfmetrics.registerFont(TTFont(reg_name, reg_path))

            if os.path.exists(bold_path):
                if bold_idx is not None:
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path, subfontIndex=bold_idx))
                else:
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            else:
                bold_name = reg_name

            _REGISTERED_FONTS[lang] = (reg_name, bold_name)
            return reg_name, bold_name
        except Exception as exc:
            logger.debug("Could not register font %s for %s: %s", reg_path, lang, exc)

    return "Helvetica", "Helvetica-Bold"


def _decode_image_reader(b64_str: Optional[str]):
    if not b64_str:
        return None
    try:
        from reportlab.lib.utils import ImageReader
        raw = base64.b64decode(b64_str)
        return ImageReader(io.BytesIO(raw))
    except Exception:
        return None


def _wrap_text(c, text: str, font_name: str, font_size: float, max_width: float) -> list:
    if not text:
        return []
    lines = []
    for para in str(text).splitlines():
        words = para.strip().split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            cand = f"{cur} {w}"
            if c.stringWidth(cand, font_name, font_size) <= max_width:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def generate_pdf_bytes(scan: dict, lang: Optional[str] = None) -> bytes:
    """
    Generate a localized, Unicode-compliant A4 PDF report for the given scan document.
    Supports all 8 languages in the language selector and includes side-by-side
    Original vs. Enhanced images when a blurry leaf image was enhanced.
    """
    target_lang = (lang or scan.get("language") or "en").strip().lower()
    if target_lang not in SUPPORTED_LANG_CODES:
        target_lang = "en"

    report = translate_report(scan, target_lang)

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    page_w, page_h = A4  # 595.27 x 841.89 pt
    margin = 40.0
    content_w = page_w - margin * 2
    footer_y = 38.0

    reg_font, bold_font = _get_reportlab_fonts(target_lang)

    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(t("pdf.title", target_lang))
    c.setAuthor("SmartFarm AI")

    y = page_h

    def draw_page_chrome(is_first: bool):
        nonlocal y
        # Warm parchment background
        c.setFillColor(colors.HexColor("#FAF8F4"))
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        if is_first:
            c.setFillColor(colors.HexColor("#1C3A27"))
            c.rect(0, page_h - 92, page_w, 92, fill=1, stroke=0)

            c.setFillColor(colors.HexColor("#F4F1EB"))
            c.setFont(bold_font, 18)
            c.drawString(margin, page_h - 42, t("pdf.title", target_lang))

            created_raw = report.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                date_str = created_raw or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            meta = f"{t('pdf.generated', target_lang)} {date_str}"
            if report.get("crop_name"):
                meta += f"   ·   {t('pdf.crop', target_lang)} {report['crop_name']}"

            c.setFillColor(colors.HexColor("#C9D6CB"))
            c.setFont(reg_font, 10)
            c.drawString(margin, page_h - 68, meta)
            y = page_h - 114
        else:
            c.setFillColor(colors.HexColor("#1C3A27"))
            c.rect(0, page_h - 48, page_w, 48, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#F4F1EB"))
            c.setFont(bold_font, 12)
            c.drawString(margin, page_h - 30, t("pdf.title", target_lang))
            y = page_h - 70

        # Footer
        c.setStrokeColor(colors.HexColor("#D5CFC2"))
        c.setLineWidth(0.75)
        c.line(margin, footer_y + 14, page_w - margin, footer_y + 14)
        c.setFillColor(colors.HexColor("#6E746B"))
        c.setFont(reg_font, 8)
        footer_lines = _wrap_text(c, t("pdf.footer", target_lang), reg_font, 8, content_w)
        if footer_lines:
            c.drawString(margin, footer_y, footer_lines[0])

    def ensure_space(needed: float):
        nonlocal y
        if y - needed < footer_y + 24:
            c.showPage()
            draw_page_chrome(False)

    draw_page_chrome(True)

    # ── Summary 4-Column Box ─────────────────────────────────────────────────
    box_h = 64.0
    c.setFillColor(colors.HexColor("#EFECE4"))
    c.setStrokeColor(colors.HexColor("#D5CFC2"))
    c.setLineWidth(1)
    c.rect(margin, y - box_h, content_w, box_h, fill=1, stroke=1)

    status_key = f"status.{report.get('plant_health_status', 'Uncertain')}"
    stress_key = f"stress.{report.get('water_stress_level', 'Low')}"
    cols = [
        (t("pdf.status", target_lang), t(status_key, target_lang)),
        (t("pdf.disease", target_lang), str(report.get("predicted_disease", "—"))),
        (t("pdf.confidence", target_lang), f"{report.get('confidence_score', 0)}%"),
        (t("pdf.water", target_lang), t(stress_key, target_lang)),
    ]
    col_w = content_w / len(cols)
    for i, (lbl, val) in enumerate(cols):
        cx = margin + i * col_w + 10
        if i > 0:
            c.setStrokeColor(colors.HexColor("#D5CFC2"))
            c.line(margin + i * col_w, y - box_h + 10, margin + i * col_w, y - 10)
        c.setFillColor(colors.HexColor("#6E746B"))
        c.setFont(bold_font, 8.5)
        c.drawString(cx, y - 18, lbl)

        c.setFillColor(colors.HexColor("#1C3A27"))
        c.setFont(bold_font, 11)
        vlines = _wrap_text(c, val, bold_font, 11, col_w - 16)
        for idx_l, vln in enumerate(vlines[:2]):
            c.drawString(cx, y - 36 - idx_l * 14, vln)

    y -= box_h + 20

    # ── Images (Side-by-Side when Enhanced, Single when Sharp) ───────────────
    orig_reader = _decode_image_reader(report.get("image_base64"))
    is_enhanced = bool(report.get("image_enhanced") and report.get("enhanced_image_base64"))
    enh_reader = _decode_image_reader(report.get("enhanced_image_base64")) if is_enhanced else None

    if is_enhanced and orig_reader and enh_reader:
        ensure_space(185)
        # Note bar
        c.setFillColor(colors.HexColor("#E3EDE5"))
        c.setStrokeColor(colors.HexColor("#8CA38D"))
        c.rect(margin, y - 22, content_w, 22, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#1C3A27"))
        c.setFont(bold_font, 9)
        c.drawString(margin + 8, y - 15, f"* {t('pdf.imageEnhancedNote', target_lang)}")
        y -= 32

        gap = 16.0
        img_w = (content_w - gap) / 2.0
        img_h = 130.0

        c.setFillColor(colors.HexColor("#1C3A27"))
        c.setFont(bold_font, 9.5)
        c.drawString(margin, y - 10, t("pdf.originalImage", target_lang))
        c.drawString(margin + img_w + gap, y - 10, t("pdf.enhancedImage", target_lang))
        y -= 16

        c.drawImage(orig_reader, margin, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, anchor="c")
        c.setStrokeColor(colors.HexColor("#C9C2B2"))
        c.rect(margin, y - img_h, img_w, img_h, fill=0, stroke=1)

        c.drawImage(enh_reader, margin + img_w + gap, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, anchor="c")
        c.setStrokeColor(colors.HexColor("#1C3A27"))
        c.setLineWidth(1.5)
        c.rect(margin + img_w + gap, y - img_h, img_w, img_h, fill=0, stroke=1)
        c.setLineWidth(1)

        y -= img_h + 20
    elif orig_reader:
        ensure_space(145)
        img_w = 210.0
        img_h = 125.0
        c.drawImage(orig_reader, margin, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, anchor="c")
        c.setStrokeColor(colors.HexColor("#C9C2B2"))
        c.rect(margin, y - img_h, img_w, img_h, fill=0, stroke=1)
        y -= img_h + 20

    # ── Section Helpers ──────────────────────────────────────────────────────
    def draw_heading(title: str):
        nonlocal y
        ensure_space(42)
        c.setFillColor(colors.HexColor("#1C3A27"))
        c.setFont(bold_font, 12)
        c.drawString(margin, y - 12, title)
        y -= 18
        c.setStrokeColor(colors.HexColor("#D5CFC2"))
        c.setLineWidth(0.8)
        c.line(margin, y, margin + content_w, y)
        y -= 14

    def draw_paragraph_section(title: str, text: str):
        nonlocal y
        if not text:
            return
        draw_heading(title)
        lines = _wrap_text(c, text, reg_font, 10, content_w)
        for ln in lines:
            ensure_space(16)
            c.setFillColor(colors.HexColor("#2B2E2A"))
            c.setFont(reg_font, 10)
            c.drawString(margin, y, ln)
            y -= 15
        y -= 8

    def draw_list_section(title: str, items: list, numbered: bool = False):
        nonlocal y
        if not items:
            return
        draw_heading(title)
        for idx, item in enumerate(items):
            prefix = f"{idx + 1:02d}. " if numbered else "•  "
            lines = _wrap_text(c, prefix + str(item), reg_font, 10, content_w - 12)
            for l_idx, ln in enumerate(lines):
                ensure_space(16)
                c.setFillColor(colors.HexColor("#2B2E2A"))
                c.setFont(reg_font, 10)
                c.drawString(margin + (4 if l_idx == 0 else 18), y, ln)
                y -= 15
            y -= 2
        y -= 8

    draw_paragraph_section(t("pdf.severity", target_lang), report.get("severity_assessment", ""))
    draw_list_section(t("pdf.symptoms", target_lang), report.get("detected_symptoms", []), numbered=False)
    draw_list_section(t("pdf.actions", target_lang), report.get("recommended_actions", []), numbered=True)
    draw_list_section(t("pdf.preventive", target_lang), report.get("preventive_measures", []), numbered=False)
    draw_paragraph_section(t("pdf.notes", target_lang), report.get("notes", ""))

    c.save()
    return buf.getvalue()


# Alias for backward compatibility with routes importing generate_report_pdf
generate_report_pdf = generate_pdf_bytes


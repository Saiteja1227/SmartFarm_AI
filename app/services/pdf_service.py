"""Server-side PDF generation for scan reports using fpdf2."""
import io
import textwrap
from datetime import datetime

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


def generate_report_pdf(report: dict) -> bytes:
    """Return the PDF as raw bytes, or raise RuntimeError if fpdf2 not installed."""
    if not FPDF_AVAILABLE:
        raise RuntimeError("fpdf2 not installed — PDF generation unavailable server-side.")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Fonts ─────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(28, 58, 39)  # Deep Forest Green
    pdf.cell(0, 10, "SmartFarm AI — Plant Health Report", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    created = report.get("created_at", "")
    if created:
        try:
            created = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass
    pdf.cell(0, 5, f"Generated: {created}", ln=True)
    if report.get("crop_name"):
        pdf.cell(0, 5, f"Crop: {report['crop_name']}", ln=True)
    pdf.ln(4)

    # ── Summary table ─────────────────────────────────────────────────────────
    def row(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(28, 58, 39)
        pdf.cell(55, 7, label + ":", border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 7, str(value or "—"), ln=True)

    row("Health Status", report.get("plant_health_status", "—"))
    row("Predicted Disease", report.get("predicted_disease", "—"))
    row("Confidence", f"{report.get('confidence_score', 0)}%")
    row("Water Stress", report.get("water_stress_level", "—"))
    pdf.ln(4)

    # ── Sections ──────────────────────────────────────────────────────────────
    def section(title, content):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(28, 58, 39)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        if isinstance(content, list):
            for item in content:
                for line in textwrap.wrap(f"• {item}", 95):
                    pdf.cell(0, 6, line, ln=True)
        else:
            for line in textwrap.wrap(str(content or "—"), 95):
                pdf.cell(0, 6, line, ln=True)
        pdf.ln(3)

    section("Severity Assessment", report.get("severity_assessment", ""))
    section("Detected Symptoms", report.get("detected_symptoms", []))
    section("Recommended Actions", report.get("recommended_actions", []))
    section("Preventive Measures", report.get("preventive_measures", []))
    if report.get("notes"):
        section("Notes", report["notes"])

    # ── Footer ────────────────────────────────────────────────────────────────
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, "SmartFarm AI — Informational only. Does not replace professional agronomy advice.", ln=True)

    buf = io.BytesIO()
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    return pdf_bytes

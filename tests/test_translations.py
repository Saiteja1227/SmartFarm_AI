"""Tests for centralized translation system and multilingual AI/ML recommendations."""
import json
import re
from pathlib import Path

from app.translations import LANGUAGES, get_all_translations, translate, translate_report
from app.services.ai_service import analyze_image
import io
from PIL import Image
import base64

ROOT = Path(__file__).resolve().parent.parent


def test_translation_files_exist_and_match():
    en_path = ROOT / "translations/en.json"
    hi_path = ROOT / "translations/hi.json"
    te_path = ROOT / "translations/te.json"

    assert en_path.exists(), "translations/en.json must exist"
    assert hi_path.exists(), "translations/hi.json must exist"
    assert te_path.exists(), "translations/te.json must exist"

    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)
    with open(hi_path, "r", encoding="utf-8") as f:
        hi = json.load(f)
    with open(te_path, "r", encoding="utf-8") as f:
        te = json.load(f)

    assert len(en) >= 200, f"Expected 200+ keys in en.json, got {len(en)}"
    assert set(en.keys()) == set(hi.keys()), f"Key diff between en and hi: {set(en.keys()) ^ set(hi.keys())}"
    assert set(en.keys()) == set(te.keys()), f"Key diff between en and te: {set(en.keys()) ^ set(te.keys())}"

    # Ensure no empty values
    for k, v in en.items():
        assert v.strip(), f"Empty value for {k} in en.json"
    for k, v in hi.items():
        assert v.strip(), f"Empty value for {k} in hi.json"
    for k, v in te.items():
        assert v.strip(), f"Empty value for {k} in te.json"


def test_ui_translations():
    assert translate("en", "nav.analyze") == "Analyze"
    assert translate("hi", "nav.analyze") == "विश्लेषण"
    assert translate("te", "nav.analyze") == "విశ్లేషణ"

    assert translate("en", "nav.history") == "History"
    assert translate("hi", "nav.history") == "इतिहास"
    assert translate("te", "nav.history") == "చరిత్ర"

    assert translate("en", "status.Healthy") == "Healthy"
    assert translate("hi", "status.Healthy") == "स्वस्थ"
    assert translate("te", "status.Healthy") == "ఆరోగ్యకరం"

    assert translate("en", "stress.High") == "High"
    assert translate("hi", "stress.High") == "अधिक"
    assert translate("te", "stress.High") == "అధికం"


def test_translate_report_hindi():
    sample = {
        "plant_health_status": "Unhealthy",
        "predicted_disease": "Late Blight",
        "confidence_score": 85,
        "water_stress_level": "High",
        "detected_symptoms": ["Brown spots", "Lesions"],
        "severity_assessment": "Late blight detected with 85% confidence. Serious fungal disease.",
        "recommended_actions": [
            "Remove and destroy affected plants immediately",
            "Apply fungicide containing chlorothalonil",
        ],
        "preventive_measures": [
            "Use certified disease-free seeds",
            "Plant resistant varieties",
        ],
        "notes": "Two-stage analysis: Health=Unhealthy, Disease=Late Blight, Confidence=85%, Water Stress=High.",
    }

    hi_rep = translate_report(sample, "hi")

    # Enums must remain strictly English for API/DB contracts
    assert hi_rep["plant_health_status"] == "Unhealthy"
    assert hi_rep["water_stress_level"] == "High"
    assert hi_rep["confidence_score"] == 85

    # Human-facing text must be Hindi / Devanagari script
    devanagari = re.compile(r"[\u0900-\u097F]")
    assert devanagari.search(hi_rep["predicted_disease"])
    assert any(devanagari.search(s) for s in hi_rep["detected_symptoms"])
    assert any(devanagari.search(a) for a in hi_rep["recommended_actions"])
    assert any(devanagari.search(p) for p in hi_rep["preventive_measures"])
    assert devanagari.search(hi_rep["severity_assessment"])
    assert devanagari.search(hi_rep["notes"])


def test_translate_report_telugu():
    sample = {
        "plant_health_status": "Unhealthy",
        "predicted_disease": "Early Blight",
        "confidence_score": 75,
        "water_stress_level": "Moderate",
        "detected_symptoms": ["Yellow patches", "Circular lesions"],
        "severity_assessment": "Early blight detected with 75% confidence. Fungal infection likely.",
        "recommended_actions": [
            "Remove affected leaves to prevent spread",
            "Apply copper-based fungicide",
        ],
        "preventive_measures": [
            "Space plants properly for airflow",
            "Water at base of plants, not leaves",
        ],
        "notes": "Two-stage analysis: Health=Unhealthy, Disease=Early Blight, Confidence=75%, Water Stress=Moderate.",
    }

    te_rep = translate_report(sample, "te")

    # Enums must remain strictly English for API/DB contracts
    assert te_rep["plant_health_status"] == "Unhealthy"
    assert te_rep["water_stress_level"] == "Moderate"
    assert te_rep["confidence_score"] == 75

    # Human-facing text must be Telugu script
    telugu = re.compile(r"[\u0C00-\u0C7F]")
    assert telugu.search(te_rep["predicted_disease"])
    assert any(telugu.search(s) for s in te_rep["detected_symptoms"])
    assert any(telugu.search(a) for a in te_rep["recommended_actions"])
    assert any(telugu.search(p) for p in te_rep["preventive_measures"])
    assert telugu.search(te_rep["severity_assessment"])
    assert telugu.search(te_rep["notes"])


def test_translate_report_healthy_telugu_roundtrip():
    sample_healthy = {
        "plant_health_status": "Healthy",
        "predicted_disease": "Healthy",
        "confidence_score": 85,
        "water_stress_level": "Low",
        "detected_symptoms": [
            "No visible disease symptoms",
            "Uniform green color",
            "No lesions or spots"
        ],
        "severity_assessment": "Plant appears healthy with no obvious signs of disease.",
        "recommended_actions": [
            "Maintain current watering schedule",
            "Monitor for any changes in leaf appearance",
            "Maintain proper plant nutrition"
        ],
        "preventive_measures": [
            "Regularly inspect plants for early signs of disease",
            "Maintain proper spacing between plants",
            "Ensure good air circulation"
        ],
        "notes": "Two-stage analysis: Health=Healthy, Disease=Healthy, Confidence=85%, Water Stress=Low."
    }

    te = translate_report(sample_healthy, "te")
    assert te["plant_health_status"] == "Healthy"
    assert te["water_stress_level"] == "Low"
    assert te["confidence_score"] == 85
    assert te["predicted_disease"] == "ఆరోగ్యకరమైనది"
    assert te["severity_assessment"] == "మొక్క ఆరోగ్యంగా కనిపిస్తోంది మరియు ఎటువంటి వ్యాధి లక్షణాలు లేవు."
    assert "కనిపించే వ్యాధి లక్షణాలు లేవు" in te["detected_symptoms"]
    assert "ప్రస్తుత నీటి షెడ్యూల్‌ను కొనసాగించండి" in te["recommended_actions"]
    assert "మొక్కల మధ్య సరైన దూరం పాటించండి" in te["preventive_measures"]
    assert "రెండు-దశల విశ్లేషణ" in te["notes"]
    assert "ఆరోగ్యం=ఆరోగ్యకరం" in te["notes"]

    # Roundtrip back to English
    en = translate_report(te, "en")
    assert en["predicted_disease"] == "Healthy"
    assert en["severity_assessment"] == "Plant appears healthy with no obvious signs of disease."
    assert "No visible disease symptoms" in en["detected_symptoms"]
    assert "Maintain current watering schedule" in en["recommended_actions"]
    assert "Maintain proper spacing between plants" in en["preventive_measures"]
    assert "Two-stage analysis" in en["notes"]


def test_ai_service_analyze_image_multilingual():
    img = Image.new("RGB", (224, 224), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # English
    res_en = analyze_image(b64, "Tomato", "en")
    assert res_en["plant_health_status"] in {"Healthy", "Unhealthy", "Uncertain"}

    # Hindi
    res_hi = analyze_image(b64, "Tomato", "hi")
    devanagari = re.compile(r"[\u0900-\u097F]")
    assert devanagari.search(res_hi["predicted_disease"]) or devanagari.search(res_hi["severity_assessment"])

    # Telugu
    res_te = analyze_image(b64, "Tomato", "te")
    telugu = re.compile(r"[\u0C00-\u0C7F]")
    assert telugu.search(res_te["predicted_disease"]) or telugu.search(res_te["severity_assessment"])


if __name__ == "__main__":
    test_translation_files_exist_and_match()
    test_ui_translations()
    test_translate_report_hindi()
    test_translate_report_telugu()
    test_translate_report_healthy_telugu_roundtrip()
    test_ai_service_analyze_image_multilingual()
    print("All translation tests passed successfully!")

"""AI analysis service — wraps CNN model for disease detection and water stress estimation."""
import json
import logging
import re
import os
import uuid

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "te": "Telugu (తెలుగు)",
    "ta": "Tamil (தமிழ்)",
    "bn": "Bengali (বাংলা)",
    "mr": "Marathi (मराठी)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "gu": "Gujarati (ગુજરાતી)",
}

SUPPORTED_LANGUAGES = set(LANGUAGE_NAMES.keys())

SYSTEM_PROMPT = """You are an experienced agronomist and plant pathology specialist.
You analyze plant leaf images to detect diseases and water stress, and provide practical
recommendations for home gardeners and urban farmers.

You MUST respond ONLY with a valid JSON object (no markdown, no backticks, no prose).
The JSON object must follow this exact schema:
{{
  "plant_health_status": "Healthy" | "Unhealthy" | "Uncertain",
  "predicted_disease": string,
  "confidence_score": integer (0-100),
  "water_stress_level": "Low" | "Moderate" | "High" | "Critical",
  "detected_symptoms": [string, ...],
  "severity_assessment": string,
  "recommended_actions": [string, ...],
  "preventive_measures": [string, ...],
  "is_plant_image": boolean,
  "notes": string
}}

Rules:
- Practical and actionable, written for home gardeners.
- Do not invent diseases unsupported by visible symptoms.
- If the image is NOT a plant/leaf, set is_plant_image=false, predicted_disease="N/A",
  confidence_score=0, and explain in notes.
- If confidence is low (< 60), state uncertainty in the notes.
- Keep each list item short (under 18 words).
- Total content must be under 250 words.
- Focus only on plant health, disease detection, and water stress.
- LANGUAGE RULE: Respond in {LANGUAGE_NAME}. Keep these two field VALUES strictly in English
  so the UI can interpret them: `plant_health_status` (Healthy/Unhealthy/Uncertain) and
  `water_stress_level` (Low/Moderate/High/Critical). All other text VALUES — including
  predicted_disease, severity_assessment, detected_symptoms, recommended_actions,
  preventive_measures and notes — must be written in {LANGUAGE_NAME}.
"""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise


def _coerce_report(parsed: dict) -> dict:
    def as_list(x):
        if isinstance(x, list):
            return [str(i).strip() for i in x if str(i).strip()]
        if isinstance(x, str) and x.strip():
            return [x.strip()]
        return []

    valid_stress = {"Low", "Moderate", "High", "Critical"}
    valid_status = {"Healthy", "Unhealthy", "Uncertain"}

    stress = str(parsed.get("water_stress_level", "Low")).title()
    if stress not in valid_stress:
        stress = "Low"

    status = str(parsed.get("plant_health_status", "Uncertain")).title()
    if status not in valid_status:
        status = "Uncertain"

    try:
        conf = int(parsed.get("confidence_score", 0))
    except (TypeError, ValueError):
        conf = 0
    conf = max(0, min(100, conf))

    return {
        "plant_health_status": status,
        "predicted_disease": str(parsed.get("predicted_disease", "Unknown")).strip() or "Unknown",
        "confidence_score": conf,
        "water_stress_level": stress,
        "detected_symptoms": as_list(parsed.get("detected_symptoms")),
        "severity_assessment": str(parsed.get("severity_assessment", "")).strip(),
        "recommended_actions": as_list(parsed.get("recommended_actions")),
        "preventive_measures": as_list(parsed.get("preventive_measures")),
        "is_plant_image": bool(parsed.get("is_plant_image", True)),
        "notes": str(parsed.get("notes", "")).strip(),
    }


def _build_user_prompt(crop_hint: str, language_code: str) -> str:
    language_name = LANGUAGE_NAMES.get(language_code, "English")
    base = (
        f"Analyze this plant leaf image and produce the JSON report exactly as instructed. "
        f"Write text values in {language_name}."
    )
    crop = f" Crop hint provided by the user: {crop_hint}." if crop_hint else ""
    tail = " If the image is not a plant/leaf, set is_plant_image=false and respond accordingly."
    return base + crop + tail


def _get_fallback_response(language_name: str, crop_hint: str) -> dict:
    """
    Return a structured fallback response when AI analysis fails.
    This ensures the app continues to work even when vision models are unavailable.
    """
    crop_info = f" for {crop_hint}" if crop_hint else ""
    
    return {
        "plant_health_status": "Uncertain",
        "predicted_disease": "Analysis unavailable",
        "confidence_score": 0,
        "water_stress_level": "Low",
        "detected_symptoms": [
            "AI vision service temporarily unavailable",
            "Please try again later"
        ],
        "severity_assessment": f"Unable to analyze leaf image{crop_info} due to service limitations.",
        "recommended_actions": [
            "Check leaf for visible spots or discoloration",
            "Ensure proper watering and sunlight",
            "Consult local agricultural extension if symptoms persist"
        ],
        "preventive_measures": [
            "Regularly inspect plants for early signs of disease",
            "Maintain proper spacing between plants",
            "Avoid overhead watering to reduce fungal risk"
        ],
        "is_plant_image": True,
        "notes": "AI analysis service is currently experiencing issues. This is a fallback response. Please try uploading the image again later."
    }


def analyze_image(img_b64: str, crop_hint: str, language_code: str) -> dict:
    """
    Analyze plant leaf image using CNN models for disease detection and water stress estimation.
    Returns structured analysis with recommendations.
    """
    try:
        from app.services.cnn_analysis import analyze_with_cnn
    except ImportError as exc:
        raise RuntimeError(
            "CNN analysis service not available. "
            "Ensure TensorFlow is installed and models are trained."
        ) from exc

    try:
        # Use CNN analysis
        result = analyze_with_cnn(img_b64, crop_hint, language_code)
        if language_code and language_code != "en":
            from app.translations import translate_report
            result = translate_report(result, language_code)
        return result
    except Exception as exc:
        logger.exception("CNN analysis failed, using fallback")
        # Return fallback response on error
        language_name = LANGUAGE_NAMES.get(language_code, "English")
        fallback = _get_fallback_response(language_name, crop_hint)
        if language_code and language_code != "en":
            from app.translations import translate_report
            fallback = translate_report(fallback, language_code)
        return fallback

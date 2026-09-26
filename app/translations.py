"""UI translations — centralized translations loader and report translation helper."""
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LANGUAGES = [
    {"code": "en", "label": "English",  "native": "English",     "bcp47": "en-US"},
    {"code": "hi", "label": "Hindi",    "native": "हिन्दी",       "bcp47": "hi-IN"},
    {"code": "te", "label": "Telugu",   "native": "తెలుగు",       "bcp47": "te-IN"},
    {"code": "ta", "label": "Tamil",    "native": "தமிழ்",        "bcp47": "ta-IN"},
    {"code": "bn", "label": "Bengali",  "native": "বাংলা",        "bcp47": "bn-IN"},
    {"code": "mr", "label": "Marathi",  "native": "मराठी",        "bcp47": "mr-IN"},
    {"code": "kn", "label": "Kannada",  "native": "ಕನ್ನಡ",        "bcp47": "kn-IN"},
    {"code": "gu", "label": "Gujarati", "native": "ગુજરાતી",      "bcp47": "gu-IN"},
]

DEFAULT_LANGUAGE = "en"

# Base directory for translation JSON files
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TRANSLATIONS_DIR = _PROJECT_ROOT / "translations"


def _load_json_translations(lang: str) -> Dict[str, str]:
    json_path = _TRANSLATIONS_DIR / f"{lang}.json"
    if json_path.is_file():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not read %s: %s", json_path, exc)
    return {}


_en = _load_json_translations("en")
_hi = _load_json_translations("hi")
_te = _load_json_translations("te")

# Existing stubs for other languages
_ta = {
    "nav.analyze": "பகுப்பாய்வு", "nav.history": "வரலாறு", "nav.language": "மொழி",
    "hero.title1": "ஒரே இலையில் இருந்து", "hero.title2": "தாவர நோயைக் கண்டறியுங்கள்.",
    "hero.cta": "இலையை பகுப்பாய்வு செய்", "hero.howCta": "எப்படி வேலை செய்கிறது",
    "uploader.analyzeBtn": "இலையை பகுப்பாய்வு செய்", "uploader.analyzing": "பகுப்பாய்வு செய்கிறது…",
    "report.health": "ஆரோக்கிய நிலை", "report.disease": "சாத்தியமான நோய்",
    "report.speak": "கேள்", "report.stop": "நிறுத்து",
    "status.Healthy": "ஆரோக்கியம்", "status.Unhealthy": "நோய்வாய்ப்பட்டது", "status.Uncertain": "நிச்சயமற்றது",
    "history.title": "ஸ்கேன் வரலாறு", "detail.back": "வரலாற்றுக்கு திரும்பு",
}

_bn = {
    "nav.analyze": "বিশ্লেষণ", "nav.history": "ইতিহাস", "nav.language": "ভাষা",
    "hero.title1": "একটি পাতা থেকে", "hero.title2": "গাছের রোগ চিহ্নিত করুন।",
    "hero.cta": "পাতা বিশ্লেষণ করুন",
    "uploader.analyzeBtn": "পাতা বিশ্লেষণ করুন", "uploader.analyzing": "বিশ্লেষণ চলছে…",
    "report.speak": "শুনুন", "report.stop": "থামান",
    "status.Healthy": "সুস্থ", "status.Unhealthy": "অসুস্থ", "status.Uncertain": "অনিশ্চিত",
    "history.title": "স্ক্যান ইতিহাস", "detail.back": "ইতিহাসে ফিরুন",
}

_mr = {
    "nav.analyze": "विश्लेषण", "nav.history": "इतिहास", "nav.language": "भाषा",
    "hero.title1": "एका पानावरून", "hero.title2": "वनस्पतीचा रोग ओळखा.",
    "hero.cta": "पानाचे विश्लेषण करा",
    "uploader.analyzeBtn": "पानाचे विश्लेषण करा", "uploader.analyzing": "विश्लेषण होत आहे…",
    "report.speak": "ऐका", "report.stop": "थांबवा",
    "status.Healthy": "निरोगी", "status.Unhealthy": "अनारोग्यकर", "status.Uncertain": "अनिश्चित",
    "history.title": "स्कॅन इतिहास", "detail.back": "इतिहासाकडे परत",
}

_kn = {
    "nav.analyze": "ವಿಶ್ಲೇಷಣೆ", "nav.history": "ಇತಿಹಾಸ", "nav.language": "ಭಾಷೆ",
    "hero.title1": "ಒಂದು ಎಲೆಯಿಂದ", "hero.title2": "ಸಸ್ಯ ರೋಗವನ್ನು ಪತ್ತೆಹಚ್ಚಿ.",
    "hero.cta": "ಎಲೆಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ",
    "uploader.analyzeBtn": "ಎಲೆಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ", "uploader.analyzing": "ವಿಶ್ಲೇಷಣೆ ನಡೆಯುತ್ತಿದೆ…",
    "report.speak": "ಆಲಿಸಿ", "report.stop": "ನಿಲ್ಲಿಸಿ",
    "status.Healthy": "ಆರೋಗ್ಯಕರ", "status.Unhealthy": "ಅನಾರೋಗ್ಯಕರ", "status.Uncertain": "ಅನಿಶ್ಚಿತ",
    "history.title": "ಸ್ಕ್ಯಾನ್ ಇತಿಹಾಸ", "detail.back": "ಇತಿಹಾಸಕ್ಕೆ ಹಿಂದಿರುಗಿ",
}

_gu = {
    "nav.analyze": "વિશ્લેષણ", "nav.history": "ઇતિહાસ", "nav.language": "ભાષા",
    "hero.title1": "એક પાંદડામાંથી", "hero.title2": "છોડનો રોગ ઓળખો.",
    "hero.cta": "પાંદડાનું વિશ્લેષણ",
    "uploader.analyzeBtn": "પાંદડાનું વિશ્લેષણ", "uploader.analyzing": "વિશ્લેષણ ચાલુ છે…",
    "report.speak": "સાંભળો", "report.stop": "રોકો",
    "status.Healthy": "સ્વસ્થ", "status.Unhealthy": "અસ્વસ્થ", "status.Uncertain": "અનિશ્ચિત",
    "history.title": "સ્કેન ઇતિહાસ", "detail.back": "ઇતિહાસ પર પાછા",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": _en,
    "hi": _hi,
    "te": _te,
    "ta": _ta,
    "bn": _bn,
    "mr": _mr,
    "kn": _kn,
    "gu": _gu,
}

# Build reverse index for cross-language lookup
_REVERSE_INDEX: Dict[str, str] = {}
for lang_dict in (_en, _hi, _te):
    for key, text in lang_dict.items():
        if text and isinstance(text, str):
            _REVERSE_INDEX[text.strip().lower()] = key


def translate(lang: str, key: str, default: Optional[str] = None) -> str:
    """Translate a key into the given language with English fallback."""
    d = TRANSLATIONS.get(lang, _en)
    if key in d:
        return d[key]
    if key in _en:
        return _en[key]
    return default if default is not None else key


def get_all_translations(lang: str) -> Dict[str, str]:
    """Return merged dict (lang overrides + English fallbacks) for a language."""
    base = dict(_en)
    overrides = TRANSLATIONS.get(lang, {})
    base.update(overrides)
    return base


def _find_key_for_text(text: str) -> Optional[str]:
    """Find the translation key corresponding to a given localized or English text."""
    if not text:
        return None
    normalized = text.strip().lower()
    return _REVERSE_INDEX.get(normalized)


def _translate_item(text: str, prefix: str, target_lang: str) -> str:
    """Translate an individual item by checking direct key or reverse index."""
    if not text:
        return ""
    text_clean = text.strip()
    direct_key = f"{prefix}.{text_clean}"
    if direct_key in _en:
        return translate(target_lang, direct_key)
    
    no_punct = re.sub(r"[.,!?:;]+$", "", text_clean).strip()
    clean_key = f"{prefix}.{no_punct}"
    if clean_key in _en:
        return translate(target_lang, clean_key)
    
    key = _find_key_for_text(text_clean) or _find_key_for_text(no_punct)
    if key and key.startswith(prefix):
        return translate(target_lang, key)
    
    target_lower = text_clean.lower()
    target_no_punct = no_punct.lower()
    for dict_lang in ("en", "hi", "te", "ta", "bn", "mr", "kn", "gu"):
        d = TRANSLATIONS.get(dict_lang, {})
        for k, v in d.items():
            if k.startswith(prefix):
                v_clean = v.strip().lower()
                v_no_punct = re.sub(r"[.,!?:;]+$", "", v_clean).strip()
                if v_clean == target_lower or v_no_punct == target_no_punct:
                    return translate(target_lang, k)

    return text


def _translate_severity(severity: str, disease: str, confidence: int, target_lang: str) -> str:
    """Translate severity assessment string into target language."""
    if not severity:
        return ""
    
    s = severity.lower()
    if target_lang == "en":
        if "healthy" in s or "स्वस्थ" in severity or "ఆరోగ్య" in severity:
            return "Plant appears healthy with no obvious signs of disease."
        if "late blight" in s or "पछेती" in severity or "లేట్ బ్లైట్" in severity or "ఆలస్యపు" in severity:
            return f"Late blight detected with {confidence}% confidence. Serious fungal disease."
        if "early blight" in s or "अगेती" in severity or "ఎర్లీ బ్లైట్" in severity or "ముందస్తు" in severity:
            return f"Early blight detected with {confidence}% confidence. Fungal infection likely."
        if "leaf mold" in s or "मोल्ड" in severity or "ఆకు బూజు" in severity:
            return f"Leaf mold detected with {confidence}% confidence. Fungal infection present."
        if "septoria" in s or "सेप्टोरिया" in severity or "సెప్టోరియా" in severity:
            return f"Septoria leaf spot detected with {confidence}% confidence. Common fungal disease."
        if "bacterial" in s or "जीवाणु" in severity or "बैक्टीरियल" in severity or "బాక్టీరియల్" in severity:
            return f"Bacterial spot detected with {confidence}% confidence. Bacterial infection."
        if "uncertain" in s or "अनिश्चित" in severity or "అనిశ్చిత" in severity:
            return f"Uncertain result with {confidence}% confidence. Manual verification recommended."
        if "unable" in s or "असमर्थ" in severity or "విశ్లేషించలేకపోయాము" in severity:
            return "Unable to analyze leaf image due to service limitations."
        if "స్పష్టంగా లేదు" in severity or "स्पष्ट नहीं" in severity:
            return f"Disease detected with {confidence}% confidence. Specific type unclear."
        return severity

    if target_lang == "hi":
        if "healthy" in s or "स्वस्थ" in severity or "ఆరోగ్య" in severity:
            return "पौधा स्वस्थ दिखता है और बीमारी का कोई स्पष्ट संकेत नहीं है।"
        if "late blight" in s or "पछेती" in severity or "లేట్ బ్లైట్" in severity or "ఆలస్యపు" in severity:
            return f"पछेती झुलसा {confidence}% विश्वास के साथ पहचाना गया। गंभीर फंगल रोग।"
        if "early blight" in s or "अगेती" in severity or "ఎర్లీ బ్లైట్" in severity or "ముందస్తు" in severity:
            return f"अगेती झुलसा {confidence}% विश्वास के साथ पहचाना गया। फंगल संक्रमण की संभावना।"
        if "leaf mold" in s or "मोल्ड" in severity or "ఆకు బూజు" in severity:
            return f"लीफ मोल्ड {confidence}% विश्वास के साथ पहचाना गया। फंगल संक्रमण मौजूद है।"
        if "septoria" in s or "सेप्टोरिया" in severity or "సెప్టోరియా" in severity:
            return f"सेप्टोरिया लीफ स्पॉट {confidence}% विश्वास के साथ पहचाना गया। सामान्य फंगल रोग।"
        if "bacterial" in s or "जीवाणु" in severity or "बैक्टीरियल" in severity or "బాక్టీరియల్" in severity:
            return f"बैक्टीरियल स्पॉट {confidence}% विश्वास के साथ पहचाना गया। जीवाणु संक्रमण।"
        if "uncertain" in s or "अनिश्चित" in severity or "అనిశ్చిత" in severity:
            return f"अनिश्चित परिणाम {confidence}% विश्वास के साथ। मैन्युअल सत्यापन अनुशंसित।"
        if "unable" in s or "असमर्थ" in severity or "విశ్లేషించలేకపోయాము" in severity:
            return "सेवा सीमाओं के कारण पत्ती की छवि का विश्लेषण करने में असमर्थ।"
        return f"रोग {confidence}% विश्वास के साथ पहचाना गया। विशिष्ट प्रकार स्पष्ट नहीं है।"

    if target_lang == "te":
        if "healthy" in s or "ఆరోగ్య" in severity or "स्वस्थ" in severity:
            return "మొక్క ఆరోగ్యంగా కనిపిస్తోంది మరియు ఎటువంటి వ్యాధి లక్షణాలు లేవు."
        if "late blight" in s or "లేట్ బ్లైట్" in severity or "ఆలస్యపు" in severity or "पछेती" in severity:
            return f"లేట్ బ్లైట్ {confidence}% విశ్వాసంతో గుర్తించబడింది. తీవ్రమైన ఫంగల్ వ్యాధి."
        if "early blight" in s or "ఎర్లీ బ్లైట్" in severity or "ముందస్తు" in severity or "अगेती" in severity:
            return f"ఎర్లీ బ్లైట్ {confidence}% విశ్వాసంతో గుర్తించబడింది. ఫంగల్ ఇన్ఫెక్షన్ సంభావ్యత."
        if "leaf mold" in s or "ఆకు బూజు" in severity or "मोल्ड" in severity:
            return f"ఆకు బూజు తెగులు {confidence}% విశ్వాసంతో గుర్తించబడింది. ఫంగల్ ఇన్ఫెక్షన్ ఉంది."
        if "septoria" in s or "సెప్టోరియా" in severity or "सेप्टोरिया" in severity:
            return f"సెప్టోరియా ఆకు మచ్చ తెగులు {confidence}% విశ్వాసంతో గుర్తించబడింది. సాధారణ ఫంగల్ వ్యాధి."
        if "bacterial" in s or "బాక్టీరియల్" in severity or "जीवाणु" in severity or "बैक्टीरियल" in severity:
            return f"బాక్టీరియల్ స్పాట్ {confidence}% విశ్వాసంతో గుర్తించబడింది. బ్యాక్టీరియల్ ఇన్ఫెక్షన్."
        if "uncertain" in s or "అనిశ్చిత" in severity or "अनिश्चित" in severity:
            return f"అనిశ్చిత ఫలితం {confidence}% విశ్వాసంతో. మాన్యువల్ ధృవీకరణ సిఫార్సు చేయబడింది."
        if "unable" in s or "విశ్లేషించలేకపోయాము" in severity or "असमर्थ" in severity:
            return "సేవా పరిమితుల కారణంగా ఆకు చిత్రాన్ని విశ్లేషించలేకపోయాము."
        return f"వ్యాధి {confidence}% విశ్వాసంతో గుర్తించబడింది. నిర్దిష్ట రకం అస్పష్టంగా ఉంది."

    return severity


def _translate_notes(notes: str, health: str, disease: str, confidence: int, stress: str, target_lang: str) -> str:
    """Translate notes string into target language."""
    if not notes:
        return ""
    
    disease_translated = _translate_item(disease, "ml.disease", target_lang)
    health_translated = translate(target_lang, f"status.{health}", health)
    stress_translated = translate(target_lang, f"stress.{stress}", stress)

    if target_lang == "hi":
        if "two-stage" in notes.lower() or "विश्लेषण" in notes or "విశ్లేషణ" in notes:
            return f"दो-चरणीय विश्लेषण: स्वास्थ्य={health_translated}, रोग={disease_translated}, विश्वास={confidence}%, जल तनाव={stress_translated}।"
        if "experiencing issues" in notes.lower() or "fallback" in notes.lower() or "अस्थायी" in notes or "తాత్కాలికంగా" in notes:
            return "एआई विश्लेषण सेवा वर्तमान में समस्याओं का सामना कर रही है। यह एक वैकल्पिक प्रतिक्रिया है। कृपया बाद में छवि को पुनः अपलोड करें।"
        if "manual verification" in notes.lower() or "failed" in notes.lower() or "विफल" in notes or "విఫలమైంది" in notes:
            return "छवि विश्लेषण विफल रहा। मैन्युअल सत्यापन अनुशंसित।"
        return notes

    if target_lang == "te":
        if "two-stage" in notes.lower() or "విశ్లేషణ" in notes or "विश्लेषण" in notes:
            return f"రెండు-దశల విశ్లేషణ: ఆరోగ్యం={health_translated}, వ్యాధి={disease_translated}, విశ్వాసం={confidence}%, నీటి ఒత్తిడి={stress_translated}."
        if "experiencing issues" in notes.lower() or "fallback" in notes.lower() or "తాత్కాలికంగా" in notes or "अस्थायी" in notes:
            return "AI విశ్లేషణ సేవ ప్రస్తుతం సమస్యలను ఎదుర్కొంటోంది. ఇది ప్రత్యామ్నాయ ప్రతిస్పందన. దయచేసి తర్వాత మళ్ళీ చిత్రాన్ని అప్‌లోడ్ చేయడానికి ప్రయత్నించండి."
        if "manual verification" in notes.lower() or "failed" in notes.lower() or "విఫలమైంది" in notes or "विफल" in notes:
            return "చిత్ర విశ్లేషణ విఫలమైంది. మాన్యువల్ ధృవీకరణ సిఫార్సు చేయబడింది."
        return notes

    if target_lang == "en":
        if "two-stage" in notes.lower() or "విశ్లేషణ" in notes or "विश्लेषण" in notes:
            en_disease = _translate_item(disease, "ml.disease", "en")
            return f"Two-stage analysis: Health={health}, Disease={en_disease}, Confidence={confidence}%, Water Stress={stress}."
        if "अस्थायी" in notes or "తాత్కాలికంగా" in notes:
            return "AI analysis service is currently experiencing issues. This is a fallback response. Please try uploading the image again later."
        if "विफल" in notes or "విఫలమైంది" in notes:
            return "Image analysis failed. Manual verification recommended."
        return notes

    return notes


def translate_report(report: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
    """
    Translate an AI/ML scan report into target_lang ('en', 'hi', 'te', etc.).
    Preserves enums: plant_health_status and water_stress_level remain English enums.
    Translates: predicted_disease, detected_symptoms, severity_assessment,
    recommended_actions, preventive_measures, notes.
    """
    if not report or not target_lang:
        return report

    copied = dict(report)
    health = copied.get("plant_health_status", "Uncertain")
    stress = copied.get("water_stress_level", "Low")
    disease = copied.get("predicted_disease", "Unknown")
    confidence = int(copied.get("confidence_score", 0))

    # Translate disease
    copied["predicted_disease"] = _translate_item(disease, "ml.disease", target_lang)

    # Translate symptoms
    symptoms = copied.get("detected_symptoms") or []
    copied["detected_symptoms"] = [_translate_item(s, "ml.symptom", target_lang) for s in symptoms]

    # Translate recommended actions
    actions = copied.get("recommended_actions") or []
    copied["recommended_actions"] = [_translate_item(a, "ml.action", target_lang) for a in actions]

    # Translate preventive measures
    preventive = copied.get("preventive_measures") or []
    copied["preventive_measures"] = [_translate_item(p, "ml.preventive", target_lang) for p in preventive]

    # Translate severity assessment
    severity = copied.get("severity_assessment", "")
    copied["severity_assessment"] = _translate_severity(severity, disease, confidence, target_lang)

    # Translate notes
    notes = copied.get("notes", "")
    copied["notes"] = _translate_notes(notes, health, disease, confidence, stress, target_lang)

    return copied

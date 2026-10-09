"""Centralized translation loader and dynamic ML report translator for SmartFarm AI."""
import json
import os
import re
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_TRANS_DIR = _BASE_DIR / "translations"

LANGUAGES = [
    {"code": "en", "label": "English",  "native": "English",  "bcp47": "en-US"},
    {"code": "hi", "label": "Hindi",    "native": "हिन्दी",    "bcp47": "hi-IN"},
    {"code": "te", "label": "Telugu",   "native": "తెలుగు",   "bcp47": "te-IN"},
    {"code": "ta", "label": "Tamil",    "native": "தமிழ்",    "bcp47": "ta-IN"},
    {"code": "bn", "label": "Bengali",  "native": "বাংলা",    "bcp47": "bn-IN"},
    {"code": "mr", "label": "Marathi",  "native": "मराठी",    "bcp47": "mr-IN"},
    {"code": "kn", "label": "Kannada",  "native": "ಕನ್ನಡ",    "bcp47": "kn-IN"},
    {"code": "gu", "label": "Gujarati", "native": "ગુજરાતી",  "bcp47": "gu-IN"},
]

SUPPORTED_LANG_CODES = [lang["code"] for lang in LANGUAGES]


def _load_json(lang_code: str) -> dict:
    file_path = _TRANS_DIR / f"{lang_code}.json"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


TRANSLATIONS = {code: _load_json(code) for code in SUPPORTED_LANG_CODES}


def get_translation_dict(lang: str) -> dict:
    """Return merged translation dictionary (with English fallback for any missing keys)."""
    base = dict(TRANSLATIONS.get("en", {}))
    if lang and lang != "en" and lang in TRANSLATIONS:
        base.update(TRANSLATIONS[lang])
    return base


# Alias for backward compatibility
get_all_translations = get_translation_dict


def t(key: str, lang: str = "en") -> str:
    """Translate a single key with fallback to English."""
    lang_dict = TRANSLATIONS.get(lang, {})
    if key in lang_dict:
        return lang_dict[key]
    return TRANSLATIONS.get("en", {}).get(key, key)


def translate(lang: str, key: str) -> str:
    """Translate a key given (lang, key) argument order."""
    return t(key, lang)


# Build reverse lookup maps so reports already translated to any supported language
# can be normalized back to English keys and re-translated to any target language.
_REVERSE_INDEX = {}
for _lang_code, _d in TRANSLATIONS.items():
    for _k, _v in _d.items():
        if _k.startswith("ml.") and not _k.startswith(("ml.severity.", "ml.notes.")):
            _REVERSE_INDEX[_v.strip().lower()] = _k

# Stress word reverse map across all 8 languages -> canonical English stress level
_STRESS_REVERSE = {
    "low": "Low",
    "moderate": "Moderate",
    "high": "High",
    "critical": "Critical",
}
for _lang_code, _d in TRANSLATIONS.items():
    for _lvl in ("Low", "Moderate", "High", "Critical"):
        _val = _d.get(f"stress.{_lvl}", "").strip().lower()
        if _val:
            _STRESS_REVERSE[_val] = _lvl

# Status word reverse map across all 8 languages -> canonical English status
_STATUS_REVERSE = {
    "healthy": "Healthy",
    "unhealthy": "Unhealthy",
    "uncertain": "Uncertain",
}
for _lang_code, _d in TRANSLATIONS.items():
    for _st in ("Healthy", "Unhealthy", "Uncertain"):
        _val = _d.get(f"status.{_st}", "").strip().lower()
        if _val:
            _STATUS_REVERSE[_val] = _st


def _template_to_regex(tmpl: str) -> re.Pattern:
    """Convert a parameterized translation template into a regex pattern."""
    escaped = re.escape(tmpl.strip())
    escaped = escaped.replace(re.escape("{confidence}"), r"(?P<confidence>\d+)")
    escaped = escaped.replace(re.escape("{stress}"), r"(?P<stress>.+?)")
    escaped = escaped.replace(re.escape("{status}"), r"(?P<status>.+?)")
    escaped = escaped.replace(re.escape("{crop}"), r"(?P<crop>.*?)")
    escaped = escaped.replace(re.escape("{crop_note}"), r"(?P<crop_note>.*?)")
    return re.compile(f"^{escaped}$", re.IGNORECASE | re.DOTALL)


_SEVERITY_KEYS = [
    "ml.severity.healthy",
    "ml.severity.late_blight",
    "ml.severity.early_blight",
    "ml.severity.leaf_mold",
    "ml.severity.septoria",
    "ml.severity.bacterial_spot",
    "ml.severity.unhealthy_unknown",
    "ml.severity.low_conf",
    "ml.severity.unable_analyze",
    "ml.severity.service_limit",
]

_SEVERITY_PATTERNS = []
for _skey in _SEVERITY_KEYS:
    for _lcode in SUPPORTED_LANG_CODES:
        _tmpl = TRANSLATIONS.get(_lcode, {}).get(_skey)
        if _tmpl:
            _SEVERITY_PATTERNS.append((_skey, _lcode, _template_to_regex(_tmpl)))

_NOTES_KEYS = [
    "ml.notes.two_stage",
    "ml.notes.binary",
    "ml.notes.low_conf",
    "ml.notes.tech_error",
    "ml.notes.fallback",
]

_NOTES_PATTERNS = []
for _nkey in _NOTES_KEYS:
    for _lcode in SUPPORTED_LANG_CODES:
        _tmpl = TRANSLATIONS.get(_lcode, {}).get(_nkey)
        if _tmpl:
            _NOTES_PATTERNS.append((_nkey, _lcode, _template_to_regex(_tmpl)))

_CROP_CONTEXT_PATTERNS = []
for _lcode in SUPPORTED_LANG_CODES:
    _ctmpl = TRANSLATIONS.get(_lcode, {}).get("ml.notes.crop_context")
    if _ctmpl:
        _CROP_CONTEXT_PATTERNS.append(_template_to_regex(_ctmpl))

_FOR_CROP_PATTERNS = []
for _lcode in SUPPORTED_LANG_CODES:
    _fctmpl = TRANSLATIONS.get(_lcode, {}).get("ml.severity.for_crop")
    if _fctmpl:
        _FOR_CROP_PATTERNS.append(_template_to_regex(_fctmpl))


def _format_stress_for_lang(canonical_stress: str, target_lang: str) -> str:
    """Return the localized stress word suitable for insertion into a severity sentence."""
    lvl = canonical_stress.strip().title() if canonical_stress else "Low"
    if lvl not in ("Low", "Moderate", "High", "Critical"):
        lvl = _STRESS_REVERSE.get(canonical_stress.strip().lower(), "Low")
    if target_lang == "en":
        return lvl.lower()
    return t(f"stress.{lvl}", target_lang)


def _format_status_for_lang(canonical_status: str, target_lang: str) -> str:
    """Return the localized status word suitable for insertion into a notes sentence."""
    st = canonical_status.strip().title() if canonical_status else "Healthy"
    if st not in ("Healthy", "Unhealthy", "Uncertain"):
        st = _STATUS_REVERSE.get(canonical_status.strip().lower(), "Healthy")
    if target_lang == "en":
        return st.lower()
    return t(f"status.{st}", target_lang)


def _translate_severity(text: str, target_lang: str, report_context: dict = None) -> str:
    """Translate dynamic severity_assessment string into any of the 8 supported languages."""
    if not text:
        return text

    s = text.strip()
    ctx = report_context or {}

    # 1. Match against all registered template patterns across all 8 languages
    for skey, _src_lang, regex in _SEVERITY_PATTERNS:
        m = regex.match(s)
        if m:
            gd = m.groupdict()
            conf = gd.get("confidence") or str(ctx.get("confidence_score", 0))
            raw_stress = gd.get("stress", "")
            canon_stress = ctx.get("water_stress_level") or _STRESS_REVERSE.get(raw_stress.strip().lower(), "Low")
            stress_str = _format_stress_for_lang(canon_stress, target_lang)

            raw_crop = (gd.get("crop") or "").strip()
            crop_name = ctx.get("crop_name") or ""
            if not crop_name and raw_crop:
                for fc_re in _FOR_CROP_PATTERNS:
                    fcm = fc_re.match(raw_crop)
                    if fcm and fcm.groupdict().get("crop"):
                        crop_name = fcm.groupdict()["crop"].strip()
                        break
                if not crop_name:
                    crop_name = raw_crop

            crop_clause = t("ml.severity.for_crop", target_lang).format(crop=crop_name) if crop_name else ""
            target_tmpl = t(skey, target_lang)
            return target_tmpl.format(confidence=conf, stress=stress_str, crop=crop_clause)

    # 2. Fallback: reconstruct from report_context if available
    if ctx and "confidence_score" in ctx:
        conf = str(ctx.get("confidence_score", 0))
        canon_stress = ctx.get("water_stress_level", "Low")
        stress_str = _format_stress_for_lang(canon_stress, target_lang)
        raw_dis = str(ctx.get("predicted_disease", ""))
        eng_dis_key = _REVERSE_INDEX.get(raw_dis.strip().lower())
        eng_dis = TRANSLATIONS["en"].get(eng_dis_key, raw_dis) if eng_dis_key else raw_dis

        dis_to_skey = {
            "Healthy": "ml.severity.healthy",
            "Late Blight": "ml.severity.late_blight",
            "Early Blight": "ml.severity.early_blight",
            "Leaf Mold": "ml.severity.leaf_mold",
            "Septoria Leaf Spot": "ml.severity.septoria",
            "Bacterial Spot": "ml.severity.bacterial_spot",
            "Unhealthy (Unknown Type)": "ml.severity.unhealthy_unknown",
            "Uncertain Result - Manual Verification Recommended": "ml.severity.low_conf",
        }
        skey = dis_to_skey.get(eng_dis)
        if skey:
            return t(skey, target_lang).format(confidence=conf, stress=stress_str, crop="")

    return text


def _translate_notes(text: str, target_lang: str, report_context: dict = None) -> str:
    """Translate dynamic notes string into any of the 8 supported languages."""
    if not text:
        return text

    s = text.strip()
    ctx = report_context or {}

    # Check if the enhanced-image note suffix is attached
    has_enhanced_note = bool(ctx.get("image_enhanced"))
    for lcode in SUPPORTED_LANG_CODES:
        enh_suffix = TRANSLATIONS.get(lcode, {}).get("ml.notes.enhanced", "").strip()
        if enh_suffix and enh_suffix in s:
            has_enhanced_note = True
            s = s.replace(enh_suffix, "").strip()

    def _append_enhanced(base_note: str) -> str:
        if has_enhanced_note:
            enh = t("ml.notes.enhanced", target_lang)
            if enh.strip() not in base_note:
                return base_note.rstrip() + " " + enh.strip()
        return base_note

    for nkey, _src_lang, regex in _NOTES_PATTERNS:
        m = regex.match(s)
        if m:
            gd = m.groupdict()
            conf = gd.get("confidence") or str(ctx.get("confidence_score", 0))
            raw_status = gd.get("status", "")
            canon_status = ctx.get("plant_health_status") or _STATUS_REVERSE.get(raw_status.strip().lower(), "Healthy")
            status_str = _format_status_for_lang(canon_status, target_lang)

            raw_crop_note = (gd.get("crop_note") or "").strip()
            crop_name = ctx.get("crop_name") or ""
            if not crop_name and raw_crop_note:
                for cc_re in _CROP_CONTEXT_PATTERNS:
                    ccm = cc_re.match(raw_crop_note)
                    if ccm and ccm.groupdict().get("crop"):
                        crop_name = ccm.groupdict()["crop"].strip()
                        break

            crop_note_str = t("ml.notes.crop_context", target_lang).format(crop=crop_name) if crop_name else ""
            target_tmpl = t(nkey, target_lang)
            rendered = target_tmpl.format(confidence=conf, status=status_str, crop_note=crop_note_str)
            return _append_enhanced(rendered)

    # Fallback: reconstruct from report_context if legacy notes string
    if ctx and "plant_health_status" in ctx:
        crop_name = ctx.get("crop_name") or ""
        crop_note_str = t("ml.notes.crop_context", target_lang).format(crop=crop_name) if crop_name else ""
        if ctx.get("plant_health_status") == "Uncertain":
            conf = str(ctx.get("confidence_score", 0))
            rendered = t("ml.notes.low_conf", target_lang).format(confidence=conf, crop_note=crop_note_str)
            return _append_enhanced(rendered)
        rendered = t("ml.notes.two_stage", target_lang).format(crop_note=crop_note_str)
        return _append_enhanced(rendered)

    return _append_enhanced(text)


def translate_ml_item(item: str, prefix: str, target_lang: str) -> str:
    """Translate a single ML output item (disease, symptom, action, preventive measure)."""
    if not item:
        return item
    clean = item.strip()
    direct_key = f"{prefix}.{clean}"
    lang_dict = get_translation_dict(target_lang)
    if direct_key in lang_dict:
        return lang_dict[direct_key]

    rev_key = _REVERSE_INDEX.get(clean.lower())
    if rev_key and rev_key in lang_dict:
        return lang_dict[rev_key]

    return item


def translate_report(report: dict, target_lang: str) -> dict:
    """Translate all user-facing text fields of an ML analysis report into target_lang."""
    if not report or not isinstance(report, dict):
        return report
    if target_lang not in SUPPORTED_LANG_CODES:
        target_lang = "en"

    out = dict(report)

    if "predicted_disease" in out and out["predicted_disease"]:
        out["predicted_disease"] = translate_ml_item(out["predicted_disease"], "ml.disease", target_lang)

    if "detected_symptoms" in out and isinstance(out["detected_symptoms"], list):
        out["detected_symptoms"] = [
            translate_ml_item(s, "ml.symptom", target_lang) for s in out["detected_symptoms"]
        ]

    if "recommended_actions" in out and isinstance(out["recommended_actions"], list):
        out["recommended_actions"] = [
            translate_ml_item(a, "ml.action", target_lang) for a in out["recommended_actions"]
        ]

    if "preventive_measures" in out and isinstance(out["preventive_measures"], list):
        out["preventive_measures"] = [
            translate_ml_item(p, "ml.preventive", target_lang) for p in out["preventive_measures"]
        ]

    if "severity_assessment" in out and out["severity_assessment"]:
        out["severity_assessment"] = _translate_severity(out["severity_assessment"], target_lang, report_context=report)

    if "notes" in out and out["notes"]:
        out["notes"] = _translate_notes(out["notes"], target_lang, report_context=report)

    return out

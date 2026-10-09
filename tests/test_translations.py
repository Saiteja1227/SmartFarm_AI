"""Comprehensive tests for all 3 required changes in SmartFarm AI:
1. Complete 8-Language Website Multi-Language Support (en, hi, te, ta, bn, mr, kn, gu)
2. Human-Readable Multilingual PDF Reports in the Selected Language
3. Blurry Leaf Image Detection, Enhancement & Side-by-Side Original vs Enhanced Display
"""
import base64
import io
import json
import re
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from app import create_app
from app.services.ai_service import analyze_image
from app.services.cnn_analysis import analyze_with_cnn, detect_and_enhance_blurry_image
from app.services.pdf_service import generate_pdf_bytes
from app.translations import (
    LANGUAGES,
    SUPPORTED_LANG_CODES,
    get_all_translations,
    translate,
    translate_report,
)

ROOT = Path(__file__).resolve().parent.parent

SCRIPT_REGEXES = {
    "en": re.compile(r"[A-Za-z]"),
    "hi": re.compile(r"[\u0900-\u097F]"),  # Devanagari
    "mr": re.compile(r"[\u0900-\u097F]"),  # Devanagari
    "te": re.compile(r"[\u0C00-\u0C7F]"),  # Telugu
    "ta": re.compile(r"[\u0B80-\u0BFF]"),  # Tamil
    "bn": re.compile(r"[\u0980-\u09FF]"),  # Bengali
    "kn": re.compile(r"[\u0C80-\u0CFF]"),  # Kannada
    "gu": re.compile(r"[\u0A80-\u0AFF]"),  # Gujarati
}


def _make_sharp_and_blurry_leaf_b64():
    sharp_img = Image.new("RGB", (300, 300), (32, 128, 42))
    draw = ImageDraw.Draw(sharp_img)
    for i in range(12, 288, 12):
        draw.line([(150, i), (28, i - 14)], fill=(95, 205, 85), width=2)
        draw.line([(150, i), (272, i - 14)], fill=(95, 205, 85), width=2)
    for x, y in [(85, 95), (195, 145), (125, 215)]:
        draw.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(105, 55, 25), outline=(225, 195, 45), width=2)

    buf_s = io.BytesIO()
    sharp_img.save(buf_s, format="JPEG", quality=95)
    sharp_b64 = base64.b64encode(buf_s.getvalue()).decode("ascii")

    blurry_img = sharp_img.filter(ImageFilter.GaussianBlur(radius=4.5))
    buf_b = io.BytesIO()
    blurry_img.save(buf_b, format="JPEG", quality=90)
    blurry_b64 = base64.b64encode(buf_b.getvalue()).decode("ascii")

    return sharp_b64, blurry_b64


class TestSmartFarmThreeChanges(unittest.TestCase):

    def test_1_all_8_translation_files_exist_and_have_full_key_parity(self):
        expected_langs = ["en", "hi", "te", "ta", "bn", "mr", "kn", "gu"]
        self.assertEqual(SUPPORTED_LANG_CODES, expected_langs)

        en_dict = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(en_dict), 250)

        for lang in expected_langs:
            fpath = ROOT / f"translations/{lang}.json"
            self.assertTrue(fpath.exists(), f"Missing translation file: {fpath}")
            data = json.loads(fpath.read_text(encoding="utf-8"))
            self.assertEqual(
                set(en_dict.keys()),
                set(data.keys()),
                f"Key mismatch in {lang}.json: {set(en_dict.keys()) ^ set(data.keys())}",
            )
            for k, v in data.items():
                self.assertTrue(str(v).strip(), f"Empty translation for {k} in {lang}.json")

            # Verify native script characters appear in UI & ML keys
            script_re = SCRIPT_REGEXES[lang]
            for check_key in [
                "nav.analyze",
                "nav.history",
                "hero.title1",
                "uploader.analyzeBtn",
                "report.overline",
                "report.originalImage",
                "report.enhancedImage",
                "pdf.title",
            ]:
                self.assertIsNotNone(
                    script_re.search(data[check_key]),
                    f"Key {check_key} in {lang} does not match expected script: {data[check_key]}",
                )

    def test_2_multihop_report_translation_across_all_8_languages(self):
        sample = {
            "plant_health_status": "Unhealthy",
            "predicted_disease": "Early Blight",
            "confidence_score": 88,
            "water_stress_level": "Moderate",
            "crop_name": "Tomato",
            "detected_symptoms": ["Brown spots", "Yellow patches", "Circular lesions"],
            "severity_assessment": (
                "Moderate severity (88% confidence). Early blight typically affects lower leaves first. "
                "Water stress is moderate."
            ),
            "recommended_actions": [
                "Remove affected leaves to prevent spread",
                "Apply copper-based fungicide",
                "Increase watering frequency slightly",
            ],
            "preventive_measures": [
                "Space plants properly for airflow",
                "Water at base of plants, not leaves",
            ],
            "notes": (
                "Two-stage analysis: Binary health classification followed by disease identification. "
                "Contextualized for Tomato. Based on visible symptoms only."
            ),
            "image_enhanced": True,
        }

        cur = sample
        # Hop through every single language in sequence and back to English
        for lang in ["te", "hi", "ta", "bn", "mr", "kn", "gu", "en"]:
            cur = translate_report(cur, lang)
            self.assertEqual(cur["plant_health_status"], "Unhealthy")
            self.assertEqual(cur["water_stress_level"], "Moderate")
            self.assertEqual(cur["confidence_score"], 88)

            script_re = SCRIPT_REGEXES[lang]
            self.assertIsNotNone(script_re.search(cur["predicted_disease"]), f"Failed disease in {lang}")
            self.assertIsNotNone(script_re.search(cur["severity_assessment"]), f"Failed severity in {lang}")
            self.assertIsNotNone(script_re.search(cur["notes"]), f"Failed notes in {lang}")
            self.assertTrue(all(script_re.search(s) for s in cur["detected_symptoms"]), f"Failed symptoms in {lang}")
            self.assertTrue(all(script_re.search(a) for a in cur["recommended_actions"]), f"Failed actions in {lang}")
            self.assertTrue(all(script_re.search(p) for p in cur["preventive_measures"]), f"Failed preventive in {lang}")

        # Verify clean round-trip back to English
        self.assertEqual(cur["predicted_disease"], "Early Blight")
        self.assertIn("Moderate severity (88% confidence)", cur["severity_assessment"])
        self.assertIn("Remove affected leaves to prevent spread", cur["recommended_actions"])

    def test_3_blurry_vs_sharp_leaf_image_detection_and_enhancement(self):
        sharp_b64, blurry_b64 = _make_sharp_and_blurry_leaf_b64()

        # Sharp image -> not blurry, not enhanced
        sharp_res = analyze_with_cnn(sharp_b64, "Tomato", "en")
        self.assertFalse(sharp_res["is_blurry"])
        self.assertFalse(sharp_res["image_enhanced"])
        self.assertEqual(sharp_res["enhancement_status"], "not_needed")
        self.assertIsNone(sharp_res["enhanced_image_base64"])

        # Blurry image -> detected as blurry, enhanced, and enhanced image returned
        blurry_res = analyze_with_cnn(blurry_b64, "Tomato", "en")
        self.assertTrue(blurry_res["is_blurry"])
        self.assertTrue(blurry_res["image_enhanced"])
        self.assertEqual(blurry_res["enhancement_status"], "enhanced")
        self.assertIsNotNone(blurry_res["enhanced_image_base64"])
        self.assertGreater(blurry_res["enhanced_blur_score"], blurry_res["blur_score"])

        # Verify enhanced image is valid decodable high-clarity JPEG with preserved aspect ratio
        enh_bytes = base64.b64decode(blurry_res["enhanced_image_base64"])
        enh_pil = Image.open(io.BytesIO(enh_bytes))
        self.assertEqual(enh_pil.size[0], enh_pil.size[1])
        self.assertGreaterEqual(enh_pil.size[0], 900)

    def test_4_pdf_generation_in_all_8_languages_with_enhanced_images(self):
        sharp_b64, blurry_b64 = _make_sharp_and_blurry_leaf_b64()
        blurry_res = analyze_with_cnn(blurry_b64, "Tomato", "en")
        blurry_res["id"] = "test-scan-12345678"
        blurry_res["crop_name"] = "Tomato"
        blurry_res["image_base64"] = blurry_b64
        blurry_res["image_mime"] = "image/jpeg"
        blurry_res["created_at"] = "2026-10-09T10:00:00Z"

        for lang in SUPPORTED_LANG_CODES:
            pdf_bytes = generate_pdf_bytes(blurry_res, lang=lang)
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"), f"Invalid PDF header for {lang}")
            self.assertGreater(len(pdf_bytes), 5000, f"PDF too small for {lang}")

    def test_5_flask_api_endpoints_for_translations_blur_and_pdf(self):
        app = create_app()
        client = app.test_client()
        headers = {"X-User-Id": "test-user-multilang"}

        # 1. Check /api/translations/<lang> for all 8 languages
        for lang in SUPPORTED_LANG_CODES:
            resp = client.get(f"/api/translations/{lang}")
            self.assertEqual(resp.status_code, 200)
            payload = resp.get_json()
            self.assertEqual(payload["language"], lang)
            self.assertGreaterEqual(len(payload["translations"]), 250)

        # 2. Upload a blurry leaf image in Tamil ('ta') and verify response + PDF download in Telugu ('te')
        _, blurry_b64 = _make_sharp_and_blurry_leaf_b64()
        blurry_bytes = base64.b64decode(blurry_b64)

        resp_analyze = client.post(
            "/api/analyze",
            headers=headers,
            data={
                "image": (io.BytesIO(blurry_bytes), "blurry_leaf.jpg"),
                "crop_name": "Tomato",
                "language": "ta",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp_analyze.status_code, 200)
        scan_doc = resp_analyze.get_json()
        self.assertTrue(scan_doc["is_blurry"])
        self.assertTrue(scan_doc["image_enhanced"])
        self.assertTrue(scan_doc["enhanced_image_base64"])
        self.assertIsNotNone(SCRIPT_REGEXES["ta"].search(scan_doc["predicted_disease"]))

        # 3. Download PDF for this scan in all 8 languages via /api/scan/<id>/pdf?lang=<code>
        scan_id = scan_doc["id"]
        for lang in SUPPORTED_LANG_CODES:
            pdf_resp = client.get(f"/api/scan/{scan_id}/pdf?lang={lang}", headers=headers)
            self.assertEqual(pdf_resp.status_code, 200)
            self.assertEqual(pdf_resp.mimetype, "application/pdf")
            self.assertIn(f"smartfarm-report-{lang}-", pdf_resp.headers.get("Content-Disposition", ""))
            self.assertTrue(pdf_resp.data.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()

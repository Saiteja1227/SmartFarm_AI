"""
Comprehensive tests for Plant & Leaf Image Validation in SmartFarm AI.
Covers all 9 required test cases:
1. Clear leaf image -> analyze normally
2. Plant image (multi-leaf / potted plant) -> analyze normally
3. Human face image -> reject with "Please upload a leaf or plant image for analysis."
4. Animal image -> reject
5. Vehicle or building image -> reject
6. Screenshot or text image -> reject
7. Corrupted or unsupported file -> display appropriate upload error
8. Blurry image containing a leaf -> allow validation & run image enhancement pipeline
9. Ambiguous image -> request a clearer plant image instead of producing an unreliable result
"""
import base64
import io
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from werkzeug.security import generate_password_hash

from app import create_app
from app.routes.admin import reset_rate_limits
from app.services.ai_service import analyze_image
from app.services.cnn_analysis import analyze_with_cnn
from app.services.plant_validator import (
    InvalidPlantImageError,
    VALIDATION_ERROR_MESSAGE,
    validate_leaf_or_plant_image,
)
from tests.test_cnn_analysis import (
    test_brown_spotted_leaf_is_not_classified_healthy,
    test_clean_green_leaf_is_healthy,
    test_green_leaf_with_vein_shadows_is_healthy,
    test_yellow_green_backlit_leaf_without_spots_is_healthy,
)


def _pil_to_jpeg_bytes(img: Image.Image, quality: int = 92) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _pil_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _make_clear_leaf_image(blurry: bool = False) -> bytes:
    """Create a realistic leaf image on a natural soil/earth background."""
    img = Image.new("RGB", (320, 320), (62, 54, 46))
    draw = ImageDraw.Draw(img)
    # Leaf blade polygon/ellipse
    draw.ellipse([36, 28, 284, 292], fill=(42, 138, 48), outline=(30, 105, 35), width=3)
    # Midrib and lateral veins
    draw.line([(160, 34), (160, 286)], fill=(110, 208, 92), width=4)
    for y in range(60, 270, 24):
        draw.line([(160, y), (68, y - 20)], fill=(98, 196, 82), width=2)
        draw.line([(160, y), (252, y - 20)], fill=(98, 196, 82), width=2)
    # A few disease lesions
    for cx, cy in [(115, 120), (205, 165), (135, 215)]:
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(108, 56, 24), outline=(220, 190, 45), width=2)
    if blurry:
        img = img.filter(ImageFilter.GaussianBlur(radius=4.5))
    return _pil_to_jpeg_bytes(img)


def _make_plant_canopy_image() -> bytes:
    """Create a multi-leaf potted/garden plant image with stems and multiple leaves."""
    img = Image.new("RGB", (320, 320), (215, 210, 200))
    draw = ImageDraw.Draw(img)
    # Terracotta pot at bottom
    draw.polygon([(110, 245), (210, 245), (195, 310), (125, 310)], fill=(165, 82, 52))
    # Stems
    draw.line([(160, 245), (160, 95)], fill=(48, 115, 42), width=6)
    draw.line([(160, 190), (95, 130)], fill=(48, 115, 42), width=4)
    draw.line([(160, 175), (225, 120)], fill=(48, 115, 42), width=4)
    # Multiple plant leaves forming canopy
    leaf_boxes = [
        (45, 95, 145, 165),
        (175, 90, 275, 160),
        (60, 155, 155, 225),
        (165, 150, 265, 220),
        (105, 40, 215, 125),
    ]
    for x0, y0, x1, y1 in leaf_boxes:
        draw.ellipse([x0, y0, x1, y1], fill=(46, 148, 52), outline=(32, 110, 38), width=2)
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        draw.line([(x0 + 10, my), (x1 - 10, my)], fill=(102, 202, 88), width=2)
    return _pil_to_jpeg_bytes(img)


def _make_human_face_image() -> bytes:
    """Create a human face / portrait image with skin tones, hair, eyes, nose, and mouth."""
    img = Image.new("RGB", (320, 320), (185, 202, 220))  # Soft blue-gray studio backdrop
    draw = ImageDraw.Draw(img)
    # Shoulders / shirt
    draw.ellipse([40, 235, 280, 360], fill=(45, 68, 115))
    # Neck
    draw.rectangle([130, 200, 190, 255], fill=(218, 164, 134))
    # Hair
    draw.ellipse([72, 28, 248, 215], fill=(42, 30, 24))
    # Face oval (human skin tone in YCbCr/RGB locus)
    draw.ellipse([86, 56, 234, 228], fill=(228, 174, 142), outline=(202, 148, 116), width=2)
    # Cheeks / shading
    draw.ellipse([98, 130, 138, 168], fill=(234, 162, 132))
    draw.ellipse([182, 130, 222, 168], fill=(234, 162, 132))
    # Eyebrows & eyes
    draw.line([(110, 108), (142, 106)], fill=(48, 34, 26), width=4)
    draw.line([(178, 106), (210, 108)], fill=(48, 34, 26), width=4)
    draw.ellipse([114, 116, 140, 130], fill=(248, 248, 248), outline=(60, 42, 34), width=2)
    draw.ellipse([180, 116, 206, 130], fill=(248, 248, 248), outline=(60, 42, 34), width=2)
    draw.ellipse([122, 118, 132, 128], fill=(52, 38, 28))
    draw.ellipse([188, 118, 198, 128], fill=(52, 38, 28))
    # Nose & lips
    draw.line([(160, 122), (154, 162), (168, 164)], fill=(188, 132, 104), width=3)
    draw.ellipse([134, 180, 186, 198], fill=(196, 98, 92))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    return _pil_to_jpeg_bytes(img)


def _make_animal_image() -> bytes:
    """Create an animal image (brown/golden dog portrait with fur, ears, eyes, dark snout)."""
    img = Image.new("RGB", (320, 320), (135, 165, 195))  # Outdoor sky/neutral backdrop
    draw = ImageDraw.Draw(img)
    # Small strip of distant ground at very bottom
    draw.rectangle([0, 265, 320, 320], fill=(120, 112, 95))
    # Dog body & furry head (warm brown/tan fur)
    draw.ellipse([70, 175, 250, 315], fill=(168, 118, 68))
    # Floppy ears
    draw.ellipse([52, 78, 112, 195], fill=(122, 78, 38))
    draw.ellipse([208, 78, 268, 195], fill=(122, 78, 38))
    # Head
    draw.ellipse([85, 65, 235, 215], fill=(182, 132, 78))
    # Muzzle
    draw.ellipse([115, 135, 205, 208], fill=(212, 175, 128))
    # Dark eyes & black nose
    draw.ellipse([118, 105, 138, 125], fill=(28, 22, 18))
    draw.ellipse([182, 105, 202, 125], fill=(28, 22, 18))
    draw.ellipse([142, 145, 178, 172], fill=(32, 26, 24))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.7))
    return _pil_to_jpeg_bytes(img)


def _make_vehicle_image() -> bytes:
    """Create a vehicle image (red/silver car on an asphalt road against sky)."""
    img = Image.new("RGB", (320, 320), (145, 185, 235))  # Sky
    draw = ImageDraw.Draw(img)
    # Asphalt road
    draw.rectangle([0, 200, 320, 320], fill=(68, 70, 74))
    # Car body & cabin
    draw.rectangle([38, 145, 282, 215], fill=(198, 36, 42), outline=(140, 20, 25), width=2)
    draw.polygon([(78, 145), (112, 96), (218, 96), (252, 145)], fill=(198, 36, 42))
    # Glass windows
    draw.polygon([(88, 142), (116, 102), (160, 102), (160, 142)], fill=(175, 210, 235))
    draw.polygon([(166, 142), (166, 102), (214, 102), (242, 142)], fill=(175, 210, 235))
    # Wheels / tires
    draw.ellipse([65, 185, 125, 245], fill=(25, 25, 28), outline=(180, 184, 190), width=5)
    draw.ellipse([195, 185, 255, 245], fill=(25, 25, 28), outline=(180, 184, 190), width=5)
    return _pil_to_jpeg_bytes(img)


def _make_building_image() -> bytes:
    """Create a building / architecture image with concrete/brick facade and rectangular windows."""
    img = Image.new("RGB", (320, 320), (165, 198, 235))  # Sky
    draw = ImageDraw.Draw(img)
    # Building facade
    draw.rectangle([45, 35, 275, 320], fill=(178, 168, 156), outline=(110, 102, 94), width=3)
    # Grid of glass windows
    for row_y in range(55, 265, 48):
        for col_x in range(65, 245, 45):
            draw.rectangle([col_x, row_y, col_x + 28, row_y + 32], fill=(72, 105, 138), outline=(230, 230, 230), width=2)
    # Entrance door
    draw.rectangle([135, 268, 185, 320], fill=(64, 48, 38))
    return _pil_to_jpeg_bytes(img)


def _make_screenshot_or_text_image(with_green_ui_banner: bool = False) -> bytes:
    """Create a document / screenshot image with horizontal lines of text and optional green UI bar."""
    img = Image.new("RGB", (320, 320), (248, 249, 250))
    draw = ImageDraw.Draw(img)
    if with_green_ui_banner:
        # Simulate a website screenshot with a green top navbar and a green CTA button
        draw.rectangle([0, 0, 320, 42], fill=(28, 88, 45))
        draw.rectangle([24, 255, 145, 288], fill=(38, 135, 58))
    # Simulate dense lines of text / character glyphs
    for y in range(62, 238, 16):
        x = 24
        while x < 285:
            word_w = ((x * 7 + y * 3) % 28) + 10
            for gx in range(x, min(x + word_w, 290), 4):
                draw.rectangle([gx, y, gx + 2, y + 7], fill=(32, 35, 40))
            x += word_w + 8
    return _pil_to_png_bytes(img)


def _make_ambiguous_image(kind: str = "dark") -> bytes:
    """Create an ambiguous image (severely dark, overexposed, or tiny indistinct green spot)."""
    if kind == "dark":
        # Extremely dark underexposed photo
        arr = np.full((256, 256, 3), 8, dtype=np.uint8)
        arr[100:150, 100:150, 1] = 18
        return _pil_to_jpeg_bytes(Image.fromarray(arr))
    elif kind == "tiny_speck":
        # Mostly soil/wood background with only a tiny ~11% distant green patch
        img = Image.new("RGB", (300, 300), (118, 96, 78))
        draw = ImageDraw.Draw(img)
        draw.ellipse([120, 120, 215, 215], fill=(48, 138, 52))
        return _pil_to_jpeg_bytes(img)
    else:
        # Random static noise
        rng = np.random.default_rng(42)
        arr = rng.integers(0, 255, size=(256, 256, 3), dtype=np.uint8)
        return _pil_to_png_bytes(Image.fromarray(arr))


class TestPlantImageValidation(unittest.TestCase):

    def setUp(self):
        reset_rate_limits()
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-plant-validation"
        self.app.config["ADMIN_USERNAME"] = "owner_admin"
        self.app.config["ADMIN_PASSWORD"] = ""
        self.app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash("Sup3rS3cur3_Own3r#2026")
        self.client = self.app.test_client()
        self.headers = {"X-User-Id": "validation-tester-12345678"}

    def _get_admin_scan_count(self) -> int:
        from app.models.scan import get_admin_scans_and_stats
        with self.app.app_context():
            data = get_admin_scans_and_stats(page=1, per_page=50)
            return data["stats"]["total_scans"]

    def test_0_existing_cnn_unit_tests_continue_to_pass(self):
        test_clean_green_leaf_is_healthy()
        test_green_leaf_with_vein_shadows_is_healthy()
        test_yellow_green_backlit_leaf_without_spots_is_healthy()
        test_brown_spotted_leaf_is_not_classified_healthy()

    def test_1_clear_leaf_image_analyzed_normally(self):
        leaf_bytes = _make_clear_leaf_image(blurry=False)
        before_count = self._get_admin_scan_count()

        res = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "crop_name": "Tomato",
                "language": "en",
                "image": (io.BytesIO(leaf_bytes), "clear_leaf.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["is_plant_image"])
        self.assertTrue(body["scan_saved"])
        self.assertIn(body["plant_health_status"], {"Healthy", "Unhealthy", "Uncertain"})
        self.assertIsInstance(body["confidence_score"], int)
        self.assertIn(body["water_stress_level"], {"Low", "Moderate", "High", "Critical"})
        self.assertEqual(self._get_admin_scan_count(), before_count + 1)

    def test_2_plant_canopy_image_analyzed_normally(self):
        plant_bytes = _make_plant_canopy_image()
        before_count = self._get_admin_scan_count()

        res = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "crop_name": "Basil",
                "language": "en",
                "image": (io.BytesIO(plant_bytes), "potted_plant.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["is_plant_image"])
        self.assertTrue(body["scan_saved"])
        self.assertIn(body["plant_health_status"], {"Healthy", "Unhealthy", "Uncertain"})
        self.assertEqual(self._get_admin_scan_count(), before_count + 1)

    def test_3_human_face_image_rejected_with_exact_message(self):
        face_bytes = _make_human_face_image()
        before_count = self._get_admin_scan_count()

        res = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "crop_name": "Tomato",
                "language": "en",
                "image": (io.BytesIO(face_bytes), "human_face.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertEqual(body["detail"], "Please upload a leaf or plant image for analysis.")
        self.assertEqual(body["message"], "Please upload a leaf or plant image for analysis.")
        self.assertFalse(body["is_plant_image"])
        self.assertFalse(body["scan_saved"])
        self.assertNotIn("predicted_disease", body)
        self.assertNotIn("confidence_score", body)
        self.assertEqual(self._get_admin_scan_count(), before_count)

    def test_4_animal_image_rejected_with_exact_message(self):
        animal_bytes = _make_animal_image()
        before_count = self._get_admin_scan_count()

        res = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "crop_name": "Potato",
                "language": "en",
                "image": (io.BytesIO(animal_bytes), "dog_photo.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertEqual(body["detail"], "Please upload a leaf or plant image for analysis.")
        self.assertFalse(body["is_plant_image"])
        self.assertFalse(body["scan_saved"])
        self.assertNotIn("predicted_disease", body)

        # Also test animal sitting on a green grass lawn (grass around border, animal in center)
        dog_lawn = Image.new("RGB", (320, 320), (52, 138, 48))
        d2 = ImageDraw.Draw(dog_lawn)
        d2.ellipse([75, 70, 245, 270], fill=(165, 112, 64))
        d2.ellipse([110, 95, 210, 195], fill=(185, 132, 78))
        d2.ellipse([145, 145, 175, 170], fill=(25, 22, 20))
        res_lawn = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "crop_name": "Tomato",
                "language": "en",
                "image": (io.BytesIO(_pil_to_jpeg_bytes(dog_lawn)), "dog_on_lawn.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res_lawn.status_code, 400)
        self.assertEqual(res_lawn.get_json()["detail"], "Please upload a leaf or plant image for analysis.")
        self.assertEqual(self._get_admin_scan_count(), before_count)

    def test_5_vehicle_and_building_images_rejected(self):
        before_count = self._get_admin_scan_count()

        for label, img_bytes in [("car.jpg", _make_vehicle_image()), ("building.jpg", _make_building_image())]:
            res = self.client.post(
                "/api/analyze",
                headers=self.headers,
                data={
                    "crop_name": "Tomato",
                    "language": "en",
                    "image": (io.BytesIO(img_bytes), label, "image/jpeg"),
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 400, f"Expected 400 for {label}")
            body = res.get_json()
            self.assertEqual(body["detail"], "Please upload a leaf or plant image for analysis.")
            self.assertFalse(body["is_plant_image"])
            self.assertFalse(body["scan_saved"])
            self.assertNotIn("predicted_disease", body)

        self.assertEqual(self._get_admin_scan_count(), before_count)

    def test_6_screenshot_and_text_images_rejected(self):
        before_count = self._get_admin_scan_count()

        for label, img_bytes in [
            ("document_text.png", _make_screenshot_or_text_image(with_green_ui_banner=False)),
            ("ui_screenshot.png", _make_screenshot_or_text_image(with_green_ui_banner=True)),
        ]:
            res = self.client.post(
                "/api/analyze",
                headers=self.headers,
                data={
                    "crop_name": "Tomato",
                    "language": "en",
                    "image": (io.BytesIO(img_bytes), label, "image/png"),
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 400, f"Expected 400 for {label}")
            body = res.get_json()
            self.assertEqual(body["detail"], "Please upload a leaf or plant image for analysis.")
            self.assertFalse(body["is_plant_image"])
            self.assertFalse(body["scan_saved"])
            self.assertNotIn("predicted_disease", body)

        self.assertEqual(self._get_admin_scan_count(), before_count)

    def test_7_corrupted_or_unsupported_files_rejected_with_upload_error(self):
        before_count = self._get_admin_scan_count()

        # 7a. Corrupted JPEG bytes claiming to be image/jpeg
        res_corrupt = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "image": (io.BytesIO(b"\xff\xd8\xff\xe0corrupted-not-a-real-jpeg-data"), "broken.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res_corrupt.status_code, 400)
        body_corrupt = res_corrupt.get_json()
        self.assertEqual(body_corrupt["validation_status"], "corrupted")
        self.assertIn("Invalid or corrupted image file", body_corrupt["detail"])
        self.assertFalse(body_corrupt["scan_saved"])

        # 7b. Unsupported file format (text/plain or application/pdf)
        res_unsupported = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "image": (io.BytesIO(b"hello world text file"), "notes.txt", "text/plain"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res_unsupported.status_code, 400)
        self.assertIn("Only JPEG, PNG, or WEBP images are accepted", res_unsupported.get_json()["detail"])

        self.assertEqual(self._get_admin_scan_count(), before_count)

    def test_8_blurry_leaf_image_passes_validation_and_triggers_enhancement(self):
        blurry_leaf_bytes = _make_clear_leaf_image(blurry=True)
        before_count = self._get_admin_scan_count()

        res = self.client.post(
            "/api/analyze",
            headers=self.headers,
            data={
                "crop_name": "Tomato",
                "language": "en",
                "image": (io.BytesIO(blurry_leaf_bytes), "blurry_leaf.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["is_plant_image"])
        self.assertTrue(body["is_blurry"])
        self.assertTrue(body["image_enhanced"])
        self.assertIsNotNone(body["enhanced_image_base64"])
        self.assertTrue(body["scan_saved"])
        self.assertEqual(self._get_admin_scan_count(), before_count + 1)

    def test_9_ambiguous_images_rejected_and_request_clearer_image(self):
        before_count = self._get_admin_scan_count()

        for kind in ["dark", "tiny_speck", "noise"]:
            amb_bytes = _make_ambiguous_image(kind=kind)
            res = self.client.post(
                "/api/analyze",
                headers=self.headers,
                data={
                    "crop_name": "Tomato",
                    "language": "en",
                    "image": (io.BytesIO(amb_bytes), f"ambiguous_{kind}.jpg", "image/jpeg"),
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 400, f"Expected 400 for ambiguous_{kind}")
            body = res.get_json()
            self.assertEqual(body["detail"], VALIDATION_ERROR_MESSAGE)
            self.assertEqual(body["validation_status"], "ambiguous")
            self.assertIn("clearer", body["guidance"].lower())
            self.assertFalse(body["is_plant_image"])
            self.assertFalse(body["scan_saved"])
            self.assertNotIn("predicted_disease", body)

        # Also verify direct backend calls raise InvalidPlantImageError and do not return fallback reports
        face_b64 = base64.b64encode(_make_human_face_image()).decode("ascii")
        with self.assertRaises(InvalidPlantImageError):
            analyze_with_cnn(face_b64, "Tomato", "en")
        with self.assertRaises(InvalidPlantImageError):
            analyze_image(face_b64, "Tomato", "en")

        self.assertEqual(self._get_admin_scan_count(), before_count)


if __name__ == "__main__":
    unittest.main()

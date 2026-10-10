"""
Backend Plant & Leaf Image Validation Service for SmartFarm AI.

Validates uploaded images BEFORE running the plant disease detection pipeline.
Ensures that only valid leaf or plant images are analyzed, while rejecting:
- Human faces and portraits
- Animals and pets
- Vehicles, buildings, and man-made architecture
- Screenshots, text images, documents, charts, and UI graphics
- Food, everyday objects, and non-plant scenes
- Corrupted, unreadable, or extreme/ambiguous images
"""
import base64
import io
import logging
from typing import Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

logger = logging.getLogger(__name__)

VALIDATION_ERROR_MESSAGE = "Please upload a leaf or plant image for analysis."
CORRUPTED_IMAGE_MESSAGE = "Invalid or corrupted image file. Please upload a valid JPEG, PNG, or WEBP image."


class InvalidPlantImageError(ValueError):
    """Raised when an uploaded image is not a valid leaf or plant image."""

    def __init__(self, message: str = VALIDATION_ERROR_MESSAGE, validation: dict = None):
        super().__init__(message)
        self.message = message
        self.validation = validation or {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "message": message,
        }


def _detect_haar_face(gray_u8: np.ndarray) -> bool:
    """Use OpenCV Haar cascades (if available) to detect frontal/profile human faces."""
    if cv2 is None or not hasattr(cv2, "data"):
        return False
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            return False
        faces = face_cascade.detectMultiScale(
            gray_u8, scaleFactor=1.1, minNeighbors=5, minSize=(36, 36)
        )
        if len(faces) > 0:
            img_area = float(gray_u8.shape[0] * gray_u8.shape[1])
            max_face_area = max(float(w * h) for (_, _, w, h) in faces)
            if max_face_area / img_area >= 0.05:
                return True
    except Exception:
        pass
    return False


def _compute_gradients(lum: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute horizontal, vertical, and magnitude gradients on a [0, 1] luminance array."""
    gx = np.zeros_like(lum)
    gy = np.zeros_like(lum)
    gx[:, 1:-1] = (lum[:, 2:] - lum[:, :-2]) * 0.5
    gy[1:-1, :] = (lum[2:, :] - lum[:-2, :]) * 0.5
    mag = np.hypot(gx, gy)
    return gx, gy, mag


def validate_leaf_or_plant_image(raw_bytes: bytes) -> dict:
    """
    Inspect raw image bytes and determine whether the image contains a valid
    leaf or plant suitable for plant pathology analysis.

    Returns a dictionary:
      {
        "is_valid_plant": bool,
        "status": "valid" | "invalid_non_plant" | "ambiguous" | "corrupted",
        "confidence": float,
        "reason": str,
        "message": str,
        "guidance": str,
      }
    """
    if not raw_bytes or not isinstance(raw_bytes, (bytes, bytearray)):
        return {
            "is_valid_plant": False,
            "status": "corrupted",
            "confidence": 1.0,
            "reason": "Empty or missing image bytes.",
            "message": CORRUPTED_IMAGE_MESSAGE,
            "guidance": CORRUPTED_IMAGE_MESSAGE,
        }

    # ── Stage 1: Decode & Integrity Check ────────────────────────────────────
    try:
        pil_img = Image.open(io.BytesIO(raw_bytes))
        pil_img.load()
    except (UnidentifiedImageError, OSError, ValueError, Exception) as exc:
        logger.warning("Uploaded file could not be decoded as a valid image: %s", exc)
        return {
            "is_valid_plant": False,
            "status": "corrupted",
            "confidence": 1.0,
            "reason": "Corrupted or unreadable image file.",
            "message": CORRUPTED_IMAGE_MESSAGE,
            "guidance": CORRUPTED_IMAGE_MESSAGE,
        }

    w, h = pil_img.size
    if w < 24 or h < 24:
        return {
            "is_valid_plant": False,
            "status": "corrupted",
            "confidence": 1.0,
            "reason": f"Image dimensions ({w}x{h}) are too small for leaf analysis.",
            "message": CORRUPTED_IMAGE_MESSAGE,
            "guidance": CORRUPTED_IMAGE_MESSAGE,
        }

    aspect = max(w, h) / float(min(w, h))
    if aspect > 6.5:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.95,
            "reason": "Extreme banner/strip aspect ratio is not a valid leaf or plant photo.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    rgb_pil = pil_img.convert("RGB")
    work_pil = rgb_pil.resize((256, 256), Image.Resampling.BILINEAR)
    arr_u8 = np.asarray(work_pil, dtype=np.uint8)
    arr = arr_u8.astype(np.float32) / 255.0

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    lum = 0.299 * r + 0.587 * g + 0.114 * b
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    chroma = c_max - c_min
    sat = chroma / (c_max + 1e-5)

    # ── Stage 2: Exposure, Blank Canvas & Random Noise Check (Ambiguous) ─────
    mean_lum = float(np.mean(lum))
    std_lum = float(np.std(lum))
    p95_lum = float(np.percentile(lum, 95))
    mean_chroma = float(np.mean(chroma))

    # Pitch-dark / severely underexposed
    if mean_lum < 0.055 or p95_lum < 0.12:
        return {
            "is_valid_plant": False,
            "status": "ambiguous",
            "confidence": 0.90,
            "reason": "Image is too dark or underexposed to identify a plant or leaf.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": "Please upload a clearer, well-lit leaf or plant image for analysis.",
        }

    # Completely blown-out / overexposed white or near-blank canvas
    if mean_lum > 0.94 and std_lum < 0.045:
        return {
            "is_valid_plant": False,
            "status": "ambiguous",
            "confidence": 0.92,
            "reason": "Image is overexposed or blank and does not show a clear leaf or plant.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": "Please upload a clearer leaf or plant image for analysis.",
        }

    # Purely achromatic (grayscale / B&W / concrete / fog with near-zero color saturation)
    if mean_chroma < 0.042 and float(np.percentile(chroma, 90)) < 0.085:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.92,
            "reason": "Image lacks natural plant pigmentation (grayscale, document, or concrete scene).",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # High-frequency uncorrelated pixel noise check
    diff_h = np.abs(arr[:, 1:, :] - arr[:, :-1, :])
    diff_v = np.abs(arr[1:, :, :] - arr[:-1, :, :])
    mean_step = float(0.5 * (np.mean(diff_h) + np.mean(diff_v)))
    if mean_step > 0.21:
        return {
            "is_valid_plant": False,
            "status": "ambiguous",
            "confidence": 0.95,
            "reason": "Image contains excessive noise or distortion; no clear leaf structure found.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": "Please upload a clearer leaf or plant image for analysis.",
        }

    # ── Stage 3: Biophysical Chlorophyll & Carotenoid Spectral Masks ─────────
    # Excess Green (ExG = 2G - R - B) and Normalized Green-Blue Difference (NGBDI)
    exg = 2.0 * g - r - b
    ngbdi = (g - b) / (g + b + 1e-5)

    # 1. Healthy & moderately stressed chlorophyll green foliage
    green_foliage = (
        (g > b + 0.04)
        & (g >= r * 0.84)
        & (exg > 0.06)
        & (ngbdi > 0.10)
        & (sat > 0.10)
        & (lum >= 0.06)
        & (lum <= 0.95)
    )

    # 2. Carotenoid yellow-green / chlorotic leaf tissue
    # True yellow-green / chlorotic leaves have G >= R - 0.04 and strong Blue absorption (ExG > 0.10),
    # whereas warm brown/tan fur, skin, wood, or soil has R > G + 0.05 and low ExG.
    yellow_leaf_tissue = (
        (g > b + 0.10)
        & (r > b + 0.10)
        & (b < 0.38)
        & (r <= g + 0.04)
        & (exg > 0.10)
        & (sat > 0.24)
        & (lum >= 0.14)
        & (lum <= 0.90)
    )

    # 3. Shaded / deep dark-green foliage
    deep_green_foliage = (
        (g > r + 0.02)
        & (g > b + 0.03)
        & (exg > 0.045)
        & (sat > 0.14)
        & (lum >= 0.05)
        & (lum <= 0.36)
    )

    primary_plant_mask = green_foliage | yellow_leaf_tissue | deep_green_foliage
    plant_frac_total = float(np.mean(primary_plant_mask))

    # Central subject window (inner 60% x 60%: rows/cols 51..205 of 256)
    c0, c1 = 51, 205
    center_plant_mask = primary_plant_mask[c0:c1, c0:c1]
    plant_frac_center = float(np.mean(center_plant_mask))

    # Inner core window (inner 44% x 44%: rows/cols 72..184 of 256)
    k0, k1 = 72, 184
    plant_frac_core = float(np.mean(primary_plant_mask[k0:k1, k0:k1]))

    # Outer border ring fraction
    border_mask = np.ones_like(primary_plant_mask, dtype=bool)
    border_mask[c0:c1, c0:c1] = False
    plant_frac_border = float(np.mean(primary_plant_mask[border_mask]))

    # ── Stage 4: Screenshot, Text Document & Synthetic UI Detection ──────────
    # Check for paper/white/light-gray or dark-mode flat UI background
    white_doc_bg = (r > 0.84) & (g > 0.84) & (b > 0.84) & (chroma < 0.07)
    dark_ui_bg = (r < 0.17) & (g < 0.17) & (b < 0.22) & (chroma < 0.08)
    neutral_gray_bg = (lum >= 0.17) & (lum <= 0.84) & (chroma < 0.045)
    ui_bg_frac = float(np.mean(white_doc_bg | dark_ui_bg | neutral_gray_bg))

    # Exact pixel repetition along scanlines (characteristic of digital screenshots/text/UI)
    exact_run_h = np.max(np.abs(arr[:, 1:, :] - arr[:, :-1, :]), axis=2) < 0.0025
    exact_run_frac = float(np.mean(exact_run_h))

    # Rapid high-contrast text/glyph transitions along horizontal lines
    lum_jump_h = np.abs(lum[:, 1:] - lum[:, :-1]) > 0.26
    # Count rows that have many sharp text-like jumps (> 8 jumps in a 256px row)
    row_jump_counts = np.sum(lum_jump_h, axis=1)
    text_like_rows_frac = float(np.mean(row_jump_counts >= 8))

    gx, gy, gmag = _compute_gradients(lum)
    strong_edges = gmag > 0.12
    strong_edge_frac = float(np.mean(strong_edges))
    if strong_edge_frac > 0.015:
        ax_aligned = strong_edges & ((np.abs(gx) > 3.2 * np.abs(gy)) | (np.abs(gy) > 3.2 * np.abs(gx)))
        axis_aligned_ratio = float(np.sum(ax_aligned) / (np.sum(strong_edges) + 1e-5))
    else:
        axis_aligned_ratio = 0.0

    # Reject text documents, scanned pages, and UI screenshots
    if text_like_rows_frac > 0.18 and (ui_bg_frac > 0.35 or exact_run_frac > 0.30):
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.96,
            "reason": "Text document or screenshot detected instead of a leaf or plant photo.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    if exact_run_frac > 0.45 and ui_bg_frac > 0.42 and plant_frac_center < 0.40:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.94,
            "reason": "Digital screenshot, diagram, or UI graphic detected.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # Even if a screenshot contains a large green UI box/banner, digital UI boxes have
    # high exact horizontal runs + strong axis-aligned H/V edges + flat non-plant background.
    if exact_run_frac > 0.52 and axis_aligned_ratio > 0.58 and ui_bg_frac > 0.22:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.93,
            "reason": "Synthetic UI screenshot or graphic layout detected.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # ── Stage 5: Human Face, Portrait & Skin-Tone Detection ──────────────────
    # Convert RGB [0..255] to YCbCr for biophysical human skin locus detection
    r255 = arr_u8[:, :, 0].astype(np.float32)
    g255 = arr_u8[:, :, 1].astype(np.float32)
    b255 = arr_u8[:, :, 2].astype(np.float32)
    cb = 128.0 + (-0.148223 * r255 - 0.290993 * g255 + 0.439216 * b255)
    cr = 128.0 + (0.439216 * r255 - 0.367789 * g255 - 0.071427 * b255)

    skin_mask = (
        (r255 > 65.0)
        & (g255 > 30.0)
        & (b255 > 15.0)
        & (r255 > g255 + 6.0)
        & (r255 > b255 + 16.0)
        & (g255 >= b255 - 6.0)
        & (cb >= 77.0)
        & (cb <= 133.0)
        & (cr >= 131.0)
        & (cr <= 178.0)
        & ((2.0 * g255 - r255 - b255) < -4.0)
        & (~primary_plant_mask)
    )
    skin_frac_total = float(np.mean(skin_mask))
    skin_frac_center = float(np.mean(skin_mask[c0:c1, c0:c1]))

    gray_u8 = np.clip(lum * 255.0, 0, 255).astype(np.uint8)
    if _detect_haar_face(gray_u8) and plant_frac_center < 0.45:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.97,
            "reason": "Human face detected; image is not a plant or leaf.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # Reject portraits / faces / skin-dominated photos
    if (skin_frac_center > 0.16 or skin_frac_total > 0.15) and plant_frac_center < 0.38:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.94,
            "reason": "Human skin / portrait region dominates the frame instead of a leaf or plant.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # ── Stage 6: Non-Plant Chromaticity (Sky/Blue/Red/Brick/Fur/Asphalt) ─────
    # Blue/cyan/purple/magenta/sky/water/denim/paint (Blue > Green)
    blue_purple_mask = (b > g + 0.04) & (sat > 0.12)
    # Pure red/crimson/orange/pink/warm-brown where Red exceeds Green & ExG is non-positive
    red_warm_nonplant_mask = (r > g + 0.05) & (exg < 0.02) & (~primary_plant_mask)
    # Achromatic concrete/asphalt/metal/gray/white/black
    achromatic_mask = chroma < 0.055

    non_plant_evidence_mask = (blue_purple_mask | red_warm_nonplant_mask | achromatic_mask) & (~primary_plant_mask)
    non_plant_center_frac = float(np.mean(non_plant_evidence_mask[c0:c1, c0:c1]))
    non_plant_core_frac = float(np.mean(non_plant_evidence_mask[k0:k1, k0:k1]))

    # Account for necrotic brown disease spots ONLY when embedded in genuine leaf tissue
    brown_lesion_mask = (
        (r > g + 0.02)
        & (g > b + 0.01)
        & (b < r * 0.68)
        & (lum >= 0.06)
        & (lum <= 0.62)
        & (~primary_plant_mask)
    )
    if plant_frac_center >= 0.24 and plant_frac_total >= 0.18:
        effective_plant_center = min(1.0, plant_frac_center + float(np.mean(brown_lesion_mask[c0:c1, c0:c1])) * 0.7)
        effective_plant_total = min(1.0, plant_frac_total + float(np.mean(brown_lesion_mask)) * 0.7)
    else:
        effective_plant_center = plant_frac_center
        effective_plant_total = plant_frac_total

    # Clearly non-plant when almost no vegetative chlorophyll/carotenoid pixels exist
    if effective_plant_total < 0.03 and effective_plant_center < 0.04:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.96,
            "reason": "No recognizable plant leaf or foliage detected in the image.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # Ambiguous borderline band: some weak green/yellow-green pixels exist, but too sparse
    # or obscured to confidently confirm a leaf or plant for disease analysis
    if effective_plant_center < 0.22 or effective_plant_total < 0.14:
        return {
            "is_valid_plant": False,
            "status": "ambiguous",
            "confidence": 0.65,
            "reason": "Could not confidently determine that the image contains a clear leaf or plant.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": "Please upload a clearer, closer photo of a leaf or plant for analysis.",
        }

    # If the central core of the image is dominated by non-plant object (e.g. animal, car,
    # building, person, food dish) even if there is grass/trees around the border:
    if plant_frac_core < 0.25 and non_plant_core_frac > 0.50:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.93,
            "reason": "Central subject is a non-plant object (animal, vehicle, building, person, or object).",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # Animal / object in front of outdoor grass background:
    # Border has significantly more green than the central core, and central core is < 30% plant
    if (
        plant_frac_core < 0.28
        and plant_frac_border > plant_frac_core + 0.18
        and non_plant_core_frac > 0.42
    ):
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.91,
            "reason": "Foreground subject is not a leaf or plant.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # Building / vehicle / urban scene with strong rectilinear edges and low plant presence
    if axis_aligned_ratio > 0.52 and strong_edge_frac > 0.05 and plant_frac_center < 0.32:
        return {
            "is_valid_plant": False,
            "status": "invalid_non_plant",
            "confidence": 0.93,
            "reason": "Man-made rectilinear structure (building, vehicle, or screenshot) detected.",
            "message": VALIDATION_ERROR_MESSAGE,
            "guidance": VALIDATION_ERROR_MESSAGE,
        }

    # Valid leaf or plant image!
    plant_conf = float(min(0.99, max(0.72, 0.55 + 0.45 * max(effective_plant_center, effective_plant_total))))
    return {
        "is_valid_plant": True,
        "status": "valid",
        "confidence": round(plant_conf, 2),
        "reason": "Valid leaf or plant foliage confirmed.",
        "message": "Valid leaf or plant image.",
        "guidance": "",
    }


def validate_leaf_or_plant_b64(img_b64: str) -> dict:
    """Validate a base64-encoded image string before running disease analysis."""
    if not img_b64 or not isinstance(img_b64, str):
        return {
            "is_valid_plant": False,
            "status": "corrupted",
            "confidence": 1.0,
            "reason": "Empty or missing base64 image data.",
            "message": CORRUPTED_IMAGE_MESSAGE,
            "guidance": CORRUPTED_IMAGE_MESSAGE,
        }
    try:
        raw_bytes = base64.b64decode(img_b64)
    except Exception:
        return {
            "is_valid_plant": False,
            "status": "corrupted",
            "confidence": 1.0,
            "reason": "Invalid base64 image encoding.",
            "message": CORRUPTED_IMAGE_MESSAGE,
            "guidance": CORRUPTED_IMAGE_MESSAGE,
        }
    return validate_leaf_or_plant_image(raw_bytes)

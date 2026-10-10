"""Rule-based image analysis service for plant disease detection and water stress estimation."""
import os
import logging
import base64
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

logger = logging.getLogger(__name__)

# Sharpness threshold (variance of discrete 2D Laplacian on scale-normalized grayscale).
# Images below this threshold are detected as blurry and enhanced before analysis.
BLUR_SHARPNESS_THRESHOLD = 115.0


def _laplacian_variance(gray_arr: np.ndarray) -> float:
    """Compute discrete 2D Laplacian variance on a float32 grayscale array."""
    laplacian = (
        gray_arr[:-2, 1:-1]
        + gray_arr[2:, 1:-1]
        + gray_arr[1:-1, :-2]
        + gray_arr[1:-1, 2:]
        - 4.0 * gray_arr[1:-1, 1:-1]
    )
    return float(np.var(laplacian))


def compute_blur_score(pil_img: Image.Image) -> float:
    """
    Compute a multi-scale sharpness score using discrete 2D Laplacian variance.
    Evaluates sharpness at 256x256 and, for larger images, also checks native/512px
    scale so high-resolution out-of-focus photos are not masked by downsampling.
    """
    gray_pil = pil_img.convert("L")
    w, h = gray_pil.size
    g256 = np.asarray(gray_pil.resize((256, 256), Image.Resampling.BILINEAR), dtype=np.float32)
    s256 = _laplacian_variance(g256)
    if max(w, h) >= 384:
        ref_dim = min(max(w, h), 512)
        g_ref = np.asarray(gray_pil.resize((ref_dim, ref_dim), Image.Resampling.BILINEAR), dtype=np.float32)
        s_ref = _laplacian_variance(g_ref)
        return float(min(s256, s_ref * 1.6))
    return float(s256)


def _morph_dilate_erode_blur(arr: np.ndarray, ksize: int, sigma: float):
    """Compute morphological dilation, erosion, and Gaussian blur using cv2 or PIL+NumPy."""
    if cv2 is not None:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        raw_max = cv2.dilate(arr, kernel)
        raw_min = cv2.erode(arr, kernel)
        local_max = cv2.GaussianBlur(raw_max, (3, 3), sigmaX=0.8)
        local_min = cv2.GaussianBlur(raw_min, (3, 3), sigmaX=0.8)
        blur = cv2.GaussianBlur(arr, (0, 0), sigmaX=sigma)
        return raw_max, raw_min, local_max, local_min, blur

    # Pure PIL + NumPy implementation (for serverless environments without OpenCV)
    pil_u8 = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    max_img = pil_u8.filter(ImageFilter.MaxFilter(size=ksize))
    min_img = pil_u8.filter(ImageFilter.MinFilter(size=ksize))
    raw_max = np.asarray(max_img, dtype=np.float32)
    raw_min = np.asarray(min_img, dtype=np.float32)
    local_max = np.asarray(max_img.filter(ImageFilter.GaussianBlur(radius=0.8)), dtype=np.float32)
    local_min = np.asarray(min_img.filter(ImageFilter.GaussianBlur(radius=0.8)), dtype=np.float32)
    blur = np.asarray(pil_u8.filter(ImageFilter.GaussianBlur(radius=sigma)), dtype=np.float32)
    return raw_max, raw_min, local_max, local_min, blur


def _coupled_shock_and_unsharp(
    work: np.ndarray,
    ksize: int,
    sigma: float,
    shock_alpha: float,
    unsharp_gain: float,
    slope: float = 3.4,
    overshoot_allowance: float = 0.14,
) -> np.ndarray:
    """
    Coupled Luminance-Guided Kramer-Bruckner Shock + Soft-Clamped Unsharp Filter.
    - Computes the edge transition phase from perceptual luminance so all RGB channels
      steepen at the exact same sub-pixel boundary without false-color fringes.
    - Uses Gaussian-smoothed local morphological bounds to ensure smooth circular and
      diagonal contours with zero staircasing or halo ringing.
    """
    raw_max, raw_min, local_max, local_min, _ = _morph_dilate_erode_blur(work, ksize, sigma)
    local_mid = 0.5 * (local_max + local_min)
    local_range = np.maximum(local_max - local_min, 1e-3)

    lum = 0.114 * work[:, :, 0] + 0.587 * work[:, :, 1] + 0.299 * work[:, :, 2]
    _, _, lum_max, lum_min, _ = _morph_dilate_erode_blur(lum, ksize, sigma)
    lum_mid = 0.5 * (lum_max + lum_min)
    lum_range = np.maximum(lum_max - lum_min, 1e-3)

    lum_pos = np.clip((lum - lum_mid) / (0.5 * lum_range), -1.0, 1.0)[..., None]
    ch_pos = np.clip((work - local_mid) / (0.5 * local_range), -1.0, 1.0)
    lum_weight = np.clip(lum_range / 12.0, 0.0, 1.0)[..., None]
    norm_pos = lum_weight * lum_pos + (1.0 - lum_weight) * ch_pos

    steep = local_mid + 0.5 * local_range * (np.tanh(slope * norm_pos) / np.tanh(slope))
    work = (1.0 - shock_alpha) * work + shock_alpha * steep

    if cv2 is not None:
        blur = cv2.GaussianBlur(work, (0, 0), sigmaX=sigma)
    else:
        pil_w = Image.fromarray(np.clip(work, 0, 255).astype(np.uint8))
        blur = np.asarray(pil_w.filter(ImageFilter.GaussianBlur(radius=sigma)), dtype=np.float32)

    unsharp = work + unsharp_gain * (work - blur)

    # Allow slight ridge peak recovery on low-amplitude thin veins while clamping strong step edges
    thin_ridge_factor = np.exp(-local_range / 35.0)
    pad = overshoot_allowance * local_range * thin_ridge_factor
    return np.clip(unsharp, raw_min - pad, raw_max + pad)


def _enhance_leaf_clarity(orig_img: Image.Image) -> Image.Image:
    """
    High-clarity deblurring and edge restoration pipeline for blurry leaf images.
    Uses Coupled Luminance-Guided Shock Filtering + Multi-Scale Soft-Clamped
    Unsharp Deconvolution + Lanczos-4 HD Super-Resolution.
    """
    rgb = np.asarray(orig_img.convert("RGB"), dtype=np.uint8)
    bgr = rgb[:, :, ::-1].copy()
    h0, w0 = bgr.shape[:2]

    # Step 1: Edge-preserving pre-denoising at native scale
    if cv2 is not None:
        bgr = cv2.bilateralFilter(bgr, d=5, sigmaColor=14, sigmaSpace=14)
    scale_factor = max(1.0, max(h0, w0) / 480.0)
    work = bgr.astype(np.float32)

    # Step 2: Multi-scale Coupled Shock + Soft-Clamped Unsharp Deconvolution
    k1 = int(round(9 * scale_factor)) | 1
    k2 = int(round(5 * scale_factor)) | 1
    s1 = 2.8 * scale_factor
    s2 = 1.4 * scale_factor

    work = _coupled_shock_and_unsharp(
        work, k1, s1, shock_alpha=0.68, unsharp_gain=1.65, slope=3.4, overshoot_allowance=0.18
    )
    work = _coupled_shock_and_unsharp(
        work, k2, s2, shock_alpha=0.58, unsharp_gain=1.40, slope=3.2, overshoot_allowance=0.12
    )
    bgr_deblurred = np.clip(work, 0, 255).astype(np.uint8)

    # Step 3: Lanczos-4 Super-Resolution upscale to at least 900px + fine sub-pixel pass
    max_dim = max(h0, w0)
    if max_dim < 900:
        up_scale = 900.0 / float(max_dim)
        target_w, target_h = int(round(w0 * up_scale)), int(round(h0 * up_scale))
        if cv2 is not None:
            bgr_deblurred = cv2.resize(bgr_deblurred, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            rgb_tmp = Image.fromarray(bgr_deblurred[:, :, ::-1]).resize((target_w, target_h), Image.Resampling.LANCZOS)
            bgr_deblurred = np.asarray(rgb_tmp, dtype=np.uint8)[:, :, ::-1].copy()

        work_hd = bgr_deblurred.astype(np.float32)
        work_hd = _coupled_shock_and_unsharp(
            work_hd, 5, 1.1, shock_alpha=0.48, unsharp_gain=1.05, slope=2.8, overshoot_allowance=0.05
        )
        bgr_deblurred = np.clip(work_hd, 0, 255).astype(np.uint8)

    # Step 4: Gentle contour-preserving bilateral polish for smooth anti-aliased edges
    if cv2 is not None:
        bgr_deblurred = cv2.bilateralFilter(bgr_deblurred, d=5, sigmaColor=12, sigmaSpace=12)
    enhanced_rgb = bgr_deblurred[:, :, ::-1]
    return Image.fromarray(enhanced_rgb)


def detect_and_enhance_blurry_image(img_b64: str) -> dict:
    """
    Inspect the uploaded leaf image for blurriness.
    When blurry (blur_score < BLUR_SHARPNESS_THRESHOLD), apply a multi-stage
    computer vision deblurring and clarity restoration pipeline and return the
    enhanced image base64.
    """
    try:
        image_data = base64.b64decode(img_b64)
        orig_img = Image.open(io.BytesIO(image_data))
        if orig_img.mode != "RGB":
            orig_img = orig_img.convert("RGB")
    except Exception as exc:
        logger.exception("Failed to decode image for blur detection")
        return {
            "is_blurry": False,
            "image_enhanced": False,
            "enhancement_status": "not_needed",
            "blur_score": None,
            "enhanced_blur_score": None,
            "enhanced_image_base64": None,
            "enhanced_image_mime": None,
        }

    blur_score = compute_blur_score(orig_img)
    is_blurry = bool(blur_score < BLUR_SHARPNESS_THRESHOLD)

    if not is_blurry:
        return {
            "is_blurry": False,
            "image_enhanced": False,
            "enhancement_status": "not_needed",
            "blur_score": round(blur_score, 2),
            "enhanced_blur_score": None,
            "enhanced_image_base64": None,
            "enhanced_image_mime": None,
        }

    # Image is blurry -> apply high-clarity CV deblurring & edge restoration pipeline
    try:
        enhanced = _enhance_leaf_clarity(orig_img)

        buf = io.BytesIO()
        enhanced.save(buf, format="JPEG", quality=96, subsampling=0)
        enhanced_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        enhanced_blur_score = compute_blur_score(enhanced)

        logger.info(
            "Blurry leaf image enhanced: blur_score=%.2f -> enhanced_blur_score=%.2f",
            blur_score,
            enhanced_blur_score,
        )
        return {
            "is_blurry": True,
            "image_enhanced": True,
            "enhancement_status": "enhanced",
            "blur_score": round(blur_score, 2),
            "enhanced_blur_score": round(enhanced_blur_score, 2),
            "enhanced_image_base64": enhanced_b64,
            "enhanced_image_mime": "image/jpeg",
        }
    except Exception as exc:
        logger.exception("Blurry image enhancement failed")
        return {
            "is_blurry": True,
            "image_enhanced": False,
            "enhancement_status": "failed",
            "blur_score": round(blur_score, 2),
            "enhanced_blur_score": None,
            "enhanced_image_base64": None,
            "enhanced_image_mime": None,
        }


def preprocess_image(img_b64: str):
    """Preprocess base64 image for analysis."""
    try:
        # Decode base64
        image_data = base64.b64decode(img_b64)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize to 224x224
        image = image.resize((224, 224))
        
        # Convert to numpy array and normalize
        image_array = np.array(image, dtype=np.float32)
        image_array = image_array / 255.0  # Normalize to [0, 1]
        
        return image_array
        
    except Exception as exc:
        logger.exception("Failed to preprocess image")
        raise RuntimeError(f"Failed to preprocess image: {exc}") from exc


def estimate_water_stress(image_array: np.ndarray) -> str:
    """
    Estimate water stress level based on image characteristics.
    Rule-based approach using color and texture analysis.
    """
    try:
        # Calculate color statistics
        red_channel = image_array[:, :, 0]
        green_channel = image_array[:, :, 1]
        blue_channel = image_array[:, :, 2]
        
        # Identify non-background pixels
        leaf_mask = (green_channel > blue_channel + 0.05)
        
        # Fallback to the entire image if the mask is too small or empty
        if np.sum(leaf_mask) < 100:
            leaf_mask = np.ones_like(red_channel, dtype=bool)
            
        green_mean = np.mean(green_channel[leaf_mask])
        yellow_ratio = np.mean(red_channel[leaf_mask]) / (np.mean(blue_channel[leaf_mask]) + 0.01)
        brightness = np.mean(image_array[leaf_mask])
        std_dev = np.std(image_array[leaf_mask])
        
        # Rule-based classification
        if green_mean > 0.4 and brightness > 0.3:
            # Healthy green leaf
            return "Low"
        elif green_mean > 0.3 and brightness > 0.25:
            # Slight yellowing
            return "Moderate"
        elif green_mean > 0.2 or yellow_ratio > 1.5:
            # Significant yellowing or browning
            return "High"
        else:
            # Severe wilting or browning
            return "Critical"
            
    except Exception as exc:
        logger.exception("Failed to estimate water stress")
        # Default to Low on error
        return "Low"


def _leaf_mask(red_channel: np.ndarray, green_channel: np.ndarray, blue_channel: np.ndarray) -> np.ndarray:
    """Return pixels likely to belong to the leaf, excluding dark/blurred background."""
    brightness = (red_channel + green_channel + blue_channel) / 3.0
    green_excess = green_channel - np.maximum(red_channel, blue_channel)
    plant_like = (
        (green_channel > blue_channel + 0.03)
        & (green_channel > red_channel - 0.08)
        & (green_channel > 0.12)
        & (brightness > 0.10)
    )
    diseased_tissue = (
        (red_channel > blue_channel + 0.05)
        & (green_channel > blue_channel + 0.03)
        & (green_channel > 0.08)
        & (brightness > 0.08)
    )
    strong_green = green_excess > 0.02
    mask = plant_like | diseased_tissue | (strong_green & (brightness > 0.08))

    # Fallback to the old broad mask, then whole image, if segmentation is too small.
    if np.sum(mask) < 100:
        mask = green_channel > blue_channel + 0.05
    if np.sum(mask) < 100:
        mask = np.ones_like(red_channel, dtype=bool)
    return mask


def detect_disease_symptoms(image_array: np.ndarray) -> dict:
    """
    Two-stage disease detection:
    Stage 1: Plant Health Classification (Healthy/Diseased)
    Stage 2: If Diseased, predict disease type
    
    Strict symptom detection - never classify as diseased unless visible symptoms exist.
    """
    try:
        # Calculate color statistics
        red_channel = image_array[:, :, 0]
        green_channel = image_array[:, :, 1]
        blue_channel = image_array[:, :, 2]
        
        # Identify leaf pixels while avoiding dark/background areas that dilute spot fractions.
        leaf_mask = _leaf_mask(red_channel, green_channel, blue_channel)
        
        # Overall color distribution of the leaf
        red_mean = np.mean(red_channel[leaf_mask])
        green_mean = np.mean(green_channel[leaf_mask])
        blue_mean = np.mean(blue_channel[leaf_mask])
        
        # Color variance (spots cause high variance)
        red_var = np.var(red_channel[leaf_mask])
        green_var = np.var(green_channel[leaf_mask])
        blue_var = np.var(blue_channel[leaf_mask])
        total_var = red_var + green_var + blue_var
        
        # Yellow/brown detection (disease indicator)
        yellow_ratio = red_mean / (green_mean + 0.01)
        brown_ratio = red_mean / (blue_mean + 0.01)
        
        # Brightness of the leaf
        brightness = np.mean(image_array[leaf_mask])
        
        # Detailed symptom extraction - pixel-fraction based detection
        detected_symptoms = []
        symptom_confidence = 0.0
        
        # Calculate local pixel-level brown, yellow, and necrotic spot fractions.
        leaf_pixels_count = np.sum(leaf_mask)
        leaf_brightness = (red_channel + green_channel + blue_channel) / 3.0
        brown_pixel_mask = (
            (red_channel > green_channel + 0.02)
            & (green_channel > blue_channel + 0.01)
            & (blue_channel < red_channel * 0.65)
            & leaf_mask
        )
        yellow_pixel_mask = (
            (red_channel > green_channel - 0.04)
            & (green_channel > blue_channel + 0.06)
            & (blue_channel < 0.45)
            & (leaf_brightness > 0.22)
            & leaf_mask
        )
        dark_spot_mask = (
            (leaf_brightness < max(brightness * 0.72, 0.16))
            & (red_channel > green_channel + 0.01)
            & (green_channel > blue_channel + 0.01)
            & leaf_mask
        )
        
        brown_pixel_fraction = np.sum(brown_pixel_mask) / leaf_pixels_count if leaf_pixels_count > 0 else 0.0
        yellow_pixel_fraction = np.sum(yellow_pixel_mask) / leaf_pixels_count if leaf_pixels_count > 0 else 0.0
        dark_spot_fraction = np.sum(dark_spot_mask) / leaf_pixels_count if leaf_pixels_count > 0 else 0.0
        lesion_pixel_fraction = brown_pixel_fraction + dark_spot_fraction
        
        # Check for brown/dark spots. Localized lesions can be visible while total variance remains moderate.
        brown_spots = (brown_pixel_fraction > 0.012 and total_var > 0.018) or (
            dark_spot_fraction > 0.018 and brown_pixel_fraction > 0.006
        )
        if brown_spots:
            detected_symptoms.append("Brown spots")
            symptom_confidence += 0.3
        
        # Check for yellow patches.
        yellow_patches = yellow_pixel_fraction > 0.025 and total_var > 0.015
        if yellow_patches:
            detected_symptoms.append("Yellow patches")
            symptom_confidence += 0.3
        
        # Check for lesions using brown and dark necrotic tissue.
        lesions = lesion_pixel_fraction > 0.02 and total_var > 0.015
        if lesions:
            detected_symptoms.append("Lesions")
            symptom_confidence += 0.25
        
        # Check for mold (high brightness with spots)
        mold = brightness > 0.45 and total_var > 0.04
        if mold:
            detected_symptoms.append("Mold")
            symptom_confidence += 0.25
        
        # Check for wilting (low brightness, low green)
        wilting = brightness < 0.2 and green_mean < 0.3
        if wilting:
            detected_symptoms.append("Wilting")
            symptom_confidence += 0.3
        
        # Check for curling (color pattern irregularity)
        curling = yellow_ratio > 1.4 and green_mean < 0.35
        if curling:
            detected_symptoms.append("Curling")
            symptom_confidence += 0.2
        
        # Check for discoloration (non-uniform color or non-green color)
        red_std = np.std(red_channel[leaf_mask])
        green_std = np.std(green_channel[leaf_mask])
        blue_std = np.std(blue_channel[leaf_mask])
        color_std = float((red_std + green_std + blue_std) / 3.0)
        
        # A healthy backlit leaf can be yellow-green, so do not require a large
        # green-over-red margin unless there is actual spot evidence.
        green_dominant = green_mean > (red_mean + 0.05) and green_mean > (blue_mean + 0.05)
        healthy_green_signal = (
            (green_mean > 0.34 and green_mean >= red_mean * 0.85 and green_mean > blue_mean + 0.04)
            or green_dominant
        )
        spotty_leaf = lesion_pixel_fraction > 0.015 or yellow_pixel_fraction > 0.025
        disease_evidence = brown_spots or yellow_patches or lesions or wilting or curling or mold or spotty_leaf
        # Healthy leaves can have strong green variation from veins/backlighting.
        # Treat variation as discoloration only when it is paired with spot evidence
        # or the leaf does not have a healthy green color signal overall.
        discoloration = (color_std > 0.14 and spotty_leaf) or (not healthy_green_signal)
        if discoloration:
            detected_symptoms.append("Discoloration")
            symptom_confidence += 0.1
        
        # Log extracted symptoms
        logger.info(f"Extracted symptoms: {detected_symptoms}, Symptom confidence: {symptom_confidence:.2f}")
        
        # STAGE 1: Plant Health Classification
        # Only classify as Healthy if NO symptoms and uniform green color
        has_symptoms = len(detected_symptoms) > 0
        uniform_green = healthy_green_signal and (color_std < 0.24 or not disease_evidence)
        no_lesions = not lesions
        no_spots = not brown_spots and not yellow_patches and not spotty_leaf
        no_wilting = not wilting
        
        health_status = None
        confidence = 0.0
        disease_name = None
        
        if (not disease_evidence) and uniform_green and no_lesions and no_spots and no_wilting:
            # Strict healthy classification
            health_status = "Healthy"
            disease_name = "Healthy"
            confidence = 0.85
            detected_symptoms = ["No visible disease symptoms", "Uniform green color", "No lesions or spots"]
            logger.info("Stage 1: Classified as Healthy (strict criteria met)")
        elif has_symptoms:
            # Symptoms detected - classify as Unhealthy
            health_status = "Unhealthy"
            confidence = min(symptom_confidence + 0.35, 0.78)
            logger.info(f"Stage 1: Classified as Unhealthy (symptoms: {detected_symptoms})")
        else:
            # No clear evidence - uncertain
            health_status = "Uncertain"
            disease_name = "Uncertain"
            confidence = 0.4
            detected_symptoms = ["Insufficient evidence for classification"]
            logger.info("Stage 1: Classified as Uncertain (insufficient evidence)")
        
        # STAGE 2: Disease Type Prediction (only if Unhealthy)
        if health_status == "Unhealthy":
            # Predict specific disease based on symptom patterns
            if brown_spots and lesions and (yellow_patches or lesion_pixel_fraction > 0.08):
                disease_name = "Late Blight"
                confidence = min(confidence + 0.1, 0.8)
                if "Water-soaked lesions" not in detected_symptoms:
                    detected_symptoms.append("Water-soaked lesions")
                logger.info("Stage 2: Predicted Late Blight")
            elif yellow_patches and lesions:
                disease_name = "Early Blight"
                confidence = min(confidence + 0.1, 0.8)
                if "Circular lesions" not in detected_symptoms:
                    detected_symptoms.append("Circular lesions")
                logger.info("Stage 2: Predicted Early Blight")
            elif mold:
                disease_name = "Leaf Mold"
                confidence = min(confidence + 0.1, 0.8)
                if "Powdery coating" not in detected_symptoms:
                    detected_symptoms.append("Powdery coating")
                logger.info("Stage 2: Predicted Leaf Mold")
            elif brown_spots:
                disease_name = "Septoria Leaf Spot"
                confidence = min(confidence + 0.15, 0.8)
                if "Small brown spots" not in detected_symptoms:
                    detected_symptoms.append("Small brown spots")
                logger.info("Stage 2: Predicted Septoria Leaf Spot")
            elif discoloration and lesions:
                disease_name = "Bacterial Spot"
                confidence = min(confidence + 0.1, 0.8)
                if "Water-soaked spots" not in detected_symptoms:
                    detected_symptoms.append("Water-soaked spots")
                logger.info("Stage 2: Predicted Bacterial Spot")
            else:
                disease_name = "Unhealthy (Unknown Type)"
                confidence = min(confidence, 0.6)
                logger.info("Stage 2: Disease type unclear")
        
        return {
            "health_status": health_status,
            "disease_name": disease_name,
            "confidence": confidence,
            "detected_symptoms": detected_symptoms,
            "symptom_confidence": symptom_confidence,
            "has_symptoms": has_symptoms,
            "uniform_green": uniform_green,
            "brightness": brightness
        }
        
    except Exception as exc:
        logger.exception("Failed to detect disease symptoms")
        # Return uncertain state on error
        return {
            "health_status": "Uncertain",
            "disease_name": "Uncertain",
            "confidence": 0.3,
            "detected_symptoms": ["Analysis error", "Manual verification required"],
            "symptom_confidence": 0.0,
            "has_symptoms": False,
            "uniform_green": False,
            "brightness": 0.3
        }


def analyze_with_cnn(img_b64: str, crop_hint: str, language_code: str) -> dict:
    """
    Analyze plant leaf image using two-stage rule-based image analysis.
    Pre-Stage: Validate that the uploaded image contains a valid leaf or plant.
    Stage 0: Blurry image detection & CV enhancement (when blurry)
    Stage 1: Plant Health Classification (Healthy/Unhealthy)
    Stage 2: If Unhealthy, predict disease type
    Water stress analysis is independent from disease analysis.
    Confidence validation: <70% = Uncertain Result - Manual Verification Recommended.
    """
    from app.services.plant_validator import (
        InvalidPlantImageError,
        VALIDATION_ERROR_MESSAGE,
        validate_leaf_or_plant_b64,
    )

    validation = validate_leaf_or_plant_b64(img_b64)
    if not validation["is_valid_plant"]:
        msg = validation["message"] if validation["status"] == "corrupted" else VALIDATION_ERROR_MESSAGE
        raise InvalidPlantImageError(msg, validation=validation)

    enh_info = detect_and_enhance_blurry_image(img_b64)
    analysis_b64 = (
        enh_info["enhanced_image_base64"]
        if enh_info.get("image_enhanced") and enh_info.get("enhanced_image_base64")
        else img_b64
    )

    try:
        # Preprocess image (uses enhanced image when input was blurry and enhanced)
        image_array = preprocess_image(analysis_b64)
        
        # STAGE 1 & 2: Disease detection (two-stage pipeline)
        disease_result = detect_disease_symptoms(image_array)
        if enh_info.get("image_enhanced") and disease_result["health_status"] == "Uncertain":
            orig_result = detect_disease_symptoms(preprocess_image(img_b64))
            if orig_result["confidence"] > disease_result["confidence"]:
                disease_result = orig_result
        health_status = disease_result["health_status"]
        disease_name = disease_result["disease_name"]
        confidence = disease_result["confidence"]
        detected_symptoms = disease_result["detected_symptoms"]
        
        # INDEPENDENT: Water stress analysis (separate from disease)
        water_stress = estimate_water_stress(image_array)
        stress_lower = water_stress.lower()
        
        # Convert confidence to percentage
        confidence_percent = int(confidence * 100)
        
        # Confidence validation: <70% = Uncertain Result
        if confidence_percent < 70:
            health_status = "Uncertain"
            disease_name = "Uncertain Result - Manual Verification Recommended"
            confidence_percent = 65  # Cap at 65% for uncertain results
            logger.info(f"Confidence {confidence_percent}% < 70%, returning Uncertain Result")
        
        # Log final prediction
        logger.info(f"Final prediction: Health={health_status}, Disease={disease_name}, Confidence={confidence_percent}%")
        
        # Generate recommendations based on health status (not disease-specific for uncertain)
        if health_status == "Healthy":
            severity_assessment = (
                f"Plant appears healthy with {confidence_percent}% confidence. "
                f"Water stress is {stress_lower}."
            )
            recommended_actions = [
                "Maintain current watering schedule",
                "Monitor for any changes in leaf appearance",
                "Maintain proper plant nutrition"
            ]
            preventive_measures = [
                "Regularly inspect plants for early signs of disease",
                "Maintain proper spacing between plants",
                "Ensure good air circulation"
            ]
        elif health_status == "Unhealthy":
            # Disease-specific recommendations
            if "Late Blight" in disease_name:
                severity_assessment = (
                    f"Critical condition ({confidence_percent}% confidence). "
                    f"Late blight spreads rapidly and can destroy entire crops. "
                    f"Water stress is {stress_lower}."
                )
                recommended_actions = [
                    "Remove and destroy affected plants immediately",
                    "Apply fungicide containing chlorothalonil",
                    "Avoid working with plants when wet",
                    "Rotate crops to prevent recurrence"
                ]
                preventive_measures = [
                    "Use certified disease-free seeds",
                    "Plant resistant varieties",
                    "Ensure good drainage",
                    "Avoid overhead irrigation"
                ]
            elif "Early Blight" in disease_name:
                severity_assessment = (
                    f"Moderate severity ({confidence_percent}% confidence). "
                    f"Early blight typically affects lower leaves first. "
                    f"Water stress is {stress_lower}."
                )
                recommended_actions = [
                    "Remove affected leaves to prevent spread",
                    "Apply copper-based fungicide",
                    "Improve air circulation around plants",
                    "Avoid overhead watering"
                ]
                preventive_measures = [
                    "Space plants properly for airflow",
                    "Water at base of plants, not leaves",
                    "Remove plant debris regularly",
                    "Use disease-resistant varieties"
                ]
            elif "Leaf Mold" in disease_name:
                severity_assessment = (
                    f"Moderate severity ({confidence_percent}% confidence). "
                    f"Leaf mold thrives in high humidity conditions. "
                    f"Water stress is {stress_lower}."
                )
                recommended_actions = [
                    "Improve air circulation significantly",
                    "Reduce humidity around plants",
                    "Remove affected lower leaves",
                    "Apply fungicide if severe"
                ]
                preventive_measures = [
                    "Maintain proper spacing between plants",
                    "Avoid overcrowding",
                    "Ensure good ventilation",
                    "Water at soil level only"
                ]
            elif "Septoria Leaf Spot" in disease_name:
                severity_assessment = (
                    f"Moderate severity ({confidence_percent}% confidence). "
                    f"Septoria leaf spot can cause significant defoliation. "
                    f"Water stress is {stress_lower}."
                )
                recommended_actions = [
                    "Remove infected leaves immediately",
                    "Apply fungicide containing chlorothalonil",
                    "Improve air circulation around plants",
                    "Mulch to prevent splash dispersal"
                ]
                preventive_measures = [
                    "Rotate crops annually",
                    "Space plants properly",
                    "Avoid overhead irrigation",
                    "Remove plant debris in fall"
                ]
            elif "Bacterial Spot" in disease_name:
                severity_assessment = (
                    f"Moderate to high severity ({confidence_percent}% confidence). "
                    f"Bacterial spot affects leaves and fruit. "
                    f"Water stress is {stress_lower}."
                )
                recommended_actions = [
                    "Remove infected plant material",
                    "Apply copper-based bactericide",
                    "Avoid working with plants when wet",
                    "Disinfect tools between uses"
                ]
                preventive_measures = [
                    "Use disease-free seeds and transplants",
                    "Avoid overhead irrigation",
                    "Maintain proper spacing between plants",
                    "Control insect vectors"
                ]
            else:
                severity_assessment = (
                    f"Plant appears unhealthy ({confidence_percent}% confidence), "
                    f"but specific disease could not be identified with certainty. "
                    f"Water stress is {stress_lower}."
                )
                recommended_actions = [
                    "Inspect plant closely for additional symptoms",
                    "Consult agricultural extension service",
                    "Isolate affected plant if possible",
                    "Monitor for spread to other plants"
                ]
                preventive_measures = [
                    "Regular plant inspections",
                    "Maintain proper sanitation",
                    "Quarantine new plants",
                    "Keep garden area clean"
                ]
        else:  # Uncertain
            severity_assessment = (
                f"Low confidence ({confidence_percent}%) in classification. "
                f"Manual inspection recommended. Water stress appears {stress_lower}."
            )
            recommended_actions = [
                "Inspect plant closely for symptoms",
                "Consult agricultural extension",
                "Monitor for changes in plant condition"
            ]
            preventive_measures = [
                "Regular plant inspections",
                "Maintain proper plant care practices"
            ]
        
        # Add water stress specific recommendations (independent from disease)
        if water_stress == "Low":
            water_actions = ["Maintain current watering schedule"]
        elif water_stress == "Moderate":
            water_actions = ["Increase watering frequency slightly", "Check soil moisture regularly"]
        elif water_stress == "High":
            water_actions = ["Increase watering significantly", "Add mulch to retain moisture", "Provide shade during peak heat"]
        else:  # Critical
            water_actions = ["Immediate deep watering required", "Consider plant recovery measures", "Protect from direct sunlight"]
        
        for wa in water_actions:
            if wa not in recommended_actions:
                recommended_actions.append(wa)

        crop_note = f" Contextualized for {crop_hint.strip()}." if crop_hint and crop_hint.strip() else ""
        if health_status == "Uncertain":
            notes_str = (
                f"Low confidence ({confidence_percent}%) suggests image quality issues or atypical symptoms. "
                f"Consider retaking photo in better lighting or consulting an expert.{crop_note}"
            )
        else:
            notes_str = (
                f"Two-stage analysis: Binary health classification followed by disease identification.{crop_note} "
                f"Based on visible symptoms only."
            )
        if enh_info.get("image_enhanced"):
            notes_str += " Blurred input image was automatically enhanced prior to analysis."
        
        return {
            "plant_health_status": health_status,
            "predicted_disease": disease_name,
            "confidence_score": confidence_percent,
            "water_stress_level": water_stress,
            "detected_symptoms": detected_symptoms,
            "severity_assessment": severity_assessment,
            "recommended_actions": recommended_actions[:6],  # Limit to 6 actions
            "preventive_measures": preventive_measures[:4],  # Limit to 4 measures
            "is_plant_image": True,
            "notes": notes_str,
            "is_blurry": enh_info["is_blurry"],
            "image_enhanced": enh_info["image_enhanced"],
            "enhancement_status": enh_info["enhancement_status"],
            "blur_score": enh_info["blur_score"],
            "enhanced_blur_score": enh_info["enhanced_blur_score"],
            "enhanced_image_base64": enh_info["enhanced_image_base64"],
            "enhanced_image_mime": enh_info["enhanced_image_mime"],
        }
        
    except Exception as exc:
        logger.exception("Image analysis failed")
        # Return uncertain result on error (never default to Healthy or Unhealthy)
        return {
            "plant_health_status": "Uncertain",
            "predicted_disease": "Uncertain Result - Manual Verification Recommended",
            "confidence_score": 30,
            "water_stress_level": "Low",
            "detected_symptoms": ["Image analysis error occurred", "Manual verification required"],
            "severity_assessment": "Unable to complete analysis due to technical error.",
            "recommended_actions": [
                "Inspect plant closely for symptoms",
                "Consult agricultural extension",
                "Try uploading the image again"
            ],
            "preventive_measures": [
                "Regular plant inspections",
                "Maintain proper plant care practices"
            ],
            "is_plant_image": True,
            "notes": "A technical error occurred during analysis. Please ensure the image is a clear photo of a plant leaf and try again.",
            "is_blurry": enh_info["is_blurry"],
            "image_enhanced": enh_info["image_enhanced"],
            "enhancement_status": enh_info["enhancement_status"],
            "blur_score": enh_info["blur_score"],
            "enhanced_blur_score": enh_info["enhanced_blur_score"],
            "enhanced_image_base64": enh_info["enhanced_image_base64"],
            "enhanced_image_mime": enh_info["enhanced_image_mime"],
        }


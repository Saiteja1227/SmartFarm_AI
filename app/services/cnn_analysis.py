"""Rule-based image analysis service for plant disease detection and water stress estimation."""
import os
import logging
import base64
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)


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
    Stage 1: Plant Health Classification (Healthy/Unhealthy)
    Stage 2: If Unhealthy, predict disease type
    Water stress analysis is independent from disease analysis.
    Confidence validation: <70% = Uncertain Result - Manual Verification Recommended.
    """
    try:
        # Preprocess image
        image_array = preprocess_image(img_b64)
        
        # STAGE 1 & 2: Disease detection (two-stage pipeline)
        disease_result = detect_disease_symptoms(image_array)
        health_status = disease_result["health_status"]
        disease_name = disease_result["disease_name"]
        confidence = disease_result["confidence"]
        detected_symptoms = disease_result["detected_symptoms"]
        
        # INDEPENDENT: Water stress analysis (separate from disease)
        water_stress = estimate_water_stress(image_array)
        
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
            severity_assessment = "Plant appears healthy with no obvious signs of disease."
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
                severity_assessment = f"Late blight detected with {confidence_percent}% confidence. Serious fungal disease."
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
                severity_assessment = f"Early blight detected with {confidence_percent}% confidence. Fungal infection likely."
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
                severity_assessment = f"Leaf mold detected with {confidence_percent}% confidence. Fungal infection present."
                recommended_actions = [
                    "Improve air circulation significantly",
                    "Reduce humidity around plants",
                    "Remove affected lower leaves",
                    "Apply fungicide if severe"
                ]
                preventive_measures = [
                    "Maintain proper plant spacing",
                    "Avoid overcrowding",
                    "Ensure good ventilation",
                    "Water at soil level only"
                ]
            elif "Septoria Leaf Spot" in disease_name:
                severity_assessment = f"Septoria leaf spot detected with {confidence_percent}% confidence. Common fungal disease."
                recommended_actions = [
                    "Remove infected leaves immediately",
                    "Apply fungicide containing chlorothalonil",
                    "Improve air circulation",
                    "Mulch to prevent splash dispersal"
                ]
                preventive_measures = [
                    "Rotate crops annually",
                    "Space plants properly",
                    "Avoid overhead watering",
                    "Remove plant debris in fall"
                ]
            elif "Bacterial Spot" in disease_name:
                severity_assessment = f"Bacterial spot detected with {confidence_percent}% confidence. Bacterial infection."
                recommended_actions = [
                    "Remove infected plant material",
                    "Apply copper-based bactericide",
                    "Avoid working with wet plants",
                    "Disinfect tools between uses"
                ]
                preventive_measures = [
                    "Use disease-free seeds and transplants",
                    "Avoid overhead irrigation",
                    "Maintain proper plant spacing",
                    "Control insect vectors"
                ]
            else:
                severity_assessment = f"Disease detected with {confidence_percent}% confidence. Specific type unclear."
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
            severity_assessment = f"Uncertain result with {confidence_percent}% confidence. Manual verification recommended."
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
        
        recommended_actions.extend(water_actions)
        
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
            "notes": f"Two-stage analysis: Health={health_status}, Disease={disease_name}, Confidence={confidence_percent}%, Water Stress={water_stress}."
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
            "severity_assessment": "Unable to analyze image due to processing error. Manual inspection required.",
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
            "notes": f"Image analysis failed: {str(exc)}. Manual verification recommended."
        }

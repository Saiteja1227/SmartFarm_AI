import base64
import io

import numpy as np
from PIL import Image

from app.services.cnn_analysis import analyze_with_cnn


def _image_to_b64(image_array):
    image = Image.fromarray((image_array * 255).astype("uint8"), "RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _green_leaf():
    image = np.zeros((224, 224, 3), dtype=np.float32)
    image[..., 0] = 0.18
    image[..., 1] = 0.55
    image[..., 2] = 0.16
    return image


def test_clean_green_leaf_is_healthy():
    result = analyze_with_cnn(_image_to_b64(_green_leaf()), "Tomato", "en")

    assert result["plant_health_status"] == "Healthy"
    assert result["predicted_disease"] == "Healthy"


def test_green_leaf_with_vein_shadows_is_healthy():
    image = _green_leaf()
    image[..., 0] = 0.24
    image[..., 1] = 0.70
    image[..., 2] = 0.12

    for offset in range(-2, 3):
        image[110 + offset, :, :] = [0.12, 0.38, 0.08]
        image[:, 112 + offset, :] = [0.13, 0.40, 0.08]

    for diagonal in range(30, 190):
        for offset in range(-1, 2):
            image[diagonal, min(223, diagonal + 22 + offset), :] = [0.14, 0.42, 0.08]
            image[diagonal, max(0, 190 - diagonal + offset), :] = [0.13, 0.39, 0.08]

    yy, xx = np.ogrid[:224, :224]
    for cy, cx, radius in [(70, 78, 2), (145, 155, 2), (88, 160, 1)]:
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
        image[mask] = [0.09, 0.28, 0.07]

    result = analyze_with_cnn(_image_to_b64(image), "Tomato", "en")

    assert result["plant_health_status"] == "Healthy"
    assert result["predicted_disease"] == "Healthy"


def test_yellow_green_backlit_leaf_without_spots_is_healthy():
    image = np.zeros((224, 224, 3), dtype=np.float32)
    image[..., 0] = 0.50
    image[..., 1] = 0.58
    image[..., 2] = 0.12

    for offset in range(-2, 3):
        image[112 + offset, :, :] = [0.30, 0.44, 0.08]

    result = analyze_with_cnn(_image_to_b64(image), "Tomato", "en")

    assert result["plant_health_status"] == "Healthy"
    assert result["predicted_disease"] == "Healthy"


def test_brown_spotted_leaf_is_not_classified_healthy():
    image = _green_leaf()
    yy, xx = np.ogrid[:224, :224]
    for cy, cx, radius in [(70, 70, 9), (130, 115, 12), (90, 155, 7), (165, 80, 8)]:
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
        image[mask] = [0.36, 0.16, 0.06]

    result = analyze_with_cnn(_image_to_b64(image), "Tomato", "en")

    assert result["plant_health_status"] == "Unhealthy"
    assert result["predicted_disease"] == "Septoria Leaf Spot"
    assert "Brown spots" in result["detected_symptoms"]

"""Scan data model helpers — creation, serialisation, and MongoDB I/O."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.extensions import get_db


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_scan_doc(
    user_id: str,
    crop_name: Optional[str],
    language: str,
    image_base64: str,
    image_mime: str,
    ai_result: dict,
) -> dict:
    """Build a new scan document ready for MongoDB insertion."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "crop_name": crop_name or None,
        "language": language,
        "image_base64": image_base64,
        "image_mime": image_mime,
        "plant_health_status": ai_result.get("plant_health_status", "Uncertain"),
        "predicted_disease": ai_result.get("predicted_disease", "Unknown"),
        "confidence_score": ai_result.get("confidence_score", 0),
        "water_stress_level": ai_result.get("water_stress_level", "Low"),
        "detected_symptoms": ai_result.get("detected_symptoms", []),
        "severity_assessment": ai_result.get("severity_assessment", ""),
        "recommended_actions": ai_result.get("recommended_actions", []),
        "preventive_measures": ai_result.get("preventive_measures", []),
        "is_plant_image": ai_result.get("is_plant_image", True),
        "notes": ai_result.get("notes", ""),
        "is_blurry": bool(ai_result.get("is_blurry", False)),
        "image_enhanced": bool(ai_result.get("image_enhanced", False)),
        "enhancement_status": ai_result.get("enhancement_status", "not_needed"),
        "blur_score": ai_result.get("blur_score"),
        "enhanced_blur_score": ai_result.get("enhanced_blur_score"),
        "enhanced_image_base64": ai_result.get("enhanced_image_base64"),
        "enhanced_image_mime": ai_result.get("enhanced_image_mime") or "image/jpeg",
        "created_at": _utcnow_iso(),
    }


def insert_scan(doc: dict) -> None:
    db = get_db()
    db.scans.insert_one(dict(doc))


def get_history(user_id: str, limit: int = 50) -> list:
    db = get_db()
    projection = {
        "_id": 0,
        "id": 1,
        "crop_name": 1,
        "plant_health_status": 1,
        "predicted_disease": 1,
        "confidence_score": 1,
        "water_stress_level": 1,
        "image_mime": 1,
        "image_base64": 1,
        "created_at": 1,
    }
    cursor = db.scans.find({"user_id": user_id}, projection).sort("created_at", -1).limit(limit)
    items = []
    for doc in cursor:
        # Thumbnail is first 200 000 chars of base64 (same as original)
        thumbnail = (doc.get("image_base64") or "")[:200000]
        items.append(
            {
                "id": doc["id"],
                "crop_name": doc.get("crop_name"),
                "plant_health_status": doc.get("plant_health_status", "Uncertain"),
                "predicted_disease": doc.get("predicted_disease", "Unknown"),
                "confidence_score": int(doc.get("confidence_score", 0)),
                "water_stress_level": doc.get("water_stress_level", "Low"),
                "image_mime": doc.get("image_mime", "image/jpeg"),
                "thumbnail_base64": thumbnail,
                "created_at": doc.get("created_at", ""),
            }
        )
    return items


def get_scan(scan_id: str, user_id: str) -> Optional[dict]:
    db = get_db()
    doc = db.scans.find_one({"id": scan_id, "user_id": user_id}, {"_id": 0})
    return doc


def delete_scan(scan_id: str, user_id: str) -> bool:
    db = get_db()
    result = db.scans.delete_one({"id": scan_id, "user_id": user_id})
    return result.deleted_count > 0


def get_dashboard_stats(user_id: str) -> dict:
    db = get_db()
    total = db.scans.count_documents({"user_id": user_id})
    unhealthy = db.scans.count_documents({"user_id": user_id, "plant_health_status": "Unhealthy"})
    healthy = db.scans.count_documents({"user_id": user_id, "plant_health_status": "Healthy"})
    high_stress = db.scans.count_documents(
        {"user_id": user_id, "water_stress_level": {"$in": ["High", "Critical"]}}
    )
    return {
        "total": total,
        "healthy": healthy,
        "unhealthy": unhealthy,
        "high_stress": high_stress,
    }

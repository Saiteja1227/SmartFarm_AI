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
    analysis_status: str = "Completed",
    user_type: str = "anonymous",
) -> dict:
    """Build a new scan document ready for MongoDB insertion."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_type": user_type,
        "crop_name": crop_name or None,
        "language": language,
        "image_base64": image_base64,
        "image_mime": image_mime,
        "analysis_status": analysis_status,
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


def make_failed_scan_doc(
    user_id: str,
    crop_name: Optional[str],
    language: str,
    image_mime: str,
    error_reason: str,
) -> dict:
    """Build a failed scan record when leaf analysis encounters an error."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_type": "anonymous",
        "crop_name": crop_name or None,
        "language": language,
        "image_base64": None,
        "image_mime": image_mime,
        "analysis_status": "Failed",
        "plant_health_status": "Uncertain",
        "predicted_disease": "Analysis Failed",
        "confidence_score": 0,
        "water_stress_level": "Low",
        "detected_symptoms": [],
        "severity_assessment": "",
        "recommended_actions": [],
        "preventive_measures": [],
        "is_plant_image": False,
        "notes": f"Analysis failed: {error_reason}",
        "is_blurry": False,
        "image_enhanced": False,
        "enhancement_status": "not_needed",
        "blur_score": None,
        "enhanced_blur_score": None,
        "enhanced_image_base64": None,
        "enhanced_image_mime": "image/jpeg",
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
        "thumbnail_base64": 1,
        "created_at": 1,
    }
    query = {"user_id": user_id, "analysis_status": {"$ne": "Failed"}}
    cursor = db.scans.find(query, projection).sort("created_at", -1).limit(limit)
    items = []
    for doc in cursor:
        # Thumbnail is first 200 000 chars of base64 (or pre-extracted thumbnail_base64)
        thumbnail = (doc.get("thumbnail_base64") or doc.get("image_base64") or "")[:200000]
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
    base_q = {"user_id": user_id, "analysis_status": {"$ne": "Failed"}}
    total = db.scans.count_documents(base_q)
    unhealthy = db.scans.count_documents({**base_q, "plant_health_status": "Unhealthy"})
    healthy = db.scans.count_documents({**base_q, "plant_health_status": "Healthy"})
    high_stress = db.scans.count_documents(
        {**base_q, "water_stress_level": {"$in": ["High", "Critical"]}}
    )
    return {
        "total": total,
        "healthy": healthy,
        "unhealthy": unhealthy,
        "high_stress": high_stress,
    }


def get_scan_by_id_admin(scan_id: str) -> Optional[dict]:
    """Retrieve a single scan record by ID across all users (Admin only)."""
    db = get_db()
    return db.scans.find_one({"id": scan_id}, {"_id": 0})


def get_admin_scans_and_stats(
    q: str = "",
    crop: str = "",
    disease: str = "",
    health_status: str = "",
    analysis_status: str = "",
    enhanced: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """
    Query scan history across all users with search, filters, pagination,
    and real database summary statistics for the Private Admin Dashboard.
    """
    db = get_db()
    projection = {
        "_id": 0,
        "id": 1,
        "user_id": 1,
        "user_type": 1,
        "crop_name": 1,
        "language": 1,
        "analysis_status": 1,
        "plant_health_status": 1,
        "predicted_disease": 1,
        "confidence_score": 1,
        "water_stress_level": 1,
        "detected_symptoms": 1,
        "severity_assessment": 1,
        "is_plant_image": 1,
        "is_blurry": 1,
        "image_enhanced": 1,
        "enhancement_status": 1,
        "blur_score": 1,
        "enhanced_blur_score": 1,
        "image_mime": 1,
        "created_at": 1,
    }
    all_docs = list(db.scans.find({}, projection).sort("created_at", -1))

    # 1. Calculate global summary statistics from actual database records
    total_scans = len(all_docs)
    unique_users_set = set()
    completed_scans = 0
    successful_analyses = 0
    failed_analyses = 0
    enhanced_scans = 0
    crops_set = set()
    diseases_set = set()

    for d in all_docs:
        uid = (d.get("user_id") or "").strip()
        if uid:
            unique_users_set.add(uid)
        status_val = d.get("analysis_status") or "Completed"
        if status_val == "Failed":
            failed_analyses += 1
        else:
            completed_scans += 1
            successful_analyses += 1
        if d.get("image_enhanced"):
            enhanced_scans += 1
        c_name = (d.get("crop_name") or "").strip()
        if c_name:
            crops_set.add(c_name)
        dis_name = (d.get("predicted_disease") or "").strip()
        if dis_name:
            diseases_set.add(dis_name)

    # 2. Apply filters
    q_norm = (q or "").strip().lower()
    crop_norm = (crop or "").strip().lower()
    disease_norm = (disease or "").strip().lower()
    health_norm = (health_status or "").strip().lower()
    status_norm = (analysis_status or "").strip().lower()
    enhanced_norm = (enhanced or "").strip().lower()
    date_from_norm = (date_from or "").strip()
    date_to_norm = (date_to or "").strip()

    filtered = []
    for d in all_docs:
        doc_status = d.get("analysis_status") or "Completed"
        doc_crop = d.get("crop_name") or ""
        doc_disease = d.get("predicted_disease") or "Unknown"
        doc_health = d.get("plant_health_status") or "Uncertain"
        doc_created = d.get("created_at") or ""
        doc_date_part = doc_created[:10] if len(doc_created) >= 10 else ""

        if crop_norm:
            if crop_norm == "__unspecified__":
                if doc_crop.strip():
                    continue
            elif doc_crop.strip().lower() != crop_norm:
                continue

        if disease_norm and doc_disease.strip().lower() != disease_norm:
            continue

        if health_norm and doc_health.strip().lower() != health_norm:
            continue

        if status_norm and doc_status.strip().lower() != status_norm:
            continue

        if enhanced_norm == "yes" and not d.get("image_enhanced"):
            continue
        if enhanced_norm == "no" and d.get("image_enhanced"):
            continue

        if date_from_norm and doc_date_part and doc_date_part < date_from_norm:
            continue
        if date_to_norm and doc_date_part and doc_date_part > date_to_norm:
            continue

        if q_norm:
            haystack = " ".join(
                [
                    str(d.get("id") or ""),
                    str(d.get("user_id") or ""),
                    str(doc_crop),
                    str(doc_disease),
                    str(doc_health),
                    str(doc_status),
                    " ".join(str(s) for s in (d.get("detected_symptoms") or [])),
                ]
            ).lower()
            if q_norm not in haystack:
                continue

        filtered.append(
            {
                "id": d.get("id", ""),
                "user_id": d.get("user_id") or "anonymous",
                "user_type": d.get("user_type") or "anonymous",
                "crop_name": d.get("crop_name") or "Unspecified",
                "language": d.get("language") or "en",
                "analysis_status": doc_status,
                "plant_health_status": doc_health,
                "predicted_disease": doc_disease,
                "confidence_score": int(d.get("confidence_score") or 0),
                "water_stress_level": d.get("water_stress_level") or "Low",
                "is_blurry": bool(d.get("is_blurry", False)),
                "image_enhanced": bool(d.get("image_enhanced", False)),
                "enhancement_status": d.get("enhancement_status") or "not_needed",
                "blur_score": d.get("blur_score"),
                "enhanced_blur_score": d.get("enhanced_blur_score"),
                "created_at": doc_created,
            }
        )

    total_filtered = len(filtered)
    per_page = max(1, min(100, int(per_page or 20)))
    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    page = max(1, min(total_pages, int(page or 1)))
    start_idx = (page - 1) * per_page
    paginated_items = filtered[start_idx : start_idx + per_page]

    return {
        "stats": {
            "total_scans": total_scans,
            "completed_scans": completed_scans,
            "unique_users": len(unique_users_set),
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses,
            "enhanced_scans": enhanced_scans,
        },
        "filters": {
            "crops": sorted(crops_set),
            "diseases": sorted(diseases_set),
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total_filtered,
            "total_pages": total_pages,
        },
        "scans": paginated_items,
    }

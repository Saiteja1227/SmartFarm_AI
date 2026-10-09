"""REST API blueprint — /api/* endpoints."""
import base64
import logging
import os

from flask import Blueprint, jsonify, request

from app.models.scan import (
    delete_scan,
    get_dashboard_stats,
    get_history,
    get_scan,
    insert_scan,
    make_scan_doc,
)
from app.services.ai_service import SUPPORTED_LANGUAGES, analyze_image

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)

ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_BYTES = 8 * 1024 * 1024  # 8 MB


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_user_id():
    uid = (request.headers.get("X-User-Id") or "").strip()
    if not uid or len(uid) < 8 or len(uid) > 128:
        return None, (jsonify({"detail": "Missing or invalid X-User-Id header."}), 400)
    return uid, None


# ── Health & Translations ─────────────────────────────────────────────────────

@api_bp.route("/", methods=["GET"])
def health():
    return jsonify({"message": "SmartFarm AI API", "status": "ok"})


@api_bp.route("/translations", methods=["GET"])
def list_translations():
    from app.translations import LANGUAGES
    return jsonify({"languages": LANGUAGES})


@api_bp.route("/translations/<lang>", methods=["GET"])
def get_translations_for_lang(lang):
    from app.translations import SUPPORTED_LANG_CODES, get_translation_dict
    code = (lang or "en").strip().lower()
    if code not in SUPPORTED_LANG_CODES:
        code = "en"
    return jsonify({"language": code, "translations": get_translation_dict(code)})


# ── Analyze ───────────────────────────────────────────────────────────────────

@api_bp.route("/analyze", methods=["POST"])
def analyze():
    user_id, err = _require_user_id()
    if err:
        return err

    if "image" not in request.files:
        return jsonify({"detail": "No image file provided."}), 400

    image_file = request.files["image"]
    raw_bytes = image_file.read()
    mime = (image_file.content_type or "").lower()

    # Validate
    if mime not in ALLOWED_MIME:
        return jsonify({"detail": "Only JPEG, PNG, or WEBP images are accepted."}), 400
    if not raw_bytes:
        return jsonify({"detail": "Empty image upload."}), 400
    if len(raw_bytes) > MAX_BYTES:
        return jsonify({"detail": "Image too large (max 8MB)."}), 400

    crop_name = (request.form.get("crop_name") or "").strip()
    language = (request.form.get("language") or "en").lower()
    if language not in SUPPORTED_LANGUAGES:
        language = "en"

    img_b64 = base64.b64encode(raw_bytes).decode("utf-8")

    try:
        ai_result = analyze_image(img_b64, crop_name, language)
    except RuntimeError as exc:
        return jsonify({"detail": str(exc)}), 502

    doc = make_scan_doc(
        user_id=user_id,
        crop_name=crop_name or None,
        language=language,
        image_base64=img_b64,
        image_mime=mime,
        ai_result=ai_result,
    )

    try:
        insert_scan(doc)
    except Exception as exc:
        logger.exception("MongoDB insert failed")
        return jsonify({"detail": f"Database error: {exc}"}), 500

    return jsonify(doc)


# ── History ───────────────────────────────────────────────────────────────────

@api_bp.route("/history", methods=["GET"])
def list_history():
    user_id, err = _require_user_id()
    if err:
        return err

    try:
        items = get_history(user_id, limit=50)
    except Exception as exc:
        logger.exception("History fetch failed")
        return jsonify({"detail": f"Database error: {exc}"}), 500

    return jsonify(items)


# ── Single scan ───────────────────────────────────────────────────────────────

@api_bp.route("/scan/<scan_id>", methods=["GET"])
def get_scan_route(scan_id):
    user_id, err = _require_user_id()
    if err:
        return err

    try:
        doc = get_scan(scan_id, user_id)
    except Exception as exc:
        logger.exception("DB error on get_scan")
        return jsonify({"detail": f"Database error: {exc}"}), 503
    if not doc:
        return jsonify({"detail": "Scan not found."}), 404

    return jsonify(doc)


@api_bp.route("/scan/<scan_id>", methods=["DELETE"])
def delete_scan_route(scan_id):
    user_id, err = _require_user_id()
    if err:
        return err

    try:
        deleted = delete_scan(scan_id, user_id)
    except Exception as exc:
        logger.exception("DB error on delete_scan")
        return jsonify({"detail": f"Database error: {exc}"}), 503
    if not deleted:
        return jsonify({"detail": "Scan not found."}), 404

    return jsonify({"deleted": True, "id": scan_id})


# ── Dashboard stats ───────────────────────────────────────────────────────────

@api_bp.route("/stats", methods=["GET"])
def stats():
    user_id, err = _require_user_id()
    if err:
        return err

    try:
        data = get_dashboard_stats(user_id)
    except Exception as exc:
        logger.exception("Stats fetch failed")
        return jsonify({"detail": f"Database error: {exc}"}), 503

    return jsonify(data)


# ── PDF download (server-side, optional) ─────────────────────────────────────

@api_bp.route("/scan/<scan_id>/pdf", methods=["GET"])
def download_pdf(scan_id):
    user_id, err = _require_user_id()
    if err:
        return err

    try:
        doc = get_scan(scan_id, user_id)
    except Exception as exc:
        return jsonify({"detail": f"Database error: {exc}"}), 503
    if not doc:
        return jsonify({"detail": "Scan not found."}), 404

    req_lang = (request.args.get("lang") or doc.get("language") or "en").strip().lower()

    try:
        from app.services.pdf_service import generate_pdf_bytes
        pdf_bytes = generate_pdf_bytes(doc, lang=req_lang)
    except RuntimeError as exc:
        return jsonify({"detail": str(exc)}), 501

    from flask import Response
    filename = f"smartfarm-report-{req_lang}-{scan_id[:8]}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


"""Private Admin Dashboard & Secure Scan History routes and APIs."""
import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from functools import wraps

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from app.models.scan import get_admin_scans_and_stats, get_scan_by_id_admin

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)

# Session timeout (8 hours), CSRF lifetime (2 hours), and brute-force rate limit settings
ADMIN_SESSION_MAX_AGE_SECONDS = 8 * 3600
CSRF_MAX_AGE_SECONDS = 2 * 3600
ADMIN_COOKIE_NAME = "sf_admin_token"
RATE_LIMIT_WINDOW_SECONDS = 15 * 60
RATE_LIMIT_MAX_ATTEMPTS = 5
_FAILED_LOGIN_ATTEMPTS = {}


def _get_signing_key() -> bytes:
    key = (
        current_app.config.get("SECRET_KEY")
        or os.environ.get("SECRET_KEY")
        or "smartfarm-ai-prod-secret-key-2026-9f8e7d6c5b4a"
    )
    return str(key).encode("utf-8")


def _get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _FAILED_LOGIN_ATTEMPTS.get(ip, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    _FAILED_LOGIN_ATTEMPTS[ip] = attempts
    return len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS


def _record_failed_attempt(ip: str) -> None:
    now = time.time()
    attempts = [t for t in _FAILED_LOGIN_ATTEMPTS.get(ip, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    attempts.append(now)
    _FAILED_LOGIN_ATTEMPTS[ip] = attempts


def _clear_failed_attempts(ip: str) -> None:
    _FAILED_LOGIN_ATTEMPTS.pop(ip, None)


def reset_rate_limits() -> None:
    """Clear in-memory failed login rate limit tracking (used in tests)."""
    _FAILED_LOGIN_ATTEMPTS.clear()


def _get_admin_username() -> str:
    return (
        current_app.config.get("ADMIN_USERNAME")
        or os.environ.get("ADMIN_USERNAME")
        or "admin"
    ).strip()


def _get_admin_password_config():
    """Return (password_hash, plain_password) from app config or environment."""
    pw_hash = (
        current_app.config.get("ADMIN_PASSWORD_HASH")
        or os.environ.get("ADMIN_PASSWORD_HASH")
        or ""
    ).strip()
    pw_plain = (
        current_app.config.get("ADMIN_PASSWORD")
        or os.environ.get("ADMIN_PASSWORD")
        or ""
    ).strip()
    return pw_hash, pw_plain


def _is_admin_configured() -> bool:
    pw_hash, pw_plain = _get_admin_password_config()
    return bool(pw_hash or pw_plain)


def _verify_admin_credentials(username: str, password: str) -> bool:
    """
    Verify administrator username and password on the backend using constant-time
    comparisons or PBKDF2/scrypt password hash verification. Never logs secrets.
    """
    if not username or not password or not _is_admin_configured():
        return False

    expected_user = _get_admin_username()
    pw_hash, pw_plain = _get_admin_password_config()

    user_ok = hmac.compare_digest(
        username.strip().encode("utf-8"),
        expected_user.encode("utf-8"),
    )

    if pw_hash:
        try:
            pass_ok = check_password_hash(pw_hash, password)
        except Exception:
            pass_ok = False
    elif pw_plain:
        pass_ok = hmac.compare_digest(
            password.encode("utf-8"),
            pw_plain.encode("utf-8"),
        )
    else:
        pass_ok = False

    return bool(user_ok and pass_ok)


def _create_admin_cookie_token(username: str, auth_time: int) -> str:
    payload = f"admin|{username}|{auth_time}"
    sig = hmac.new(_get_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _verify_admin_cookie_token(token: str) -> bool:
    if not token:
        return False
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        role, username, ts_str, sig = decoded.split("|", 3)
        if role != "admin":
            return False
        expected_user = _get_admin_username()
        if not hmac.compare_digest(username.encode("utf-8"), expected_user.encode("utf-8")):
            return False
        auth_time = int(ts_str)
        if time.time() - auth_time > ADMIN_SESSION_MAX_AGE_SECONDS:
            return False
        payload = f"admin|{username}|{auth_time}"
        expected_sig = hmac.new(_get_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


def _is_authenticated_admin() -> bool:
    """Verify server-side session or signed admin token has valid, non-expired administrator role."""
    expected_user = _get_admin_username()
    try:
        if session.get("is_admin") and session.get("role") == "admin":
            sess_user = (session.get("admin_username") or "").strip()
            auth_time = session.get("admin_auth_time")
            if (
                sess_user
                and hmac.compare_digest(sess_user.encode("utf-8"), expected_user.encode("utf-8"))
                and isinstance(auth_time, (int, float))
                and (time.time() - auth_time <= ADMIN_SESSION_MAX_AGE_SECONDS)
            ):
                return True
    except Exception:
        pass

    cookie_token = request.cookies.get(ADMIN_COOKIE_NAME, "")
    return _verify_admin_cookie_token(cookie_token)


def _ensure_csrf_token() -> str:
    ts = str(int(time.time()))
    nonce = secrets.token_hex(12)
    msg = f"csrf|{ts}|{nonce}"
    sig = hmac.new(_get_signing_key(), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{ts}.{nonce}.{sig}"
    try:
        session["admin_csrf_token"] = token
    except Exception:
        pass
    return token


def _verify_csrf_token(submitted: str) -> bool:
    if not submitted:
        return False
    try:
        expected_sess = session.get("admin_csrf_token") or ""
        if expected_sess and hmac.compare_digest(submitted, expected_sess):
            return True
    except Exception:
        pass

    try:
        ts_str, nonce, sig = submitted.split(".", 2)
        ts = int(ts_str)
        if abs(time.time() - ts) > CSRF_MAX_AGE_SECONDS:
            return False
        msg = f"csrf|{ts_str}|{nonce}"
        expected_sig = hmac.new(_get_signing_key(), msg.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


@admin_bp.after_request
def _add_admin_security_headers(response):
    """Add strict security and anti-indexing headers to all admin responses."""
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    return response


def admin_required(view_func):
    """Decorator for private Admin HTML pages — redirects unauthenticated requests to /admin/login."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not _is_authenticated_admin():
            return redirect(url_for("admin.admin_login"))
        return view_func(*args, **kwargs)
    return wrapped


def admin_api_required(view_func):
    """Decorator for private Admin JSON/media APIs — rejects unauthenticated requests with 403."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not _is_authenticated_admin():
            return jsonify({"detail": "Forbidden: Administrator authentication required."}), 403
        return view_func(*args, **kwargs)
    return wrapped


# ── Private Admin HTML Routes ────────────────────────────────────────────────

@admin_bp.route("/admin", methods=["GET"])
def admin_root():
    if not _is_authenticated_admin():
        return redirect(url_for("admin.admin_login"))
    return redirect(url_for("admin.scan_history_dashboard"))


@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if _is_authenticated_admin() and request.method == "GET":
        return redirect(url_for("admin.scan_history_dashboard"))

    error = None
    status_code = 200
    client_ip = _get_client_ip()

    if request.method == "POST":
        if _is_rate_limited(client_ip):
            error = "Too many failed login attempts. Please wait 15 minutes before trying again."
            status_code = 429
        else:
            submitted_csrf = (request.form.get("csrf_token") or "").strip()
            if not _verify_csrf_token(submitted_csrf):
                error = "Invalid or expired form session. Please try again."
                status_code = 400
            elif not _is_admin_configured():
                error = (
                    "Administrator credentials are not configured on the server. "
                    "Please set ADMIN_USERNAME and ADMIN_PASSWORD (or ADMIN_PASSWORD_HASH) in environment variables."
                )
                status_code = 503
            else:
                username = (request.form.get("username") or "").strip()
                password = request.form.get("password") or ""
                if _verify_admin_credentials(username, password):
                    _clear_failed_attempts(client_ip)
                    now_ts = int(time.time())
                    admin_user = _get_admin_username()
                    try:
                        session.clear()
                        session.permanent = True
                        session["is_admin"] = True
                        session["role"] = "admin"
                        session["admin_username"] = admin_user
                        session["admin_auth_time"] = now_ts
                    except Exception:
                        pass

                    resp = make_response(redirect(url_for("admin.scan_history_dashboard")))
                    is_https = bool(
                        request.is_secure
                        or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
                        or current_app.config.get("SESSION_COOKIE_SECURE")
                    )
                    resp.set_cookie(
                        ADMIN_COOKIE_NAME,
                        _create_admin_cookie_token(admin_user, now_ts),
                        max_age=ADMIN_SESSION_MAX_AGE_SECONDS,
                        httponly=True,
                        samesite="Lax",
                        secure=is_https,
                        path="/",
                    )
                    logger.info("Administrator login succeeded for user '%s'", admin_user)
                    return resp
                else:
                    _record_failed_attempt(client_ip)
                    logger.warning("Failed administrator login attempt from IP %s", client_ip)
                    error = "Invalid administrator username or password."
                    status_code = 401

    csrf_token = _ensure_csrf_token()
    return (
        render_template(
            "admin_login.html",
            error=error,
            csrf_token=csrf_token,
            is_configured=_is_admin_configured(),
        ),
        status_code,
    )


@admin_bp.route("/admin/logout", methods=["POST", "GET"])
def admin_logout():
    try:
        session.clear()
    except Exception:
        pass
    resp = make_response(redirect(url_for("admin.admin_login")))
    resp.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return resp


@admin_bp.route("/admin/scan-history", methods=["GET"])
@admin_required
def scan_history_dashboard():
    csrf_token = _ensure_csrf_token()
    return render_template(
        "admin_scan_history.html",
        admin_username=_get_admin_username(),
        csrf_token=csrf_token,
    )


# ── Protected Admin API Endpoints ────────────────────────────────────────────

@admin_bp.route("/api/admin/scans", methods=["GET"])
@admin_api_required
def api_admin_list_scans():
    q = request.args.get("q", "")
    crop = request.args.get("crop", "")
    disease = request.args.get("disease", "")
    health_status = request.args.get("health_status", "")
    analysis_status = request.args.get("analysis_status", "")
    enhanced = request.args.get("enhanced", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", 20))
    except (TypeError, ValueError):
        per_page = 20

    try:
        data = get_admin_scans_and_stats(
            q=q,
            crop=crop,
            disease=disease,
            health_status=health_status,
            analysis_status=analysis_status,
            enhanced=enhanced,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )
        return jsonify(data)
    except Exception as exc:
        logger.exception("Admin scan list query failed")
        return jsonify({"detail": f"Database error: {exc}"}), 500


@admin_bp.route("/api/admin/scans/<scan_id>", methods=["GET"])
@admin_api_required
def api_admin_scan_detail(scan_id):
    try:
        doc = get_scan_by_id_admin(scan_id)
    except Exception as exc:
        logger.exception("Admin scan detail query failed")
        return jsonify({"detail": f"Database error: {exc}"}), 500

    if not doc:
        return jsonify({"detail": "Scan record not found."}), 404

    has_orig = bool(doc.get("image_base64"))
    has_enh = bool(doc.get("enhanced_image_base64"))

    return jsonify(
        {
            "id": doc.get("id"),
            "user_id": doc.get("user_id") or "anonymous",
            "user_type": doc.get("user_type") or "anonymous",
            "crop_name": doc.get("crop_name") or "Unspecified",
            "language": doc.get("language") or "en",
            "analysis_status": doc.get("analysis_status") or "Completed",
            "plant_health_status": doc.get("plant_health_status") or "Uncertain",
            "predicted_disease": doc.get("predicted_disease") or "Unknown",
            "confidence_score": int(doc.get("confidence_score") or 0),
            "water_stress_level": doc.get("water_stress_level") or "Low",
            "detected_symptoms": doc.get("detected_symptoms") or [],
            "severity_assessment": doc.get("severity_assessment") or "",
            "recommended_actions": doc.get("recommended_actions") or [],
            "preventive_measures": doc.get("preventive_measures") or [],
            "is_plant_image": bool(doc.get("is_plant_image", True)),
            "notes": doc.get("notes") or "",
            "is_blurry": bool(doc.get("is_blurry", False)),
            "image_enhanced": bool(doc.get("image_enhanced", False)),
            "enhancement_status": doc.get("enhancement_status") or "not_needed",
            "blur_score": doc.get("blur_score"),
            "enhanced_blur_score": doc.get("enhanced_blur_score"),
            "created_at": doc.get("created_at") or "",
            "has_original_image": has_orig,
            "has_enhanced_image": has_enh,
            "original_image_url": url_for("admin.api_admin_scan_image", scan_id=scan_id, type="original")
            if has_orig
            else None,
            "enhanced_image_url": url_for("admin.api_admin_scan_image", scan_id=scan_id, type="enhanced")
            if has_enh
            else None,
            "pdf_report_url": url_for("admin.api_admin_scan_pdf", scan_id=scan_id),
        }
    )


@admin_bp.route("/api/admin/scans/<scan_id>/image", methods=["GET"])
@admin_api_required
def api_admin_scan_image(scan_id):
    img_type = (request.args.get("type") or "original").strip().lower()
    doc = get_scan_by_id_admin(scan_id)
    if not doc:
        return jsonify({"detail": "Scan record not found."}), 404

    if img_type == "enhanced":
        b64_data = doc.get("enhanced_image_base64")
        mime = doc.get("enhanced_image_mime") or "image/jpeg"
    else:
        b64_data = doc.get("image_base64") or doc.get("thumbnail_base64")
        mime = (
            doc.get("image_mime")
            if doc.get("image_base64")
            else (doc.get("thumbnail_mime") or doc.get("image_mime"))
        ) or "image/jpeg"

    if not b64_data:
        return jsonify({"detail": "Requested image not available for this scan."}), 404

    try:
        raw_bytes = base64.b64decode(b64_data)
    except Exception:
        return jsonify({"detail": "Stored image data could not be decoded."}), 500

    return Response(
        raw_bytes,
        mimetype=mime,
        headers={"Cache-Control": "private, no-store, no-cache, must-revalidate"},
    )


@admin_bp.route("/api/admin/scans/<scan_id>/pdf", methods=["GET"])
@admin_api_required
def api_admin_scan_pdf(scan_id):
    doc = get_scan_by_id_admin(scan_id)
    if not doc:
        return jsonify({"detail": "Scan record not found."}), 404

    req_lang = (request.args.get("lang") or doc.get("language") or "en").strip().lower()
    try:
        from app.services.pdf_service import generate_pdf_bytes

        pdf_bytes = generate_pdf_bytes(doc, lang=req_lang)
    except RuntimeError as exc:
        return jsonify({"detail": str(exc)}), 501

    filename = f"smartfarm-admin-report-{req_lang}-{scan_id[:8]}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store, no-cache, must-revalidate",
        },
    )

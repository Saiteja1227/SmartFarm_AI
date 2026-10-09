"""SmartFarm AI — Flask application factory."""
import os
from datetime import timedelta
from pathlib import Path
from flask import Flask
from dotenv import dotenv_values, load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
_fallback_env = dotenv_values(ROOT_DIR / ".env.example") if (ROOT_DIR / ".env.example").exists() else {}


def _env_or_fallback(key: str, default: str = "") -> str:
    val = (os.environ.get(key) or "").strip()
    if val:
        return val
    fb = (_fallback_env.get(key) or "").strip()
    if fb and fb not in ("replace_with_strong_admin_password", "change_this_to_a_random_secret_key"):
        return fb
    return default


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────────────────────
    secret_key = _env_or_fallback("SECRET_KEY", "smartfarm-ai-prod-secret-key-2026-9f8e7d6c5b4a")
    app.config["SECRET_KEY"] = secret_key
    app.secret_key = secret_key
    app.config["MONGO_URI"] = (os.environ.get("MONGO_URL") or "").strip()
    app.config["DB_NAME"] = (os.environ.get("DB_NAME") or "").strip() or "smartfarm"
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.jinja_env.auto_reload = True

    # ── Session & Admin Security Config ───────────────────────────────────────
    is_secure_env = bool(
        os.environ.get("VERCEL")
        or os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("SESSION_COOKIE_SECURE", "").lower() == "true"
    )
    app.config["SESSION_COOKIE_NAME"] = "sf_session"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = is_secure_env
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
    app.config["ADMIN_USERNAME"] = _env_or_fallback("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = _env_or_fallback("ADMIN_PASSWORD", "")
    app.config["ADMIN_PASSWORD_HASH"] = _env_or_fallback("ADMIN_PASSWORD_HASH", "")

    @app.after_request
    def add_no_cache_headers(response):
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # ── Extensions ────────────────────────────────────────────────────────────
    from app.extensions import init_extensions
    init_extensions(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp)

    return app

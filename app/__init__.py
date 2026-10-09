"""SmartFarm AI — Flask application factory."""
import os
from datetime import timedelta
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["MONGO_URI"] = os.environ.get("MONGO_URL", "")
    app.config["DB_NAME"] = os.environ.get("DB_NAME", "smartfarm")
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
    app.config["ADMIN_USERNAME"] = os.environ.get("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "")
    app.config["ADMIN_PASSWORD_HASH"] = os.environ.get("ADMIN_PASSWORD_HASH", "")

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

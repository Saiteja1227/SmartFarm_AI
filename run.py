"""Application entry point. Start with: gunicorn run:app"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")
    app.run(debug=debug_mode, host="0.0.0.0", port=port)

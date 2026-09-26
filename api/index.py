import sys
from pathlib import Path

# Add the project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run import app


class VercelPathFixMiddleware:
    """
    Middleware ensuring that requests routed by Vercel serverless functions
    receive the expected PATH_INFO in Flask.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        raw_path = environ.get("PATH_INFO", "")
        # Check for original URI headers set by Vercel Edge
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_MATCHED_PATH")
        if forwarded_uri and not forwarded_uri.startswith("/api/index"):
            # Strip query params from forwarded_uri
            path_only = forwarded_uri.split("?", 1)[0]
            environ["PATH_INFO"] = path_only
        elif raw_path.startswith("/api/index.py"):
            stripped = raw_path[len("/api/index.py"):]
            environ["PATH_INFO"] = stripped if stripped else "/"
        elif raw_path.startswith("/api/index"):
            stripped = raw_path[len("/api/index"):]
            environ["PATH_INFO"] = stripped if stripped else "/"

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

if __name__ == "__main__":
    app.run()

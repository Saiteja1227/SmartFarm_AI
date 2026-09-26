import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run import app


class VercelPathFixMiddleware:
    """
    WSGI middleware ensuring proper PATH_INFO and QUERY_STRING handling
    for Flask applications deployed on Vercel serverless functions.
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Check if rewritten path was provided in query string
        qs = environ.get("QUERY_STRING", "")
        if "__sf_path" in qs:
            parsed = parse_qs(qs, keep_blank_values=True)
            if "__sf_path" in parsed:
                orig = parsed.pop("__sf_path")[0]
                if not orig.startswith("/"):
                    orig = "/" + orig
                while orig.startswith("//"):
                    orig = orig[1:]
                environ["PATH_INFO"] = orig
                environ["QUERY_STRING"] = urlencode(parsed, doseq=True)
        else:
            # 2. Check for original URI headers if set by proxies/gateways
            forwarded_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_MATCHED_PATH")
            if forwarded_uri and not forwarded_uri.startswith("/api/index"):
                environ["PATH_INFO"] = forwarded_uri.split("?", 1)[0]
            else:
                # 3. Fallback: normalize raw PATH_INFO
                raw = environ.get("PATH_INFO", "")
                if raw.startswith("/api/index.py"):
                    stripped = raw[len("/api/index.py"):]
                    environ["PATH_INFO"] = stripped if stripped else "/"
                elif raw.startswith("/api/index"):
                    stripped = raw[len("/api/index"):]
                    environ["PATH_INFO"] = stripped if stripped else "/"

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

if __name__ == "__main__":
    app.run()

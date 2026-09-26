"""Main page routes — serve Jinja2 templates."""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/api/index")
@main_bp.route("/api/index.py")
def index():
    return render_template("index.html")


@main_bp.route("/debug-vercel")
def debug_vercel():
    from flask import request, jsonify
    return jsonify({
        "path": request.path,
        "environ_path_info": request.environ.get("PATH_INFO"),
        "environ_x_forwarded_uri": request.environ.get("HTTP_X_FORWARDED_URI"),
        "environ_x_matched_path": request.environ.get("HTTP_X_MATCHED_PATH"),
        "headers": dict(request.headers)
    })


@main_bp.route("/history")
def history():
    return render_template("history.html")


@main_bp.route("/scan/<scan_id>")
def scan_detail(scan_id):
    return render_template("scan_detail.html", scan_id=scan_id)

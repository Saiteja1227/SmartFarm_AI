"""Main page routes — serve Jinja2 templates."""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/history")
def history():
    return render_template("history.html")


@main_bp.route("/scan/<scan_id>")
def scan_detail(scan_id):
    return render_template("scan_detail.html", scan_id=scan_id)

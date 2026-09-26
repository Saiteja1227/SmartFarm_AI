"""SmartFarm AI — integration tests.
Run against a live server: BASE_URL env var or http://localhost:5000
"""
import os
import re
import uuid
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")
API = f"{BASE_URL}/api"

LEAF_JPG = "/tmp/leaf.jpg"
LEAF_GIF = "/tmp/leaf.gif"
TXT_FILE = "/tmp/foo.txt"

USER_A = "user-aaaaaaaa-" + uuid.uuid4().hex[:8]
USER_B = "user-bbbbbbbb-" + uuid.uuid4().hex[:8]

HDR_A = {"X-User-Id": USER_A}
HDR_B = {"X-User-Id": USER_B}

state = {
    "scan_id_a": None, "scan_id_a2": None,
    "scan_id_b": None, "scan_id_hi": None, "scan_id_te": None,
}


# ── Health ────────────────────────────────────────────────────────────────────
def test_health_root():
    r = requests.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ── X-User-Id validation ──────────────────────────────────────────────────────
def test_history_without_user_id_returns_400():
    r = requests.get(f"{API}/history", timeout=15)
    assert r.status_code == 400


def test_analyze_without_user_id_returns_400():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(f"{API}/analyze", files={"image": ("leaf.jpg", f, "image/jpeg")}, timeout=30)
    assert r.status_code == 400


def test_history_with_too_short_user_id_returns_400():
    r = requests.get(f"{API}/history", headers={"X-User-Id": "abc"}, timeout=15)
    assert r.status_code == 400


# ── File validation ───────────────────────────────────────────────────────────
def test_analyze_rejects_text_file():
    with open(TXT_FILE, "rb") as f:
        r = requests.post(f"{API}/analyze", files={"image": ("foo.txt", f, "text/plain")}, headers=HDR_A, timeout=30)
    assert r.status_code == 400


def test_analyze_rejects_gif():
    with open(LEAF_GIF, "rb") as f:
        r = requests.post(f"{API}/analyze", files={"image": ("leaf.gif", f, "image/gif")}, headers=HDR_A, timeout=30)
    assert r.status_code == 400


def test_analyze_rejects_empty_upload():
    r = requests.post(f"{API}/analyze", files={"image": ("empty.jpg", b"", "image/jpeg")}, headers=HDR_A, timeout=30)
    assert r.status_code == 400


# ── Successful analysis (English) ────────────────────────────────────────────
def test_analyze_user_a_english():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(
            f"{API}/analyze",
            files={"image": ("leaf.jpg", f, "image/jpeg")},
            data={"crop_name": "Tomato", "language": "en"},
            headers=HDR_A, timeout=120,
        )
    assert r.status_code == 200, f"Body: {r.text[:500]}"
    data = r.json()
    required = ["id", "user_id", "language", "crop_name", "image_base64", "image_mime",
                "plant_health_status", "predicted_disease", "confidence_score",
                "water_stress_level", "detected_symptoms", "severity_assessment",
                "recommended_actions", "preventive_measures", "is_plant_image", "notes", "created_at"]
    for k in required:
        assert k in data, f"Missing field: {k}"
    assert data["user_id"] == USER_A
    assert data["language"] == "en"
    assert data["plant_health_status"] in {"Healthy", "Unhealthy", "Uncertain"}
    assert data["water_stress_level"] in {"Low", "Moderate", "High", "Critical"}
    state["scan_id_a"] = data["id"]


def test_analyze_default_language_en():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(f"{API}/analyze", files={"image": ("leaf.jpg", f, "image/jpeg")}, headers=HDR_A, timeout=120)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["language"] == "en"
    state["scan_id_a2"] = r.json()["id"]


def test_analyze_invalid_language_falls_back_to_en():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(
            f"{API}/analyze",
            files={"image": ("leaf.jpg", f, "image/jpeg")},
            data={"language": "xx-bad"},
            headers=HDR_A, timeout=120,
        )
    assert r.status_code == 200
    assert r.json()["language"] == "en"


# ── Hindi output ──────────────────────────────────────────────────────────────
def test_analyze_hindi_returns_devanagari():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(
            f"{API}/analyze",
            files={"image": ("leaf.jpg", f, "image/jpeg")},
            data={"language": "hi"},
            headers=HDR_A, timeout=120,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["language"] == "hi"
    assert data["plant_health_status"] in {"Healthy", "Unhealthy", "Uncertain"}
    devanagari = re.compile(r"[\u0900-\u097F]")
    combined = " ".join([
        data.get("predicted_disease", ""),
        data.get("severity_assessment", ""),
        " ".join(data.get("detected_symptoms") or []),
        " ".join(data.get("recommended_actions") or []),
        " ".join(data.get("preventive_measures") or []),
        data.get("notes", ""),
    ])
    assert devanagari.search(combined), f"No Devanagari found. Sample: {combined[:300]}"
    state["scan_id_hi"] = data["id"]


# ── Telugu output ─────────────────────────────────────────────────────────────
def test_analyze_telugu_returns_telugu_script():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(
            f"{API}/analyze",
            files={"image": ("leaf.jpg", f, "image/jpeg")},
            data={"language": "te"},
            headers=HDR_A, timeout=120,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["language"] == "te"
    telugu = re.compile(r"[\u0C00-\u0C7F]")
    combined = " ".join([
        data.get("predicted_disease", ""),
        data.get("severity_assessment", ""),
        " ".join(data.get("detected_symptoms") or []),
        " ".join(data.get("recommended_actions") or []),
        " ".join(data.get("preventive_measures") or []),
        data.get("notes", ""),
    ])
    assert telugu.search(combined), f"No Telugu found. Sample: {combined[:300]}"
    state["scan_id_te"] = data["id"]


# ── User B isolation ──────────────────────────────────────────────────────────
def test_analyze_user_b():
    with open(LEAF_JPG, "rb") as f:
        r = requests.post(
            f"{API}/analyze",
            files={"image": ("leaf.jpg", f, "image/jpeg")},
            data={"crop_name": "Basil"},
            headers=HDR_B, timeout=120,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == USER_B
    state["scan_id_b"] = data["id"]


# ── History isolation ─────────────────────────────────────────────────────────
def test_history_user_a_only_sees_own():
    r = requests.get(f"{API}/history", headers=HDR_A, timeout=30)
    assert r.status_code == 200
    ids = [it["id"] for it in r.json()]
    for key in ("scan_id_a", "scan_id_a2", "scan_id_hi", "scan_id_te"):
        sid = state[key]
        if sid:
            assert sid in ids, f"User A history missing {key}"
    if state["scan_id_b"]:
        assert state["scan_id_b"] not in ids, "User A leaked User B scan!"


def test_history_user_b_only_sees_own():
    r = requests.get(f"{API}/history", headers=HDR_B, timeout=30)
    assert r.status_code == 200
    ids = [it["id"] for it in r.json()]
    assert state["scan_id_b"] in ids
    for key in ("scan_id_a", "scan_id_a2", "scan_id_hi", "scan_id_te"):
        sid = state[key]
        if sid:
            assert sid not in ids, f"User B leaked User A {key}"


# ── Cross-user access ─────────────────────────────────────────────────────────
def test_get_scan_cross_user_returns_404():
    sid = state["scan_id_a"]
    assert sid
    r = requests.get(f"{API}/scan/{sid}", headers=HDR_B, timeout=15)
    assert r.status_code == 404


def test_get_scan_owner_succeeds():
    sid = state["scan_id_a"]
    r = requests.get(f"{API}/scan/{sid}", headers=HDR_A, timeout=15)
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_get_scan_unknown_returns_404():
    r = requests.get(f"{API}/scan/nonexistent-id", headers=HDR_A, timeout=15)
    assert r.status_code == 404


def test_delete_cross_user_returns_404():
    sid = state["scan_id_a"]
    r = requests.delete(f"{API}/scan/{sid}", headers=HDR_B, timeout=15)
    assert r.status_code == 404
    r2 = requests.get(f"{API}/scan/{sid}", headers=HDR_A, timeout=15)
    assert r2.status_code == 200


def test_delete_owner_succeeds():
    sid = state["scan_id_a2"]
    assert sid
    r = requests.delete(f"{API}/scan/{sid}", headers=HDR_A, timeout=15)
    assert r.status_code == 200
    assert r.json().get("deleted") is True
    r2 = requests.get(f"{API}/scan/{sid}", headers=HDR_A, timeout=15)
    assert r2.status_code == 404


# ── Stats endpoint ────────────────────────────────────────────────────────────
def test_stats_returns_counts():
    r = requests.get(f"{API}/stats", headers=HDR_A, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data and "healthy" in data


# ── Cleanup ───────────────────────────────────────────────────────────────────
def test_zz_cleanup():
    for key in ("scan_id_a", "scan_id_hi", "scan_id_te"):
        sid = state.get(key)
        if sid:
            requests.delete(f"{API}/scan/{sid}", headers=HDR_A, timeout=15)
    if state.get("scan_id_b"):
        requests.delete(f"{API}/scan/{state['scan_id_b']}", headers=HDR_B, timeout=15)

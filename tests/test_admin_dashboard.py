"""Comprehensive tests for the Private Admin Dashboard & Secure Scan History feature."""
import base64
import io
import re
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.scan import insert_scan, make_failed_scan_doc
from app.routes.admin import reset_rate_limits

ROOT = Path(__file__).resolve().parent.parent


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else ""


def _create_leaf_bytes(blurry: bool = False) -> bytes:
    img = Image.new("RGB", (300, 300), (32, 128, 42))
    draw = ImageDraw.Draw(img)
    for i in range(15, 285, 14):
        draw.line([(150, i), (30, i - 12)], fill=(95, 205, 85), width=2)
        draw.line([(150, i), (270, i - 12)], fill=(95, 205, 85), width=2)
    for x, y in [(90, 100), (195, 150), (130, 215)]:
        draw.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(105, 55, 25), outline=(225, 195, 45), width=2)
    if blurry:
        img = img.filter(ImageFilter.GaussianBlur(radius=4.5))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


class TestPrivateAdminDashboard(unittest.TestCase):

    def setUp(self):
        reset_rate_limits()
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-for-admin-session"
        self.app.config["ADMIN_USERNAME"] = "owner_admin"
        self.app.config["ADMIN_PASSWORD"] = ""
        self.app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash("Sup3rS3cur3_Own3r#2026")
        self.client = self.app.test_client()

    def _login_as_admin(self, username="owner_admin", password="Sup3rS3cur3_Own3r#2026"):
        get_resp = self.client.get("/admin/login")
        csrf_token = _extract_csrf_token(get_resp.get_data(as_text=True))
        return self.client.post(
            "/admin/login",
            data={
                "username": username,
                "password": password,
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )

    def test_1_no_admin_links_or_buttons_on_public_pages_or_static_files(self):
        for route in ["/", "/history", "/scan/sample-scan-id"]:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True).lower()
            self.assertNotIn("/admin", html, f"Public page {route} must not contain /admin links")
            self.assertNotIn("admin dashboard", html, f"Public page {route} must not mention admin dashboard")
            self.assertNotIn("admin login", html, f"Public page {route} must not mention admin login")

        # Verify no admin credentials or links in public JS files
        for js_file in (ROOT / "app/static/js").glob("*.js"):
            content = js_file.read_text(encoding="utf-8")
            self.assertNotIn("/admin/scan-history", content)
            self.assertNotIn("ADMIN_PASSWORD", content)

    def test_2_unauthenticated_and_normal_users_cannot_access_admin_dashboard_or_apis(self):
        # Direct browser request to /admin/scan-history redirects to /admin/login
        res = self.client.get("/admin/scan-history")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login", res.headers.get("Location", ""))

        # Attempting to spoof admin via query params, headers, or X-User-Id is denied
        spoof_headers = {
            "X-User-Id": "admin-user-12345678",
            "X-Admin": "true",
            "Role": "admin",
        }
        res_spoof = self.client.get("/admin/scan-history?admin=1&role=admin", headers=spoof_headers)
        self.assertEqual(res_spoof.status_code, 302)
        self.assertIn("/admin/login", res_spoof.headers.get("Location", ""))

        # Direct API requests by normal users are rejected with 403 Forbidden
        for api_url in [
            "/api/admin/scans",
            "/api/admin/scans/fake-id",
            "/api/admin/scans/fake-id/image",
            "/api/admin/scans/fake-id/pdf",
        ]:
            api_res = self.client.get(api_url, headers=spoof_headers)
            self.assertEqual(api_res.status_code, 403, f"Expected 403 on {api_url}")

    def test_3_admin_login_authentication_csrf_and_rate_limiting(self):
        # 1. Missing CSRF token -> 400
        res_no_csrf = self.client.post(
            "/admin/login",
            data={"username": "owner_admin", "password": "Sup3rS3cur3_Own3r#2026"},
        )
        self.assertEqual(res_no_csrf.status_code, 400)

        # 2. Wrong password -> 401
        res_bad_pw = self._login_as_admin(username="owner_admin", password="wrong-password")
        self.assertEqual(res_bad_pw.status_code, 401)
        self.assertIn("Invalid administrator username or password", res_bad_pw.get_data(as_text=True))

        # 3. Wrong username -> 401
        res_bad_user = self._login_as_admin(username="intruder", password="Sup3rS3cur3_Own3r#2026")
        self.assertEqual(res_bad_user.status_code, 401)

        # 4. Brute-force rate limiting after 5 failed attempts -> 429
        for _ in range(3):
            self._login_as_admin(username="owner_admin", password="wrong")
        res_locked = self._login_as_admin(username="owner_admin", password="Sup3rS3cur3_Own3r#2026")
        self.assertEqual(res_locked.status_code, 429)

        # Reset rate limit and verify valid login succeeds -> 302 to /admin/scan-history
        reset_rate_limits()
        res_ok = self._login_as_admin()
        self.assertEqual(res_ok.status_code, 302)
        self.assertIn("/admin/scan-history", res_ok.headers.get("Location", ""))

        # Verify /admin/scan-history renders for authenticated admin
        dash_res = self.client.get("/admin/scan-history")
        self.assertEqual(dash_res.status_code, 200)
        dash_html = dash_res.get_data(as_text=True)
        self.assertIn("User Leaf Scan History", dash_html)
        self.assertIn("owner_admin", dash_html)
        self.assertEqual(dash_res.headers.get("X-Robots-Tag"), "noindex, nofollow, noarchive")

        # Verify logout clears session and blocks subsequent access
        self.client.post("/admin/logout")
        after_logout = self.client.get("/admin/scan-history")
        self.assertEqual(after_logout.status_code, 302)
        self.assertEqual(self.client.get("/api/admin/scans").status_code, 403)

    def test_4_scan_tracking_filters_pagination_and_secure_media_access(self):
        # Simulate scans from two different users (one sharp Tomato scan, one blurry Potato scan)
        sharp_bytes = _create_leaf_bytes(blurry=False)
        blurry_bytes = _create_leaf_bytes(blurry=True)

        r1 = self.client.post(
            "/api/analyze",
            headers={"X-User-Id": "user-alpha-11112222"},
            data={
                "crop_name": "Tomato",
                "language": "en",
                "image": (io.BytesIO(sharp_bytes), "tomato_sharp.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(r1.status_code, 200)
        scan1 = r1.get_json()

        r2 = self.client.post(
            "/api/analyze",
            headers={"X-User-Id": "user-beta-33334444"},
            data={
                "crop_name": "Potato",
                "language": "te",
                "image": (io.BytesIO(blurry_bytes), "potato_blurry.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(r2.status_code, 200)
        scan2 = r2.get_json()
        self.assertTrue(scan2["image_enhanced"])

        # Also record a failed scan in DB
        with self.app.app_context():
            insert_scan(
                make_failed_scan_doc(
                    user_id="user-gamma-55556666",
                    crop_name="Pepper",
                    language="hi",
                    image_mime="image/jpeg",
                    error_reason="Simulated model timeout",
                )
            )

        # Log in as administrator
        login_res = self._login_as_admin()
        self.assertEqual(login_res.status_code, 302)

        # 1. Fetch admin scan list & verify summary stats
        list_res = self.client.get("/api/admin/scans")
        self.assertEqual(list_res.status_code, 200)
        payload = list_res.get_json()

        stats = payload["stats"]
        self.assertGreaterEqual(stats["total_scans"], 3)
        self.assertGreaterEqual(stats["completed_scans"], 2)
        self.assertGreaterEqual(stats["successful_analyses"], 2)
        self.assertGreaterEqual(stats["failed_analyses"], 1)
        self.assertGreaterEqual(stats["unique_users"], 3)
        self.assertGreaterEqual(stats["enhanced_scans"], 1)

        # 2. Test crop filter
        tomato_res = self.client.get("/api/admin/scans?crop=Tomato").get_json()
        self.assertTrue(all(s["crop_name"] == "Tomato" for s in tomato_res["scans"]))
        self.assertTrue(any(s["id"] == scan1["id"] for s in tomato_res["scans"]))

        # 3. Test enhanced filter
        enh_res = self.client.get("/api/admin/scans?enhanced=yes").get_json()
        self.assertTrue(all(s["image_enhanced"] is True for s in enh_res["scans"]))
        self.assertTrue(any(s["id"] == scan2["id"] for s in enh_res["scans"]))

        # 4. Test analysis_status=Failed filter
        fail_res = self.client.get("/api/admin/scans?analysis_status=Failed").get_json()
        self.assertGreaterEqual(len(fail_res["scans"]), 1)
        self.assertTrue(all(s["analysis_status"] == "Failed" for s in fail_res["scans"]))

        # 5. Test search query by user_id
        q_res = self.client.get("/api/admin/scans?q=user-beta-33334444").get_json()
        self.assertEqual(len(q_res["scans"]), 1)
        self.assertEqual(q_res["scans"][0]["id"], scan2["id"])

        # 6. Test pagination (per_page=1)
        pg1 = self.client.get("/api/admin/scans?per_page=1&page=1").get_json()
        pg2 = self.client.get("/api/admin/scans?per_page=1&page=2").get_json()
        self.assertEqual(len(pg1["scans"]), 1)
        self.assertEqual(len(pg2["scans"]), 1)
        self.assertNotEqual(pg1["scans"][0]["id"], pg2["scans"][0]["id"])

        # 7. Test scan detail endpoint & secure image/PDF endpoints
        detail_res = self.client.get(f"/api/admin/scans/{scan2['id']}")
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.get_json()
        self.assertEqual(detail["id"], scan2["id"])
        self.assertTrue(detail["has_original_image"])
        self.assertTrue(detail["has_enhanced_image"])

        orig_img_res = self.client.get(detail["original_image_url"])
        self.assertEqual(orig_img_res.status_code, 200)
        self.assertEqual(orig_img_res.mimetype, "image/jpeg")

        enh_img_res = self.client.get(detail["enhanced_image_url"])
        self.assertEqual(enh_img_res.status_code, 200)
        self.assertEqual(enh_img_res.mimetype, "image/jpeg")

        pdf_res = self.client.get(f"/api/admin/scans/{scan2['id']}/pdf?lang=te")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertTrue(pdf_res.data.startswith(b"%PDF-"))

    def test_5_cross_device_sync_and_live_auto_polling(self):
        # 1. Verify /api/analyze returns scan_saved=True
        sharp_bytes = _create_leaf_bytes(blurry=False)
        res = self.client.post(
            "/api/analyze",
            headers={"X-User-Id": "mobile-device-user-99887766"},
            data={
                "crop_name": "Tomato",
                "language": "en",
                "image": (io.BytesIO(sharp_bytes), "phone_leaf.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body.get("scan_saved"), "Expected scan_saved=True in /api/analyze response")

        # 2. Verify Admin Dashboard includes Live Auto-Sync polling UI & script
        self._login_as_admin()
        dash_html = self.client.get("/admin/scan-history").get_data(as_text=True)
        self.assertIn("AUTO_SYNC_INTERVAL_MS = 4000", dash_html)
        self.assertIn("startAutoSync()", dash_html)
        self.assertIn("toggleAutoSync()", dash_html)
        self.assertIn("admin-live-sync-toggle", dash_html)


if __name__ == "__main__":
    unittest.main()


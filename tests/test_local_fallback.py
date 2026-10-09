import os
import unittest

from app import create_app
from app.extensions import get_db


class TestLocalFallback(unittest.TestCase):
    def test_invalid_mongo_url_falls_back_to_in_memory_db(self):
        old_url = os.environ.get("MONGO_URL")
        os.environ["MONGO_URL"] = "mongodb+srv://invalid.invalid/test"
        try:
            app = create_app()
            db = get_db()
            db.scans.insert_one({"id": "scan-1", "user_id": "user-1", "created_at": "2024-01-01T00:00:00Z"})
            self.assertIsNotNone(app)
            self.assertEqual(db.scans.count_documents({"user_id": "user-1"}), 1)
            self.assertEqual(db.scans.find_one({"id": "scan-1"})["user_id"], "user-1")
        finally:
            if old_url is None:
                os.environ.pop("MONGO_URL", None)
            else:
                os.environ["MONGO_URL"] = old_url


if __name__ == "__main__":
    unittest.main()

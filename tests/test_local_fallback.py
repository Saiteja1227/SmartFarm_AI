import pytest

from app import create_app
from app.extensions import get_db


def test_invalid_mongo_url_falls_back_to_in_memory_db(monkeypatch):
    monkeypatch.setenv("MONGO_URL", "mongodb+srv://invalid.invalid/test")

    app = create_app()
    db = get_db()

    db.scans.insert_one({"id": "scan-1", "user_id": "user-1", "created_at": "2024-01-01T00:00:00Z"})

    assert app is not None
    assert db.scans.count_documents({"user_id": "user-1"}) == 1
    assert db.scans.find_one({"id": "scan-1"})["user_id"] == "user-1"

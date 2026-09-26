"""Flask extensions — MongoDB client shared across the app."""
import os

from pymongo import MongoClient
from pymongo.errors import ConfigurationError

_mongo_client = None
_db = None


class _MemoryResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class _MemoryCursor:
    def __init__(self, docs, projection=None):
        self._docs = docs
        self._projection = projection or {}

    def sort(self, key, direction):
        reverse = direction == -1
        self._docs = sorted(self._docs, key=lambda d: d.get(key, ""), reverse=reverse)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        for doc in self._docs:
            if self._projection:
                out = {}
                for k in self._projection:
                    if self._projection[k] and k in doc:
                        out[k] = doc[k]
                    elif not self._projection[k] and k != "_id" and k in doc:
                        continue
                if not self._projection:
                    yield doc
                else:
                    yield {**out, **{k: v for k, v in doc.items() if k not in self._projection or self._projection[k] == 0}}
            else:
                yield doc


class _MemoryCollection:
    def __init__(self):
        self._docs = []

    def insert_one(self, doc):
        self._docs.append(dict(doc))
        return type("InsertResult", (), {"inserted_id": len(self._docs) - 1})()

    def find(self, query=None, projection=None):
        query = query or {}
        docs = []
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                docs.append(doc)
        return _MemoryCursor(docs, projection)

    def find_one(self, query=None, projection=None):
        query = query or {}
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                if projection:
                    has_include = any(v for k, v in projection.items() if k != "_id")
                    if has_include:
                        out = {k: v for k, v in doc.items() if projection.get(k)}
                        if projection.get("_id", 1) and "_id" in doc:
                            out["_id"] = doc["_id"]
                        return out
                    else:
                        return {k: v for k, v in doc.items() if not (k in projection and projection[k] == 0)}
                return dict(doc)
        return None

    def delete_one(self, query=None):
        query = query or {}
        for idx, doc in enumerate(self._docs):
            if all(doc.get(k) == v for k, v in query.items()):
                del self._docs[idx]
                return _MemoryResult(1)
        return _MemoryResult(0)

    def count_documents(self, query=None):
        query = query or {}
        return sum(1 for doc in self._docs if all(doc.get(k) == v for k, v in query.items()))


class _MemoryDatabase:
    def __init__(self):
        self.scans = _MemoryCollection()


def _create_local_db():
    return _MemoryDatabase()


def _create_db_client(mongo_url: str, db_name: str):
    """Create a real Mongo client when available, otherwise use a local in-memory fallback."""
    if not mongo_url:
        return _create_local_db(), db_name

    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        return client, db_name
    except (ConfigurationError, ValueError, Exception):
        return _create_local_db(), db_name


def init_extensions(app):
    global _mongo_client, _db
    mongo_url = app.config.get("MONGO_URI") or os.environ.get("MONGO_URL", "")
    db_name = app.config.get("DB_NAME", "smartfarm")

    _mongo_client, db_name = _create_db_client(mongo_url, db_name)
    if hasattr(_mongo_client, "__getitem__"):
        _db = _mongo_client[db_name]
    else:
        _db = _mongo_client

    @app.teardown_appcontext
    def close_mongo(exc):
        pass


def get_db():
    """Return the active MongoDB database instance."""
    if _db is None:
        raise RuntimeError("MongoDB not initialised. Check MONGO_URL env var.")
    return _db

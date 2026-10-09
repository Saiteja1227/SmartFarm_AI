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
        self._docs = list(docs)
        self._projection = projection or {}

    def sort(self, key, direction):
        reverse = direction == -1
        self._docs = sorted(self._docs, key=lambda d: d.get(key) or "", reverse=reverse)
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        for doc in self._docs:
            if self._projection:
                has_include = any(v for k, v in self._projection.items() if k != "_id")
                if has_include:
                    out = {k: v for k, v in doc.items() if self._projection.get(k)}
                    if self._projection.get("_id", 1) and "_id" in doc:
                        out["_id"] = doc["_id"]
                    yield out
                else:
                    yield {k: v for k, v in doc.items() if not (k in self._projection and self._projection[k] == 0)}
            else:
                yield dict(doc)


def _match_condition(val, cond) -> bool:
    if isinstance(cond, dict):
        for op, target in cond.items():
            if op == "$in":
                if val not in (target or []):
                    return False
            elif op == "$ne":
                if val == target:
                    return False
            elif op == "$gte":
                if val is None or val < target:
                    return False
            elif op == "$lte":
                if val is None or val > target:
                    return False
            elif op == "$regex":
                import re
                flags = re.IGNORECASE if cond.get("$options") and "i" in cond.get("$options", "") else 0
                if not re.search(str(target), str(val or ""), flags):
                    return False
            elif op == "$options":
                continue
            else:
                return False
        return True
    return val == cond


def _matches_query(doc: dict, query: dict) -> bool:
    if not query:
        return True
    for k, v in query.items():
        if k == "$or":
            if not any(_matches_query(doc, sub) for sub in v):
                return False
        elif k == "$and":
            if not all(_matches_query(doc, sub) for sub in v):
                return False
        else:
            if not _match_condition(doc.get(k), v):
                return False
    return True


class _MemoryCollection:
    def __init__(self):
        self._docs = []

    def insert_one(self, doc):
        self._docs.append(dict(doc))
        return type("InsertResult", (), {"inserted_id": len(self._docs) - 1})()

    def find(self, query=None, projection=None):
        query = query or {}
        docs = [doc for doc in self._docs if _matches_query(doc, query)]
        return _MemoryCursor(docs, projection)

    def find_one(self, query=None, projection=None):
        query = query or {}
        for doc in self._docs:
            if _matches_query(doc, query):
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
            if _matches_query(doc, query):
                del self._docs[idx]
                return _MemoryResult(1)
        return _MemoryResult(0)

    def count_documents(self, query=None):
        query = query or {}
        return sum(1 for doc in self._docs if _matches_query(doc, query))

    def distinct(self, key, query=None):
        query = query or {}
        vals = []
        for doc in self._docs:
            if _matches_query(doc, query):
                v = doc.get(key)
                if v is not None and v not in vals:
                    vals.append(v)
        return vals


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

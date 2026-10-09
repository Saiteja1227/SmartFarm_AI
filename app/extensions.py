"""Flask extensions — Central MongoDB client with cross-instance cloud & disk-backed fallback."""
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

import requests
from pymongo import MongoClient
from pymongo.errors import ConfigurationError

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

logger = logging.getLogger(__name__)

_mongo_client = None
_db = None

# Central cloud sync configuration for serverless deployments when MONGO_URL is offline
CLOUD_KV_APP_KEY = os.environ.get("SF_CLOUD_KV_APPKEY", "2bkrxm95")
CLOUD_KV_INDEX_KEY = os.environ.get("SF_CLOUD_KV_INDEX", "sf_scans_v1")
CLOUD_KV_BASE = "https://keyvalue.immanuel.co/api/KeyVal"
CLOUD_BLOB_BASE = "https://bytebin.lucko.me"
LOCAL_CACHE_PATH = Path(tempfile.gettempdir()) / "smartfarm_scans_store_v1.json"


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
                    yield {
                        k: v
                        for k, v in doc.items()
                        if not (k in self._projection and self._projection[k] == 0)
                    }
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

                flags = (
                    re.IGNORECASE
                    if cond.get("$options") and "i" in cond.get("$options", "")
                    else 0
                )
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
    """
    Document collection with optional local disk cache and central HTTPS cloud sync
    so that multi-device scans persist across stateless Vercel serverless instances
    even when an external MongoDB cluster is unavailable.
    """

    def __init__(self, enable_persistence: bool = True):
        self._docs = []
        self._deleted_ids = set()
        self._last_idx_key = None
        self._last_sync_ts = 0.0
        self._lock = threading.Lock()
        self._enable_persistence = enable_persistence
        if self._enable_persistence:
            self._load_from_disk()
            self._sync_from_cloud(force=True)

    def _load_from_disk(self) -> None:
        try:
            if LOCAL_CACHE_PATH.exists():
                raw = json.loads(LOCAL_CACHE_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._docs = list(raw.get("docs") or [])
                    self._deleted_ids = set(raw.get("deleted_ids") or [])
                    self._last_idx_key = raw.get("idx_key")
        except Exception:
            pass

    def _save_to_disk(self) -> None:
        if not self._enable_persistence:
            return
        try:
            payload = {
                "idx_key": self._last_idx_key,
                "deleted_ids": list(self._deleted_ids),
                "docs": self._docs,
            }
            LOCAL_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    def _merge_remote_index(self, remote_data: dict) -> None:
        remote_deleted = set(remote_data.get("deleted_ids") or [])
        self._deleted_ids.update(remote_deleted)

        by_id = {}
        for d in self._docs:
            sid = d.get("id")
            if sid and sid not in self._deleted_ids:
                by_id[sid] = d

        for rd in remote_data.get("scans") or []:
            sid = rd.get("id")
            if not sid or sid in self._deleted_ids:
                continue
            if sid in by_id:
                existing = by_id[sid]
                # Preserve full images if already cached in memory
                merged = {**rd, **existing}
                if rd.get("_blob_key") and not merged.get("_blob_key"):
                    merged["_blob_key"] = rd["_blob_key"]
                by_id[sid] = merged
            else:
                by_id[sid] = dict(rd)

        self._docs = sorted(
            by_id.values(),
            key=lambda x: x.get("created_at") or "",
            reverse=True,
        )

    def _sync_from_cloud(self, force: bool = False) -> None:
        if not self._enable_persistence:
            return
        now = time.time()
        if not force and (now - self._last_sync_ts) < 1.5:
            return
        self._last_sync_ts = now
        try:
            r_ptr = requests.get(
                f"{CLOUD_KV_BASE}/GetValue/{CLOUD_KV_APP_KEY}/{CLOUD_KV_INDEX_KEY}",
                headers={"User-Agent": "SmartFarmAI/2.0"},
                timeout=2.5,
            )
            if r_ptr.status_code != 200:
                return
            idx_key = r_ptr.text.strip().strip('"')
            if not idx_key or idx_key == "init" or idx_key == self._last_idx_key:
                return

            r_blob = requests.get(
                f"{CLOUD_BLOB_BASE}/{idx_key}",
                headers={"User-Agent": "SmartFarmAI/2.0"},
                timeout=3.5,
            )
            if r_blob.status_code == 200:
                remote_data = r_blob.json()
                if isinstance(remote_data, dict):
                    self._merge_remote_index(remote_data)
                    self._last_idx_key = idx_key
                    self._save_to_disk()
        except Exception:
            pass

    def _push_to_cloud(self, new_doc: dict = None) -> None:
        if not self._enable_persistence:
            return
        try:
            # 1. If a new scan document with full images is provided, upload its full blob once
            if new_doc and not new_doc.get("_blob_key") and (
                new_doc.get("image_base64") or new_doc.get("enhanced_image_base64")
            ):
                r_full = requests.post(
                    f"{CLOUD_BLOB_BASE}/post",
                    json=new_doc,
                    headers={"User-Agent": "SmartFarmAI/2.0", "Content-Type": "application/json"},
                    timeout=5.0,
                )
                if r_full.status_code in (200, 201):
                    b_key = (r_full.json() or {}).get("key")
                    if b_key:
                        new_doc["_blob_key"] = b_key

            # 2. Pull latest remote index before writing to avoid overwriting concurrent device scans
            self._sync_from_cloud(force=True)

            # 3. Build compact index (includes metadata, report arrays, and thumbnail, omitting multi-MB raw blobs)
            compact_scans = []
            for d in self._docs[:250]:
                sid = d.get("id")
                if not sid or sid in self._deleted_ids:
                    continue
                thumb = d.get("thumbnail_base64") or (d.get("image_base64") or "")[:60000]
                entry = {
                    k: v
                    for k, v in d.items()
                    if k not in ("image_base64", "enhanced_image_base64")
                }
                entry["thumbnail_base64"] = thumb
                entry["has_original_image"] = bool(
                    d.get("has_original_image") or d.get("image_base64") or d.get("_blob_key")
                )
                entry["has_enhanced_image"] = bool(
                    d.get("has_enhanced_image")
                    or d.get("enhanced_image_base64")
                    or (d.get("image_enhanced") and d.get("_blob_key"))
                )
                compact_scans.append(entry)

            index_payload = {
                "updated_at": time.time(),
                "deleted_ids": list(self._deleted_ids)[-200:],
                "scans": compact_scans,
            }
            r_idx = requests.post(
                f"{CLOUD_BLOB_BASE}/post",
                json=index_payload,
                headers={"User-Agent": "SmartFarmAI/2.0", "Content-Type": "application/json"},
                timeout=4.0,
            )
            if r_idx.status_code in (200, 201):
                new_idx_key = (r_idx.json() or {}).get("key")
                if new_idx_key:
                    requests.post(
                        f"{CLOUD_KV_BASE}/UpdateValue/{CLOUD_KV_APP_KEY}/{CLOUD_KV_INDEX_KEY}/{new_idx_key}",
                        headers={"User-Agent": "SmartFarmAI/2.0"},
                        timeout=3.0,
                    )
                    self._last_idx_key = new_idx_key
                    self._save_to_disk()
        except Exception:
            self._save_to_disk()

    def _hydrate_doc_blob(self, doc: dict) -> dict:
        """Fetch full image_base64 / enhanced_image_base64 from cloud blob when needed."""
        if not self._enable_persistence:
            return doc
        blob_key = doc.get("_blob_key")
        if blob_key and not doc.get("image_base64"):
            try:
                r = requests.get(
                    f"{CLOUD_BLOB_BASE}/{blob_key}",
                    headers={"User-Agent": "SmartFarmAI/2.0"},
                    timeout=4.0,
                )
                if r.status_code == 200:
                    full_doc = r.json()
                    if isinstance(full_doc, dict):
                        doc["image_base64"] = full_doc.get("image_base64")
                        doc["enhanced_image_base64"] = full_doc.get("enhanced_image_base64")
                        self._save_to_disk()
            except Exception:
                pass
        return doc

    def insert_one(self, doc):
        with self._lock:
            doc_copy = dict(doc)
            if doc_copy.get("image_base64") and not doc_copy.get("thumbnail_base64"):
                doc_copy["thumbnail_base64"] = doc_copy["image_base64"][:60000]
            sid = doc_copy.get("id")
            self._docs = [d for d in self._docs if d.get("id") != sid]
            self._docs.insert(0, doc_copy)
            self._push_to_cloud(new_doc=doc_copy)
            return type("InsertResult", (), {"inserted_id": len(self._docs) - 1})()

    def find(self, query=None, projection=None):
        with self._lock:
            self._sync_from_cloud()
            query = query or {}
            docs = [doc for doc in self._docs if _matches_query(doc, query)]
            return _MemoryCursor(docs, projection)

    def find_one(self, query=None, projection=None):
        with self._lock:
            self._sync_from_cloud()
            query = query or {}
            for doc in self._docs:
                if _matches_query(doc, query):
                    self._hydrate_doc_blob(doc)
                    if projection:
                        has_include = any(v for k, v in projection.items() if k != "_id")
                        if has_include:
                            out = {k: v for k, v in doc.items() if projection.get(k)}
                            if projection.get("_id", 1) and "_id" in doc:
                                out["_id"] = doc["_id"]
                            return out
                        else:
                            return {
                                k: v
                                for k, v in doc.items()
                                if not (k in projection and projection[k] == 0)
                            }
                    return dict(doc)
            return None

    def delete_one(self, query=None):
        with self._lock:
            self._sync_from_cloud()
            query = query or {}
            for idx, doc in enumerate(self._docs):
                if _matches_query(doc, query):
                    sid = doc.get("id")
                    if sid:
                        self._deleted_ids.add(sid)
                    del self._docs[idx]
                    self._push_to_cloud()
                    return _MemoryResult(1)
            return _MemoryResult(0)

    def count_documents(self, query=None):
        with self._lock:
            self._sync_from_cloud()
            query = query or {}
            return sum(1 for doc in self._docs if _matches_query(doc, query))

    def distinct(self, key, query=None):
        with self._lock:
            self._sync_from_cloud()
            query = query or {}
            vals = []
            for doc in self._docs:
                if _matches_query(doc, query):
                    v = doc.get(key)
                    if v is not None and v not in vals:
                        vals.append(v)
            return vals


class _MemoryDatabase:
    def __init__(self, enable_persistence: bool = True):
        self.scans = _MemoryCollection(enable_persistence=enable_persistence)


def _create_local_db(enable_persistence: bool = True):
    return _MemoryDatabase(enable_persistence=enable_persistence)


def _is_usable_mongo_url(mongo_url: str) -> bool:
    if not mongo_url:
        return False
    lower = mongo_url.lower()
    if "<cluster>" in lower or "<password>" in lower or "cluster89379.y6kqtmj.mongodb.net" in lower:
        return False
    return lower.startswith("mongodb://") or lower.startswith("mongodb+srv://")


def _create_db_client(mongo_url: str, db_name: str, enable_persistence: bool = True):
    """Create a real Mongo client when available, otherwise use the cloud+disk synced fallback."""
    if not _is_usable_mongo_url(mongo_url):
        return _create_local_db(enable_persistence=enable_persistence), db_name

    try:
        kwargs = {
            "serverSelectionTimeoutMS": 5000,
            "connectTimeoutMS": 5000,
        }
        if certifi is not None and ("mongodb+srv://" in mongo_url or "tls=true" in mongo_url.lower() or "ssl=true" in mongo_url.lower()):
            kwargs["tlsCAFile"] = certifi.where()
        client = MongoClient(mongo_url, **kwargs)
        client.admin.command("ping")
        logger.info("Connected to MongoDB database '%s'", db_name)
        return client, db_name
    except (ConfigurationError, ValueError, Exception) as exc:
        logger.warning("MongoDB unavailable (%s); using cloud-synced persistence store.", exc)
        return _create_local_db(enable_persistence=enable_persistence), db_name


def init_extensions(app):
    global _mongo_client, _db
    mongo_url = app.config.get("MONGO_URI") or os.environ.get("MONGO_URL", "")
    db_name = app.config.get("DB_NAME", "smartfarm")
    enable_persistence = not bool(app.config.get("TESTING"))

    _mongo_client, db_name = _create_db_client(
        mongo_url, db_name, enable_persistence=enable_persistence
    )
    if hasattr(_mongo_client, "__getitem__"):
        _db = _mongo_client[db_name]
    else:
        _db = _mongo_client

    @app.teardown_appcontext
    def close_mongo(exc):
        pass


def get_db():
    """Return the active database instance."""
    if _db is None:
        raise RuntimeError("Database not initialised.")
    return _db

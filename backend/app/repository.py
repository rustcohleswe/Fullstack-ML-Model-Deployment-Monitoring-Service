"""Persistence layer: a Repository interface with Supabase and in-memory implementations."""
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

log = logging.getLogger("mlmonitor.repository")


class DuplicateModelError(Exception):
    """A model with the same name+version already exists."""


class RepositoryError(Exception):
    """The storage backend failed."""


class Repository(Protocol):
    def create_model(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    def list_models(self, name: Optional[str], version: Optional[str]) -> List[Dict[str, Any]]: ...
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]: ...
    def add_log(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    def list_logs(self, model_id: str, limit: int) -> List[Dict[str, Any]]: ...
    def metrics(self, model_id: Optional[str] = None) -> List[Dict[str, Any]]: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def aggregate(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(logs)
    if n == 0:
        return {"request_count": 0, "avg_latency_ms": 0.0, "avg_confidence": 0.0, "last_request_at": None}
    confs = [l["confidence"] for l in logs if l.get("confidence") is not None]
    return {
        "request_count": n,
        "avg_latency_ms": sum(l["latency_ms"] for l in logs) / n,
        "avg_confidence": sum(confs) / len(confs) if confs else 0.0,
        "last_request_at": max(l["created_at"] for l in logs),
    }


class InMemoryRepository:
    """Thread-safe volatile store used for local demos and tests."""

    def __init__(self) -> None:
        self._models: Dict[str, Dict[str, Any]] = {}
        self._logs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def create_model(self, data):
        with self._lock:
            if any(m["name"] == data["name"] and m["version"] == data["version"] for m in self._models.values()):
                raise DuplicateModelError(f"{data['name']}:{data['version']} already exists")
            rec = {**data, "id": str(uuid.uuid4()), "created_at": _now()}
            self._models[rec["id"]] = rec
            return dict(rec)

    def list_models(self, name, version):
        with self._lock:
            items = list(self._models.values())
        if name:
            items = [m for m in items if name.lower() in m["name"].lower()]
        if version:
            items = [m for m in items if version.lower() in m["version"].lower()]
        return sorted(items, key=lambda m: m["created_at"], reverse=True)

    def get_model(self, model_id):
        with self._lock:
            m = self._models.get(model_id)
            return dict(m) if m else None

    def add_log(self, data):
        with self._lock:
            rec = {**data, "id": str(uuid.uuid4()), "created_at": _now()}
            self._logs.append(rec)
            return dict(rec)

    def list_logs(self, model_id, limit):
        with self._lock:
            logs = [l for l in self._logs if l["model_id"] == model_id]
        return sorted(logs, key=lambda l: l["created_at"], reverse=True)[:limit]

    def metrics(self, model_id=None):
        with self._lock:
            ids = [model_id] if model_id else list(self._models)
            return [{"model_id": i, **aggregate([l for l in self._logs if l["model_id"] == i])} for i in ids]


class SupabaseRepository:
    """Supabase (PostgREST) implementation. Schema: see supabase/schema.sql."""

    def __init__(self, client: Any) -> None:
        self._db = client

    @staticmethod
    def _wrap(exc: Exception) -> RepositoryError:
        log.error("supabase error: %s", exc)
        return RepositoryError("storage backend error")

    def create_model(self, data):
        try:
            res = self._db.table("models").insert(data).execute()
        except Exception as exc:
            if getattr(exc, "code", None) == "23505":  # unique_violation
                raise DuplicateModelError(f"{data['name']}:{data['version']} already exists") from exc
            raise self._wrap(exc) from exc
        return res.data[0]

    def list_models(self, name, version):
        try:
            q = self._db.table("models").select("*")
            if name:
                q = q.ilike("name", f"%{name}%")
            if version:
                q = q.ilike("version", f"%{version}%")
            return q.order("created_at", desc=True).execute().data
        except Exception as exc:
            raise self._wrap(exc) from exc

    def get_model(self, model_id):
        try:
            rows = self._db.table("models").select("*").eq("id", model_id).limit(1).execute().data
        except Exception as exc:
            raise self._wrap(exc) from exc
        return rows[0] if rows else None

    def add_log(self, data):
        try:
            return self._db.table("prediction_logs").insert(data).execute().data[0]
        except Exception as exc:
            raise self._wrap(exc) from exc

    def list_logs(self, model_id, limit):
        try:
            return (self._db.table("prediction_logs").select("*").eq("model_id", model_id)
                    .order("created_at", desc=True).limit(limit).execute().data)
        except Exception as exc:
            raise self._wrap(exc) from exc

    def metrics(self, model_id=None):
        try:
            q = self._db.table("model_metrics").select("*")
            if model_id:
                q = q.eq("model_id", model_id)
            return q.execute().data
        except Exception as exc:
            raise self._wrap(exc) from exc

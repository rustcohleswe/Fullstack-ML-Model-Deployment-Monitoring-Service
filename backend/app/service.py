"""Business logic: model registration, simulated predictions, metrics."""
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.repository import Repository
from app.schemas import MetricsOut, ModelCreate, ModelType, PredictRequest


class ModelNotFound(Exception):
    pass


_LABELS = {
    ModelType.classification.value: ["positive", "negative", "neutral"],
    ModelType.nlp.value: ["spam", "ham", "toxic", "safe"],
    ModelType.clustering.value: [f"cluster_{i}" for i in range(5)],
}


def simulate_prediction(model_id: str, model_type: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fake inference: the same (model, features) always yields the same output."""
    digest = hashlib.sha256((model_id + json.dumps(features, sort_keys=True)).encode()).digest()
    n = int.from_bytes(digest[:4], "big")
    labels = _LABELS.get(model_type)
    prediction = labels[n % len(labels)] if labels else round((n % 100000) / 100.0, 2)
    return {
        "prediction": prediction,
        "confidence": round(0.5 + (digest[4] / 255) * 0.5, 4),
        "simulated_latency_ms": 5 + digest[5] % 95,  # pretend inference takes 5-99 ms
    }


class ModelService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def register(self, req: ModelCreate) -> Dict[str, Any]:
        return self.repo.create_model(req.model_dump(mode="json"))

    def list_models(self, name: Optional[str], version: Optional[str]) -> List[Dict[str, Any]]:
        return self.repo.list_models(name, version)

    def get_model(self, model_id: uuid.UUID) -> Dict[str, Any]:
        model = self.repo.get_model(str(model_id))
        if model is None:
            raise ModelNotFound(f"model {model_id} not found")
        return model

    def predict(self, model_id: uuid.UUID, req: PredictRequest) -> Dict[str, Any]:
        model = self.get_model(model_id)
        start = time.perf_counter()
        sim = simulate_prediction(str(model_id), model["model_type"], req.features)
        latency = round(sim["simulated_latency_ms"] + (time.perf_counter() - start) * 1000, 2)
        response = {"prediction": sim["prediction"], "confidence": sim["confidence"]}
        log = self.repo.add_log({
            "model_id": str(model_id), "request": {"features": req.features}, "response": response,
            "latency_ms": latency, "confidence": sim["confidence"],
        })
        return {"prediction_id": log["id"], "model_id": str(model_id), **response,
                "latency_ms": latency, "created_at": log["created_at"]}

    def list_predictions(self, model_id: uuid.UUID, limit: int) -> List[Dict[str, Any]]:
        self.get_model(model_id)
        return self.repo.list_logs(str(model_id), limit)

    def metrics_for(self, model_id: uuid.UUID) -> MetricsOut:
        self.get_model(model_id)
        rows = self.repo.metrics(str(model_id))
        return MetricsOut(**rows[0]) if rows else MetricsOut(model_id=model_id)

    def all_metrics(self) -> List[MetricsOut]:
        """Metrics for every model, including models that have not been called yet."""
        by_id = {str(r["model_id"]): r for r in self.repo.metrics(None)}
        out = []
        for m in self.repo.list_models(None, None):
            out.append(MetricsOut(**by_id.get(str(m["id"]), {"model_id": m["id"]})))
        return out

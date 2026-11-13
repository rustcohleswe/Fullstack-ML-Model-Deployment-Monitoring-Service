import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app, build_repository
from app.repository import InMemoryRepository, RepositoryError

FEATS = {"features": {"age": 30, "plan": "pro"}}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_model(client):
    r = client.post("/models", json={"name": " fraud ", "version": "2", "model_type": "regression", "description": "d"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "fraud" and body["model_type"] == "regression" and body["id"] and body["created_at"]


def test_duplicate_name_version_conflict(client, model):
    r = client.post("/models", json={"name": "churn", "version": "1.0.0", "model_type": "nlp"})
    assert r.status_code == 409


@pytest.mark.parametrize("payload", [
    {}, {"name": "x", "version": "1"}, {"name": "", "version": "1", "model_type": "nlp"},
    {"name": "  ", "version": "1", "model_type": "nlp"}, {"name": "x", "version": "1", "model_type": "bogus"},
    {"name": "x", "version": "1", "model_type": "nlp", "extra": 1},
])
def test_register_validation(client, payload):
    assert client.post("/models", json=payload).status_code == 422


def test_list_and_filter(client):
    for n, v in [("churn", "1.0"), ("churn", "2.0"), ("fraud", "1.0")]:
        client.post("/models", json={"name": n, "version": v, "model_type": "other"})
    assert len(client.get("/models").json()) == 3
    assert len(client.get("/models", params={"name": "CHU"}).json()) == 2
    assert len(client.get("/models", params={"version": "2"}).json()) == 1
    assert len(client.get("/models", params={"name": "fraud", "version": "1"}).json()) == 1
    assert client.get("/models", params={"name": "zzz"}).json() == []


def test_get_model_and_404(client, model):
    assert client.get(f"/models/{model['id']}").json()["name"] == "churn"
    assert client.get("/models/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/models/not-a-uuid").status_code == 422


def test_predict_logs_and_is_deterministic(client, model):
    a = client.post(f"/models/{model['id']}/predict", json=FEATS)
    b = client.post(f"/models/{model['id']}/predict", json=FEATS)
    assert a.status_code == 200
    ja, jb = a.json(), b.json()
    assert ja["prediction"] == jb["prediction"] and ja["confidence"] == jb["confidence"]
    assert ja["prediction_id"] != jb["prediction_id"]
    assert 0.5 <= ja["confidence"] <= 1 and ja["latency_ms"] >= 5
    logs = client.get(f"/models/{model['id']}/predictions").json()
    assert len(logs) == 2 and logs[0]["request"] == FEATS and logs[0]["created_at"]


@pytest.mark.parametrize("mtype", ["regression", "clustering", "nlp", "other"])
def test_predict_all_model_types(client, mtype):
    m = client.post("/models", json={"name": mtype, "version": "1", "model_type": mtype}).json()
    assert client.post(f"/models/{m['id']}/predict", json=FEATS).status_code == 200


@pytest.mark.parametrize("payload", [{}, {"features": {}}, {"features": {"a": [1]}}, {"features": {"a": 1}, "x": 1}])
def test_predict_validation(client, model, payload):
    assert client.post(f"/models/{model['id']}/predict", json=payload).status_code == 422


def test_predict_unknown_model(client):
    assert client.post("/models/00000000-0000-0000-0000-000000000000/predict", json=FEATS).status_code == 404


def test_metrics_aggregation(client, model):
    empty = client.get(f"/models/{model['id']}/metrics").json()
    assert empty["request_count"] == 0 and empty["avg_latency_ms"] == 0
    latencies = []
    for i in range(4):
        r = client.post(f"/models/{model['id']}/predict", json={"features": {"i": i}}).json()
        latencies.append(r["latency_ms"])
    m = client.get(f"/models/{model['id']}/metrics").json()
    assert m["request_count"] == 4
    assert m["avg_latency_ms"] == pytest.approx(sum(latencies) / 4)
    assert m["last_request_at"] is not None
    assert client.get("/models/00000000-0000-0000-0000-000000000000/metrics").status_code == 404


def test_all_metrics_includes_unused_models(client, model):
    other = client.post("/models", json={"name": "b", "version": "1", "model_type": "nlp"}).json()
    client.post(f"/models/{model['id']}/predict", json=FEATS)
    by_id = {m["model_id"]: m for m in client.get("/metrics").json()}
    assert by_id[model["id"]]["request_count"] == 1 and by_id[other["id"]]["request_count"] == 0


def test_predictions_limit_validation(client, model):
    assert client.get(f"/models/{model['id']}/predictions", params={"limit": 0}).status_code == 422


def test_storage_failure_maps_to_503():
    class Broken(InMemoryRepository):
        def list_models(self, name, version):
            raise RepositoryError("down")

    c = TestClient(create_app(Settings(), Broken()))
    assert c.get("/models").status_code == 503


def test_unhandled_error_is_500():
    class Boom(InMemoryRepository):
        def list_models(self, name, version):
            raise RuntimeError("bug")

    c = TestClient(create_app(Settings(), Boom()), raise_server_exceptions=False)
    r = c.get("/models")
    assert r.status_code == 500 and "bug" not in r.text


def test_build_repository_defaults_to_memory():
    assert isinstance(build_repository(Settings()), InMemoryRepository)


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "k")
    monkeypatch.setenv("CORS_ORIGINS", "http://a, http://b")
    s = Settings.from_env()
    assert s.has_supabase and s.cors_origins == ("http://a", "http://b")

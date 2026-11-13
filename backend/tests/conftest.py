import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repository import InMemoryRepository


@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.fixture
def client(repo):
    return TestClient(create_app(Settings(), repo))


@pytest.fixture
def model(client):
    r = client.post("/models", json={"name": "churn", "version": "1.0.0", "model_type": "classification"})
    assert r.status_code == 201
    return r.json()

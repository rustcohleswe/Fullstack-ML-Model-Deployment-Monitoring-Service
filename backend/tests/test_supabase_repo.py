"""SupabaseRepository tested against a mocked client (no network needed)."""
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.main import build_repository
from app.repository import DuplicateModelError, RepositoryError, SupabaseRepository


def make(data=None, error=None):
    q = MagicMock()
    for m in ("select", "insert", "ilike", "eq", "order", "limit"):
        getattr(q, m).return_value = q
    if error:
        q.execute.side_effect = error
    else:
        q.execute.return_value = MagicMock(data=data)
    client = MagicMock()
    client.table.return_value = q
    return SupabaseRepository(client), client, q


def test_create_model():
    repo, client, q = make([{"id": "1"}])
    assert repo.create_model({"name": "a"}) == {"id": "1"}
    client.table.assert_called_with("models")
    q.insert.assert_called_with({"name": "a"})


def test_create_duplicate_maps_to_domain_error():
    err = Exception("dup")
    err.code = "23505"
    repo, _, _ = make(error=err)
    with pytest.raises(DuplicateModelError):
        repo.create_model({"name": "a", "version": "1"})


def test_create_other_error_wrapped():
    repo, _, _ = make(error=Exception("boom"))
    with pytest.raises(RepositoryError):
        repo.create_model({"name": "a", "version": "1"})


def test_list_models_applies_filters():
    repo, _, q = make([{"id": "1"}])
    assert repo.list_models("ch", "2") == [{"id": "1"}]
    q.ilike.assert_any_call("name", "%ch%")
    q.ilike.assert_any_call("version", "%2%")


def test_get_model_found_and_missing():
    assert make([{"id": "1"}])[0].get_model("1") == {"id": "1"}
    assert make([])[0].get_model("1") is None


def test_logs_and_metrics():
    repo, client, q = make([{"x": 1}])
    assert repo.add_log({"a": 1}) == {"x": 1}
    assert repo.list_logs("m", 5) == [{"x": 1}]
    assert repo.metrics("m") == [{"x": 1}]
    assert repo.metrics() == [{"x": 1}]
    client.table.assert_called_with("model_metrics")


@pytest.mark.parametrize("call", [
    lambda r: r.list_models(None, None), lambda r: r.get_model("1"), lambda r: r.add_log({}),
    lambda r: r.list_logs("1", 1), lambda r: r.metrics(),
])
def test_errors_are_wrapped(call):
    repo, _, _ = make(error=Exception("down"))
    with pytest.raises(RepositoryError):
        call(repo)


def test_build_repository_with_supabase():
    with patch("supabase.create_client", return_value=MagicMock()) as cc:
        repo = build_repository(Settings(supabase_url="https://x.supabase.co", supabase_key="k"))
    assert isinstance(repo, SupabaseRepository)
    cc.assert_called_once_with("https://x.supabase.co", "k")

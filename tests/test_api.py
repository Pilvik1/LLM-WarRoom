from fastapi.testclient import TestClient

import backend.preset_storage as preset_storage
import backend.run_storage as run_storage
from backend.main import app


client = TestClient(app)


def test_provider_catalog_is_secret_free():
    response = client.get("/api/providers")

    assert response.status_code == 200
    body = response.json()
    assert "aliases" in body
    forbidden = {"api_key", "token", "secret", "authorization"}
    assert not forbidden.intersection(str(body).lower().replace("'", "").split())


def test_builtin_presets_are_available(tmp_path, monkeypatch):
    monkeypatch.setattr(preset_storage, "PRESETS_DIR", tmp_path / "presets")
    response = client.get("/api/presets")

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} >= {
        "general-council",
        "multi-model-ask",
        "structured-compare",
    }


def test_run_history_and_detail_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")

    assert client.get("/api/runs").json() == []
    missing = client.get("/api/runs/missing")
    assert missing.status_code == 404

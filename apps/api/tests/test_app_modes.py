import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.modes import account_workspace_id, data_workspace_id


def test_mode_workspace_namespaces_are_separate_from_legacy_data():
    assert data_workspace_id("default", "prod") == "default::prod"
    assert data_workspace_id("default", "test") == "default::test"
    assert account_workspace_id("default::prod") == "default"
    assert account_workspace_id("default::test") == "default"


def test_prod_and_test_modes_keep_incident_data_isolated(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("DIAS_CHECKPOINT_PATH", str(tmp_path / "checkpoints.sqlite3"))
    monkeypatch.setenv("DIAS_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("DIAS_ARTIFACT_PATH", str(tmp_path / "artifacts"))

    import app.config as config
    import app.database as database
    import app.main as main

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(main)

    with TestClient(main.app) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={"email": "modes@example.com", "password": "correct-horse-battery", "display_name": "Modes"},
        )
        assert signup.status_code == 201
        headers = {"x-csrf-token": signup.json()["csrf_token"]}

        assert client.get("/api/v1/mode").json()["mode"] == "prod"
        prod_incident = client.post(
            "/api/v1/incidents", headers=headers,
            json={"title": "Production incident", "service": "checkout", "environment": "production"},
        )
        assert prod_incident.status_code == 201
        prod_id = prod_incident.json()["id"]

        switched = client.patch("/api/v1/mode", headers=headers, json={"mode": "test"})
        assert switched.status_code == 200
        assert switched.json()["mode"] == "test"
        assert client.get("/api/v1/incidents").json() == []
        assert client.get(f"/api/v1/incidents/{prod_id}").status_code == 404

        test_incident = client.post(
            "/api/v1/incidents", headers=headers,
            json={"title": "Test fixture", "service": "payments", "environment": "test"},
        )
        assert test_incident.status_code == 201
        test_id = test_incident.json()["id"]
        assert [item["id"] for item in client.get("/api/v1/incidents").json()] == [test_id]

        switched_back = client.patch("/api/v1/mode", headers=headers, json={"mode": "prod"})
        assert switched_back.status_code == 200
        assert [item["id"] for item in client.get("/api/v1/incidents").json()] == [prod_id]
        assert client.get(f"/api/v1/incidents/{test_id}").status_code == 404


def test_invalid_mode_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("DIAS_STORAGE_PATH", str(tmp_path / "uploads"))

    import app.config as config
    import app.database as database
    import app.main as main

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(main)

    with TestClient(main.app) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={"email": "invalid-mode@example.com", "password": "correct-horse-battery", "display_name": "Modes"},
        )
        headers = {"x-csrf-token": signup.json()["csrf_token"]}
        response = client.patch("/api/v1/mode", headers=headers, json={"mode": "demo"})
        assert response.status_code == 422

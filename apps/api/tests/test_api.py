import importlib
import time
from pathlib import Path

from fastapi.testclient import TestClient


def test_human_approved_incident_flow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("DIAS_CHECKPOINT_PATH", str(tmp_path / "checkpoints.sqlite3"))
    monkeypatch.setenv("DIAS_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("DIAS_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    import app.config as config
    importlib.reload(config)
    import app.database as database
    importlib.reload(database)
    import app.orchestrator as orchestrator
    importlib.reload(orchestrator)
    import app.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        response = client.post("/api/v1/auth/signup", json={"email":"admin@example.com","password":"correct-horse-battery","display_name":"Admin"})
        assert response.status_code == 201
        csrf = response.json()["csrf_token"]
        headers = {"x-csrf-token": csrf}
        incident = client.post("/api/v1/incidents", headers=headers, json={"title":"Database saturation","service":"checkout","environment":"production"}).json()
        upload = client.post(f"/api/v1/incidents/{incident['id']}/files", headers=headers, files=[("files",("checkout.log",b"2026-09-05T12:00:00Z CRITICAL database connection pool exhausted trace_id=req-1","text/plain"))])
        assert upload.status_code == 201
        run = client.post(f"/api/v1/incidents/{incident['id']}/runs", headers=headers)
        assert run.status_code == 202
        detail = client.get(f"/api/v1/incidents/{incident['id']}").json()
        assert detail["findings"]
        assert detail["findings"][0]["evidence"]
        action = detail["actions"][0]
        assert action["status"] == "pending"
        decision = client.post(f"/api/v1/actions/{action['id']}/approve", headers=headers, json={"payload_hash":action["payload_hash"]})
        assert decision.status_code == 200
        assert decision.json()["status"] == "delivered"

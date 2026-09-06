import importlib
import time
from pathlib import Path

from fastapi.testclient import TestClient


def test_human_approved_incident_flow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("DIAS_CHECKPOINT_PATH", str(tmp_path / "checkpoints.sqlite3"))
    monkeypatch.setenv("DIAS_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("DIAS_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DIAS_INTEGRATIONS_MODE", "mock")
    import app.config as config
    importlib.reload(config)
    import app.database as database
    importlib.reload(database)
    import app.orchestrator as orchestrator
    importlib.reload(orchestrator)
    import app.main as main
    importlib.reload(main)
    assert not orchestrator.integration_available("slack")
    assert not orchestrator.integration_available("jira")
    monkeypatch.setattr(orchestrator, "integration_available", lambda provider: provider == "slack")
    monkeypatch.setattr(main, "integration_available", lambda provider, verify=True: provider == "slack")
    with TestClient(main.app) as client:
        response = client.post("/api/v1/auth/signup", json={"email":"admin@example.com","password":"correct-horse-battery","display_name":"Admin"})
        assert response.status_code == 201
        csrf = response.json()["csrf_token"]
        headers = {"x-csrf-token": csrf}
        incident = client.post("/api/v1/incidents", headers=headers, json={"title":"Database saturation","service":"checkout","environment":"production"}).json()
        upload = client.post(f"/api/v1/incidents/{incident['id']}/files", headers=headers, files=[("files",("checkout.log",b"2026-09-05T12:00:00Z ERROR database connection pool exhausted trace_id=req-1","text/plain"))])
        assert upload.status_code == 201
        run = client.post(f"/api/v1/incidents/{incident['id']}/runs", headers=headers)
        assert run.status_code == 202
        detail = client.get(f"/api/v1/incidents/{incident['id']}").json()
        assert detail["findings"]
        assert detail["findings"][0]["evidence"]
        assert detail["status"] == "active"

        resolved = client.patch(f"/api/v1/incidents/{incident['id']}/status", headers=headers, json={"status":"resolved"})
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"
        assert resolved.json()["event"]["phase"] == "incident_status"
        assert "ACTIVE to RESOLVED" in resolved.json()["event"]["message"]
        resolved_detail = client.get(f"/api/v1/incidents/{incident['id']}").json()
        assert resolved_detail["status"] == "resolved"
        assert resolved_detail["resolved_at"] is not None

        active = client.patch(f"/api/v1/incidents/{incident['id']}/status", headers=headers, json={"status":"active"})
        assert active.status_code == 200
        assert active.json()["status"] == "active"
        active_detail = client.get(f"/api/v1/incidents/{incident['id']}").json()
        assert active_detail["status"] == "active"
        assert active_detail["resolved_at"] is None
        audit_events = client.get("/api/v1/audit").json()
        status_changes = [event for event in audit_events if event["action"] == "incident.status_changed"]
        assert len(status_changes) == 2
        assert status_changes[0]["details"] == {"from":"resolved", "to":"active"}
        actions = detail["actions"]
        assert actions
        assert all(action["status"] == "pending" for action in actions)
        assert detail["runs"][0]["status"] == "awaiting_approval"
        assert detail["runs"][0]["completed_at"] is None

        for index, action in enumerate(actions):
            decision = "approve" if index % 2 == 0 else "reject"
            response = client.post(f"/api/v1/actions/{action['id']}/{decision}", headers=headers, json={"payload_hash":action["payload_hash"]})
            assert response.status_code == 200
            expected = "delivered" if decision == "approve" else "rejected"
            assert response.json()["status"] == expected

            run_detail = client.get(f"/api/v1/runs/{detail['runs'][0]['id']}").json()
            if index < len(actions) - 1:
                assert run_detail["status"] == "awaiting_approval"
                assert run_detail["completed_at"] is None

        assert run_detail["status"] == "completed"
        assert run_detail["current_phase"] == "complete"
        assert run_detail["completed_at"] is not None

        final_detail = client.get(f"/api/v1/incidents/{incident['id']}").json()
        assert not any(action["status"] == "pending" for action in final_detail["actions"])

        critical = client.post("/api/v1/incidents", headers=headers, json={"title":"Critical database saturation","service":"checkout","environment":"production"}).json()
        critical_upload = client.post(f"/api/v1/incidents/{critical['id']}/files", headers=headers, files=[("files",("critical.log",b"2026-09-05T12:00:00Z CRITICAL database connection pool exhausted trace_id=req-2","text/plain"))])
        assert critical_upload.status_code == 201
        critical_run = client.post(f"/api/v1/incidents/{critical['id']}/runs", headers=headers)
        assert critical_run.status_code == 202
        critical_detail = client.get(f"/api/v1/incidents/{critical['id']}").json()
        assert any(action["kind"] == "slack" for action in critical_detail["actions"])
        jira = next(action for action in critical_detail["actions"] if action["kind"] == "jira")
        assert jira["status"] == "unavailable"

import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def _client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("DIAS_CHECKPOINT_PATH", str(tmp_path / "checkpoints.sqlite3"))
    monkeypatch.setenv("DIAS_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("DIAS_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    import app.config as config
    import app.database as database
    import app.auth as auth
    import app.ai_config as ai_config
    import app.providers as providers
    import app.orchestrator as orchestrator
    import app.main as main

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(auth)
    importlib.reload(ai_config)
    importlib.reload(providers)
    importlib.reload(orchestrator)
    importlib.reload(main)
    return main, TestClient(main.app)


def test_openrouter_settings_are_masked_testable_and_removable(tmp_path, monkeypatch):
    main, client = _client(tmp_path, monkeypatch)
    with client:
        signup = client.post("/api/v1/auth/signup", json={"email": "settings-admin@example.com", "password": "correct-horse-battery", "display_name": "Admin"})
        assert signup.status_code == 201, signup.text
        csrf = signup.json()["csrf_token"]
        headers = {"x-csrf-token": csrf}

        saved = client.put("/api/v1/integrations/openrouter", headers=headers, json={"api_key": "sk-or-test-secret", "model": "test/model"})
        assert saved.status_code == 200
        assert saved.json()["configured"] is True
        assert saved.json()["key_hint"] == "••••cret"
        assert "sk-or-test-secret" not in saved.text

        class Response:
            def raise_for_status(self): pass
            def json(self): return {"data": [{"id": "test/model"}]}

        monkeypatch.setattr(main.httpx, "get", lambda *args, **kwargs: Response())
        tested = client.post("/api/v1/integrations/openrouter/test", headers=headers)
        assert tested.json() == {"provider": "openrouter", "status": "connected", "model": "test/model"}

        removed = client.put("/api/v1/integrations/openrouter", headers=headers, json={"model": "test/model", "clear_api_key": True})
        assert removed.json()["status"] == "deterministic"
        assert removed.json()["key_hint"] is None


def test_incident_chat_uses_deterministic_mode_without_key(tmp_path, monkeypatch):
    _, client = _client(tmp_path, monkeypatch)
    with client:
        signup = client.post("/api/v1/auth/signup", json={"email": "fallback-admin@example.com", "password": "correct-horse-battery", "display_name": "Admin"})
        assert signup.status_code == 201, signup.text
        headers = {"x-csrf-token": signup.json()["csrf_token"]}
        client.put("/api/v1/integrations/openrouter", headers=headers, json={"model": "test/model", "clear_api_key": True})
        incident = client.post("/api/v1/incidents", headers=headers, json={"title": "Deterministic incident"}).json()

        response = client.post(f"/api/v1/incidents/{incident['id']}/chat", headers=headers, json={"content": "What happened?"})
        assert response.status_code == 201
        assert "Deterministic analysis mode is active" in response.text
        assert '"source": "deterministic"' in response.text

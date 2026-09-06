import importlib
from pathlib import Path

import httpx
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
    import app.integration_config as integration_config
    import app.connection_tests as connection_tests
    import app.providers as providers
    import app.orchestrator as orchestrator
    import app.main as main

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(auth)
    importlib.reload(ai_config)
    importlib.reload(integration_config)
    importlib.reload(connection_tests)
    importlib.reload(providers)
    importlib.reload(orchestrator)
    importlib.reload(main)
    return main, TestClient(main.app)


def test_openrouter_settings_are_masked_testable_and_removable(tmp_path, monkeypatch):
    main, client = _client(tmp_path, monkeypatch)
    import app.connection_tests as connection_tests
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

        class KeyResponse:
            def raise_for_status(self): pass
            def json(self): return {"data": {"label": "test-key"}}

        class ModelsResponse:
            def raise_for_status(self): pass
            def json(self): return {"data": [{"id": "test/model"}]}

        monkeypatch.setattr(connection_tests.httpx, "get", lambda url, *args, **kwargs: KeyResponse() if url.endswith("/key") else ModelsResponse())
        tested = client.post("/api/v1/integrations/openrouter/test", headers=headers)
        assert tested.json() == {"provider": "openrouter", "status": "connected", "model": "test/model"}

        removed = client.put("/api/v1/integrations/openrouter", headers=headers, json={"model": "test/model", "clear_api_key": True})
        assert removed.json()["status"] == "deterministic"
        assert removed.json()["key_hint"] is None


def test_openrouter_connection_rejects_an_invalid_key(tmp_path, monkeypatch):
    _, client = _client(tmp_path, monkeypatch)
    import app.connection_tests as connection_tests

    with client:
        signup = client.post("/api/v1/auth/signup", json={"email": "invalid-key-admin@example.com", "password": "correct-horse-battery", "display_name": "Admin"})
        headers = {"x-csrf-token": signup.json()["csrf_token"]}
        client.put("/api/v1/integrations/openrouter", headers=headers, json={"api_key": "sk-or-invalid", "model": "test/model"})

        class UnauthorizedResponse:
            def raise_for_status(self):
                request = httpx.Request("GET", "https://openrouter.ai/api/v1/key")
                response = httpx.Response(401, request=request)
                raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

        monkeypatch.setattr(connection_tests.httpx, "get", lambda *args, **kwargs: UnauthorizedResponse())
        tested = client.post("/api/v1/integrations/openrouter/test", headers=headers)

        assert tested.status_code == 503
        assert tested.json()["detail"] == "OpenRouter rejected the connection (HTTP 401)"


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


def test_slack_settings_are_workspace_scoped_masked_and_testable(tmp_path, monkeypatch):
    main, client = _client(tmp_path, monkeypatch)
    import app.connection_tests as connection_tests

    with client:
        signup = client.post("/api/v1/auth/signup", json={"email": "slack-admin@example.com", "password": "correct-horse-battery", "display_name": "Admin"})
        headers = {"x-csrf-token": signup.json()["csrf_token"]}
        saved = client.put("/api/v1/integrations/slack", headers=headers, json={"bot_token": "xoxb-test-secret", "channel_id": "C0123456789"})

        assert saved.status_code == 200
        assert saved.json()["status"] == "configured"
        assert saved.json()["token_hint"] == "••••cret"
        assert "xoxb-test-secret" not in saved.text
        integrations = client.get("/api/v1/integrations").json()
        assert next(item for item in integrations if item["provider"] == "slack")["status"] == "configured"
        assert next(item for item in integrations if item["provider"] == "jira")["status"] == "not configured"
        assert "sandbox" not in str(integrations).lower()
        assert "mock" not in str(integrations).lower()

        class AuthResponse:
            def raise_for_status(self): pass
            def json(self): return {"ok": True, "team": "Test workspace"}

        class ChannelResponse:
            def raise_for_status(self): pass
            def json(self): return {"ok": True, "channel": {"name": "incidents"}}

        monkeypatch.setattr(connection_tests.httpx, "post", lambda *args, **kwargs: AuthResponse())
        monkeypatch.setattr(connection_tests.httpx, "get", lambda *args, **kwargs: ChannelResponse())
        tested = client.post("/api/v1/integrations/slack/test", headers=headers)
        assert tested.json()["status"] == "connected"
        assert tested.json()["workspace"] == "Test workspace"
        assert tested.json()["channel"] == "incidents"
        assert tested.json()["channel_verified"] is True

        class MissingChannelResponse:
            def raise_for_status(self): pass
            def json(self): return {"ok": False, "error": "channel_not_found"}

        monkeypatch.setattr(connection_tests.httpx, "get", lambda *args, **kwargs: MissingChannelResponse())
        rejected = client.post("/api/v1/integrations/slack/test", headers=headers)
        assert rejected.status_code == 422
        assert rejected.json()["detail"] == "Slack channel was not found or is not accessible to this bot"

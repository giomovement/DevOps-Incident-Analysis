import importlib
import json
from pathlib import Path


def _load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("DIAS_CHECKPOINT_PATH", str(tmp_path / "checkpoints.sqlite3"))
    monkeypatch.setenv("DIAS_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("DIAS_ARTIFACT_PATH", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DIAS_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("DIAS_OPENROUTER_REASONING_MODEL", "test/model")
    monkeypatch.setenv("DIAS_OPENROUTER_BASE_URL_CHAT_COMPLETION", "https://example.test/chat/completions")
    import app.config as config
    importlib.reload(config)
    import app.database as database
    importlib.reload(database)
    import app.providers as providers
    importlib.reload(providers)
    import app.orchestrator as orchestrator
    importlib.reload(orchestrator)
    database.init_db()
    return database, orchestrator


def _seed(database):
    now = database.utcnow()
    with database.db() as conn:
        conn.execute("INSERT INTO users(id,email,password_hash,display_name,role,workspace_id,created_at) VALUES('user','ai@example.test','hash','AI Test','admin','workspace',?)", (now,))
        conn.execute("INSERT INTO incidents(id,workspace_id,title,service,environment,created_by,created_at,updated_at) VALUES('incident','workspace','Checkout errors','checkout','production','user',?,?)", (now, now))
        conn.execute("INSERT INTO runs(id,incident_id,thread_id,status,current_phase,created_at) VALUES('run','incident','thread','running','recommend',?)", (now,))
        conn.execute("INSERT INTO findings(id,incident_id,run_id,issue_type,severity,confidence,service,root_cause,rationale,created_at) VALUES('finding','incident','run','database','high',0.91,'checkout','Connection pool exhaustion','Repeated pool errors',?)", (now,))


class FakeProvider:
    async def structured_generate(self, *, model, messages, schema):
        if "recommendations" in schema["properties"]:
            phases = {phase: [f"AI {phase} step"] for phase in ("triage", "containment", "diagnosis", "remediation", "validation", "rollback")}
            return {"recommendations": [{"finding_id": "finding", "phases": phases, "rationale": "AI rationale", "assumptions": ["AI assumption"], "risks": ["AI risk"]}]}
        sections = "\n".join(f"## {name}\n- [ ] AI {name.lower()} step" for name in ("Triage", "Containment", "Diagnosis", "Remediation", "Validation", "Rollback", "Monitoring", "Post-incident follow-up"))
        return {"markdown": f"# Incident Response Cookbook\n\n> Human validation required.\n\n{sections}"}


def test_ai_recommend_and_cookbook_nodes_persist_structured_results(tmp_path, monkeypatch):
    database, orchestrator = _load_modules(tmp_path, monkeypatch)
    _seed(database)
    monkeypatch.setattr(orchestrator, "llm_provider", lambda: FakeProvider())
    state = {
        "run_id": "run", "incident_id": "incident",
        "incident_context": {"title": "Checkout errors", "service": "checkout", "environment": "production"},
        "findings": [{"id": "finding", "issue_type": "database", "severity": "high", "confidence": .91, "service": "checkout", "root_cause": "Connection pool exhaustion", "rationale": "Repeated pool errors", "evidence_ids": []}],
    }

    recommendation_result = orchestrator.remediate_with_ai(state)
    assert recommendation_result["recommendations"][0]["phases"]["triage"] == ["AI triage step"]

    cookbook_result = orchestrator.cookbook_with_ai({**state, **recommendation_result})
    assert cookbook_result["cookbook_ref"]
    with database.db() as conn:
        stored_recommendation = conn.execute("SELECT phases,rationale FROM recommendations WHERE finding_id='finding'").fetchone()
        stored_cookbook = conn.execute("SELECT markdown FROM cookbooks WHERE incident_id='incident'").fetchone()
        events = conn.execute("SELECT phase,payload FROM workflow_events WHERE status='completed'").fetchall()
    assert json.loads(stored_recommendation["phases"])["remediation"] == ["AI remediation step"]
    assert stored_recommendation["rationale"] == "AI rationale"
    assert "AI monitoring step" in stored_cookbook["markdown"]
    assert all(json.loads(event["payload"])["source"] == "ai" for event in events)


def test_ai_nodes_use_existing_deterministic_fallback(tmp_path, monkeypatch):
    database, orchestrator = _load_modules(tmp_path, monkeypatch)
    _seed(database)

    class FailingProvider:
        async def structured_generate(self, **kwargs):
            raise TimeoutError("provider unavailable")

    monkeypatch.setattr(orchestrator, "llm_provider", lambda: FailingProvider())
    fallback = {"recommendations": [{"fallback": True}]}
    monkeypatch.setattr(orchestrator, "remediate", lambda state: fallback)

    assert orchestrator.remediate_with_ai({"run_id": "run", "incident_id": "incident", "findings": [{"id": "finding"}]}) is fallback
    with database.db() as conn:
        event = conn.execute("SELECT message,payload FROM workflow_events WHERE status='partial' ORDER BY id DESC LIMIT 1").fetchone()
    assert "deterministic fallback" in event["message"]
    assert json.loads(event["payload"])["error_type"] == "TimeoutError"

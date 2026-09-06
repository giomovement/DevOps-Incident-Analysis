from app.orchestrator import (
    MAX_SLACK_MESSAGE_WORDS,
    build_slack_findings_summary,
    build_slack_findings_summary_with_ai,
)


def finding(issue_type, severity, confidence, service, root_cause):
    return {
        "issue_type": issue_type,
        "severity": severity,
        "confidence": confidence,
        "service": service,
        "root_cause": root_cause,
    }


def test_slack_summary_contains_all_findings_grouped_and_ranked():
    state = {
        "incident_id": "incident-1",
        "incident_context": {"title": "Checkout failures", "environment": "production"},
        "findings": [
            finding("network", "high", .95, "payments", "Upstream timeout"),
            finding("database", "high", .82, "checkout", "Query timeout"),
            finding("database", "critical", .91, "payments", "Connection pool exhausted"),
            finding("deployment", "medium", .78, "checkout", "Regression after deployment"),
        ],
    }

    text = build_slack_findings_summary(state)["text"]

    assert text.startswith("CRITICAL Incident analysis identified 4 finding(s) across 3 type(s)")
    assert text.count("DATABASE (2, CRITICAL)") == 1
    assert "NETWORK (1, HIGH)" in text
    assert "DEPLOYMENT (1, MEDIUM)" in text
    assert "Summary of findings classified by issue types:" in text
    assert text.index("DATABASE (") < text.index("NETWORK (") < text.index("DEPLOYMENT (")
    assert len(text.split()) <= MAX_SLACK_MESSAGE_WORDS


def test_slack_summary_uses_stable_tie_breakers_and_bounds_lines():
    state = {
        "incident_context": {},
        "findings": [
            finding("application", "high", .8, "z-service", "Z failure"),
            finding("application", "high", .8, "a-service", "A failure\nwith extra whitespace"),
            finding("capacity", "high", .8, "worker", "x" * 300),
        ],
    }

    text = build_slack_findings_summary(state)["text"]

    assert text.index("APPLICATION (") < text.index("CAPACITY (")
    assert text.index("a-service") < text.index("z-service")
    assert len(text.split()) <= MAX_SLACK_MESSAGE_WORDS


def test_ai_slack_summary_uses_prompt_level_text(monkeypatch):
    state = {
        "run_id": "run-1",
        "incident_id": "incident-1",
        "incident_context": {"title": "Checkout failures", "environment": "production"},
        "findings": [finding("database", "critical", .91, "checkout", "Connection pool exhausted")],
    }
    expected = """CRITICAL Incident analysis identified 1 finding(s) across 1 type(s)

Incident: Checkout failures
Environment: production
Affected Services: checkout

Summary of findings classified by issue types:
DATABASE: Connection pool exhaustion."""
    captured = {}

    def fake_generate_chat(*, messages):
        captured["messages"] = messages
        return expected

    monkeypatch.setattr("app.orchestrator._generate_chat", fake_generate_chat)

    assert build_slack_findings_summary_with_ai(state) == {"text": expected}
    assert "json_schema" not in str(captured["messages"])
    assert "Maximum 100 words" in captured["messages"][1]["content"]


def test_ai_slack_summary_falls_back_when_format_is_invalid(monkeypatch):
    state = {
        "run_id": "run-1",
        "incident_id": "incident-1",
        "incident_context": {"title": "Checkout failures", "environment": "production"},
        "findings": [finding("database", "critical", .91, "checkout", "Connection pool exhausted")],
    }
    monkeypatch.setattr("app.orchestrator._generate_chat", lambda **kwargs: "Invalid response")
    monkeypatch.setattr("app.orchestrator.emit", lambda *args, **kwargs: None)

    text = build_slack_findings_summary_with_ai(state)["text"]

    assert text.startswith("CRITICAL Incident analysis identified")
    assert "Affected Services:" in text
    assert len(text.split()) <= MAX_SLACK_MESSAGE_WORDS

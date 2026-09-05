from app.parsing import classify, record


def test_secret_redaction_and_normalization():
    event = record("2026-09-05T12:00:00Z ERROR token=super-secret database connection pool exhausted", 4, 4)
    assert "super-secret" not in event["message"]
    assert event["secret_redacted"] is True
    assert event["severity"] == "high"
    assert event["timestamp"].startswith("2026-09-05T12:00:00")


def test_issue_classification():
    issue, root, confidence = classify("postgres connection pool exhausted")
    assert issue == "database"
    assert confidence > 0.8

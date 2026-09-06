from app.database import POSTGRES_SCHEMA, PostgresConnection


class _FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))
        return "cursor"


def test_postgres_connection_translates_placeholders_without_interpolating_values():
    raw = _FakeConnection()
    connection = PostgresConnection(raw)

    result = connection.execute(
        "SELECT * FROM incidents WHERE workspace_id=? AND title=?",
        ("workspace", "What happened?"),
    )

    assert result == "cursor"
    assert raw.calls == [
        (
            "SELECT * FROM incidents WHERE workspace_id=%s AND title=%s",
            ("workspace", "What happened?"),
        )
    ]


def test_postgres_schema_does_not_include_sqlite_only_features():
    assert "PRAGMA" not in POSTGRES_SCHEMA
    assert "AUTOINCREMENT" not in POSTGRES_SCHEMA
    assert "CREATE VIRTUAL TABLE" not in POSTGRES_SCHEMA
    assert "BIGSERIAL PRIMARY KEY" in POSTGRES_SCHEMA
    assert "to_tsvector('english', message)" in POSTGRES_SCHEMA

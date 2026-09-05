import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator

from .config import settings


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','responder','viewer')),
  workspace_id TEXT NOT NULL DEFAULT 'default', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  id_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf_hash TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT,
  service TEXT, environment TEXT, deployment TEXT, status TEXT NOT NULL DEFAULT 'draft',
  severity TEXT, created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, resolved_at TEXT, version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  original_name TEXT NOT NULL, storage_name TEXT NOT NULL, content_type TEXT, size INTEGER NOT NULL,
  sha256 TEXT NOT NULL, status TEXT NOT NULL, warning TEXT, created_at TEXT NOT NULL,
  UNIQUE(incident_id, sha256)
);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  thread_id TEXT NOT NULL, status TEXT NOT NULL, current_phase TEXT NOT NULL,
  cancel_requested INTEGER NOT NULL DEFAULT 0, started_at TEXT, completed_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workflow_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  phase TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS log_events (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE, line_start INTEGER NOT NULL,
  line_end INTEGER NOT NULL, byte_start INTEGER NOT NULL DEFAULT 0, byte_end INTEGER NOT NULL DEFAULT 0,
  timestamp TEXT, original_timestamp TEXT, severity TEXT, service TEXT, environment TEXT,
  correlation_id TEXT, message TEXT NOT NULL, attributes TEXT NOT NULL DEFAULT '{}', content_hash TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS log_events_fts USING fts5(event_id UNINDEXED, incident_id UNINDEXED, message, tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  finding_id TEXT, event_id TEXT NOT NULL REFERENCES log_events(id) ON DELETE CASCADE,
  excerpt TEXT NOT NULL, source_label TEXT NOT NULL, line_start INTEGER NOT NULL, line_end INTEGER NOT NULL,
  content_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, issue_type TEXT NOT NULL,
  severity TEXT NOT NULL, confidence REAL NOT NULL, service TEXT, root_cause TEXT NOT NULL,
  rationale TEXT NOT NULL, first_observed TEXT, last_observed TEXT, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
  id TEXT PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  phases TEXT NOT NULL, rationale TEXT NOT NULL, assumptions TEXT NOT NULL, risks TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS action_drafts (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, kind TEXT NOT NULL,
  destination TEXT NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'pending', version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY, action_id TEXT NOT NULL REFERENCES action_drafts(id) ON DELETE CASCADE,
  payload_hash TEXT NOT NULL, decision TEXT NOT NULL, approver_id TEXT NOT NULL REFERENCES users(id),
  comment TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deliveries (
  id TEXT PRIMARY KEY, action_id TEXT NOT NULL UNIQUE REFERENCES action_drafts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL, destination TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL,
  external_id TEXT, external_url TEXT, error TEXT, delivered_at TEXT
);
CREATE TABLE IF NOT EXISTS cookbooks (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL UNIQUE REFERENCES incidents(id) ON DELETE CASCADE,
  markdown TEXT NOT NULL, artifact_path TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL, content TEXT NOT NULL, citations TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS integrations (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, provider TEXT NOT NULL, status TEXT NOT NULL,
  display_name TEXT, secret_ref TEXT, metadata TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL,
  UNIQUE(workspace_id, provider)
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, actor_id TEXT,
  incident_id TEXT, action TEXT NOT NULL, target_type TEXT, target_id TEXT, details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_workspace_created ON incidents(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_incident ON files(incident_id);
CREATE INDEX IF NOT EXISTS idx_runs_incident ON runs(incident_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_incident_timestamp ON log_events(incident_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_findings_incident_severity ON findings(incident_id, severity);
CREATE INDEX IF NOT EXISTS idx_actions_incident_status ON action_drafts(incident_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_workspace_created ON audit_events(workspace_id, created_at DESC);
"""


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def init_db() -> None:
    settings.ensure_directories()
    with sqlite3.connect(settings.database_path) as conn:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA optimize")


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_dict(row: sqlite3.Row | None):
    return dict(row) if row else None

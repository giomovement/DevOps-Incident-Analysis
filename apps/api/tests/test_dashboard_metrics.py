import importlib
from datetime import UTC, datetime, timedelta


def test_dashboard_metrics_uses_workspace_evidence_and_resolution_times(tmp_path, monkeypatch):
    monkeypatch.setenv("DIAS_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    import app.config as config
    import app.database as database
    import app.dashboard_metrics as metrics

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(metrics)
    database.init_db()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=UTC)
    resolved = created + timedelta(minutes=30)
    with database.db() as conn:
        conn.execute("INSERT INTO users(id,email,password_hash,display_name,role,workspace_id,created_at) VALUES('user','dash@example.test','hash','Dashboard','admin','workspace',?)", (created.isoformat(),))
        conn.execute("INSERT INTO incidents(id,workspace_id,title,status,severity,created_by,created_at,updated_at,resolved_at) VALUES('incident','workspace','Resolved','resolved','critical','user',?,?,?)", (created.isoformat(), resolved.isoformat(), resolved.isoformat()))
        conn.execute("INSERT INTO runs(id,incident_id,thread_id,status,current_phase,created_at) VALUES('run','incident','thread','completed','done',?)", (created.isoformat(),))
        conn.execute("INSERT INTO findings(id,incident_id,run_id,issue_type,severity,confidence,root_cause,rationale,created_at) VALUES('finding','incident','run','database','critical',0.9,'Pool exhaustion','Evidence',?)", (created.isoformat(),))
        for index, observed in enumerate((resolved - timedelta(hours=23, minutes=30), resolved - timedelta(minutes=30))):
            conn.execute("INSERT INTO files(id,incident_id,original_name,storage_name,size,sha256,status,created_at) VALUES(?,?,?,?,?,?,?,?)", (f'file-{index}', 'incident', f'{index}.log', f'{index}.log', 1, f'hash-{index}', 'parsed', created.isoformat()))
            conn.execute("INSERT INTO log_events(id,incident_id,file_id,line_start,line_end,timestamp,message,content_hash) VALUES(?,?,?,?,?,?,?,?)", (f'event-{index}', 'incident', f'file-{index}', 1, 1, observed.isoformat(), 'error', f'event-hash-{index}'))

    result = metrics.dashboard_metrics("workspace")

    assert result["active_incidents"] == 0
    assert result["critical_findings"] == 1
    assert result["mean_time_to_detect_seconds"] is None
    assert result["mean_time_to_resolve_seconds"] == 1800
    assert result["resolved_sample_size"] == 1
    assert result["event_volume"]["total"] == 2
    assert max(result["event_volume"]["buckets"]) == 1
    assert len(result["event_volume"]["buckets"]) == 24

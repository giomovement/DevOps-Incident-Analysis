from datetime import UTC, datetime, timedelta
from statistics import mean

from .database import db


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None


def dashboard_metrics(workspace_id: str, bucket_count: int = 24) -> dict:
    with db() as conn:
        active_incidents = conn.execute(
            "SELECT count(*) AS total FROM incidents WHERE workspace_id=? AND status NOT IN ('resolved','monitoring')",
            (workspace_id,),
        ).fetchone()["total"]
        critical_findings = conn.execute(
            "SELECT count(*) AS total FROM findings f JOIN incidents i ON i.id=f.incident_id WHERE i.workspace_id=? AND f.severity='critical'",
            (workspace_id,),
        ).fetchone()["total"]
        resolved_rows = conn.execute(
            "SELECT created_at,resolved_at FROM incidents WHERE workspace_id=? AND resolved_at IS NOT NULL",
            (workspace_id,),
        ).fetchall()
        event_rows = conn.execute(
            "SELECT e.timestamp FROM log_events e JOIN incidents i ON i.id=e.incident_id WHERE i.workspace_id=? AND e.timestamp IS NOT NULL",
            (workspace_id,),
        ).fetchall()

    resolution_seconds = []
    for row in resolved_rows:
        created, resolved = _timestamp(row["created_at"]), _timestamp(row["resolved_at"])
        if created and resolved and resolved >= created:
            resolution_seconds.append((resolved - created).total_seconds())

    timestamps = [parsed for row in event_rows if (parsed := _timestamp(row["timestamp"]))]
    latest = max(timestamps) if timestamps else None
    start = latest.replace(hour=0, minute=0, second=0, microsecond=0) if latest else None
    end = start + timedelta(days=1) if start else None
    buckets = [0] * bucket_count
    if start and end:
        window_seconds = max((end - start).total_seconds(), 1)
        for timestamp in timestamps:
            if timestamp < start or timestamp >= end:
                continue
            index = min(int((timestamp - start).total_seconds() / window_seconds * bucket_count), bucket_count - 1)
            buckets[index] += 1

    return {
        "active_incidents": active_incidents,
        "critical_findings": critical_findings,
        "mean_time_to_detect_seconds": None,
        "mean_time_to_resolve_seconds": mean(resolution_seconds) if resolution_seconds else None,
        "resolved_sample_size": len(resolution_seconds),
        "event_volume": {
            "buckets": buckets,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "total": sum(buckets),
        },
    }

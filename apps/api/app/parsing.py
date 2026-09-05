import csv
import hashlib
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

TIMESTAMP = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2}[T ][0-9:.+-]+Z?)")
SEVERITIES = {"fatal": "critical", "critical": "critical", "crit": "critical", "error": "high", "err": "high", "warn": "medium", "warning": "medium", "info": "low", "debug": "low"}
SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret)\s*[=:]\s*([^\s,;]+)"),
    re.compile(r"\b(?:sk|xox[baprs])-[-A-Za-z0-9_]{12,}\b"),
]
CORRELATION = re.compile(r"(?i)(?:trace[_-]?id|correlation[_-]?id|request[_-]?id)[=: ]+([A-Za-z0-9._-]+)")


def redact(text: str) -> tuple[str, bool]:
    changed = False
    for pattern in SECRET_PATTERNS:
        next_text, count = pattern.subn(lambda m: f"{m.group(1)}=[REDACTED]" if m.lastindex and m.lastindex > 1 else "[REDACTED]", text)
        text, changed = next_text, changed or count > 0
    return text, changed


def normalize_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).isoformat()
    except ValueError:
        return None


def severity_for(message: str, explicit: str | None = None) -> str:
    haystack = (explicit or "") + " " + message
    for token, normalized in SEVERITIES.items():
        if re.search(rf"\b{token}\b", haystack, re.I):
            return normalized
    return "low"


def record(message: str, line_start: int, line_end: int, data: dict | None = None) -> dict:
    data = data or {}
    match = TIMESTAMP.search(str(data.get("timestamp") or message))
    original_ts = str(data.get("timestamp") or (match.group("ts") if match else "")) or None
    corr = str(data.get("trace_id") or data.get("correlation_id") or data.get("request_id") or "") or None
    if not corr:
        found = CORRELATION.search(message)
        corr = found.group(1) if found else None
    clean, secret = redact(message.strip())
    return {
        "id": str(uuid4()), "line_start": line_start, "line_end": line_end,
        "timestamp": normalize_timestamp(original_ts), "original_timestamp": original_ts,
        "severity": severity_for(clean, str(data.get("level") or data.get("severity") or "")),
        "service": data.get("service") or data.get("component"), "environment": data.get("environment") or data.get("env"),
        "correlation_id": corr, "message": clean, "attributes": data, "secret_redacted": secret,
        "content_hash": hashlib.sha256(clean.encode()).hexdigest(),
    }


def parse_file(path: Path, extension: str) -> Iterable[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if extension == ".json":
        value = json.loads(text)
        values = value if isinstance(value, list) else [value]
        for i, item in enumerate(values, 1):
            data = item if isinstance(item, dict) else {"message": str(item)}
            yield record(str(data.get("message") or data.get("msg") or json.dumps(data)), i, i, data)
        return
    if extension == ".jsonl":
        for i, line in enumerate(text.splitlines(), 1):
            if not line.strip(): continue
            data = json.loads(line)
            yield record(str(data.get("message") or data.get("msg") or json.dumps(data)), i, i, data)
        return
    if extension == ".csv":
        for i, data in enumerate(csv.DictReader(io.StringIO(text)), 2):
            yield record(str(data.get("message") or data.get("msg") or " ".join(str(v) for v in data.values())), i, i, data)
        return
    lines = text.splitlines()
    current: list[str] = []
    start = 1
    for i, line in enumerate(lines, 1):
        is_new = bool(TIMESTAMP.search(line)) or bool(re.match(r"^(TRACE|DEBUG|INFO|WARN|ERROR|FATAL|CRITICAL)\b", line, re.I))
        if is_new and current:
            yield record("\n".join(current), start, i - 1)
            current, start = [], i
        current.append(line)
    if current:
        yield record("\n".join(current), start, len(lines))


def classify(message: str) -> tuple[str, str, float]:
    checks = [
        ("possible_security_event", r"unauthorized|forbidden|brute.?force|suspicious|credential|attack", "Possible authentication or security anomaly", .84),
        ("database", r"database|postgres|mysql|sqlite|deadlock|connection pool|sqlstate", "Database connectivity or saturation failure", .91),
        ("networking", r"dns|connection reset|connection refused|timeout|tls|socket", "Network or upstream connectivity failure", .86),
        ("capacity", r"out of memory|oom|disk full|no space|quota|pool exhausted", "Resource capacity was exhausted", .92),
        ("deployment_regression", r"deployment|release|rollback|revision|image pull", "Failure is correlated with a deployment event", .81),
        ("dependency_failure", r"upstream|dependency|503|502|service unavailable", "An upstream dependency is unavailable", .83),
        ("performance", r"latency|slow|p95|p99|deadline exceeded", "Latency exceeded the expected operating range", .79),
        ("authentication", r"authentication|oauth|jwt|token expired|login failed", "Authentication requests are failing", .87),
        ("infrastructure", r"kubernetes|pod|node|container|crashloop|evicted", "Infrastructure workload is unhealthy", .88),
    ]
    for issue, pattern, root, confidence in checks:
        if re.search(pattern, message, re.I): return issue, root, confidence
    return "application_error", "Application emitted repeated error-level events", .72

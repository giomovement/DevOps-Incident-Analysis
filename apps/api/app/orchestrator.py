import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .config import settings
from .database import db, utcnow
from .parsing import classify, parse_file
from .schemas import IncidentState

PHASES = ["validate_upload", "parse", "classify", "correlate", "recommend", "draft_actions", "review", "cookbook", "complete"]


def emit(run_id: str, phase: str, status: str, message: str, payload: dict | None = None) -> None:
    with db() as conn:
        conn.execute("UPDATE runs SET current_phase=?, status=? WHERE id=?", (phase, "running" if status == "running" else status, run_id))
        conn.execute("INSERT INTO workflow_events(run_id,phase,status,message,payload,created_at) VALUES(?,?,?,?,?,?)", (run_id, phase, status, message, json.dumps(payload or {}), utcnow()))


def cancelled(run_id: str) -> bool:
    with db() as conn:
        row = conn.execute("SELECT cancel_requested FROM runs WHERE id=?", (run_id,)).fetchone()
    return bool(row and row[0])


def validate_upload(state: IncidentState) -> dict:
    emit(state["run_id"], "validate_upload", "running", "Validating incident files")
    if not state["file_manifest"]:
        raise ValueError("At least one validated file is required")
    emit(state["run_id"], "validate_upload", "completed", f"Validated {len(state['file_manifest'])} file(s)")
    return {"current_phase": "validate_upload", "completed_nodes": ["validate_upload"]}


def parse_logs(state: IncidentState) -> dict:
    run_id, incident_id = state["run_id"], state["incident_id"]
    if cancelled(run_id): return {"cancel_requested": True}
    emit(run_id, "parse", "running", "Normalizing timestamps, severities, services, and correlation IDs")
    refs, warnings, redactions = [], [], 0
    with db() as conn:
        existing = conn.execute("SELECT id FROM log_events WHERE incident_id=?", (incident_id,)).fetchall()
        if existing:
            refs = [r[0] for r in existing]
        else:
            for file in state["file_manifest"]:
                path = settings.storage_path / file["storage_name"]
                try:
                    for event in parse_file(path, Path(file["original_name"]).suffix.lower()):
                        conn.execute("INSERT INTO log_events(id,incident_id,file_id,line_start,line_end,timestamp,original_timestamp,severity,service,environment,correlation_id,message,attributes,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event["id"], incident_id, file["id"], event["line_start"], event["line_end"], event["timestamp"], event["original_timestamp"], event["severity"], event["service"] or state["incident_context"].get("service"), event["environment"] or state["incident_context"].get("environment"), event["correlation_id"], event["message"], json.dumps(event["attributes"], default=str), event["content_hash"]))
                        conn.execute("INSERT INTO log_events_fts(event_id,incident_id,message) VALUES(?,?,?)", (event["id"], incident_id, event["message"]))
                        refs.append(event["id"]); redactions += int(event["secret_redacted"])
                except Exception as exc:
                    warnings.append(f"{file['original_name']}: {type(exc).__name__}")
                    conn.execute("UPDATE files SET status='partial', warning=? WHERE id=?", (str(exc)[:300], file["id"]))
    status = "partial" if warnings else "completed"
    emit(run_id, "parse", status, f"Parsed {len(refs):,} events; masked {redactions} possible secret(s)", {"event_count": len(refs), "warnings": warnings})
    return {"event_refs": refs, "warnings": warnings, "current_phase": "parse", "completed_nodes": ["parse"]}


def classify_events(state: IncidentState) -> dict:
    run_id, incident_id = state["run_id"], state["incident_id"]
    if state.get("cancel_requested") or cancelled(run_id): return {"cancel_requested": True}
    emit(run_id, "classify", "running", "Classifying actionable error patterns")
    with db() as conn:
        rows = conn.execute("SELECT * FROM log_events WHERE incident_id=? AND (severity IN ('critical','high','medium') OR lower(message) LIKE '%error%' OR lower(message) LIKE '%failed%' OR lower(message) LIKE '%timeout%') ORDER BY timestamp, line_start LIMIT 500", (incident_id,)).fetchall()
        groups: dict[tuple[str, str], list] = {}
        for row in rows:
            issue, root, confidence = classify(row["message"])
            groups.setdefault((issue, row["service"] or state["incident_context"].get("service") or "unknown-service"), []).append((row, root, confidence))
        findings, evidence_refs = [], []
        severity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        for (issue, service), items in list(groups.items())[:12]:
            fid, eid = str(uuid4()), str(uuid4())
            severities = [item[0]["severity"] for item in items]
            severity = max(severities, key=lambda x: severity_rank.get(x, 0))
            sample, root, confidence = items[0]
            confidence = min(.98, confidence + min(len(items), 10) * .008)
            rationale = f"{len(items)} correlated event(s) match the {issue.replace('_',' ')} signature."
            timestamps = [item[0]["timestamp"] for item in items if item[0]["timestamp"]]
            conn.execute("INSERT INTO findings(id,incident_id,run_id,issue_type,severity,confidence,service,root_cause,rationale,first_observed,last_observed,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (fid, incident_id, run_id, issue, severity, confidence, service, root, rationale, min(timestamps) if timestamps else None, max(timestamps) if timestamps else None, utcnow()))
            source = conn.execute("SELECT original_name FROM files WHERE id=?", (sample["file_id"],)).fetchone()[0]
            source_label = f"{source}:{sample['line_start']}–{sample['line_end']}"
            conn.execute("INSERT INTO evidence(id,incident_id,finding_id,event_id,excerpt,source_label,line_start,line_end,content_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (eid, incident_id, fid, sample["id"], sample["message"][:1800], source_label, sample["line_start"], sample["line_end"], sample["content_hash"], utcnow()))
            findings.append({"id": fid, "issue_type": issue, "severity": severity, "confidence": round(confidence, 2), "service": service, "root_cause": root, "rationale": rationale, "evidence_ids": [eid]}); evidence_refs.append(eid)
    emit(run_id, "classify", "completed", f"Created {len(findings)} evidence-backed finding(s)", {"finding_count": len(findings)})
    return {"findings": findings, "evidence_refs": evidence_refs, "current_phase": "classify", "completed_nodes": ["classify"]}


def correlate(state: IncidentState) -> dict:
    emit(state["run_id"], "correlate", "running", "Correlating services, timestamps, and trace identifiers")
    groups = []
    with db() as conn:
        rows = conn.execute("SELECT correlation_id,count(*) count,min(timestamp) first_seen,max(timestamp) last_seen FROM log_events WHERE incident_id=? AND correlation_id IS NOT NULL GROUP BY correlation_id ORDER BY count DESC LIMIT 20", (state["incident_id"],)).fetchall()
        groups = [dict(r) for r in rows]
    emit(state["run_id"], "correlate", "completed", f"Linked {len(groups)} correlation group(s)")
    return {"correlation_groups": groups, "current_phase": "correlate", "completed_nodes": ["correlate"]}


def remediate(state: IncidentState) -> dict:
    emit(state["run_id"], "recommend", "running", "Mapping containment, diagnosis, remediation, and validation steps")
    recommendations = []
    with db() as conn:
        for finding in state.get("findings", []):
            rid = str(uuid4())
            service = finding["service"]
            phases = {
                "triage": [f"Confirm current health and blast radius for {service}.", "Compare the first failure timestamp with deployments and dependency changes."],
                "containment": ["Reduce impact using a reviewed traffic shift, feature flag, or rollback plan."],
                "diagnosis": [f"Inspect the cited {finding['issue_type'].replace('_',' ')} evidence and correlated traces."],
                "remediation": ["Apply the smallest reversible change after an operator validates permissions and prerequisites."],
                "validation": ["Confirm error rate, saturation, and latency return to baseline."],
                "rollback": ["Stop and restore the last known-good state if validation fails."],
            }
            assumptions = ["The cited timestamps and service labels are accurate.", "Suggested commands require human validation."]
            risks = ["A rollback may reintroduce earlier defects.", "Changes can affect in-flight requests."]
            conn.execute("INSERT INTO recommendations(id,finding_id,phases,rationale,assumptions,risks,created_at) VALUES(?,?,?,?,?,?,?)", (rid, finding["id"], json.dumps(phases), f"Targets the probable cause: {finding['root_cause']}", json.dumps(assumptions), json.dumps(risks), utcnow()))
            recommendations.append({"id": rid, "finding_id": finding["id"], "phases": phases, "rationale": f"Targets the probable cause: {finding['root_cause']}", "assumptions": assumptions, "risks": risks})
    emit(state["run_id"], "recommend", "completed", f"Prepared {len(recommendations)} reviewed-action plan(s)")
    return {"recommendations": recommendations, "current_phase": "recommend", "completed_nodes": ["recommend"]}


def draft_actions(state: IncidentState) -> dict:
    emit(state["run_id"], "draft_actions", "running", "Preparing immutable Slack and Jira previews")
    if not state.get("findings"):
        emit(state["run_id"], "draft_actions", "completed", "No external actions needed")
        return {"slack_drafts": [], "jira_drafts": [], "completed_nodes": ["draft_actions"]}
    top = sorted(state["findings"], key=lambda f: ({"critical": 4, "high": 3, "medium": 2, "low": 1}[f["severity"]], f["confidence"]), reverse=True)[0]
    incident_id, run_id = state["incident_id"], state["run_id"]
    slack = {"text": f"[{top['severity'].upper()}] {top['root_cause']}\nService: {top['service']} · Confidence: {top['confidence']:.0%}\nEvidence: {len(top['evidence_ids'])} cited excerpt(s)\nNext: Review containment and validation checklist."}
    drafts = []
    with db() as conn:
        for kind, destination, payload in [("slack", "#incidents", slack)]:
            raw = json.dumps(payload, sort_keys=True); payload_hash = hashlib.sha256(raw.encode()).hexdigest(); did = str(uuid4())
            conn.execute("INSERT INTO action_drafts(id,incident_id,run_id,kind,destination,payload,payload_hash,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (did, incident_id, run_id, kind, destination, raw, payload_hash, hashlib.sha256(f"{incident_id}:{kind}:{payload_hash}".encode()).hexdigest(), utcnow(), utcnow()))
            drafts.append({"id": did, "kind": kind, "destination": destination, "payload": payload, "payload_hash": payload_hash})
        jira_drafts = []
        if top["severity"] == "critical":
            payload = {"summary": f"[{top['severity'].upper()}] {top['root_cause']}", "description": top["rationale"], "priority": "Highest", "labels": ["dias", incident_id]}
            raw = json.dumps(payload, sort_keys=True); payload_hash = hashlib.sha256(raw.encode()).hexdigest(); did = str(uuid4())
            conn.execute("INSERT INTO action_drafts(id,incident_id,run_id,kind,destination,payload,payload_hash,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (did, incident_id, run_id, "jira", "OPS", raw, payload_hash, hashlib.sha256(f"{incident_id}:jira:{payload_hash}".encode()).hexdigest(), utcnow(), utcnow()))
            jira_drafts.append({"id": did, "kind": "jira", "destination": "OPS", "payload": payload, "payload_hash": payload_hash})
    emit(run_id, "review", "waiting", f"{len(drafts) + len(jira_drafts)} external action(s) require human approval")
    return {"slack_drafts": drafts, "jira_drafts": jira_drafts, "status": "awaiting_approval", "current_phase": "review", "completed_nodes": ["draft_actions"]}


def cookbook(state: IncidentState) -> dict:
    emit(state["run_id"], "cookbook", "running", "Synthesizing incident-response cookbook")
    lines = [f"# Incident Response Cookbook\n", f"Incident: `{state['incident_id']}`\n", "> Suggestions only. Every operational action requires human validation.\n"]
    phase_order = ["triage", "containment", "diagnosis", "remediation", "validation", "rollback"]
    for phase in phase_order:
        lines.append(f"## {phase.title()}\n")
        seen = set()
        for recommendation in state.get("recommendations", []):
            for step in recommendation["phases"].get(phase, []):
                if step not in seen: lines.append(f"- [ ] {step}"); seen.add(step)
        lines.append("")
    lines.extend(["## Monitoring", "- [ ] Watch error rate, latency, resource saturation, and dependency health.", "", "## Post-incident follow-up", "- [ ] Record the verified root cause, contributing factors, ownership, and prevention actions."])
    markdown = "\n".join(lines); cid = str(uuid4()); artifact = settings.artifact_path / f"{state['incident_id']}.md"; artifact.write_text(markdown, encoding="utf-8")
    with db() as conn:
        conn.execute("INSERT INTO cookbooks(id,incident_id,markdown,artifact_path,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(incident_id) DO UPDATE SET markdown=excluded.markdown,artifact_path=excluded.artifact_path,updated_at=excluded.updated_at", (cid, state["incident_id"], markdown, str(artifact), utcnow(), utcnow()))
    emit(state["run_id"], "cookbook", "completed", "Cookbook generated")
    return {"cookbook_ref": cid, "current_phase": "cookbook", "completed_nodes": ["cookbook"]}


def finish(state: IncidentState) -> dict:
    status = "cancelled" if state.get("cancel_requested") else ("awaiting_approval" if state.get("slack_drafts") or state.get("jira_drafts") else "completed")
    with db() as conn:
        conn.execute("UPDATE runs SET status=?,current_phase=?,completed_at=? WHERE id=?", (status, "review" if status == "awaiting_approval" else "complete", utcnow(), state["run_id"]))
        conn.execute("UPDATE incidents SET status=?,severity=?,updated_at=? WHERE id=?", ("active" if state.get("findings") else "monitoring", max((f["severity"] for f in state.get("findings", [])), default="low", key=lambda x: {"low":1,"medium":2,"high":3,"critical":4}[x]), utcnow(), state["incident_id"]))
    emit(state["run_id"], "complete", status, "Analysis complete; external actions remain human-controlled" if status == "awaiting_approval" else "Analysis complete")
    return {"status": status, "current_phase": "complete", "completed_nodes": ["complete"]}


def build_graph():
    graph = StateGraph(IncidentState)
    for name, node in [("validate_upload", validate_upload), ("parse", parse_logs), ("classify", classify_events), ("correlate", correlate), ("recommend", remediate), ("draft_actions", draft_actions), ("cookbook", cookbook), ("finish", finish)]: graph.add_node(name, node)
    graph.add_edge(START, "validate_upload")
    for left, right in zip(["validate_upload","parse","classify","correlate","recommend","draft_actions","cookbook","finish"], ["parse","classify","correlate","recommend","draft_actions","cookbook","finish",END]): graph.add_edge(left, right)
    checkpoint_conn = sqlite3.connect(settings.checkpoint_path, check_same_thread=False)
    return graph.compile(checkpointer=SqliteSaver(checkpoint_conn))


_graph = None
def run_analysis(run_id: str) -> None:
    global _graph
    try:
        with db() as conn:
            run = conn.execute("SELECT r.*,i.workspace_id,i.title,i.description,i.service,i.environment,i.deployment FROM runs r JOIN incidents i ON i.id=r.incident_id WHERE r.id=?", (run_id,)).fetchone()
            files = [dict(r) for r in conn.execute("SELECT * FROM files WHERE incident_id=? AND status IN ('validated','partial')", (run["incident_id"],)).fetchall()]
            conn.execute("UPDATE runs SET status='running',started_at=? WHERE id=?", (utcnow(), run_id))
        initial: IncidentState = {"schema_version":"1.0","workspace_id":run["workspace_id"],"incident_id":run["incident_id"],"run_id":run_id,"langgraph_thread_id":run["thread_id"],"file_manifest":files,"incident_context":{"title":run["title"],"description":run["description"],"service":run["service"],"environment":run["environment"],"deployment":run["deployment"]},"status":"running","current_phase":"validate_upload","completed_nodes":[],"cancel_requested":False,"event_refs":[],"evidence_refs":[],"correlation_groups":[],"findings":[],"recommendations":[],"slack_drafts":[],"jira_drafts":[],"errors":[],"warnings":[]}
        _graph = _graph or build_graph()
        _graph.invoke(initial, {"configurable": {"thread_id": run["thread_id"]}})
    except Exception as exc:
        with db() as conn:
            conn.execute("UPDATE runs SET status='failed',completed_at=? WHERE id=?", (utcnow(), run_id))
        emit(run_id, "failed", "failed", f"Analysis stopped: {type(exc).__name__}", {"detail": str(exc)[:500]})

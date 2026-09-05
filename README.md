# DevOps Incident Analysis Suite

A local-first, production-shaped incident command center that turns operational logs into evidence-backed findings, reviewed remediation guidance, human-approved Slack/Jira actions, and reusable response cookbooks.

## Run locally

1. Copy `.env.example` to `.env` and leave integrations in `mock` mode.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`; the first account becomes workspace Admin.

The frontend also runs with `npm run dev` from `apps/web`. The API runs with `uvicorn app.main:app --reload` from `apps/api` after installing `requirements.txt` into a Python environment.

## Safety model

- `.log`, `.txt`, `.json`, `.jsonl`, and `.csv` only; up to 10 files and 250 MB per incident.
- Likely secrets are masked during normalization.
- Remediation steps are suggestions and are never executed.
- Every Slack/Jira write requires a Responder or Admin to approve the exact payload hash.
- Slack and Jira use deterministic mock adapters by default.

See [ARCHITECTURE.md](ARCHITECTURE.md) for contracts, data flow, threat boundaries, and production migration guidance.

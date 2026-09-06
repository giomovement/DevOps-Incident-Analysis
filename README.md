# DevOps Incident Analysis Suite

A local-first, production-shaped incident command center that turns operational logs into evidence-backed findings, reviewed remediation guidance, human-approved Slack/Jira actions, and reusable response cookbooks.

## Run locally

1. Copy `.env.example` to `.env` and leave integrations in `mock` mode.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`; the first account becomes workspace Admin.

The frontend also runs with `npm run dev` from `apps/web`. The API runs with `uvicorn app.main:app --reload` from `apps/api` after installing `requirements.txt` into a Python environment.

## Database selection

Local development and automated tests use SQLite by default. Set `DIAS_DATABASE_URL` to a PostgreSQL connection string to use PostgreSQL instead; this is the intended database for hosted deployments. `DIAS_DATABASE_PATH` is ignored while `DIAS_DATABASE_URL` is configured.

## Vercel deployment

The repository is prepared as two Vercel projects: `apps/api` for FastAPI and `apps/web` for Next.js. The web project proxies `/api` to the API project so authentication cookies remain same-origin. Follow [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for the exact dashboard settings.

## Safety model

- `.log`, `.txt`, `.json`, `.jsonl`, and `.csv` only; up to 5 files and 3 MB per incident for hosted compatibility.
- Likely secrets are masked during normalization.
- Remediation steps are suggestions and are never executed.
- Every Slack/Jira write requires a Responder or Admin to approve the exact payload hash.
- Slack and Jira use deterministic mock adapters by default.

## Prod and Test modes

The overview dashboard includes a Prod/Test selector beside **New analysis**. Prod is the normal workspace and starts as a clean first-time-onboarding environment. Test uses a second isolated incident-data workspace, so incidents, uploads, findings, dashboard metrics, chats, cookbooks, actions, and audit records never cross between modes. The selected mode is retained for the login session. Account authentication and integration configuration are shared between both modes. Records created before mode support remain preserved in their legacy workspace.

## Connect Slack

Create a Slack app for the target workspace, add the `chat:write` and `channels:read` bot scopes (`groups:read` as well for private channels), install it, and invite the bot to the incident channel. Then update the uncommitted `.env` file:

```dotenv
DIAS_INTEGRATIONS_MODE=official
DIAS_SLACK_BOT_TOKEN=xoxb-... # bot token; never commit this value
DIAS_SLACK_DEFAULT_CHANNEL=C0123456789 # Slack channel ID
```

Restart the API container, then use **Settings → Integrations → Test connection**. Analysis still only creates a draft; `chat.postMessage` is called solely when a Responder or Admin approves that draft.

See [ARCHITECTURE.md](ARCHITECTURE.md) for contracts, data flow, threat boundaries, and production migration guidance.

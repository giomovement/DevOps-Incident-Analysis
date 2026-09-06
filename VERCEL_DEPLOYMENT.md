# Vercel deployment

This repository deploys as two free Vercel projects connected to the same GitHub repository. Deploy the API first, then the web app.

## 1. API project

Import the GitHub repository into Vercel and choose these settings:

- **Project name:** `devops-incident-api`
- **Root Directory:** `apps/api`
- **Framework Preset:** FastAPI (Vercel should detect it)

Add these environment variables for Production, Preview, and Development:

```text
DIAS_DATABASE_URL=<your Neon connection string>
DIAS_ENVIRONMENT=production
DIAS_INTEGRATIONS_MODE=mock
DIAS_SESSION_COOKIE_SECURE=true
```

Do not add `DIAS_DATABASE_PATH` or `DIAS_STORAGE_PATH`. Vercel will use PostgreSQL and the app automatically uses `/tmp` for temporary uploads.

Deploy the project and copy its URL, for example `https://devops-incident-api.vercel.app`.

## 2. Web project

Import the same GitHub repository again and choose:

- **Project name:** `devops-incident-analysis`
- **Root Directory:** `apps/web`
- **Framework Preset:** Next.js (Vercel should detect it)

Add one environment variable for Production, Preview, and Development:

```text
API_ORIGIN=https://devops-incident-api.vercel.app
```

Use your actual API project URL and omit the trailing slash. Leave `NEXT_PUBLIC_API_URL` unset on Vercel; the browser uses the web project’s same-origin `/api/v1` path.

Deploy the web project. Open its URL, create the first account, select Test mode, and run one small test-log analysis before using Production mode.

## Optional AI settings

The app works in deterministic fallback mode without an AI key. To enable OpenRouter, add the existing `DIAS_OPENROUTER_*` values only to the API project. Never add secret values to GitHub or the web project.

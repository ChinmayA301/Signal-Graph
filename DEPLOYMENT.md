# Deployment

SignalGraph deploys as two services: the Next.js frontend on Vercel, and the
FastAPI backend as a container on Render, Railway or Fly.io.

**The backend is not deployed to Vercel on purpose.** The API depends on
`packages/scoring`, a local package that lives outside `apps/api`. The Dockerfile
copies and installs it; a serverless Python runtime rooted at `apps/api` cannot
see files above its root, so the import would fail at runtime.

## What it needs

| Requirement | Needed? | Why |
|---|---|---|
| Any secrets | **No** | `MOCK_MODE=true` is the default. The full analyze → scorecard → timeline → compare flow runs on deterministic synthetic data. |
| `GITHUB_TOKEN` | Optional | Enables live GitHub ingestion (`MOCK_MODE=false`). Needs public repo read access. |
| Database | No | Falls back to SQLite and creates its own tables at startup. Set `DATABASE_URL` for Postgres. |

A zero-secret demo is the point here: the deployed app works for anyone with no
setup, and live mode is an upgrade rather than a prerequisite.

## 1. Backend (container)

`render.yaml` is a ready blueprint — point Render at the repo and it picks it up.
Railway and Fly.io build the same `infra/docker/Dockerfile.api`.

Environment variables:

```
MOCK_MODE=true
CORS_ALLOW_ORIGINS=https://your-frontend.vercel.app
# Optional, for live GitHub data:
# MOCK_MODE=false
# GITHUB_TOKEN=ghp_...
# Optional, for durable storage:
# DATABASE_URL=postgresql+psycopg://...
```

`CORS_ALLOW_ORIGINS` is comma-separated and must list the deployed frontend
origin — the browser blocks every cross-origin call otherwise. `*` is ignored,
because the API sends credentials and browsers reject a wildcard origin on
credentialed requests.

Two things the container entrypoint handles:

- **Binds `$PORT`** when the host assigns one, falling back to 8000 locally.
- **Runs Alembic only on Postgres.** The migrations use JSONB and would fail
  against the SQLite default; on SQLite the app creates its tables at startup.

### Live mode caveat

`GITHUB_TOKEN` must be able to read public repos. Ingestion uses GitHub's
**GraphQL** API, because the REST `/stargazers` endpoint returns 404 for any repo
the token does not own — see the commit history for the investigation. If live
ingestion fails for any reason the pipeline falls back to mock data and reports
`ingestion_source: "mock_fallback"` in the response, so check that field rather
than assuming a 200 means live data.

## 2. Frontend (Vercel)

Create a Vercel project with **root directory = repository root** (not
`apps/web`). `vercel.json` handles the monorepo:

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run types:build && npm run web:build",
  "outputDirectory": "apps/web/.next"
}
```

The web app imports `@signalgraph/shared-types`, an npm workspace package that
must be compiled first — hence the two-step build. Pointing Vercel at `apps/web`
directly skips the workspace install and fails on the unbuilt dependency.

Environment variable:

```
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
```

Deploy the backend first to get its URL, then set `CORS_ALLOW_ORIGINS` on the
backend to the frontend URL once both exist.

## Local equivalent

```bash
docker compose up --build
```

Brings up Postgres, the API on :8000 and the web app on :3000 with the same
images. For the no-Docker path see the README.

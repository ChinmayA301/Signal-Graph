# SignalGraph

[![CI](https://github.com/ChinmayA301/Signal-Graph/actions/workflows/ci.yml/badge.svg)](https://github.com/ChinmayA301/Signal-Graph/actions/workflows/ci.yml)

Credibility-adjusted traction for open-source investing: heuristic scores for manipulation risk, star integrity, adoption, builder quality, and durability, with explainable outputs and conservative language (“suspicious,” “elevated risk,” not accusations).

Research grounding: ICSE 2026 work on suspected coordinated GitHub stars (StarScout / “Six Million (Suspected) Fake Stars on GitHub”) and GitHub’s own framing of stars as an approximate interest signal. Treat any automated labels as error-prone; see `PROGRESS.md` for citations and next ingestion steps (GH Archive).

**Project essay:** [SignalGraph: Replacing GitHub's Fake Star Economy with Credibility-Adjusted OSS Signals](https://app.chinmayarora.com/blog/signalgraph-github-fake-star-economy/)

## Monorepo layout

- `apps/web` — Next.js + TypeScript UI (Recharts timelines, scorecards, peer compare)
- `apps/api` — FastAPI service, SQLAlchemy models, Alembic migrations, ingestion hooks
- `packages/scoring` — pure Python scoring pipeline (features + weights + `compute_scores`)
- `packages/shared-types` — TypeScript DTOs shared with the web client
- `infra/docker` — Dockerfiles + API entrypoint (migrations + Uvicorn)

## Fastest demo — no Docker, no tokens (SQLite + mock mode)

The API defaults to a local SQLite file and mock data, so the full product runs
end-to-end on a laptop with zero external services. Two terminals:

```bash
# 1) API (creates ./signalgraph.db automatically on first run)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../../packages/scoring && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000     # → http://localhost:8000/docs

# 2) Web
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # → http://localhost:3000
```

Open `http://localhost:3000`, paste any public repo URL, and click **Run analysis**.
Postgres and a `GITHUB_TOKEN` are only needed for live stargazer sampling (below).

## Local development (Docker, Postgres)

```bash
cd signalgraph
docker compose up --build
```

- API: `http://localhost:8000/docs`
- Web: `http://localhost:3000`
- Postgres: `localhost:5432` (`signalgraph` / `signalgraph`)

`MOCK_MODE` defaults to `true` in Compose so the UI works without a GitHub token. Set `MOCK_MODE=false` and provide `GITHUB_TOKEN` for live (capped) stargazer sampling via the GitHub API. Live mode also measures same-day co-adoption: for a sample of 60 stargazers, how many other repos each starred that UTC day (`COADOPTION_ENABLED`, `COADOPTION_MAX_USERS`; adds roughly 10-30 s per analysis). It feeds the co-adoption farm signal; see `apps/api/app/services/coadoption_ingest.py` for how it differs from the GH Archive measure. Note: since 30 June 2026 GitHub lists a repo's stargazers only to its admins and collaborators, so live stargazer sampling (and every per-stargazer signal) works only for repos your token can administer; other repos fall back to mock data. Such reports carry `ingestion_source: "mock_no_stargazer_access"` and a `data_notice` the web report shows as a warning banner; every mock-based report (demo mode, failed ingestion) carries a `data_notice` saying the scores are not from the repository.

## Local development (host, Python venv)

```bash
cd signalgraph/apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../../packages/scoring
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://signalgraph:signalgraph@localhost:5432/signalgraph
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Run Postgres via Docker Compose (`docker compose up postgres -d`) or your own instance.

## Local development (host, Node)

```bash
cd signalgraph
npm install
npm run types:build
npm run web:dev
```

Set `NEXT_PUBLIC_API_URL` to point at your API (defaults to `http://localhost:8000` in the web client).

## Primary API routes

- `POST /analyze` — `{ "repo_url": "https://github.com/owner/repo", "force_mock": false }`
- `GET /repo/{owner}/{name}` — latest persisted scorecard + timeline payload
- `GET /repo/{owner}/{name}/scores`
- `GET /repo/{owner}/{name}/timeline`
- `GET /repo/{owner}/{name}/clusters`
- `GET /repo/{owner}/{name}/compare?peers=owner/repo&peers=...` — peers must already be analyzed

## Product posture

Outputs are confidence-style estimates suitable for diligence workflows, not public shaming. Prefer explainability, cohort baselines (future), and human review for high-stakes decisions.

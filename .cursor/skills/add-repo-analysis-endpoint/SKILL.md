---
name: add-repo-analysis-endpoint
description: >-
  Creates or modifies FastAPI analysis endpoints for SignalGraph with typed schemas,
  thin routes, and explainable payloads. Use when adding POST/GET routes under apps/api
  for repo reports, timelines, scores, clusters, or compare flows.
---

# Skill: add-repo-analysis-endpoint

## Workflow

1. Define request/response contracts (Pydantic in `apps/api/app/schemas/`).
2. Keep route handlers thin (`apps/api/app/api/`); delegate to services.
3. Orchestrate persistence and scoring in `apps/api/app/services/`.
4. Call `packages/scoring` cleanly; do not duplicate weight logic in routes.
5. Persist snapshots when appropriate (`repo_scores`, `star_events`, etc.).
6. Return typed outputs that include explanations and raw features where scores are shown.
7. Add tests (API integration or service-level) where practical.
8. Update `packages/shared-types` and web fetch layers if shapes change; document in `README.md` or `docs/`.

## Rules

- No business logic buried in route files.
- No untyped response payloads for user-facing analysis.
- Degraded partial results are better than hard failure when safe (especially without tokens or with partial GitHub data).

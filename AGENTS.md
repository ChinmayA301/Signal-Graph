# AGENTS.md

## Project

SignalGraph

## Mission

SignalGraph helps investors, technical diligence teams, and researchers separate visible GitHub popularity from credibility-adjusted traction.

The product does two things:

1. Detect suspicious and potentially coordinated star activity.
2. Replace raw star count with a better trust signal built from integrity, adoption, builder quality, and durability.

## Core product philosophy

GitHub stars are a weak proxy for interest, not proof of product quality, user adoption, or company quality.

SignalGraph must:

- detect suspicious patterns without making hard accusations
- prioritize explainability over black-box scoring
- make every major score decomposable into underlying features
- favor conservative language and confidence-aware outputs
- be useful even in mock mode before all live data integrations are complete

## Safety and language policy

Never state that a repository or founder "bought stars" or committed fraud unless explicitly supported by extraordinary evidence and product policy allows it.

Preferred language:

- suspicious pattern detected
- elevated manipulation risk
- likely inorganic activity
- coordinated starring behavior
- unexplained burst
- confidence is limited
- integrity risk appears elevated

Avoid:

- fake for certain
- fraudulent repo
- scam unless separately supported by other evidence
- bought stars as a definitive statement

## MVP outputs

For a repository analysis, always aim to return:

- Manipulation Risk Score
- Star Integrity Score
- Adoption Score
- Builder Quality Score
- Durability Score
- Credibility-Adjusted Traction Score
- explanation fields for each score
- raw supporting features where available

## Non-negotiables

- Always preserve explainability.
- Never return a final score without feature-level reasoning.
- Never hide missing data; surface it clearly.
- Never break mock mode.
- Never hardcode business logic that should live in config.
- Prefer modular scoring functions with tests.
- Prefer deterministic outputs for heuristic scoring paths.
- Keep typed contracts aligned across backend and frontend.

## Architecture overview

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Python
- Database: Postgres
- Local analytics/dev: DuckDB
- Charts/UI: Recharts or similar
- Monorepo with shared types and modular scoring package

## Target repo structure

/apps/web
/apps/api
/packages/shared-types
/packages/scoring
/docs
/infra

## Coding standards

### General

- keep modules small and composable
- avoid giant service files
- prefer pure functions for scoring logic
- isolate external API adapters from core logic
- prefer feature flags for incomplete/live integrations

### Backend

- use Pydantic models and typed response schemas
- keep API layer thin
- push business logic into services/scoring modules
- write migration-safe schema changes
- use config for weights, thresholds, and environment-dependent values

### Frontend

- keep pages thin and componentized
- separate data fetching, presentation, and chart logic
- every score UI should support explanation panels
- show both adjusted scores and raw signals clearly

## What "done" means

A task is done only if:

1. it works end-to-end or is feature-flagged safely
2. tests are added or updated where appropriate
3. types are aligned
4. docs are updated when architecture/contracts change
5. explanation output exists for user-facing scoring behavior

## Priority order

1. working end-to-end MVP
2. clear schema and modular scoring
3. explainable score outputs
4. good UX for repo analysis
5. live data sophistication later

## Preferred workflow for agents

When implementing a feature:

1. inspect existing architecture
2. identify affected contracts, schema, services, and UI
3. propose smallest coherent change
4. implement backend logic
5. implement typed response models
6. wire frontend display
7. add/update tests
8. update docs if architecture or scoring changed

## For scoring changes

Every scoring change must include:

- raw feature
- normalized feature or subscore
- rationale text
- test coverage
- config-based weight/threshold if applicable

## For incomplete live ingestion

Use mock or synthetic data paths instead of blocking UI work.
Always keep demoability intact.

## Cursor operating system

- Read `.cursor/rules/*.mdc` before large changes.
- Use `.cursor/skills/*/SKILL.md` for repeatable workflows (scoring, endpoints, UI, migrations, peer compare).
- See `docs/SUBAGENTS.md` for role prompts when delegating via Task.
- Project hooks live in `.cursor/hooks.json` (post-Write reminders and scoring tests when `pytest` is available).

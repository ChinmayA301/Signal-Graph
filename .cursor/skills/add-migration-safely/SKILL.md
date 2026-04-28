---
name: add-migration-safely
description: >-
  Changes Postgres schema for SignalGraph with Alembic migrations, aligned ORM models,
  API schemas, and shared TypeScript types. Use when altering apps/api models or
  persistence shape for repositories, users, star events, scores, or clusters.
---

# Skill: add-migration-safely

## Workflow

1. Update SQLAlchemy models (`apps/api/app/models/`).
2. Create a new Alembic revision under `apps/api/alembic/versions/` (forward + downgrade).
3. Update Pydantic response/request schemas.
4. Update `packages/shared-types` if the API exposes new fields to the web client.
5. Verify services that read/write the affected tables.
6. Verify frontend assumptions for any exposed fields.
7. Update `docs/DATA_DICTIONARY.md` when semantics or columns change.

## Rules

- Avoid schema drift between ORM, migrations, and runtime DTOs.
- Never change persistence shape without reviewing API + shared contracts.
- Include sensible defaults or backfill notes in migrations when adding NOT NULL columns.

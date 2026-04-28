# SignalGraph Cursor hooks

`hooks.json` registers a `postToolUse` hook (matcher: `Write`) that:

- runs `pytest packages/scoring` when scoring paths (or future `apps/api/app/scoring/`) are edited
- nudges migration and shared-type alignment when models, schemas, Alembic, API routes, or `packages/shared-types` change
- nudges doc updates when implementation paths change

Install test dependency once from repo root:

```bash
pip install -r requirements-dev.txt
```

Hooks run `python3` from your environment; ensure `pytest` is importable or the hook will report install instructions.

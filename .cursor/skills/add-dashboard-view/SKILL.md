---
name: add-dashboard-view
description: >-
  Builds or extends Next.js dashboard UI for SignalGraph repo scores, timelines,
  comparisons, and explanations. Use when adding pages or components under apps/web
  that display manipulation risk, integrity, or traction metrics.
---

# Skill: add-dashboard-view

## Workflow

1. Define the exact backend contract (reuse `packages/shared-types` DTOs).
2. Add or extend typed fetch helpers (`apps/web/lib/`).
3. Create a clear component hierarchy (presentation vs chart vs data).
4. Add loading, error, and empty states.
5. Surface explanation details alongside every score block.
6. Keep visual style consistent with existing score cards (investor-grade, low noise).
7. Add light tests only if the repo already uses a frontend test stack for similar code.

## Rules

- Keep business logic out of purely presentational components.
- Clarity over decoration.
- Never hide the distinction between raw stars and credibility-adjusted traction.

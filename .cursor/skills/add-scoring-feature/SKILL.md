---
name: add-scoring-feature
description: >-
  Adds a new heuristic, raw feature, or subscore to the SignalGraph scoring engine
  end-to-end with tests and docs. Use when changing manipulation risk, star integrity,
  adoption, builder quality, durability, or traction aggregation in packages/scoring
  or related API fields.
---

# Skill: add-scoring-feature

## Required workflow

1. Identify scoring domain affected: manipulation risk, star integrity, adoption, builder quality, durability, or traction aggregate.
2. Define raw inputs and edge cases (empty events, tiny repos, archived repos, missing timestamps).
3. Implement a pure function in `packages/scoring/signalgraph_scoring/` (prefer `features.py` or a focused module).
4. Normalize or convert to a subscore if needed; keep outputs clamped and documented.
5. Add explanation text (reason strings or mappings) consumed by the API bundle.
6. Wire into aggregate score config (`weights.py` or future config module); avoid magic numbers without names.
7. Expose raw and interpreted outputs via `compute_scores` / `ScoreBundle` and API `explanation_json` as applicable.
8. Add or update tests under `packages/scoring/tests/`.
9. Update `docs/SCORING_SPEC.md` when semantics change.

## Rules

- Do not hide feature values behind a single opaque output.
- Use config for thresholds and weights.
- Preserve deterministic behavior for heuristic MVP paths.
- Use conservative user-facing language (see `AGENTS.md` and rule `40-scoring-safety.mdc`).

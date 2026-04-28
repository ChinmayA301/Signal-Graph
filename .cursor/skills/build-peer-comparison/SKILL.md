---
name: build-peer-comparison
description: >-
  Implements or extends repo-vs-repo or cohort comparison for SignalGraph using
  normalized metrics and explainable drivers—not raw stars alone. Use when changing
  compare endpoints, peer cards, or ranking UI.
---

# Skill: build-peer-comparison

## Workflow

1. Identify comparison dimensions (e.g. manipulation risk, adjusted traction, adoption).
2. Define a comparison response model (peers may be missing; handle partial data).
3. Compute comparable normalized metrics; keep raw stars visible alongside adjusted scores.
4. Surface explanations for why two repos rank differently when heuristics diverge.
5. Build UI comparison cards or tables with empty and error states.
6. Test with missing peer rows and unscored peers.

## Rules

- Comparisons must not rely on raw stars alone as the ranking driver.
- Explain material differences using subscores and raw features when available.

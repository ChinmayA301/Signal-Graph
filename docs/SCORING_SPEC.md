# SCORING_SPEC.md

## Scores

1. Manipulation Risk Score (0–100, higher = more suspicion in heuristics)
2. Star Integrity Score (0–100, higher = more trustworthy star composition for the sample)
3. Adoption Score (0–100, interim proxies until registry signals land)
4. Builder Quality Score (0–100)
5. Durability Score (0–100)
6. Credibility-Adjusted Traction Score (0–100, weighted aggregate)

## Requirements for each score

- raw inputs documented
- normalization logic documented
- explanation text documented
- tests present (where logic is non-trivial)
- weights configurable (see `packages/scoring/signalgraph_scoring/weights.py`)

## Implementation map (v1)

| Score | Primary module |
| --- | --- |
| Manipulation risk components | `packages/scoring/signalgraph_scoring/features.py`, `scores.py` |
| Weights | `packages/scoring/signalgraph_scoring/weights.py` |
| API bundle + persistence | `apps/api/app/services/analysis_pipeline.py` |

## Manipulation risk example inputs

- burst concentration (1d / 7d / 30d windows)
- low-activity stargazer share
- recent-account share
- unexplained spikes vs commit/release/issue velocity
- co-starring overlap (placeholder ratio until graph layer)
- stars-to-forks anomaly
- stars-to-contributors anomaly

## Star integrity (v1)

Derived as a transparent blend of inverse manipulation-related signals (not a separate black box). Future versions may split additional integrity-only features.

## Adoption / builder / durability (v1)

Heuristic proxies from repository snapshot fields (forks, issues, contributors, commits/PRs, releases, push recency). Documented in code as interim until package-registry and dependency graph ingestion exist.

## Explanation requirement

Every score must map to:

- value
- short interpretation (reason strings returned in API `reasons` map)
- top contributing factors (raw `raw_features` and `subscores` in API)
- limitations/missing data when relevant (disclaimer + empty overlays where data not ingested)

## Change process

When changing formulas or weights:

1. update this doc’s table or bullet description
2. update `weights.py` or future config module
3. extend or add tests under `packages/scoring/tests/`
4. align `packages/shared-types` if API shape changes

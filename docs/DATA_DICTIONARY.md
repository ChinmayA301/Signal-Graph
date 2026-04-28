# DATA_DICTIONARY.md

Canonical persistence for MVP Postgres (see `apps/api/app/models/tables.py` and Alembic under `apps/api/alembic/versions/`).

## repositories

| Field | Type | Description |
| --- | --- | --- |
| repo_id | int PK | Internal surrogate key |
| owner | string | GitHub owner login |
| name | string | Repository name |
| github_repo_id | bigint nullable | Upstream GitHub repo id when known |
| created_at | timestamptz | Repo creation time when known |
| primary_language | string nullable | Primary language label |
| stars_count | int | Snapshot star count used for scoring |
| forks_count | int | Snapshot fork count |
| watchers_count | int | Watchers/subscribers snapshot |
| open_issues_count | int | Open issues snapshot |
| default_branch | string nullable | Default branch name |
| archived | bool | GitHub archived flag |
| disabled | bool | Disabled flag |
| deleted_flag | bool | Soft-delete marker |
| last_push_at | timestamptz nullable | Last push timestamp |
| last_release_at | timestamptz nullable | Last release timestamp (when populated) |
| contributors_count | int | Count used in heuristics |
| commits_last_30d | int | Activity proxy |
| releases_last_90d | int | Activity proxy |
| issues_opened_last_30d | int | Activity proxy |
| prs_merged_last_30d | int | Activity proxy |
| ingestion_source | string | e.g. `mock`, `github_api`, `mock_fallback` |
| updated_at | timestamptz | Row freshness |

## users

| Field | Type | Description |
| --- | --- | --- |
| user_id | bigint PK | GitHub user id |
| login | string | Username (may be synthetic in mock paths) |
| account_created_at | timestamptz nullable | Account creation |
| followers / following | int | Social graph snapshot |
| public_repos / public_gists | int | Footprint snapshot |
| account_type | string nullable | User vs org etc. |
| suspicious_activity_features_json | jsonb nullable | Reserved for future feature payloads |
| updated_at | timestamptz | Row freshness |

## star_events

| Field | Type | Description |
| --- | --- | --- |
| event_id | int PK | Surrogate |
| repo_id | FK | Parent repository |
| user_id | FK | Stargazer |
| starred_at | timestamptz | Star event time |
| source | string | Ingestion path identifier |
| ingestion_date | date | Batch date |

Unique (repo_id, user_id): one star edge per user in MVP store.

## repo_activity_daily

Daily rollups for stars (and placeholders for issues/PRs/commits when populated).

## repo_scores

| Field | Type | Description |
| --- | --- | --- |
| repo_id | FK | Repository |
| snapshot_date | date | Score as-of date |
| manipulation_risk | float | 0–100 |
| star_integrity | float | 0–100 |
| adoption_score | float | 0–100 |
| builder_score | float | 0–100 |
| durability_score | float | 0–100 |
| credibility_adjusted_traction | float | 0–100 |
| explanation_json | jsonb | Raw features, subscores, reasons, suspicious windows |

## suspicious_clusters

Heuristic time windows (often single-day bursts) with density/z-style metadata; not a verdict of fraud.

## API DTO alignment

HTTP responses mirror `packages/shared-types` TypeScript types where fields overlap. Any new persisted field should appear here, in ORM, in Pydantic schemas, and in shared types if exposed to the web client.

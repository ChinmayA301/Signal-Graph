"""Smoke tests for deterministic scoring paths."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from signalgraph_scoring.features import RepoSnapshotInput, StarEventInput
from signalgraph_scoring.scores import compute_scores


def test_compute_scores_empty_stars():
    snapshot = RepoSnapshotInput(
        stars_count=0,
        forks_count=0,
        contributors_count=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=400),
        last_push_at=datetime.now(timezone.utc),
        open_issues_count=0,
        releases_last_90d=0,
        commits_last_30d=0,
        issues_opened_last_30d=0,
        prs_merged_last_30d=0,
    )
    bundle = compute_scores(star_events=[], snapshot=snapshot, peer_overlap_ratio=0.0)
    assert 0 <= bundle.manipulation_risk <= 100
    assert 0 <= bundle.star_integrity <= 100
    assert 0 <= bundle.credibility_adjusted_traction <= 100


def test_compute_scores_with_burst_pattern():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    events = []
    for index in range(50):
        events.append(
            StarEventInput(
                user_id=1000 + index,
                starred_at=base + timedelta(hours=index),
                account_created_at=base - timedelta(days=400),
                public_repos=10,
                followers=5,
            )
        )
    for index in range(40):
        events.append(
            StarEventInput(
                user_id=2000 + index,
                starred_at=base + timedelta(days=10, hours=index),
                account_created_at=base + timedelta(days=9),
                public_repos=1,
                followers=0,
            )
        )
    snapshot = RepoSnapshotInput(
        stars_count=90,
        forks_count=3,
        contributors_count=5,
        created_at=base - timedelta(days=30),
        last_push_at=base + timedelta(days=15),
        open_issues_count=2,
        releases_last_90d=0,
        commits_last_30d=2,
        issues_opened_last_30d=1,
        prs_merged_last_30d=1,
    )
    bundle = compute_scores(star_events=events, snapshot=snapshot, peer_overlap_ratio=0.3)
    assert bundle.manipulation_risk >= 0
    assert "manipulation_risk" in bundle.reasons
    assert len(bundle.reasons["manipulation_risk"]) >= 1

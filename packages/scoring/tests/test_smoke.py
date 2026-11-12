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


def _snapshot(stars):
    return RepoSnapshotInput(
        stars_count=stars, forks_count=10, contributors_count=3,
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc), last_push_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open_issues_count=5, releases_last_90d=1, commits_last_30d=10, issues_opened_last_30d=2, prs_merged_last_30d=2,
    )


def test_arrival_regularity_scripted_vs_spread():
    from signalgraph_scoring.features import arrival_regularity
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    scripted = [StarEventInput(user_id=i, starred_at=base + timedelta(seconds=20 * i)) for i in range(60)]
    spread = [StarEventInput(user_id=i, starred_at=base + timedelta(hours=7 * i)) for i in range(60)]
    assert arrival_regularity(scripted)["arrival_regularity_score"] > 0.9
    assert arrival_regularity(spread)["arrival_regularity_score"] == 0.0


def test_co_adoption_inactive_without_data_and_flags_farms():
    from signalgraph_scoring.features import co_adoption_farm_share
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    missing = [StarEventInput(user_id=i, starred_at=base + timedelta(hours=i)) for i in range(30)]
    farm = [StarEventInput(user_id=i, starred_at=base + timedelta(hours=i), same_day_other_stars=40) for i in range(30)]
    normal = [StarEventInput(user_id=i, starred_at=base + timedelta(hours=i), same_day_other_stars=2) for i in range(30)]
    assert co_adoption_farm_share(missing)["co_adoption_farm_score"] == 0.0
    assert co_adoption_farm_share(farm)["co_adoption_farm_score"] == 1.0
    assert co_adoption_farm_share(normal)["co_adoption_farm_score"] == 0.0


def test_scripted_campaign_scores_higher_than_spread_organic():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    campaign = [StarEventInput(user_id=i, starred_at=base + timedelta(seconds=15 * i), same_day_other_stars=35) for i in range(100)]
    organic = [StarEventInput(user_id=i, starred_at=base + timedelta(hours=5 * i), same_day_other_stars=1) for i in range(100)]
    c = compute_scores(star_events=campaign, snapshot=_snapshot(100))
    o = compute_scores(star_events=organic, snapshot=_snapshot(100))
    assert c.manipulation_risk > o.manipulation_risk + 20
    assert any("less than a minute" in r for r in c.reasons["manipulation_risk"])

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from signalgraph_scoring.features import RepoSnapshotInput, StarEventInput


@dataclass(frozen=True)
class MockDataset:
    snapshot: RepoSnapshotInput
    star_events: list[StarEventInput]
    peer_overlap_ratio: float


def _stable_seed(owner: str, name: str) -> int:
    digest = hashlib.sha256(f"{owner}/{name}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def build_mock_dataset(owner: str, name: str) -> MockDataset:
    seed = _stable_seed(owner, name)
    rng = random.Random(seed)

    now = datetime.now(timezone.utc)
    created = now - timedelta(days=rng.randint(400, 1200))

    stars_total = rng.randint(800, 6000)
    forks = max(3, int(stars_total / rng.uniform(8, 140)))
    contributors = rng.randint(4, 120)
    open_issues = rng.randint(0, 400)

    burst_day = created + timedelta(days=rng.randint(30, 200))
    burst_size = int(stars_total * rng.uniform(0.18, 0.42))
    organic = stars_total - burst_size

    events: list[StarEventInput] = []
    user_id_cursor = seed % 900_000_000

    def add_user_batch(count: int, day_center: datetime, new_account_bias: float) -> None:
        nonlocal user_id_cursor
        for _ in range(count):
            user_id_cursor += 1
            jitter_hours = rng.randint(-18, 18)
            starred_at = day_center + timedelta(hours=jitter_hours)
            if rng.random() < new_account_bias:
                account_created = starred_at - timedelta(days=rng.randint(0, 10))
                public_repos = rng.randint(0, 2)
                followers = rng.randint(0, 2)
            else:
                account_created = starred_at - timedelta(days=rng.randint(120, 2000))
                public_repos = rng.randint(3, 80)
                followers = rng.randint(0, 500)
            events.append(
                StarEventInput(
                    user_id=user_id_cursor,
                    starred_at=starred_at,
                    account_created_at=account_created,
                    public_repos=public_repos,
                    followers=followers,
                )
            )

    # Organic gradual growth
    for idx in range(organic):
        day = created + timedelta(days=int(400 * idx / max(1, organic)))
        add_user_batch(1, day + timedelta(days=rng.randint(0, 120)), new_account_bias=0.08)

    # Coordinated burst window
    add_user_batch(burst_size, burst_day, new_account_bias=0.55)

    events.sort(key=lambda event: str(event.starred_at))

    commits_last_30d = rng.randint(5, 220)
    prs_merged_last_30d = rng.randint(2, 80)
    releases_last_90d = rng.randint(0, 10)
    issues_opened_last_30d = rng.randint(0, 60)

    snapshot = RepoSnapshotInput(
        stars_count=stars_total,
        forks_count=forks,
        contributors_count=contributors,
        created_at=created,
        last_push_at=now - timedelta(days=rng.randint(0, 25)),
        open_issues_count=open_issues,
        releases_last_90d=releases_last_90d,
        commits_last_30d=commits_last_30d,
        issues_opened_last_30d=issues_opened_last_30d,
        prs_merged_last_30d=prs_merged_last_30d,
    )

    peer_overlap_ratio = rng.uniform(0.05, 0.45)
    return MockDataset(snapshot=snapshot, star_events=events, peer_overlap_ratio=peer_overlap_ratio)

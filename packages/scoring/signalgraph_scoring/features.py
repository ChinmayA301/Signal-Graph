from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import log1p, sqrt
from typing import Iterable, Sequence


def _parse_dt(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text)


@dataclass(frozen=True)
class StarEventInput:
    user_id: int
    starred_at: datetime | str
    account_created_at: datetime | str | None = None
    public_repos: int | None = None
    followers: int | None = None
    # How many OTHER repositories this account starred on the same UTC day (from GH Archive
    # WatchEvents). None when not ingested; co-adoption scoring is then inactive.
    same_day_other_stars: int | None = None


@dataclass(frozen=True)
class RepoSnapshotInput:
    stars_count: int
    forks_count: int
    contributors_count: int
    created_at: datetime | str | None
    last_push_at: datetime | str | None
    open_issues_count: int
    releases_last_90d: int
    commits_last_30d: int
    issues_opened_last_30d: int
    prs_merged_last_30d: int


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def burst_concentration(star_events: Sequence[StarEventInput], repo_created_at: datetime | None) -> dict[str, float]:
    """Share of stars arriving in best 1d/7d/30d windows (proxy for coordinated bursts)."""
    times: list[datetime] = []
    for event in star_events:
        parsed = _parse_dt(event.starred_at)
        if parsed:
            times.append(parsed)
    if not times:
        return {"top1d_share": 0.0, "top7d_share": 0.0, "top30d_share": 0.0, "burst_score": 0.0}
    times.sort()
    total = len(times)
    start = min(times)
    end = max(times)

    def window_share(days: int) -> float:
        window = timedelta(days=days)
        best = 0
        left = 0
        for right in range(total):
            while times[right] - times[left] > window:
                left += 1
            best = max(best, right - left + 1)
        return best / total

    top1d = window_share(1)
    top7d = window_share(7)
    top30d = window_share(30)
    burst_score = clamp01(0.45 * top1d + 0.35 * top7d + 0.20 * top30d)
    return {"top1d_share": top1d, "top7d_share": top7d, "top30d_share": top30d, "burst_score": burst_score}


def low_activity_stargazer_share(star_events: Sequence[StarEventInput]) -> dict[str, float]:
    """Heuristic: accounts with very few public repos and low followers look lower-signal."""
    if not star_events:
        return {"low_activity_share": 0.0, "low_activity_stargazer_score": 0.0}
    low = 0
    for event in star_events:
        repos = event.public_repos if event.public_repos is not None else 0
        followers = event.followers if event.followers is not None else 0
        if repos <= 2 and followers <= 3:
            low += 1
    share = low / len(star_events)
    return {"low_activity_share": share, "low_activity_stargazer_score": clamp01(share * 1.15)}


def recent_account_share(star_events: Sequence[StarEventInput]) -> dict[str, float]:
    """Share of stargazers whose accounts were created shortly before starring."""
    if not star_events:
        return {"recent_account_share": 0.0, "recent_account_score": 0.0}
    recent = 0
    counted = 0
    for event in star_events:
        starred = _parse_dt(event.starred_at)
        created = _parse_dt(event.account_created_at)
        if not starred or not created:
            continue
        counted += 1
        if (starred - created).days <= 14:
            recent += 1
    share = recent / counted if counted else 0.0
    return {"recent_account_share": share, "recent_account_score": clamp01(share * 1.1)}


def ratio_anomalies(snapshot: RepoSnapshotInput) -> dict[str, float]:
    stars = max(1, snapshot.stars_count)
    forks = max(0, snapshot.forks_count)
    contributors = max(1, snapshot.contributors_count)
    star_fork_ratio = stars / (forks + 5)
    star_contrib_ratio = stars / contributors
    # Empirical soft caps — v1 baselines; tune with cohort stats later.
    fork_anomaly = clamp01(log1p(max(0.0, star_fork_ratio - 35.0)) / log1p(200.0))
    contrib_anomaly = clamp01(log1p(max(0.0, star_contrib_ratio - 120.0)) / log1p(800.0))
    return {
        "stars_to_forks_ratio": star_fork_ratio,
        "stars_to_contributors_ratio": star_contrib_ratio,
        "star_to_fork_anomaly": fork_anomaly,
        "star_to_contributor_anomaly": contrib_anomaly,
    }


def spike_without_activity(
    star_events: Sequence[StarEventInput], snapshot: RepoSnapshotInput
) -> dict[str, float]:
    """If recent star velocity is high but engineering signals are flat, elevate suspicion."""
    times = sorted([_parse_dt(e.starred_at) for e in star_events if _parse_dt(e.starred_at)])
    if len(times) < 8:
        return {"recent_star_velocity": 0.0, "no_activity_spike_score": 0.0}
    cutoff = times[-1] - timedelta(days=14)
    recent = sum(1 for t in times if t and t >= cutoff)
    velocity = recent / 14.0
    activity = (
        snapshot.commits_last_30d
        + snapshot.prs_merged_last_30d
        + snapshot.releases_last_90d // 3
        + snapshot.issues_opened_last_30d // 4
    )
    score = clamp01((velocity / 25.0) * (1.0 / (1.0 + sqrt(activity + 1))))
    return {"recent_star_velocity": velocity, "no_activity_spike_score": score}


def arrival_regularity(star_events: Sequence[StarEventInput]) -> dict[str, float]:
    """Share of consecutive stars arriving under 60 seconds apart, plus inter-arrival dispersion.

    Evidence (manufactured-virality Phase B, StarScout labels, 2024 hold-out): suspected
    campaigns are dominated by sub-minute arrivals (median share 0.84 vs 0.00 for normal repos;
    single-feature AUC 0.91), and the signal still separates campaigns that are spread over
    more than a day. A confidence signal, not proof: scripted-looking arrival can also come
    from an organic front-page spike, so it is weighted alongside other components.
    """
    times = sorted(t for t in (_parse_dt(e.starred_at) for e in star_events) if t)
    if len(times) < 8:
        return {"sub_minute_share": 0.0, "interarrival_cv": 0.0, "arrival_regularity_score": 0.0}
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    sub_minute = sum(1 for g in gaps if g < 60) / len(gaps)
    mean = sum(gaps) / len(gaps)
    cv = sqrt(sum((g - mean) ** 2 for g in gaps) / len(gaps)) / mean if mean > 0 else 0.0
    return {"sub_minute_share": sub_minute, "interarrival_cv": cv,
            "arrival_regularity_score": clamp01(1.25 * sub_minute)}


def co_adoption_farm_share(star_events: Sequence[StarEventInput]) -> dict[str, float]:
    """Share of stargazers who starred 20+ other repositories on the same day.

    Evidence (manufactured-virality Phase B, GH Archive via BigQuery): lockstep-flagged repos
    have a median share of 0.96, normal repos 0.05. Inactive (score 0) when the per-star
    `same_day_other_stars` field has not been ingested for at least 8 stars.
    """
    vals = [e.same_day_other_stars for e in star_events if e.same_day_other_stars is not None]
    if len(vals) < 8:
        return {"co_adoption_coverage": len(vals) / max(1, len(star_events)), "farm_share": 0.0,
                "co_adoption_farm_score": 0.0}
    share = sum(1 for v in vals if v >= 20) / len(vals)
    return {"co_adoption_coverage": len(vals) / max(1, len(star_events)), "farm_share": share,
            "co_adoption_farm_score": clamp01((share - 0.05) / 0.45)}


def co_starring_overlap_score(peer_overlap_ratio: float) -> dict[str, float]:
    """Placeholder for graph-derived overlap; mock layer supplies synthetic ratio."""
    ratio = clamp01(peer_overlap_ratio)
    return {"co_starring_overlap_ratio": ratio, "co_starring_overlap_score": ratio}


def daily_star_counts(star_events: Sequence[StarEventInput]) -> dict[date, int]:
    buckets: dict[date, int] = defaultdict(int)
    for event in star_events:
        starred = _parse_dt(event.starred_at)
        if not starred:
            continue
        day = starred.date()
        buckets[day] += 1
    return dict(buckets)


def flag_suspicious_windows(
    daily_counts: dict[date, int], z_threshold: float = 2.5
) -> list[dict[str, str | float]]:
    """Simple burst detector on daily star deltas for visualization."""
    if not daily_counts:
        return []
    days = sorted(daily_counts)
    values = [float(daily_counts[d]) for d in days]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / max(1, len(values) - 1)
    std = sqrt(variance) if variance > 0 else 0.0
    windows: list[dict[str, str | float]] = []
    for day, count in zip(days, values):
        z = (count - mean) / std if std > 1e-6 else 0.0
        if z >= z_threshold and count >= max(5.0, mean + 3):
            windows.append(
                {
                    "start": day.isoformat(),
                    "end": day.isoformat(),
                    "z_score": round(z, 2),
                    "stars": count,
                }
            )
    return windows


def adoption_builder_durability(snapshot: RepoSnapshotInput) -> dict[str, float]:
    """Lightweight proxies until registry/dependency ingestion exists."""
    forks = snapshot.forks_count
    stars = max(1, snapshot.stars_count)
    fork_rate = clamp01(log1p(forks) / log1p(stars))
    doc_issue_signal = clamp01(log1p(snapshot.open_issues_count + 1) / log1p(stars / 10 + 2))
    adoption = clamp01(0.55 * fork_rate + 0.45 * doc_issue_signal)

    push_age_days = None
    last_push = _parse_dt(snapshot.last_push_at)
    created = _parse_dt(snapshot.created_at)
    if last_push and created:
        push_age_days = max(0, (datetime.now(timezone.utc) - last_push).days)
    continuity = clamp01(1.0 - (push_age_days or 0) / 365.0) if push_age_days is not None else 0.5
    release_signal = clamp01(log1p(snapshot.releases_last_90d) / log1p(6))
    contrib_signal = clamp01(log1p(snapshot.contributors_count) / log1p(40))
    builder = clamp01(0.35 * continuity + 0.35 * release_signal + 0.30 * contrib_signal)

    pr_velocity = clamp01(log1p(snapshot.prs_merged_last_30d) / log1p(25))
    commit_velocity = clamp01(log1p(snapshot.commits_last_30d) / log1p(200))
    durability = clamp01(0.5 * pr_velocity + 0.5 * commit_velocity)

    return {
        "adoption_score": adoption,
        "builder_score": builder,
        "durability_score": durability,
    }


def raw_popularity_score(stars_count: int) -> float:
    return clamp01(log1p(stars_count) / log1p(5000))

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from signalgraph_scoring.features import (
    RepoSnapshotInput,
    StarEventInput,
    burst_concentration,
    co_starring_overlap_score,
    flag_suspicious_windows,
    low_activity_stargazer_share,
    raw_popularity_score,
    recent_account_share,
    ratio_anomalies,
    spike_without_activity,
    adoption_builder_durability,
    daily_star_counts,
    clamp01,
)
from signalgraph_scoring.weights import MANIPULATION_WEIGHTS, TRACTION_WEIGHTS


def _weighted_sum(weights: dict[str, float], values: dict[str, float]) -> float:
    total_w = sum(weights.values()) or 1.0
    return sum(weights[k] * values.get(k, 0.0) for k in weights) / total_w


@dataclass(frozen=True)
class ScoreBundle:
    manipulation_risk: float
    star_integrity: float
    adoption_score: float
    builder_score: float
    durability_score: float
    credibility_adjusted_traction: float
    raw_features: dict[str, Any]
    subscores: dict[str, float]
    reasons: dict[str, list[str]]
    suspicious_windows: list[dict[str, Any]]


def compute_scores(
    *,
    star_events: Sequence[StarEventInput],
    snapshot: RepoSnapshotInput,
    peer_overlap_ratio: float = 0.0,
) -> ScoreBundle:
    burst = burst_concentration(star_events, _parse_dt(snapshot.created_at))
    low_act = low_activity_stargazer_share(star_events)
    recent = recent_account_share(star_events)
    ratios = ratio_anomalies(snapshot)
    spike = spike_without_activity(star_events, snapshot)
    overlap = co_starring_overlap_score(peer_overlap_ratio)
    abd = adoption_builder_durability(snapshot)

    manipulation_components = {
        "burst_score": burst["burst_score"],
        "low_activity_stargazer_score": low_act["low_activity_stargazer_score"],
        "recent_account_score": recent["recent_account_score"],
        "star_to_fork_anomaly": ratios["star_to_fork_anomaly"],
        "star_to_contributor_anomaly": ratios["star_to_contributor_anomaly"],
        "no_activity_spike_score": spike["no_activity_spike_score"],
        "co_starring_overlap_score": overlap["co_starring_overlap_score"],
    }
    manipulation_risk = 100.0 * _weighted_sum(MANIPULATION_WEIGHTS, manipulation_components)

    integrity_components = {
        "inverse_burst": 1.0 - burst["burst_score"],
        "inverse_low_activity": 1.0 - low_act["low_activity_stargazer_score"],
        "inverse_recent": 1.0 - recent["recent_account_score"],
        "inverse_ratios": 1.0 - (ratios["star_to_fork_anomaly"] + ratios["star_to_contributor_anomaly"]) / 2.0,
        "inverse_spike": 1.0 - spike["no_activity_spike_score"],
        "inverse_overlap": 1.0 - overlap["co_starring_overlap_score"],
    }
    star_integrity = 100.0 * sum(integrity_components.values()) / max(1, len(integrity_components))

    adoption = abd["adoption_score"] * 100.0
    builder = abd["builder_score"] * 100.0
    durability = abd["durability_score"] * 100.0
    popularity = raw_popularity_score(snapshot.stars_count) * 100.0

    traction_components = {
        "star_integrity": star_integrity / 100.0,
        "adoption_score": adoption / 100.0,
        "builder_score": builder / 100.0,
        "durability_score": durability / 100.0,
        "raw_popularity_score": popularity / 100.0,
    }
    credibility_adjusted_traction = 100.0 * _weighted_sum(TRACTION_WEIGHTS, traction_components)

    raw_features: dict[str, Any] = {
        **burst,
        **low_act,
        **recent,
        **ratios,
        **spike,
        **overlap,
        **abd,
        "recent_star_velocity": spike.get("recent_star_velocity"),
        "stars_count": snapshot.stars_count,
    }

    subscores = {**manipulation_components, **traction_components}

    reasons = _build_reasons(
        manipulation_risk=manipulation_risk,
        star_integrity=star_integrity,
        adoption=adoption,
        builder=builder,
        durability=durability,
        raw_features=raw_features,
    )

    daily = daily_star_counts(star_events)
    suspicious_windows = flag_suspicious_windows(daily)

    return ScoreBundle(
        manipulation_risk=round(manipulation_risk, 2),
        star_integrity=round(star_integrity, 2),
        adoption_score=round(adoption, 2),
        builder_score=round(builder, 2),
        durability_score=round(durability, 2),
        credibility_adjusted_traction=round(credibility_adjusted_traction, 2),
        raw_features=raw_features,
        subscores=subscores,
        reasons=reasons,
        suspicious_windows=suspicious_windows,
    )


def _parse_dt(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def _build_reasons(
    *,
    manipulation_risk: float,
    star_integrity: float,
    adoption: float,
    builder: float,
    durability: float,
    raw_features: dict[str, Any],
) -> dict[str, list[str]]:
    def mr() -> list[str]:
        items: list[str] = []
        if raw_features.get("top1d_share", 0) > 0.2:
            items.append("A large share of stars arrived inside a single day window.")
        if raw_features.get("low_activity_share", 0) > 0.35:
            items.append("Many stargazers show minimal public footprint (heuristic low-activity signal).")
        if raw_features.get("recent_account_share", 0) > 0.25:
            items.append("Elevated share of stars from very new accounts.")
        if raw_features.get("star_to_fork_anomaly", 0) > 0.55:
            items.append("Stars-to-forks ratio looks unusual versus typical OSS patterns.")
        if raw_features.get("no_activity_spike_score", 0) > 0.45:
            items.append("Recent star velocity is high relative to commit/release/issue activity.")
        if not items:
            items.append("No strong burst or ratio anomalies detected in v1 heuristics.")
        return items[:5]

    def integrity() -> list[str]:
        items = []
        if star_integrity < 55:
            items.append("Integrity is pulled down by burst or low-activity stargazer signals.")
        else:
            items.append("Stargazer composition looks comparatively stable for this sample.")
        items.append("This is a confidence estimate, not proof of manipulation.")
        return items[:5]

    def adopt() -> list[str]:
        return [
            "Adoption proxy uses forks and issue engagement relative to stars until registry signals land."
        ]

    def build() -> list[str]:
        return [
            "Builder quality blends push recency, releases, and contributor count as interim proxies."
        ]

    def dur() -> list[str]:
        return [
            "Durability emphasizes recent engineering velocity (commits/PRs) as a momentum persistence check."
        ]

    return {
        "manipulation_risk": mr(),
        "star_integrity": integrity(),
        "adoption_score": adopt(),
        "builder_score": build(),
        "durability_score": dur(),
    }


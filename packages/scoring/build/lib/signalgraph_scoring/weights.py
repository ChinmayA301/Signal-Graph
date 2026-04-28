"""Default weights for v1 heuristics — adjust here or override via API config later."""

MANIPULATION_WEIGHTS = {
    "burst_score": 0.25,
    "low_activity_stargazer_score": 0.20,
    "recent_account_score": 0.10,
    "star_to_fork_anomaly": 0.10,
    "star_to_contributor_anomaly": 0.10,
    "no_activity_spike_score": 0.15,
    "co_starring_overlap_score": 0.10,
}

TRACTION_WEIGHTS = {
    "star_integrity": 0.25,
    "adoption_score": 0.25,
    "builder_score": 0.20,
    "durability_score": 0.20,
    "raw_popularity_score": 0.10,
}

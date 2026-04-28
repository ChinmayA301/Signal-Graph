from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Optional, Union

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.tables import RepoActivityDaily, RepoScore, Repository, StarEvent, SuspiciousCluster, User
from app.schemas.report import (
    AnalyzeResponse,
    ClusterDTO,
    RepositoryDTO,
    ScorecardDTO,
    TimelineDTO,
    TimelinePointDTO,
)
from app.services.github_ingest import fetch_live_dataset
from app.services.mock_data import build_mock_dataset
from signalgraph_scoring.features import RepoSnapshotInput, StarEventInput
from signalgraph_scoring.scores import ScoreBundle, compute_scores

logger = logging.getLogger(__name__)


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _timeline_from_events(star_events: list[StarEventInput]) -> tuple[list[TimelinePointDTO], dict[date, int]]:
    buckets: dict[date, int] = defaultdict(int)
    for event in star_events:
        starred = event.starred_at
        if isinstance(starred, str):
            starred = datetime.fromisoformat(starred.replace("Z", "+00:00"))
        if starred.tzinfo is None:
            starred = starred.replace(tzinfo=timezone.utc)
        day = starred.date()
        buckets[day] += 1

    points: list[TimelinePointDTO] = []
    cumulative = 0
    for day in sorted(buckets):
        delta = int(buckets[day])
        cumulative += delta
        points.append(TimelinePointDTO(date=day, stars_delta=delta, cumulative_stars=cumulative))
    return points, dict(buckets)


def _normalize_dt(value: Union[datetime, str, None]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _persist_dataset(
    db: Session,
    *,
    owner: str,
    name: str,
    ingestion_source: str,
    github_repo_id: Optional[int],
    snapshot_model: RepoSnapshotInput,
    star_events: list[StarEventInput],
) -> Repository:
    now = datetime.now(timezone.utc)
    repo_row = db.execute(select(Repository).where(Repository.owner == owner, Repository.name == name)).scalar_one_or_none()
    if repo_row is None:
        repo_row = Repository(owner=owner, name=name, updated_at=now)
        db.add(repo_row)
        db.flush()

    repo_row.github_repo_id = github_repo_id or repo_row.github_repo_id
    repo_row.created_at = _normalize_dt(snapshot_model.created_at)
    repo_row.stars_count = snapshot_model.stars_count
    repo_row.forks_count = snapshot_model.forks_count
    repo_row.watchers_count = repo_row.watchers_count or 0
    repo_row.open_issues_count = snapshot_model.open_issues_count
    repo_row.archived = repo_row.archived
    repo_row.last_push_at = _normalize_dt(snapshot_model.last_push_at)
    repo_row.contributors_count = snapshot_model.contributors_count
    repo_row.commits_last_30d = snapshot_model.commits_last_30d
    repo_row.releases_last_90d = snapshot_model.releases_last_90d
    repo_row.issues_opened_last_30d = snapshot_model.issues_opened_last_30d
    repo_row.prs_merged_last_30d = snapshot_model.prs_merged_last_30d
    repo_row.ingestion_source = ingestion_source
    repo_row.updated_at = now

    db.execute(delete(StarEvent).where(StarEvent.repo_id == repo_row.repo_id))
    db.execute(delete(RepoActivityDaily).where(RepoActivityDaily.repo_id == repo_row.repo_id))
    db.execute(delete(SuspiciousCluster).where(SuspiciousCluster.repo_id == repo_row.repo_id))

    ingestion_day = _utc_today()
    for event in star_events:
        starred_at = event.starred_at
        if isinstance(starred_at, str):
            starred_at = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
        if starred_at.tzinfo is None:
            starred_at = starred_at.replace(tzinfo=timezone.utc)

        user_row = db.get(User, event.user_id)
        account_created_at = _normalize_dt(event.account_created_at)
        if user_row is None:
            user_row = User(
                user_id=event.user_id,
                login=f"user_{event.user_id}",
                account_created_at=account_created_at,
                followers=event.followers or 0,
                following=0,
                public_repos=event.public_repos or 0,
                public_gists=0,
                account_type="User",
                updated_at=now,
            )
            db.add(user_row)
        else:
            user_row.followers = event.followers or user_row.followers
            user_row.public_repos = event.public_repos or user_row.public_repos
            if account_created_at and user_row.account_created_at is None:
                user_row.account_created_at = account_created_at
            user_row.updated_at = now

        db.add(
            StarEvent(
                repo_id=repo_row.repo_id,
                user_id=event.user_id,
                starred_at=starred_at,
                source=ingestion_source,
                ingestion_date=ingestion_day,
            )
        )

    buckets: dict[date, int] = defaultdict(int)
    for event in star_events:
        starred_at = event.starred_at
        if isinstance(starred_at, str):
            starred_at = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
        if starred_at.tzinfo is None:
            starred_at = starred_at.replace(tzinfo=timezone.utc)
        buckets[starred_at.date()] += 1

    for day, delta in buckets.items():
        db.add(
            RepoActivityDaily(
                repo_id=repo_row.repo_id,
                activity_date=day,
                star_count_delta=int(delta),
            )
        )

    db.flush()
    return repo_row


def _persist_scores(db: Session, repo_id: int, bundle: ScoreBundle) -> None:
    snapshot_day = _utc_today()
    existing = db.execute(
        select(RepoScore).where(RepoScore.repo_id == repo_id, RepoScore.snapshot_date == snapshot_day)
    ).scalar_one_or_none()
    explanation = {
        "raw_features": bundle.raw_features,
        "subscores": bundle.subscores,
        "reasons": bundle.reasons,
        "suspicious_windows": bundle.suspicious_windows,
    }
    if existing:
        existing.manipulation_risk = bundle.manipulation_risk
        existing.star_integrity = bundle.star_integrity
        existing.adoption_score = bundle.adoption_score
        existing.builder_score = bundle.builder_score
        existing.durability_score = bundle.durability_score
        existing.credibility_adjusted_traction = bundle.credibility_adjusted_traction
        existing.explanation_json = explanation
    else:
        db.add(
            RepoScore(
                repo_id=repo_id,
                snapshot_date=snapshot_day,
                manipulation_risk=bundle.manipulation_risk,
                star_integrity=bundle.star_integrity,
                adoption_score=bundle.adoption_score,
                builder_score=bundle.builder_score,
                durability_score=bundle.durability_score,
                credibility_adjusted_traction=bundle.credibility_adjusted_traction,
                explanation_json=explanation,
            )
        )

    for window in bundle.suspicious_windows:
        start = datetime.fromisoformat(str(window["start"]))
        end = datetime.fromisoformat(str(window["end"]))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        db.add(
            SuspiciousCluster(
                repo_id=repo_id,
                time_window_start=start,
                time_window_end=end,
                account_count=int(float(window.get("stars", 0))),
                repos_touched=1,
                cluster_score=float(window.get("z_score", 0.0)),
                reason="Elevated daily star velocity versus baseline (heuristic window).",
            )
        )


def build_analyze_response(
    *,
    owner: str,
    name: str,
    ingestion_source: str,
    snapshot: RepoSnapshotInput,
    star_events: list[StarEventInput],
    bundle: ScoreBundle,
) -> AnalyzeResponse:
    points, _ = _timeline_from_events(star_events)
    timeline = TimelineDTO(
        points=points,
        suspicious_windows=bundle.suspicious_windows,
        overlays={
            "commits_daily": [],
            "releases": [],
            "issues": [],
        },
    )

    clusters = [
        ClusterDTO(
            cluster_id=index + 1,
            time_window_start=_normalize_dt(str(window["start"])) or datetime.now(timezone.utc),
            time_window_end=_normalize_dt(str(window["end"])) or datetime.now(timezone.utc),
            account_count=int(float(window.get("stars", 0))),
            repos_touched=1,
            cluster_score=float(window.get("z_score", 0.0)),
            reason="Elevated daily star velocity versus baseline (heuristic window).",
        )
        for index, window in enumerate(bundle.suspicious_windows)
    ]

    disclaimer = (
        "SignalGraph surfaces heuristic risk signals and confidence-style scores. "
        "Patterns can include false positives; this is not evidence of wrongdoing."
    )

    return AnalyzeResponse(
        repository=RepositoryDTO(
            owner=owner,
            name=name,
            stars_count=int(snapshot.stars_count),
            forks_count=int(snapshot.forks_count),
            watchers_count=0,
            open_issues_count=int(snapshot.open_issues_count),
            primary_language=None,
            created_at=_normalize_dt(snapshot.created_at),
            last_push_at=_normalize_dt(snapshot.last_push_at),
            last_release_at=None,
            archived=False,
            ingestion_source=ingestion_source,
        ),
        scorecard=ScorecardDTO(
            manipulation_risk=bundle.manipulation_risk,
            star_integrity=bundle.star_integrity,
            adoption_score=bundle.adoption_score,
            builder_score=bundle.builder_score,
            durability_score=bundle.durability_score,
            credibility_adjusted_traction=bundle.credibility_adjusted_traction,
            raw_features=bundle.raw_features,
            subscores=bundle.subscores,
            reasons=bundle.reasons,
            snapshot_date=_utc_today(),
        ),
        timeline=timeline,
        clusters=clusters,
        disclaimer=disclaimer,
    )


async def run_analysis(db: Session, settings: Settings, owner: str, name: str, *, force_mock: bool) -> AnalyzeResponse:
    ingestion_source = "mock"
    peer_overlap_ratio = 0.0
    github_repo_id = None

    if not settings.mock_mode and not force_mock and settings.github_token:
        try:
            live = await fetch_live_dataset(owner, name, settings.github_token)
            snapshot = live.snapshot
            star_events = live.star_events
            peer_overlap_ratio = live.peer_overlap_ratio
            github_repo_id = live.github_repo_id
            ingestion_source = "github_api"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Live ingestion failed, falling back to mock: %s", exc)
            mock = build_mock_dataset(owner, name)
            snapshot = mock.snapshot
            star_events = mock.star_events
            peer_overlap_ratio = mock.peer_overlap_ratio
            ingestion_source = "mock_fallback"
    else:
        mock = build_mock_dataset(owner, name)
        snapshot = mock.snapshot
        star_events = mock.star_events
        peer_overlap_ratio = mock.peer_overlap_ratio

    bundle = compute_scores(star_events=star_events, snapshot=snapshot, peer_overlap_ratio=peer_overlap_ratio)
    repo_row = _persist_dataset(
        db,
        owner=owner,
        name=name,
        ingestion_source=ingestion_source,
        github_repo_id=github_repo_id,
        snapshot_model=snapshot,
        star_events=star_events,
    )
    _persist_scores(db, repo_row.repo_id, bundle)
    db.commit()

    return build_analyze_response(
        owner=owner,
        name=name,
        ingestion_source=ingestion_source,
        snapshot=snapshot,
        star_events=star_events,
        bundle=bundle,
    )

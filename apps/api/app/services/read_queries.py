from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.tables import RepoScore, Repository, StarEvent, SuspiciousCluster
from app.schemas.report import (
    ClusterDTO,
    CompareDTO,
    PeerCardDTO,
    RepositoryDTO,
    ScorecardDTO,
    TimelineDTO,
    TimelinePointDTO,
)
from app.services.analysis_pipeline import _timeline_from_events
from signalgraph_scoring.features import StarEventInput


def get_repository_row(db: Session, owner: str, name: str) -> Repository | None:
    return db.execute(select(Repository).where(Repository.owner == owner, Repository.name == name)).scalar_one_or_none()


def get_latest_score(db: Session, repo_id: int) -> RepoScore | None:
    return db.execute(select(RepoScore).where(RepoScore.repo_id == repo_id).order_by(desc(RepoScore.snapshot_date)).limit(1)).scalar_one_or_none()


def repository_dto(repo: Repository) -> RepositoryDTO:
    return RepositoryDTO(
        owner=repo.owner,
        name=repo.name,
        stars_count=repo.stars_count,
        forks_count=repo.forks_count,
        watchers_count=repo.watchers_count,
        open_issues_count=repo.open_issues_count,
        primary_language=repo.primary_language,
        created_at=repo.created_at,
        last_push_at=repo.last_push_at,
        last_release_at=repo.last_release_at,
        archived=repo.archived,
        ingestion_source=repo.ingestion_source,
    )


def scorecard_dto(score: RepoScore) -> ScorecardDTO:
    explanation = score.explanation_json or {}
    return ScorecardDTO(
        manipulation_risk=score.manipulation_risk,
        star_integrity=score.star_integrity,
        adoption_score=score.adoption_score,
        builder_score=score.builder_score,
        durability_score=score.durability_score,
        credibility_adjusted_traction=score.credibility_adjusted_traction,
        raw_features=explanation.get("raw_features", {}),
        subscores=explanation.get("subscores", {}),
        reasons=explanation.get("reasons", {}),
        snapshot_date=score.snapshot_date,
    )


def build_timeline(db: Session, repo_id: int) -> TimelineDTO:
    rows = db.execute(select(StarEvent).where(StarEvent.repo_id == repo_id)).scalars().all()
    events = [
        StarEventInput(
            user_id=row.user_id,
            starred_at=row.starred_at,
        )
        for row in rows
    ]
    points, _ = _timeline_from_events(events)
    score = get_latest_score(db, repo_id)
    windows = []
    if score and score.explanation_json:
        windows = score.explanation_json.get("suspicious_windows", [])
    return TimelineDTO(points=points, suspicious_windows=windows, overlays={"commits_daily": [], "releases": [], "issues": []})


def list_clusters(db: Session, repo_id: int) -> list[ClusterDTO]:
    rows = db.execute(select(SuspiciousCluster).where(SuspiciousCluster.repo_id == repo_id)).scalars().all()
    return [
        ClusterDTO(
            cluster_id=row.cluster_id,
            time_window_start=row.time_window_start,
            time_window_end=row.time_window_end,
            account_count=row.account_count,
            repos_touched=row.repos_touched,
            cluster_score=row.cluster_score,
            reason=row.reason,
        )
        for row in rows
    ]


def build_compare(db: Session, owner: str, name: str, peers: list[tuple[str, str]]) -> CompareDTO | None:
    base_repo = get_repository_row(db, owner, name)
    if base_repo is None:
        return None
    base_score = get_latest_score(db, base_repo.repo_id)
    if base_score is None:
        return None

    base_card = PeerCardDTO(
        owner=base_repo.owner,
        name=base_repo.name,
        stars_count=base_repo.stars_count,
        credibility_adjusted_traction=base_score.credibility_adjusted_traction,
        manipulation_risk=base_score.manipulation_risk,
    )

    peer_cards: list[PeerCardDTO] = []
    for peer_owner, peer_name in peers:
        peer_repo = get_repository_row(db, peer_owner, peer_name)
        if not peer_repo:
            continue
        peer_score = get_latest_score(db, peer_repo.repo_id)
        if not peer_score:
            continue
        peer_cards.append(
            PeerCardDTO(
                owner=peer_repo.owner,
                name=peer_repo.name,
                stars_count=peer_repo.stars_count,
                credibility_adjusted_traction=peer_score.credibility_adjusted_traction,
                manipulation_risk=peer_score.manipulation_risk,
            )
        )

    return CompareDTO(base=base_card, peers=peer_cards)

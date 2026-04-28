from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import AnalyzeRequest, AnalyzeResponse, CompareDTO, ScorecardDTO, TimelineDTO
from app.services.analysis_pipeline import run_analysis
from app.services.read_queries import (
    build_compare,
    build_timeline,
    get_latest_score,
    get_repository_row,
    list_clusters,
    repository_dto,
    scorecard_dto,
)
from app.services.repo_url import parse_github_repo_url
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repo(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    parsed = parse_github_repo_url(payload.repo_url)
    return await run_analysis(
        db,
        settings,
        parsed.owner,
        parsed.name,
        force_mock=bool(payload.force_mock),
    )


@router.get("/repo/{owner}/{name}", response_model=AnalyzeResponse)
def get_repo_report(owner: str, name: str, db: Session = Depends(get_db)) -> AnalyzeResponse:
    repo = get_repository_row(db, owner, name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found; run POST /analyze first.")
    score = get_latest_score(db, repo.repo_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Scores missing; run POST /analyze first.")
    explanation = score.explanation_json or {}
    timeline = build_timeline(db, repo.repo_id)
    clusters = list_clusters(db, repo.repo_id)
    disclaimer = (
        "SignalGraph surfaces heuristic risk signals and confidence-style scores. "
        "Patterns can include false positives; this is not evidence of wrongdoing."
    )
    return AnalyzeResponse(
        repository=repository_dto(repo),
        scorecard=scorecard_dto(score),
        timeline=timeline,
        clusters=clusters,
        disclaimer=disclaimer,
    )


@router.get("/repo/{owner}/{name}/scores", response_model=ScorecardDTO)
def get_scores(owner: str, name: str, db: Session = Depends(get_db)) -> ScorecardDTO:
    repo = get_repository_row(db, owner, name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    score = get_latest_score(db, repo.repo_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Scores missing")
    return scorecard_dto(score)


@router.get("/repo/{owner}/{name}/timeline", response_model=TimelineDTO)
def get_timeline(owner: str, name: str, db: Session = Depends(get_db)) -> TimelineDTO:
    repo = get_repository_row(db, owner, name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return build_timeline(db, repo.repo_id)


@router.get("/repo/{owner}/{name}/clusters")
def get_clusters(owner: str, name: str, db: Session = Depends(get_db)):
    repo = get_repository_row(db, owner, name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"clusters": list_clusters(db, repo.repo_id)}


@router.get("/repo/{owner}/{name}/compare", response_model=CompareDTO)
def compare_repo(
    owner: str,
    name: str,
    peers: list[str] = Query(
        default=[],
        description="Repeat peers=owner/name for each comparison repository",
    ),
    db: Session = Depends(get_db),
) -> CompareDTO:
    if not peers:
        raise HTTPException(
            status_code=400,
            detail="Provide peers as repeated query params, e.g. ?peers=facebook/react&peers=vercel/next.js",
        )
    parsed_peers: list[tuple[str, str]] = []
    for token in peers:
        cleaned = token.strip()
        if "/" not in cleaned:
            raise HTTPException(status_code=400, detail=f"Invalid peer '{token}', expected owner/name")
        peer_owner, peer_name = cleaned.split("/", 1)
        parsed_peers.append((peer_owner, peer_name))
    result = build_compare(db, owner, name, parsed_peers)
    if result is None:
        raise HTTPException(status_code=404, detail="Base repository or scores not found for comparison")
    return result

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., examples=["https://github.com/microsoft/vscode"])
    force_mock: Optional[bool] = False


class RepositoryDTO(BaseModel):
    owner: str
    name: str
    stars_count: int
    forks_count: int
    watchers_count: int
    open_issues_count: int
    primary_language: Optional[str]
    created_at: Optional[datetime]
    last_push_at: Optional[datetime]
    last_release_at: Optional[datetime]
    archived: bool
    ingestion_source: str


class ScorecardDTO(BaseModel):
    manipulation_risk: float
    star_integrity: float
    adoption_score: float
    builder_score: float
    durability_score: float
    credibility_adjusted_traction: float
    raw_features: dict[str, Any]
    subscores: dict[str, float]
    reasons: dict[str, list[str]]
    snapshot_date: date


class TimelinePointDTO(BaseModel):
    date: date
    stars_delta: int
    cumulative_stars: int


class TimelineDTO(BaseModel):
    points: list[TimelinePointDTO]
    suspicious_windows: list[dict[str, Any]]
    overlays: dict[str, list[dict[str, Any]]]


class ClusterDTO(BaseModel):
    cluster_id: int
    time_window_start: datetime
    time_window_end: datetime
    account_count: int
    repos_touched: int
    cluster_score: float
    reason: Optional[str]


class PeerCardDTO(BaseModel):
    owner: str
    name: str
    stars_count: int
    credibility_adjusted_traction: float
    manipulation_risk: float


class CompareDTO(BaseModel):
    base: PeerCardDTO
    peers: list[PeerCardDTO]


class AnalyzeResponse(BaseModel):
    repository: RepositoryDTO
    scorecard: ScorecardDTO
    timeline: TimelineDTO
    clusters: list[ClusterDTO]
    disclaimer: str

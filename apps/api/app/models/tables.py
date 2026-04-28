from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("owner", "name", name="uq_repositories_owner_name"),)

    repo_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_repo_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    primary_language: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stars_count: Mapped[int] = mapped_column(Integer, default=0)
    forks_count: Mapped[int] = mapped_column(Integer, default=0)
    watchers_count: Mapped[int] = mapped_column(Integer, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    default_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    last_push_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_release_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    contributors_count: Mapped[int] = mapped_column(Integer, default=1)
    commits_last_30d: Mapped[int] = mapped_column(Integer, default=0)
    releases_last_90d: Mapped[int] = mapped_column(Integer, default=0)
    issues_opened_last_30d: Mapped[int] = mapped_column(Integer, default=0)
    prs_merged_last_30d: Mapped[int] = mapped_column(Integer, default=0)
    ingestion_source: Mapped[str] = mapped_column(String(32), default="unknown")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    star_events: Mapped[list["StarEvent"]] = relationship(back_populates="repository")
    scores: Mapped[list["RepoScore"]] = relationship(back_populates="repository")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    login: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    following: Mapped[int] = mapped_column(Integer, default=0)
    public_repos: Mapped[int] = mapped_column(Integer, default=0)
    public_gists: Mapped[int] = mapped_column(Integer, default=0)
    account_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    suspicious_activity_features_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    star_events: Mapped[list["StarEvent"]] = relationship(back_populates="user")


class StarEvent(Base):
    __tablename__ = "star_events"
    __table_args__ = (UniqueConstraint("repo_id", "user_id", name="uq_star_events_repo_user"),)

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    starred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="github_api")
    ingestion_date: Mapped[date] = mapped_column(Date, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="star_events")
    user: Mapped["User"] = relationship(back_populates="star_events")


class RepoActivityDaily(Base):
    __tablename__ = "repo_activity_daily"
    __table_args__ = (UniqueConstraint("repo_id", "activity_date", name="uq_repo_activity_daily_repo_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    star_count_delta: Mapped[int] = mapped_column(Integer, default=0)
    fork_count_delta: Mapped[int] = mapped_column(Integer, default=0)
    issues_opened: Mapped[int] = mapped_column(Integer, default=0)
    issues_closed: Mapped[int] = mapped_column(Integer, default=0)
    prs_opened: Mapped[int] = mapped_column(Integer, default=0)
    prs_merged: Mapped[int] = mapped_column(Integer, default=0)
    commits: Mapped[int] = mapped_column(Integer, default=0)
    releases: Mapped[int] = mapped_column(Integer, default=0)
    contributors_active: Mapped[int] = mapped_column(Integer, default=0)


class RepoScore(Base):
    __tablename__ = "repo_scores"
    __table_args__ = (UniqueConstraint("repo_id", "snapshot_date", name="uq_repo_scores_repo_snapshot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    manipulation_risk: Mapped[float] = mapped_column(Float, nullable=False)
    star_integrity: Mapped[float] = mapped_column(Float, nullable=False)
    adoption_score: Mapped[float] = mapped_column(Float, nullable=False)
    builder_score: Mapped[float] = mapped_column(Float, nullable=False)
    durability_score: Mapped[float] = mapped_column(Float, nullable=False)
    credibility_adjusted_traction: Mapped[float] = mapped_column(Float, nullable=False)
    explanation_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="scores")


class SuspiciousCluster(Base):
    __tablename__ = "suspicious_clusters"

    cluster_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False)
    time_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    account_count: Mapped[int] = mapped_column(Integer, default=0)
    repos_touched: Mapped[int] = mapped_column(Integer, default=0)
    cluster_score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

"""initial signalgraph schema

Revision ID: 20250424_0001
Revises:
Create Date: 2025-04-24

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20250424_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("repo_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primary_language", sa.String(length=64), nullable=True),
        sa.Column("stars_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forks_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watchers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_release_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contributors_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("commits_last_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("releases_last_90d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues_opened_last_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prs_merged_last_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ingestion_source", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner", "name", name="uq_repositories_owner_name"),
        sa.UniqueConstraint("github_repo_id", name="uq_repositories_github_repo_id"),
    )

    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("login", sa.String(length=255), nullable=False),
        sa.Column("account_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("followers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("following", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("public_repos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("public_gists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("account_type", sa.String(length=32), nullable=True),
        sa.Column("suspicious_activity_features_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_login", "users", ["login"], unique=False)

    op.create_table(
        "star_events",
        sa.Column("event_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("starred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="github_api"),
        sa.Column("ingestion_date", sa.Date(), nullable=False),
        sa.UniqueConstraint("repo_id", "user_id", name="uq_star_events_repo_user"),
    )

    op.create_table(
        "repo_activity_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("star_count_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fork_count_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues_opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues_closed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prs_opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prs_merged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("releases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contributors_active", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("repo_id", "activity_date", name="uq_repo_activity_daily_repo_date"),
    )

    op.create_table(
        "repo_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("manipulation_risk", sa.Float(), nullable=False),
        sa.Column("star_integrity", sa.Float(), nullable=False),
        sa.Column("adoption_score", sa.Float(), nullable=False),
        sa.Column("builder_score", sa.Float(), nullable=False),
        sa.Column("durability_score", sa.Float(), nullable=False),
        sa.Column("credibility_adjusted_traction", sa.Float(), nullable=False),
        sa.Column("explanation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("repo_id", "snapshot_date", name="uq_repo_scores_repo_snapshot"),
    )

    op.create_table(
        "suspicious_clusters",
        sa.Column("cluster_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repositories.repo_id", ondelete="CASCADE"), nullable=False),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repos_touched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cluster_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("suspicious_clusters")
    op.drop_table("repo_scores")
    op.drop_table("repo_activity_daily")
    op.drop_table("star_events")
    op.drop_index("ix_users_login", table_name="users")
    op.drop_table("users")
    op.drop_table("repositories")

"""Initial schema migration for Phase 2 database models

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-04 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("editor", "admin", name="userrole", native_enum=False, length=20),
            nullable=False,
            server_default="editor",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. Shows table
    op.create_table(
        "shows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("section", sa.String(length=50), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="contentstatus", native_enum=False, length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shows_id"), "shows", ["id"], unique=False)
    op.create_index(op.f("ix_shows_slug"), "shows", ["slug"], unique=True)
    op.create_index(op.f("ix_shows_section"), "shows", ["section"], unique=False)
    op.create_index(op.f("ix_shows_status"), "shows", ["status"], unique=False)

    # 3. Seasons table
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("show_id", sa.Integer(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("show_id", "season_number", name="uq_seasons_show_season_number"),
        sa.CheckConstraint("season_number >= 0", name="ck_seasons_season_number_non_negative"),
    )
    op.create_index(op.f("ix_seasons_id"), "seasons", ["id"], unique=False)
    op.create_index(op.f("ix_seasons_show_id"), "seasons", ["show_id"], unique=False)

    # 4. Episodes table
    op.create_table(
        "episodes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("show_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("content_group", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="contentstatus_ep", native_enum=False, length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_group", "language", name="uq_episodes_content_group_language"),
    )
    op.create_index(op.f("ix_episodes_id"), "episodes", ["id"], unique=False)
    op.create_index(op.f("ix_episodes_show_id"), "episodes", ["show_id"], unique=False)
    op.create_index(op.f("ix_episodes_season_id"), "episodes", ["season_id"], unique=False)
    op.create_index(op.f("ix_episodes_content_group"), "episodes", ["content_group"], unique=False)
    op.create_index(op.f("ix_episodes_language"), "episodes", ["language"], unique=False)
    op.create_index(op.f("ix_episodes_status"), "episodes", ["status"], unique=False)

    # 5. Artworks table
    op.create_table(
        "artworks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("episode_id", sa.String(length=64), nullable=False),
        sa.Column(
            "type",
            sa.Enum("poster", "banner", "thumbnail", name="artworktype", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("episode_id", "type", name="uq_artworks_episode_id_type"),
    )
    op.create_index(op.f("ix_artworks_id"), "artworks", ["id"], unique=False)
    op.create_index(op.f("ix_artworks_episode_id"), "artworks", ["episode_id"], unique=False)

    # 6. PublishRuns table
    op.create_table(
        "publish_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("triggered_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "success", "failed", name="publishrunstatus", native_enum=False, length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("show_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("episode_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publish_runs_id"), "publish_runs", ["id"], unique=False)
    op.create_index(op.f("ix_publish_runs_triggered_by_user_id"), "publish_runs", ["triggered_by_user_id"], unique=False)
    op.create_index(op.f("ix_publish_runs_status"), "publish_runs", ["status"], unique=False)
    op.create_index(op.f("ix_publish_runs_started_at"), "publish_runs", ["started_at"], unique=False)


def downgrade() -> None:
    op.drop_table("publish_runs")
    op.drop_table("artworks")
    op.drop_table("episodes")
    op.drop_table("seasons")
    op.drop_table("shows")
    op.drop_table("users")

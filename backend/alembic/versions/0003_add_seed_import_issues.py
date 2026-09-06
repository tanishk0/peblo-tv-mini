"""Record source fixture rows rejected by CMS uniqueness constraints.

Revision ID: 0003_add_seed_import_issues
Revises: 0002_add_catalogue_version
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_add_seed_import_issues"
down_revision = "0002_add_catalogue_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seed_import_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_episode_id", sa.String(length=64), nullable=False),
        sa.Column("show_slug", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_episode_id", name="uq_seed_import_issues_source_episode_id"),
    )
    op.create_index("ix_seed_import_issues_source_episode_id", "seed_import_issues", ["source_episode_id"])
    op.create_index("ix_seed_import_issues_show_slug", "seed_import_issues", ["show_slug"])


def downgrade() -> None:
    op.drop_index("ix_seed_import_issues_show_slug", table_name="seed_import_issues")
    op.drop_index("ix_seed_import_issues_source_episode_id", table_name="seed_import_issues")
    op.drop_table("seed_import_issues")

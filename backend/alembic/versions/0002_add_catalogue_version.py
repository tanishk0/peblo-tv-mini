"""Add the published catalogue version to the publish audit log.

Revision ID: 0002_add_catalogue_version
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_catalogue_version"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("publish_runs", sa.Column("catalogue_version", sa.String(length=80), nullable=True))
    op.create_index("ix_publish_runs_catalogue_version", "publish_runs", ["catalogue_version"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_publish_runs_catalogue_version", table_name="publish_runs")
    op.drop_column("publish_runs", "catalogue_version")

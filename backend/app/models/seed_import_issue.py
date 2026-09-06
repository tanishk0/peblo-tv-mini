from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SeedImportIssue(Base):
    """A source-fixture problem that cannot be represented in constrained CMS tables."""

    __tablename__ = "seed_import_issues"
    __table_args__ = (
        UniqueConstraint("source_episode_id", name="uq_seed_import_issues_source_episode_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_episode_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    show_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

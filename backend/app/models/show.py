from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Enum, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentStatus

if TYPE_CHECKING:
    from app.models.season import Season
    from app.models.episode import Episode


class Show(Base):
    """Show model representing a series, minisode, or collection."""
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    synopsis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False, length=20),
        default=ContentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    seasons: Mapped[List["Season"]] = relationship(
        "Season",
        back_populates="show",
        cascade="all, delete-orphan",
        order_by="Season.season_number",
    )
    episodes: Mapped[List["Episode"]] = relationship(
        "Episode",
        back_populates="show",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Show id={self.id} slug={self.slug!r} status={self.status.value!r}>"

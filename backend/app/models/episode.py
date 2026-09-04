from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentStatus

if TYPE_CHECKING:
    from app.models.show import Show
    from app.models.season import Season
    from app.models.artwork import Artwork


class Episode(Base):
    """Episode model representing an individual media file / language variant."""
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("content_group", "language", name="uq_episodes_content_group_language"),
    )

    # String primary key to accommodate seed data IDs ("ep_0001") and generated UUIDs
    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    show_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    synopsis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    content_group: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
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
    show: Mapped["Show"] = relationship("Show", back_populates="episodes")
    season: Mapped["Season"] = relationship("Season", back_populates="episodes")
    artworks: Mapped[List["Artwork"]] = relationship(
        "Artwork",
        back_populates="episode",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Episode id={self.id!r} title={self.title!r} "
            f"lang={self.language!r} content_group={self.content_group!r}>"
        )

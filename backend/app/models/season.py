from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.show import Show
    from app.models.episode import Episode


class Season(Base):
    """Season model. Season 0 is reserved for trailers."""
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("show_id", "season_number", name="uq_seasons_show_season_number"),
        CheckConstraint("season_number >= 0", name="ck_seasons_season_number_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    show_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
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
    show: Mapped["Show"] = relationship("Show", back_populates="seasons")
    episodes: Mapped[List["Episode"]] = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="Episode.episode_number",
    )

    def __repr__(self) -> str:
        return f"<Season id={self.id} show_id={self.show_id} season_number={self.season_number}>"

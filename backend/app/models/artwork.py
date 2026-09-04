from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ArtworkType

if TYPE_CHECKING:
    from app.models.episode import Episode


class Artwork(Base):
    """Artwork asset metadata linked to an episode (poster, banner, or thumbnail)."""
    __tablename__ = "artworks"
    __table_args__ = (
        UniqueConstraint("episode_id", "type", name="uq_artworks_episode_id_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    episode_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[ArtworkType] = mapped_column(
        Enum(ArtworkType, native_enum=False, length=20),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
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
    episode: Mapped["Episode"] = relationship("Episode", back_populates="artworks")

    def __repr__(self) -> str:
        return f"<Artwork id={self.id} episode_id={self.episode_id!r} type={self.type.value!r}>"

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PublishRunStatus

if TYPE_CHECKING:
    from app.models.user import User


class PublishRun(Base):
    """Audit log of catalog publication executions."""
    __tablename__ = "publish_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    triggered_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[PublishRunStatus] = mapped_column(
        Enum(PublishRunStatus, native_enum=False, length=20),
        default=PublishRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    show_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    episode_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    triggered_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="publish_runs",
    )

    def __repr__(self) -> str:
        return f"<PublishRun id={self.id} status={self.status.value!r} shows={self.show_count}>"

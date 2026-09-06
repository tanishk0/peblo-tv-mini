"""CMS response contracts for catalogue publishing."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.enums import PublishRunStatus


class PublishCatalogueResponse(BaseModel):
    status: PublishRunStatus
    publish_run_id: int
    catalogue_version: str
    show_count: int
    episode_count: int
    completed_at: datetime


class PublishRunResponse(BaseModel):
    """A compact, editor-readable record of one publish attempt."""

    id: int
    status: PublishRunStatus
    show_count: int
    episode_count: int
    error_message: Optional[str]
    catalogue_version: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}

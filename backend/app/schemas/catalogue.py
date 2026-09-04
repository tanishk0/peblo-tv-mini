"""CMS response contracts for catalogue publishing."""
from datetime import datetime
from pydantic import BaseModel

from app.models.enums import PublishRunStatus


class PublishCatalogueResponse(BaseModel):
    status: PublishRunStatus
    publish_run_id: int
    catalogue_version: str
    show_count: int
    episode_count: int
    completed_at: datetime

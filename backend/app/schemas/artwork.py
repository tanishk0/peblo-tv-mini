"""Response contract for CMS artwork uploads."""
from datetime import datetime
from pydantic import BaseModel

from app.models.enums import ArtworkType


class ArtworkResponse(BaseModel):
    id: int
    episode_id: str
    type: ArtworkType
    storage_key: str
    url: str
    width: int
    height: int
    file_size_bytes: int
    created_at: datetime

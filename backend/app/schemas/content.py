"""Pydantic contracts for the internal CMS content API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ArtworkType, ContentStatus
from app.services.reference import allowed_categories, allowed_languages, allowed_sections


class Page(BaseModel):
    items: list
    total: int
    offset: int
    limit: int


class ShowFields(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    synopsis: Optional[str] = None
    section: Optional[str] = Field(default=None, max_length=50)
    categories: list[str] = Field(default_factory=list)
    status: ContentStatus = ContentStatus.DRAFT

    @field_validator("section")
    @classmethod
    def section_is_known(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in allowed_sections():
            raise ValueError("section must be one of: " + ", ".join(sorted(allowed_sections())))
        return value

    @field_validator("categories")
    @classmethod
    def categories_are_known(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - allowed_categories())
        if invalid:
            raise ValueError("invalid categories: " + ", ".join(invalid))
        return value


class ShowCreate(ShowFields):
    pass


class ShowUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    synopsis: Optional[str] = None
    section: Optional[str] = Field(default=None, max_length=50)
    categories: Optional[list[str]] = None
    status: Optional[ContentStatus] = None

    @field_validator("section")
    @classmethod
    def section_is_known(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in allowed_sections():
            raise ValueError("section must be one of: " + ", ".join(sorted(allowed_sections())))
        return value

    @field_validator("categories")
    @classmethod
    def categories_are_known(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is not None:
            invalid = sorted(set(value) - allowed_categories())
            if invalid:
                raise ValueError("invalid categories: " + ", ".join(invalid))
        return value


class ShowResponse(ShowFields):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ShowPage(Page):
    items: list[ShowResponse]


class SeasonCreate(BaseModel):
    season_number: int = Field(ge=0)


class SeasonUpdate(BaseModel):
    season_number: Optional[int] = Field(default=None, ge=0)


class SeasonResponse(BaseModel):
    id: int
    show_id: int
    season_number: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SeasonPage(Page):
    items: list[SeasonResponse]


class EpisodeFields(BaseModel):
    show_id: int = Field(gt=0)
    season_id: int = Field(gt=0)
    episode_number: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=255)
    synopsis: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    language: str = Field(min_length=1, max_length=10)
    content_group: str = Field(min_length=1, max_length=255)
    status: ContentStatus = ContentStatus.DRAFT

    @field_validator("language")
    @classmethod
    def language_is_known(cls, value: str) -> str:
        if value not in allowed_languages():
            raise ValueError("language must be one of: " + ", ".join(sorted(allowed_languages())))
        return value


class EpisodeCreate(EpisodeFields):
    id: Optional[str] = Field(default=None, min_length=1, max_length=64)


class EpisodeUpdate(BaseModel):
    show_id: Optional[int] = Field(default=None, gt=0)
    season_id: Optional[int] = Field(default=None, gt=0)
    episode_number: Optional[int] = Field(default=None, ge=0)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    synopsis: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    language: Optional[str] = Field(default=None, min_length=1, max_length=10)
    content_group: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[ContentStatus] = None

    @field_validator("language")
    @classmethod
    def language_is_known(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in allowed_languages():
            raise ValueError("language must be one of: " + ", ".join(sorted(allowed_languages())))
        return value


class EpisodeResponse(EpisodeFields):
    id: str
    artwork_types: list[ArtworkType] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EpisodePage(Page):
    items: list[EpisodeResponse]

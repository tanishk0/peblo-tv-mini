"""Structured CMS response models for pre-publish validation."""
from typing import Literal

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    field: str
    message: str
    action: Literal["editor", "engineering"] = "editor"


class EpisodeValidationReport(BaseModel):
    episode_id: str
    episode_title: str
    issues: list[ValidationIssue]


class ShowValidationReport(BaseModel):
    show_id: int
    show_title: str
    issues: list[ValidationIssue]
    episodes: list[EpisodeValidationReport]


class DataQualityIssue(BaseModel):
    show_id: int | None
    show_title: str
    episode_id: str
    episode_title: str
    message: str
    action: Literal["engineering"] = "engineering"


class ValidationReport(BaseModel):
    can_publish: bool
    total_issues: int
    shows: list[ShowValidationReport]
    data_quality_issues: list[DataQualityIssue] = []

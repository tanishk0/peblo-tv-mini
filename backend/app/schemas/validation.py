"""Structured CMS response models for pre-publish validation."""
from pydantic import BaseModel


class ValidationIssue(BaseModel):
    field: str
    message: str


class EpisodeValidationReport(BaseModel):
    episode_id: str
    episode_title: str
    issues: list[ValidationIssue]


class ShowValidationReport(BaseModel):
    show_id: int
    show_title: str
    issues: list[ValidationIssue]
    episodes: list[EpisodeValidationReport]


class ValidationReport(BaseModel):
    can_publish: bool
    total_issues: int
    shows: list[ShowValidationReport]

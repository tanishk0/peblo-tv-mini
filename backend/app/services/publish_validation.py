"""Shared publish-readiness rules for CMS writes and validation reports."""
from app.models.enums import ContentStatus
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.services.reference import allowed_categories, allowed_languages, allowed_sections, required_artwork_types


def is_published(status: ContentStatus | str) -> bool:
    return status == ContentStatus.PUBLISHED or status == ContentStatus.PUBLISHED.value


def show_publish_issues(show: Show) -> list[dict[str, str]]:
    """Return all editor-readable blockers for one published show."""
    if not is_published(show.status):
        return []

    issues: list[dict[str, str]] = []
    if not show.section:
        issues.append({"field": "section", "message": "Published show requires a section."})
    elif show.section not in allowed_sections():
        issues.append({"field": "section", "message": f"Section '{show.section}' is not allowed for published shows."})

    if not isinstance(show.categories, list):
        issues.append({"field": "categories", "message": "Categories must be a list of approved categories."})
    else:
        invalid = sorted({str(category) for category in show.categories if not isinstance(category, str) or category not in allowed_categories()})
        if invalid:
            issues.append({"field": "categories", "message": "Invalid categories: " + ", ".join(invalid) + "."})
    return issues


def episode_publish_issues(episode: Episode, season: Season | None = None) -> list[dict[str, str]]:
    """Return all editor-readable blockers for one published episode."""
    if not is_published(episode.status):
        return []

    issues: list[dict[str, str]] = []
    if not episode.duration_seconds or episode.duration_seconds <= 0:
        issues.append({"field": "duration_seconds", "message": "Published episode requires a duration."})
    if episode.language not in allowed_languages():
        issues.append({"field": "language", "message": f"Language '{episode.language}' is not supported."})

    present = {artwork.type.value if hasattr(artwork.type, "value") else artwork.type for artwork in episode.artworks}
    missing = sorted(required_artwork_types() - present)
    if missing:
        issues.append({"field": "artwork", "message": "Published episode requires artwork: " + ", ".join(missing) + "."})

    if season is None:
        issues.append({"field": "season_id", "message": "Episode references a season that no longer exists."})
    elif season.show_id != episode.show_id:
        issues.append({"field": "season_id", "message": "Episode season belongs to a different show."})
    return issues

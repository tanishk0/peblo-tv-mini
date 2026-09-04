import enum


class UserRole(str, enum.Enum):
    """User access roles."""
    EDITOR = "editor"
    ADMIN = "admin"


class ContentStatus(str, enum.Enum):
    """Publication statuses for shows and episodes."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ArtworkType(str, enum.Enum):
    """Supported artwork variants per challenge specifications."""
    POSTER = "poster"
    BANNER = "banner"
    THUMBNAIL = "thumbnail"


class PublishRunStatus(str, enum.Enum):
    """Execution status for catalog publishing runs."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

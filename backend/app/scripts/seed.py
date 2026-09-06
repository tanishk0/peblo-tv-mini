"""Idempotently load the supplied catalogue fixture for local Docker use."""
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models import Artwork, ArtworkType, ContentStatus, Episode, Season, SeedImportIssue, Show, User, UserRole
from app.services.reference import reference_data
from app.services.storage import LocalStorageProvider


SEED_PATH = Path(__file__).resolve().parents[1] / "api" / "v1" / "files" / "seed_shows.json"
SEED_ARTWORK_FILENAMES = {
    "poster": "poster_good.jpg",
    "banner": "banner_good.jpg",
    "thumbnail": "thumb_good.jpg",
}


def content_status(value: str) -> ContentStatus:
    return ContentStatus(value)


def seed_users(db) -> None:
    users = (("admin@peblo.tv", "admin123", UserRole.ADMIN), ("editor@peblo.tv", "editor123", UserRole.EDITOR))
    for email, password, role in users:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, password_hash=get_password_hash(password), role=role))


def seed_catalogue(db) -> None:
    records = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    storage = LocalStorageProvider()
    shows: dict[str, Show] = {}
    for record in records:
        show = shows.get(record["slug"]) or db.query(Show).filter(Show.slug == record["slug"]).first()
        if not show:
            show = Show(
                title=record["show_title"], slug=record["slug"], synopsis=record.get("synopsis"),
                section=record.get("section"), categories=record.get("categories", []),
                status=content_status(record["status"]),
            )
            db.add(show)
            db.flush()
        shows[record["slug"]] = show
        season = db.query(Season).filter(Season.show_id == show.id, Season.season_number == record["season_number"]).first()
        if not season:
            season = Season(show_id=show.id, season_number=record["season_number"])
            db.add(season)
            db.flush()
        episode = db.get(Episode, record["episode_id"])
        # The supplied fixture contains one deliberately inconsistent duplicate
        # content-group/language variant.  Keep the database constraint intact
        # and use the first valid variant rather than making container startup
        # fail on seed data that cannot exist in the application schema.
        if not episode:
            episode = (
                db.query(Episode)
                .filter(
                    Episode.content_group == record["content_group"],
                    Episode.language == record["language"],
                )
                .first()
            )
            if episode:
                record_seed_import_issue(db, record)
        if not episode:
            episode = Episode(
                id=record["episode_id"], show_id=show.id, season_id=season.id,
                episode_number=record["episode_number"], title=record["episode_title"],
                synopsis=record.get("synopsis"), duration_seconds=record.get("duration_seconds"),
                language=record["language"], content_group=record["content_group"],
                status=content_status(record["status"]),
            )
            db.add(episode)
            db.flush()
        for artwork_name in record.get("artwork_available", []):
            artwork_type = ArtworkType(artwork_name)
            storage_key = f"seed/{episode.id}/{artwork_name}.jpg"
            content, width, height = seed_artwork(artwork_name)
            artwork = db.query(Artwork).filter(Artwork.episode_id == episode.id, Artwork.type == artwork_type).first()
            if not artwork:
                artwork = Artwork(
                    episode_id=episode.id, type=artwork_type,
                    storage_key=storage_key, width=width, height=height, file_size_bytes=len(content),
                )
                db.add(artwork)
            else:
                artwork.storage_key = storage_key
                artwork.width = width
                artwork.height = height
                artwork.file_size_bytes = len(content)
            storage.save(content, storage_key)


def record_seed_import_issue(db, record: dict) -> None:
    """Expose fixture rows rejected by the database's uniqueness invariant.

    The source contains a duplicate (content_group, language) row.  It must not
    be inserted into ``episodes`` because that would undermine the production
    constraint, but it must also never disappear silently from seed validation.
    """
    language = {"en": "English", "hi": "Hindi"}.get(record["language"], record["language"])
    message = (
        f"Two {language} versions of “{record['episode_title']}” were provided for the same episode. "
        "One version is not available in the CMS. Ask engineering to restore and reconcile the source record, "
        "then confirm which version to keep."
    )
    issue = db.query(SeedImportIssue).filter(SeedImportIssue.source_episode_id == record["episode_id"]).first()
    if issue:
        issue.message = message
        return
    db.add(SeedImportIssue(source_episode_id=record["episode_id"], show_slug=record["slug"], message=message))


def seed_artwork(artwork_type: str) -> tuple[bytes, int, int]:
    """Read and verify the supplied valid demo asset before storing it."""
    source = settings.seed_assets_path / SEED_ARTWORK_FILENAMES[artwork_type]
    try:
        content = source.read_bytes()
        image = Image.open(BytesIO(content))
        image.load()
    except (OSError, ValueError) as error:
        raise RuntimeError(f"Missing or invalid seed artwork: {source}") from error
    width, height = image.size
    expected_width, expected_height = reference_data()["artwork_specs"][artwork_type]["target_px"]
    if (width, height) != (expected_width, expected_height):
        raise RuntimeError(f"Seed artwork {source.name} does not meet the {artwork_type} specification")
    return content, width, height


def main() -> None:
    db = SessionLocal()
    try:
        seed_users(db)
        seed_catalogue(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

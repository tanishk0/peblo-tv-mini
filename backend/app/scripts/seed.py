"""Idempotently load the supplied catalogue fixture for local Docker use."""
import json
from pathlib import Path

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models import Artwork, ArtworkType, ContentStatus, Episode, Season, Show, User, UserRole


SEED_PATH = Path(__file__).resolve().parents[1] / "api" / "v1" / "files" / "seed_shows.json"


def content_status(value: str) -> ContentStatus:
    return ContentStatus(value)


def seed_users(db) -> None:
    users = (("admin@peblo.tv", "admin123", UserRole.ADMIN), ("editor@peblo.tv", "editor123", UserRole.EDITOR))
    for email, password, role in users:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, password_hash=get_password_hash(password), role=role))


def seed_catalogue(db) -> None:
    records = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    shows: dict[str, Show] = {}
    for record in records:
        show = shows.get(record["slug"]) or db.query(Show).filter(Show.slug == record["slug"]).first()
        if not show:
            show = Show(
                title=record["show_title"], slug=record["slug"], synopsis=record.get("synopsis"),
                section=record.get("section"), categories=record.get("categories", []),
                status=ContentStatus.PUBLISHED if record["status"] == "published" else ContentStatus.DRAFT,
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
            if not db.query(Artwork).filter(Artwork.episode_id == episode.id, Artwork.type == artwork_type).first():
                db.add(Artwork(
                    episode_id=episode.id, type=artwork_type,
                    storage_key=f"seed/{episode.id}/{artwork_name}.jpg", width=1, height=1, file_size_bytes=0,
                ))


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

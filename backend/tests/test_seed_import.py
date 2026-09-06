"""Regression checks for deliberately imperfect supplied seed data."""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Artwork, ArtworkType, ContentStatus, Episode, SeedImportIssue
from app.scripts import seed
from app.services.storage import LocalStorageProvider
from app.services.validation import ValidationService


def test_seed_preserves_artwork_state_and_surfaces_unimportable_duplicate(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(seed, "LocalStorageProvider", lambda: LocalStorageProvider(root=Path(tmp_path) / "artwork"))
    db = Session()
    try:
        seed.seed_catalogue(db)
        db.commit()

        # 95 source rows include one duplicate content_group/language pair that
        # the real database invariant correctly rejects rather than rewriting.
        assert db.query(Episode).count() == 94
        assert db.query(Episode).filter(Episode.status == ContentStatus.PUBLISHED).count() == 84
        assert db.query(Episode).filter(Episode.status == ContentStatus.DRAFT).count() == 10
        assert db.get(Episode, "ep_9001") is None

        assert [asset.type.value for asset in db.get(Episode, "ep_0036").artworks] == []
        assert [asset.type.value for asset in db.get(Episode, "ep_0093").artworks] == ["thumbnail"]
        assert [asset.type.value for asset in db.get(Episode, "ep_0094").artworks] == ["thumbnail"]
        assert db.query(Artwork).count() == 275

        source_issue = db.query(SeedImportIssue).one()
        assert source_issue.source_episode_id == "ep_9001"
        report = ValidationService(db).report()
        assert report["can_publish"] is False
        assert report["total_issues"] == 3
        blocker_ids = {
            episode["episode_id"]
            for show in report["shows"]
            for episode in show["episodes"]
        }
        assert blocker_ids == {"ep_0036", "ep_0093", "ep_0094"}
        duplicate_issue = report["data_quality_issues"][0]
        assert duplicate_issue["action"] == "engineering"
        assert "Two Hindi versions" in duplicate_issue["message"]
        assert "content_group" not in duplicate_issue["message"]
        assert "seed row" not in duplicate_issue["message"]

        for episode_id in ("ep_0036", "ep_0093", "ep_0094"):
            existing = {asset.type for asset in db.get(Episode, episode_id).artworks}
            db.add_all([
                Artwork(episode_id=episode_id, type=kind, storage_key=f"manual/{episode_id}/{kind.value}.jpg", width=1, height=1, file_size_bytes=1)
                for kind in ArtworkType
                if kind not in existing
            ])
        db.commit()
        resolved_report = ValidationService(db).report()
        assert resolved_report["can_publish"] is True
        assert resolved_report["total_issues"] == 0
        assert len(resolved_report["data_quality_issues"]) == 1
    finally:
        db.close()

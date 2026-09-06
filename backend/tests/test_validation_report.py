import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import get_password_hash
from app.db.base import Base
from app.main import app
from app.models.artwork import Artwork
from app.models.enums import ArtworkType, ContentStatus, UserRole
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.models.user import User


@pytest.fixture
def validation_client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    seed = TestingSession()
    seed.add_all([
        User(email="editor@peblo.tv", password_hash=get_password_hash("editor123"), role=UserRole.EDITOR),
        User(email="admin@peblo.tv", password_hash=get_password_hash("admin123"), role=UserRole.ADMIN),
    ])
    seed.commit()
    seed.close()

    def database_override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = database_override
    with TestClient(app) as client:
        yield client, TestingSession
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def headers(client, email="admin@peblo.tv", password="admin123"):
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def published_episode(db, show: Show, *, episode_id="ep-1", duration=60, language="en", artworks=True):
    season = Season(show_id=show.id, season_number=1)
    db.add(season)
    db.flush()
    episode = Episode(
        id=episode_id, show_id=show.id, season_id=season.id, episode_number=1,
        title="A Kite", duration_seconds=duration, language=language,
        content_group=episode_id, status=ContentStatus.PUBLISHED,
    )
    db.add(episode)
    if artworks:
        db.add_all([
            Artwork(episode_id=episode_id, type=kind, storage_key=f"{episode_id}/{kind.value}.png", width=1, height=1, file_size_bytes=1)
            for kind in ArtworkType
        ])
    return episode


def test_admin_gets_clean_report_for_a_valid_published_dataset(validation_client):
    client, Session = validation_client
    db = Session()
    show = Show(title="Moti", slug="moti", section="featured", categories=["adventure"], status=ContentStatus.PUBLISHED)
    db.add(show)
    db.flush()
    published_episode(db, show)
    db.commit()
    db.close()

    response = client.get("/api/v1/admin/validation-report", headers=headers(client))
    assert response.status_code == 200
    assert response.json() == {"can_publish": True, "total_issues": 0, "shows": [], "data_quality_issues": []}


def test_report_groups_all_show_and_episode_problems(validation_client):
    client, Session = validation_client
    db = Session()
    show = Show(title="Broken Show", slug="broken-show", section=None, categories=["not-approved"], status=ContentStatus.PUBLISHED)
    db.add(show)
    db.flush()
    published_episode(db, show, episode_id="ep-broken", duration=None, language="fr", artworks=False)
    db.commit()
    db.close()

    report = client.get("/api/v1/admin/validation-report", headers=headers(client)).json()
    assert report["can_publish"] is False
    assert report["total_issues"] == 5  # show section/category + episode duration/language/artwork
    assert len(report["shows"]) == 1
    show_report = report["shows"][0]
    assert show_report["show_title"] == "Broken Show"
    assert {issue["field"] for issue in show_report["issues"]} == {"section", "categories"}
    assert show_report["episodes"][0]["episode_id"] == "ep-broken"
    assert {issue["field"] for issue in show_report["episodes"][0]["issues"]} == {"duration_seconds", "language", "artwork"}


def test_missing_artwork_and_duration_are_separate_episode_issues(validation_client):
    client, Session = validation_client
    db = Session()
    show = Show(title="Moti", slug="moti", section="featured", categories=[], status=ContentStatus.PUBLISHED)
    db.add(show)
    db.flush()
    published_episode(db, show, duration=None, artworks=False)
    db.commit()
    db.close()

    episode_issues = client.get("/api/v1/admin/validation-report", headers=headers(client)).json()["shows"][0]["episodes"][0]["issues"]
    assert {issue["field"] for issue in episode_issues} == {"duration_seconds", "artwork"}


def test_validation_report_is_admin_only(validation_client):
    client, _ = validation_client
    assert client.get("/api/v1/admin/validation-report").status_code == 401
    editor = client.get("/api/v1/admin/validation-report", headers=headers(client, "editor@peblo.tv", "editor123"))
    assert editor.status_code == 403
    assert client.get("/api/v1/admin/validation-report", headers=headers(client)).status_code == 200

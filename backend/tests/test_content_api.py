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
from app.models.enums import ArtworkType, UserRole
from app.models.user import User


@pytest.fixture
def cms_client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    session.add_all([
        User(email="editor@peblo.tv", password_hash=get_password_hash("editor123"), role=UserRole.EDITOR),
        User(email="admin@peblo.tv", password_hash=get_password_hash("admin123"), role=UserRole.ADMIN),
    ])
    session.commit()
    session.close()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, Session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def headers(client, email="editor@peblo.tv", password="editor123"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def create_show(client, auth):
    return client.post("/api/v1/shows", headers=auth, json={"title": "Moti", "slug": "moti", "categories": ["adventure"]})


def test_content_crud_is_editor_authorized_and_paginated(cms_client):
    client, _ = cms_client
    assert client.get("/api/v1/shows").status_code == 401
    auth = headers(client)
    show = create_show(client, auth)
    assert show.status_code == 201
    show_id = show.json()["id"]
    assert client.get("/api/v1/shows?limit=1", headers=auth).json()["total"] == 1

    season = client.post(f"/api/v1/shows/{show_id}/seasons", headers=auth, json={"season_number": 1})
    assert season.status_code == 201
    season_id = season.json()["id"]
    episode = client.post("/api/v1/episodes", headers=auth, json={
        "id": "ep-moti-1", "show_id": show_id, "season_id": season_id, "episode_number": 1,
        "title": "Kite", "language": "en", "content_group": "moti-s01e01",
    })
    assert episode.status_code == 201
    assert client.get("/api/v1/episodes?show_id=" + str(show_id), headers=auth).json()["total"] == 1
    assert client.delete("/api/v1/episodes/ep-moti-1", headers=auth).status_code == 204


def test_reference_and_publish_validation(cms_client):
    client, Session = cms_client
    auth = headers(client)
    assert client.post("/api/v1/shows", headers=auth, json={"title": "Bad", "slug": "bad", "categories": ["not-a-category"]}).status_code == 422
    assert client.post("/api/v1/shows", headers=auth, json={"title": "Published", "slug": "published", "status": "published"}).status_code == 422
    show_id = create_show(client, auth).json()["id"]
    season_id = client.post(f"/api/v1/shows/{show_id}/seasons", headers=auth, json={"season_number": 1}).json()["id"]
    invalid_language = client.post("/api/v1/episodes", headers=auth, json={
        "show_id": show_id, "season_id": season_id, "episode_number": 1, "title": "Kite", "language": "fr", "content_group": "moti-s01e01",
    })
    assert invalid_language.status_code == 422
    episode = client.post("/api/v1/episodes", headers=auth, json={
        "id": "ep-publish", "show_id": show_id, "season_id": season_id, "episode_number": 1, "title": "Kite", "language": "en", "content_group": "moti-s01e01",
    })
    assert episode.status_code == 201
    assert client.patch("/api/v1/episodes/ep-publish", headers=auth, json={"status": "published", "duration_seconds": 20}).status_code == 422

    db = Session()
    db.add_all([Artwork(episode_id="ep-publish", type=kind, storage_key=f"{kind.value}.jpg", width=1, height=1, file_size_bytes=1) for kind in ArtworkType])
    db.commit()
    db.close()
    published = client.patch("/api/v1/episodes/ep-publish", headers=auth, json={"status": "published", "duration_seconds": 20})
    assert published.status_code == 200
    assert {item for item in published.json()["artwork_types"]} == {"poster", "banner", "thumbnail"}


def test_episode_must_belong_to_the_given_show(cms_client):
    client, _ = cms_client
    auth = headers(client, "admin@peblo.tv", "admin123")
    first_show = create_show(client, auth).json()["id"]
    second_show = client.post("/api/v1/shows", headers=auth, json={"title": "Other", "slug": "other"}).json()["id"]
    season_id = client.post(f"/api/v1/shows/{first_show}/seasons", headers=auth, json={"season_number": 1}).json()["id"]
    response = client.post("/api/v1/episodes", headers=auth, json={
        "show_id": second_show, "season_id": season_id, "episode_number": 1, "title": "Mismatch", "language": "en", "content_group": "other-s01e01",
    })
    assert response.status_code == 422
    assert "belong" in response.json()["detail"]

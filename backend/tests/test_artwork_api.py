from io import BytesIO
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.v1.endpoints.artwork import get_storage_provider
from app.core.security import get_password_hash
from app.db.base import Base
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.services.storage import LocalStorageProvider


@pytest.fixture
def artwork_client(tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    seed = TestingSession()
    seed.add(User(email="editor@peblo.tv", password_hash=get_password_hash("editor123"), role=UserRole.EDITOR))
    seed.commit()
    seed.close()

    def database_override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    provider = LocalStorageProvider(root=tmp_path, url_prefix="/test-artwork")
    app.dependency_overrides[get_db] = database_override
    app.dependency_overrides[get_storage_provider] = lambda: provider
    with TestClient(app) as client:
        yield client, TestingSession, provider
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers(client):
    login = client.post("/api/v1/auth/login", json={"email": "editor@peblo.tv", "password": "editor123"})
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def image_bytes(width: int, height: int, *, noisy: bool = False) -> bytes:
    image = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)) if noisy else Image.new("RGB", (width, height), "blue")
    result = BytesIO()
    image.save(result, format="PNG")
    return result.getvalue()


def episode_id(client, headers):
    show = client.post("/api/v1/shows", headers=headers, json={"title": "Moti", "slug": "moti", "categories": ["adventure"]})
    show_id = show.json()["id"]
    season = client.post(f"/api/v1/shows/{show_id}/seasons", headers=headers, json={"season_number": 1})
    response = client.post("/api/v1/episodes", headers=headers, json={
        "id": "ep-artwork", "show_id": show_id, "season_id": season.json()["id"],
        "episode_number": 1, "title": "Kite", "language": "en", "content_group": "moti-s01e01",
    })
    assert response.status_code == 201
    return "ep-artwork"


@pytest.mark.parametrize(("artwork_type", "dimensions"), [
    ("poster", (600, 900)), ("banner", (1280, 720)), ("thumbnail", (640, 360)),
])
def test_uploads_each_valid_artwork_type(artwork_client, artwork_type, dimensions):
    client, _, provider = artwork_client
    headers = auth_headers(client)
    episode = episode_id(client, headers)
    response = client.post(
        f"/api/v1/episodes/{episode}/artwork", headers=headers,
        data={"artwork_type": artwork_type}, files={"file": ("image.png", image_bytes(*dimensions), "image/png")},
    )
    assert response.status_code == 201
    result = response.json()
    assert (result["width"], result["height"]) == dimensions
    assert (provider.root / result["storage_key"]).is_file()


def test_artwork_upload_requires_authenticated_cms_user(artwork_client):
    client, _, _ = artwork_client
    response = client.post(
        "/api/v1/episodes/not-an-episode/artwork",
        data={"artwork_type": "poster"},
        files={"file": ("poster.png", image_bytes(600, 900), "image/png")},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_rejects_large_or_invalid_images_with_editor_friendly_errors(artwork_client):
    client, _, _ = artwork_client
    headers = auth_headers(client)
    episode = episode_id(client, headers)
    too_large = client.post(f"/api/v1/episodes/{episode}/artwork", headers=headers, data={"artwork_type": "poster"}, files={"file": ("large.png", image_bytes(600, 900, noisy=True), "image/png")})
    assert too_large.status_code == 422
    assert "200 KB" in too_large.json()["detail"]

    wrong_dimensions = client.post(f"/api/v1/episodes/{episode}/artwork", headers=headers, data={"artwork_type": "banner"}, files={"file": ("small.png", image_bytes(800, 450), "image/png")})
    assert wrong_dimensions.status_code == 422
    assert "1280×720" in wrong_dimensions.json()["detail"]

    wrong_aspect = client.post(f"/api/v1/episodes/{episode}/artwork", headers=headers, data={"artwork_type": "banner"}, files={"file": ("square.png", image_bytes(800, 800), "image/png")})
    assert wrong_aspect.status_code == 422
    assert "16:9" in wrong_aspect.json()["detail"]

    invalid_type = client.post(f"/api/v1/episodes/{episode}/artwork", headers=headers, data={"artwork_type": "avatar"}, files={"file": ("image.png", image_bytes(600, 900), "image/png")})
    assert invalid_type.status_code == 422
    assert invalid_type.json()["detail"] == "Choose poster, banner, or thumbnail artwork."


def test_duplicate_type_is_rejected_without_creating_another_file(artwork_client):
    client, _, provider = artwork_client
    headers = auth_headers(client)
    episode = episode_id(client, headers)
    upload = lambda: client.post(f"/api/v1/episodes/{episode}/artwork", headers=headers, data={"artwork_type": "poster"}, files={"file": ("poster.png", image_bytes(600, 900), "image/png")})
    assert upload().status_code == 201
    duplicate = upload()
    assert duplicate.status_code == 409
    assert "already has poster" in duplicate.json()["detail"]
    assert len(list(provider.root.rglob("*.*"))) == 1


def test_database_failure_removes_stored_file(artwork_client, monkeypatch):
    client, _, provider = artwork_client
    headers = auth_headers(client)
    episode = episode_id(client, headers)

    def fail_commit(self):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post(f"/api/v1/episodes/{episode}/artwork", headers=headers, data={"artwork_type": "poster"}, files={"file": ("poster.png", image_bytes(600, 900), "image/png")})
    assert response.status_code == 500
    assert not list(provider.root.rglob("*.*"))

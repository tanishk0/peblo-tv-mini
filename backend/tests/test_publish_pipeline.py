import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.v1.endpoints.admin import get_catalogue_storage
from app.core.security import get_password_hash
from app.db.base import Base
from app.main import app
from app.models.artwork import Artwork
from app.models.enums import ArtworkType, ContentStatus, PublishRunStatus, UserRole
from app.models.episode import Episode
from app.models.publish_run import PublishRun
from app.models.season import Season
from app.models.show import Show
from app.models.user import User
from app.services.catalogue_storage import LocalCatalogueStorageProvider


@pytest.fixture
def publish_client(tmp_path):
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

    storage = LocalCatalogueStorageProvider(root=tmp_path / "catalogues")
    app.dependency_overrides[get_db] = database_override
    app.dependency_overrides[get_catalogue_storage] = lambda: storage
    with TestClient(app) as client:
        yield client, TestingSession, storage
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def headers(client, email="admin@peblo.tv", password="admin123"):
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def add_artwork(db, episode_id):
    db.add_all([
        Artwork(episode_id=episode_id, type=kind, storage_key=f"assets/{episode_id}-{kind.value}.png", width=600, height=900, file_size_bytes=100)
        for kind in ArtworkType
    ])


def add_episode(db, show, season, *, episode_id, group, language="en", status=ContentStatus.PUBLISHED, number=1):
    episode = Episode(
        id=episode_id, show_id=show.id, season_id=season.id, episode_number=number,
        title=f"Title {group}", synopsis="Episode synopsis", duration_seconds=120,
        language=language, content_group=group, status=status,
    )
    db.add(episode)
    if status == ContentStatus.PUBLISHED:
        add_artwork(db, episode_id)
    return episode


def seed_publishable_data(session):
    featured = Show(title="Zebra Show", slug="zebra-show", synopsis="Show synopsis", section="featured", categories=["music", "adventure"], status=ContentStatus.PUBLISHED)
    series = Show(title="Alpha Show", slug="alpha-show", section="series", categories=["stories"], status=ContentStatus.PUBLISHED)
    draft = Show(title="Draft Show", slug="draft-show", section="featured", categories=[], status=ContentStatus.DRAFT)
    session.add_all([featured, series, draft])
    session.flush()
    featured_s1 = Season(show_id=featured.id, season_number=1)
    featured_s0 = Season(show_id=featured.id, season_number=0)
    series_s1 = Season(show_id=series.id, season_number=1)
    draft_s1 = Season(show_id=draft.id, season_number=1)
    session.add_all([featured_s1, featured_s0, series_s1, draft_s1])
    session.flush()
    add_episode(session, featured, featured_s1, episode_id="ep-en", group="zebra-s01e01", language="en")
    add_episode(session, featured, featured_s1, episode_id="ep-hi", group="zebra-s01e01", language="hi")
    add_episode(session, featured, featured_s0, episode_id="ep-trailer", group="zebra-trailer", number=0)
    add_episode(session, featured, featured_s1, episode_id="ep-draft", group="zebra-draft", status=ContentStatus.DRAFT, number=2)
    add_episode(session, series, series_s1, episode_id="ep-series", group="alpha-s01e01")
    add_episode(session, draft, draft_s1, episode_id="ep-hidden", group="draft-s01e01")
    featured_id = featured.id
    session.commit()
    return featured_id


def test_catalogue_filters_groups_collapses_and_orders_content(publish_client):
    client, Session, storage = publish_client
    db = Session()
    seed_publishable_data(db)
    db.close()

    response = client.post("/api/v1/admin/catalog/publish", headers=headers(client))
    assert response.status_code == 201
    catalogue = storage.read_current()
    assert [section["id"] for section in catalogue["sections"]] == ["featured", "series"]
    featured = catalogue["sections"][0]["shows"][0]
    assert featured["slug"] == "zebra-show"
    assert featured["categories"] == ["adventure", "music"]
    assert len(featured["seasons"][0]["episodes"]) == 1
    entry = featured["seasons"][0]["episodes"][0]
    assert entry["content_group"] == "zebra-s01e01"
    assert [variant["language"] for variant in entry["languages"]] == ["en", "hi"]
    assert {"poster", "banner", "thumbnail"} == set(entry["languages"][0]["artwork"])
    assert featured["trailers"][0]["content_group"] == "zebra-trailer"
    assert "season_number" not in featured["trailers"][0]
    assert response.json()["episode_count"] == 4


def test_validation_blocks_publish_and_records_failed_run(publish_client):
    client, Session, storage = publish_client
    db = Session()
    show = Show(title="Broken", slug="broken", section=None, categories=[], status=ContentStatus.PUBLISHED)
    db.add(show)
    db.commit()
    db.close()

    response = client.post("/api/v1/admin/catalog/publish", headers=headers(client))
    assert response.status_code == 422
    assert response.json()["detail"]["validation_report"]["can_publish"] is False
    assert storage.read_current() is None
    db = Session()
    run = db.query(PublishRun).one()
    assert run.status == PublishRunStatus.FAILED
    assert "blocked" in run.error_message
    db.close()


def test_admin_only_and_successful_publish_is_idempotent(publish_client):
    client, Session, storage = publish_client
    db = Session()
    seed_publishable_data(db)
    db.close()
    assert client.post("/api/v1/admin/catalog/publish").status_code == 401
    assert client.post("/api/v1/admin/catalog/publish", headers=headers(client, "editor@peblo.tv", "editor123")).status_code == 403

    first = client.post("/api/v1/admin/catalog/publish", headers=headers(client))
    second = client.post("/api/v1/admin/catalog/publish", headers=headers(client))
    assert first.status_code == second.status_code == 201
    assert first.json()["catalogue_version"] == second.json()["catalogue_version"]
    assert len(list(storage.root.glob("catalogue_*.json"))) == 1
    db = Session()
    assert [run.status for run in db.query(PublishRun).order_by(PublishRun.id)] == [PublishRunStatus.SUCCESS, PublishRunStatus.SUCCESS]
    db.close()


def test_successful_publish_atomically_switches_to_a_new_complete_snapshot(publish_client):
    client, Session, storage = publish_client
    db = Session()
    show_id = seed_publishable_data(db)
    db.close()
    first = client.post("/api/v1/admin/catalog/publish", headers=headers(client))
    assert first.status_code == 201
    first_version = first.json()["catalogue_version"]
    previous_file = storage.root / f"catalogue_{first_version}.json"
    previous_snapshot = json.loads(previous_file.read_text(encoding="utf-8"))

    db = Session()
    db.get(Show, show_id).title = "New live title"
    db.commit()
    db.close()
    second = client.post("/api/v1/admin/catalog/publish", headers=headers(client))

    assert second.status_code == 201
    assert second.json()["catalogue_version"] != first_version
    assert storage.read_current()["sections"][0]["shows"][0]["title"] == "New live title"
    # The earlier immutable version remains complete; only current.json changed.
    assert json.loads(previous_file.read_text(encoding="utf-8")) == previous_snapshot


def test_failed_switch_preserves_previous_complete_catalogue_and_records_failure(publish_client):
    client, Session, storage = publish_client
    db = Session()
    show_id = seed_publishable_data(db)
    db.close()
    assert client.post("/api/v1/admin/catalog/publish", headers=headers(client)).status_code == 201
    previous = storage.read_current()

    db = Session()
    db.get(Show, show_id).title = "Changed after first publish"
    db.commit()
    db.close()

    class FailingSwitchStorage(LocalCatalogueStorageProvider):
        def switch_current(self, version, storage_key):
            raise OSError("disk failure")

    app.dependency_overrides[get_catalogue_storage] = lambda: FailingSwitchStorage(root=storage.root)
    response = client.post("/api/v1/admin/catalog/publish", headers=headers(client))
    assert response.status_code == 500
    assert storage.read_current() == previous
    db = Session()
    assert db.query(PublishRun).order_by(PublishRun.id).all()[-1].status == PublishRunStatus.FAILED
    db.close()


def test_local_storage_reader_sees_only_complete_previous_catalogue_on_failed_switch(tmp_path):
    storage = LocalCatalogueStorageProvider(root=tmp_path)
    first = b'{"sections":["old"]}'
    first_key = storage.write_version("v-old", first)
    storage.switch_current("v-old", first_key)
    assert storage.read_current() == {"sections": ["old"]}

    second_key = storage.write_version("v-new", b'{"sections":["new"]}')
    original_atomic_write = storage._atomic_write

    def fail_pointer(destination, payload):
        if destination.name == storage.CURRENT_POINTER:
            raise OSError("interrupted pointer update")
        original_atomic_write(destination, payload)

    storage._atomic_write = fail_pointer
    with pytest.raises(OSError):
        storage.switch_current("v-new", second_key)
    assert storage.read_current() == {"sections": ["old"]}

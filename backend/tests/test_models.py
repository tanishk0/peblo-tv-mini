import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import (
    Artwork,
    ArtworkType,
    ContentStatus,
    Episode,
    PublishRun,
    PublishRunStatus,
    Season,
    Show,
    User,
    UserRole,
)


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for model testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_user(db_session):
    """Verify user creation with defaults and uniqueness constraint."""
    user = User(
        email="editor@peblo.tv",
        password_hash="hashed_secret",
        role=UserRole.EDITOR,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "editor@peblo.tv"
    assert user.role == UserRole.EDITOR

    # Duplicate email should fail
    duplicate_user = User(
        email="editor@peblo.tv",
        password_hash="another_hash",
        role=UserRole.ADMIN,
    )
    db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_show_and_seasons_relationship(db_session):
    """Verify Show and Season relationship and season uniqueness per show."""
    show = Show(
        title="Moti's Many Lives",
        slug="motis-many-lives",
        synopsis="Moti travels India.",
        section="featured",
        categories=["adventure", "india"],
        status=ContentStatus.PUBLISHED,
    )
    db_session.add(show)
    db_session.commit()

    # Season 0 for trailers
    s0 = Season(show_id=show.id, season_number=0)
    s1 = Season(show_id=show.id, season_number=1)
    db_session.add_all([s0, s1])
    db_session.commit()

    db_session.refresh(show)
    assert len(show.seasons) == 2
    assert [s.season_number for s in show.seasons] == [0, 1]

    # Duplicate season number for same show must fail
    dup_s = Season(show_id=show.id, season_number=1)
    db_session.add(dup_s)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_episode_content_group_language_unique(db_session):
    """Verify UNIQUE(content_group, language) constraint on episodes."""
    show = Show(title="Test Show", slug="test-show", categories=[])
    db_session.add(show)
    db_session.commit()

    season = Season(show_id=show.id, season_number=1)
    db_session.add(season)
    db_session.commit()

    # Create English variant
    ep_en = Episode(
        id="ep_0001",
        show_id=show.id,
        season_id=season.id,
        episode_number=1,
        title="The Lost Kite",
        duration_seconds=510,
        language="en",
        content_group="test-show-s01e01",
        status=ContentStatus.PUBLISHED,
    )
    # Create Hindi variant of same content group
    ep_hi = Episode(
        id="ep_0002",
        show_id=show.id,
        season_id=season.id,
        episode_number=1,
        title="The Lost Kite",
        duration_seconds=480,
        language="hi",
        content_group="test-show-s01e01",
        status=ContentStatus.PUBLISHED,
    )
    db_session.add_all([ep_en, ep_hi])
    db_session.commit()

    assert len(season.episodes) == 2

    # Attempting to insert another Hindi variant for the same content_group must fail
    ep_hi_dup = Episode(
        id="ep_9001",
        show_id=show.id,
        season_id=season.id,
        episode_number=1,
        title="The Lost Kite v2",
        duration_seconds=490,
        language="hi",
        content_group="test-show-s01e01",
        status=ContentStatus.PUBLISHED,
    )
    db_session.add(ep_hi_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_artwork_unique_type_per_episode(db_session):
    """Verify artwork creation and UNIQUE(episode_id, type) constraint."""
    show = Show(title="Test Show 2", slug="test-show-2", categories=[])
    db_session.add(show)
    db_session.commit()

    season = Season(show_id=show.id, season_number=1)
    db_session.add(season)
    db_session.commit()

    episode = Episode(
        id="ep_0010",
        show_id=show.id,
        season_id=season.id,
        episode_number=1,
        title="Sample Ep",
        language="en",
        content_group="test-s01e01",
        status=ContentStatus.DRAFT,
    )
    db_session.add(episode)
    db_session.commit()

    poster = Artwork(
        episode_id=episode.id,
        type=ArtworkType.POSTER,
        storage_key="artworks/ep_0010_poster.jpg",
        width=600,
        height=900,
        file_size_bytes=150000,
    )
    banner = Artwork(
        episode_id=episode.id,
        type=ArtworkType.BANNER,
        storage_key="artworks/ep_0010_banner.jpg",
        width=1280,
        height=720,
        file_size_bytes=180000,
    )
    db_session.add_all([poster, banner])
    db_session.commit()

    db_session.refresh(episode)
    assert len(episode.artworks) == 2

    # Second poster for the same episode must violate unique constraint
    duplicate_poster = Artwork(
        episode_id=episode.id,
        type=ArtworkType.POSTER,
        storage_key="artworks/ep_0010_poster_2.jpg",
        width=600,
        height=900,
        file_size_bytes=160000,
    )
    db_session.add(duplicate_poster)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_publish_run_and_user_relationship(db_session):
    """Verify PublishRun creation and user relation with SET NULL on user delete."""
    admin_user = User(
        email="admin@peblo.tv",
        password_hash="secret_hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin_user)
    db_session.commit()

    run = PublishRun(
        triggered_by_user_id=admin_user.id,
        status=PublishRunStatus.SUCCESS,
        show_count=5,
        episode_count=45,
    )
    db_session.add(run)
    db_session.commit()

    db_session.refresh(admin_user)
    assert len(admin_user.publish_runs) == 1
    assert admin_user.publish_runs[0].status == PublishRunStatus.SUCCESS
    assert admin_user.publish_runs[0].show_count == 5

    # Delete user and verify publish_run is preserved with triggered_by_user_id = NULL
    run_id = run.id
    db_session.delete(admin_user)
    db_session.commit()

    refreshed_run = db_session.get(PublishRun, run_id)
    assert refreshed_run is not None
    assert refreshed_run.triggered_by_user_id is None
    assert refreshed_run.status == PublishRunStatus.SUCCESS

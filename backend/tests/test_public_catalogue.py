import json

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.v1.endpoints.catalog import get_public_catalogue_storage
from app.main import app
from app.services.catalogue_storage import LocalCatalogueStorageProvider


@pytest.fixture
def public_client(tmp_path):
    storage = LocalCatalogueStorageProvider(root=tmp_path / "catalogues")
    app.dependency_overrides[get_public_catalogue_storage] = lambda: storage
    with TestClient(app) as client:
        yield client, storage
    app.dependency_overrides.clear()


def snapshot():
    return {
        "schema_version": 1,
        "sections": [
            {
                "id": "featured",
                "shows": [{
                    "id": 1, "slug": "adventure-show", "title": "Adventure Show", "synopsis": "Explore together",
                    "categories": ["adventure", "music"],
                    "seasons": [{"season_number": 1, "episodes": [{
                        "content_group": "adventure-s01e01", "episode_number": 1, "title": "The Lost Kite", "synopsis": "Find it",
                        "languages": [
                            {"episode_id": "ep-en", "language": "en", "title": "The Lost Kite", "synopsis": "Find it", "duration_seconds": 120, "artwork": {}},
                            {"episode_id": "ep-hi", "language": "hi", "title": "Khoi Hui Patang", "synopsis": "Find it", "duration_seconds": 125, "artwork": {}},
                        ],
                    }]}],
                    "trailers": [],
                }],
            },
            {
                "id": "series",
                "shows": [{
                    "id": 2, "slug": "science-show", "title": "Science Stories", "synopsis": None, "categories": ["science"],
                    "seasons": [{"season_number": 1, "episodes": [{
                        "content_group": "science-s01e01", "episode_number": 1, "title": "Stars Above", "synopsis": None,
                        "languages": [{"episode_id": "ep-stars", "language": "en", "title": "Stars Above", "synopsis": None, "duration_seconds": 100, "artwork": {}}],
                    }]}],
                    "trailers": [],
                }],
            },
        ],
    }


def publish_snapshot(storage, content=None):
    content = content or snapshot()
    payload = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    key = storage.write_version("v-test", payload)
    storage.switch_current("v-test", key)
    return content


def test_catalog_returns_exact_current_snapshot_without_authentication(public_client):
    client, storage = public_client
    expected = publish_snapshot(storage)
    response = client.get("/api/v1/catalog")
    assert response.status_code == 200
    assert response.json() == expected


def test_catalog_returns_meaningful_error_before_first_publish(public_client):
    client, _ = public_client
    response = client.get("/api/v1/catalog")
    assert response.status_code == 404
    assert response.json()["detail"] == "No published catalogue is available yet."


def test_public_catalogue_never_uses_cms_database_or_unpublished_changes(public_client):
    client, storage = public_client
    published = publish_snapshot(storage)

    def forbidden_database_access():
        raise AssertionError("Public catalogue endpoint must not access CMS tables")

    app.dependency_overrides[get_db] = forbidden_database_access
    response = client.get("/api/v1/catalog")
    assert response.status_code == 200
    assert response.json() == published
    assert "Unpublished CMS title" not in response.text


@pytest.mark.parametrize("query, expected_slug", [
    ("adventure", "adventure-show"),       # show title and category, case-insensitive
    ("LOST KITE", "adventure-show"),       # episode title
    ("science", "science-show"),           # category and show title
])
def test_search_matches_show_episode_and_category_case_insensitively(public_client, query, expected_slug):
    client, storage = public_client
    publish_snapshot(storage)
    response = client.get("/api/v1/catalog/search", params={"q": query})
    assert response.status_code == 200
    assert response.json()["total_shows"] == 1
    assert response.json()["sections"][0]["shows"][0]["slug"] == expected_slug


def test_search_filters_are_composable_and_trim_language_variants(public_client):
    client, storage = public_client
    publish_snapshot(storage)
    response = client.get("/api/v1/catalog/search", params={"category": "ADVENTURE", "language": "hi", "section": "FEATURED"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_shows"] == body["total_entries"] == 1
    assert [section["id"] for section in body["sections"]] == ["featured"]
    variants = body["sections"][0]["shows"][0]["seasons"][0]["episodes"][0]["languages"]
    assert [variant["language"] for variant in variants] == ["hi"]


def test_search_section_category_language_and_empty_results(public_client):
    client, storage = public_client
    publish_snapshot(storage)
    section = client.get("/api/v1/catalog/search", params={"section": "series"}).json()
    assert section["sections"][0]["shows"][0]["slug"] == "science-show"
    category = client.get("/api/v1/catalog/search", params={"category": "music"}).json()
    assert category["sections"][0]["shows"][0]["slug"] == "adventure-show"
    language = client.get("/api/v1/catalog/search", params={"language": "hi"}).json()
    assert language["total_entries"] == 1
    empty = client.get("/api/v1/catalog/search", params={"q": "not present", "language": "hi"})
    assert empty.status_code == 200
    assert empty.json()["total_shows"] == empty.json()["total_entries"] == 0
    assert empty.json()["sections"] == []

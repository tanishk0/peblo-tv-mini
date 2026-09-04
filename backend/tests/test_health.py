from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_endpoint():
    """Verify that the primary GET /health endpoint returns 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "app" in data
    assert "environment" in data


def test_api_v1_health_endpoint():
    """Verify that the versioned GET /api/v1/health endpoint also returns 200 and status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "app" in data
    assert "environment" in data


def test_api_root_endpoint():
    """Verify that GET / returns welcome payload with documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data.get("health") == "/health"
    assert data.get("docs") == "/docs"

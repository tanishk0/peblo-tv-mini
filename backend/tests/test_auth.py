import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import get_password_hash
from app.db.base import Base
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture
def auth_client():
    """Create a test client with an in-memory SQLite database and pre-seeded users."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Seed an editor user and an admin user
    seed_session = TestingSessionLocal()
    editor_user = User(
        email="editor@peblo.tv",
        password_hash=get_password_hash("editor123"),
        role=UserRole.EDITOR,
    )
    admin_user = User(
        email="admin@peblo.tv",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
    )
    seed_session.add_all([editor_user, admin_user])
    seed_session.commit()
    seed_session.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_login_success(auth_client):
    """Verify that valid credentials return a JWT access token and user info."""
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "editor@peblo.tv", "password": "editor123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "editor@peblo.tv"
    assert data["user"]["role"] == "editor"


def test_login_invalid_password(auth_client):
    """Verify that invalid passwords are rejected with HTTP 401."""
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "editor@peblo.tv", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_email(auth_client):
    """Verify that non-existent accounts are rejected with HTTP 401."""
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "stranger@peblo.tv", "password": "anypassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_unauthenticated_request_rejected(auth_client):
    """Verify that unauthenticated requests to protected endpoints return HTTP 401."""
    # Attempting to read profile without token
    me_resp = auth_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 401
    assert me_resp.json()["detail"] == "Not authenticated"

    # Attempting admin endpoint without token
    admin_resp = auth_client.get("/api/v1/auth/admin-check")
    assert admin_resp.status_code == 401
    assert admin_resp.json()["detail"] == "Not authenticated"


def test_editor_denied_access_to_admin_endpoint(auth_client):
    """Verify that editors receive HTTP 403 Forbidden when accessing admin-only endpoints."""
    # Login as editor
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "editor@peblo.tv", "password": "editor123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Editor CAN access their own profile
    me_resp = auth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "editor@peblo.tv"

    # Editor is DENIED access to admin-only endpoint
    admin_resp = auth_client.get("/api/v1/auth/admin-check", headers=headers)
    assert admin_resp.status_code == 403
    assert "Admin access required" in admin_resp.json()["detail"]


def test_admin_allowed_access_to_admin_endpoint(auth_client):
    """Verify that admins are granted access (HTTP 200) to admin-only endpoints."""
    # Login as admin
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@peblo.tv", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Admin CAN access admin-only endpoint
    admin_resp = auth_client.get("/api/v1/auth/admin-check", headers=headers)
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert data["status"] == "ok"
    assert data["role"] == "admin"

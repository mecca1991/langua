import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture
def valid_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "user_metadata": {"full_name": "Test User", "avatar_url": "https://example.com/avatar.png"},
        "aud": "authenticated",
        "iss": f"https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def expired_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "expired@example.com",
        "user_metadata": {"full_name": "Expired User"},
        "aud": "authenticated",
        "iss": f"https://test.supabase.co/auth/v1",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://test.supabase.co")

    from app.core.config import Settings
    test_settings = Settings(
        supabase_jwt_secret=TEST_SECRET,
        supabase_project_url="https://test.supabase.co",
    )
    monkeypatch.setattr("app.core.auth.settings", test_settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_protected_route_without_token(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_valid_token(client, valid_token):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"


@pytest.mark.anyio
async def test_protected_route_with_expired_token(client, expired_token):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_invalid_token(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-string"},
    )
    assert response.status_code == 401

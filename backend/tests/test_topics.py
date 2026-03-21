import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture
def auth_headers():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "user_metadata": {"full_name": "Test User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


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
async def test_get_topics_for_japanese(client, auth_headers):
    response = await client.get("/topics?language=ja", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    topics = data["topics"]
    assert len(topics) == 5
    assert "Greetings" in topics
    assert "Ordering Food" in topics
    assert "Directions" in topics
    assert "Shopping" in topics
    assert "Travel" in topics


@pytest.mark.anyio
async def test_get_topics_defaults_to_japanese(client, auth_headers):
    response = await client.get("/topics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["topics"]) == 5


@pytest.mark.anyio
async def test_get_topics_unknown_language(client, auth_headers):
    response = await client.get("/topics?language=xx", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["topics"] == []

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.session import Session

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"
TEST_DATABASE_URL = "postgresql+asyncpg://langua:langua@localhost:5432/langua_test"


@pytest.fixture
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def auth_headers(user_id):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": "conv@example.com",
        "user_metadata": {"full_name": "Conv User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(monkeypatch, engine, session_factory):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://test.supabase.co")
    from app.core.config import Settings
    test_settings = Settings(
        SUPABASE_JWT_SECRET=TEST_SECRET,
        SUPABASE_PROJECT_URL="https://test.supabase.co",
        DATABASE_URL=TEST_DATABASE_URL,
    )
    monkeypatch.setattr("app.core.auth.settings", test_settings)
    monkeypatch.setattr("app.core.database.engine", engine)
    monkeypatch.setattr("app.core.database.async_session", session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_start_conversation_learn(client, auth_headers, user_id, session_factory):
    response = await client.post(
        "/conversation/start",
        headers=auth_headers,
        json={"language": "ja", "mode": "learn", "topic": "Greetings"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data

    async with session_factory() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Session).where(Session.id == uuid.UUID(data["session_id"]))
        )
        session = result.scalar_one()
        assert session.status == "active"
        assert session.mode == "learn"
        assert session.topic == "Greetings"
        assert session.user_id == user_id


@pytest.mark.anyio
async def test_start_conversation_quiz(client, auth_headers):
    response = await client.post(
        "/conversation/start",
        headers=auth_headers,
        json={"language": "ja", "mode": "quiz", "topic": "Ordering Food"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


@pytest.mark.anyio
async def test_start_conversation_invalid_mode(client, auth_headers):
    response = await client.post(
        "/conversation/start",
        headers=auth_headers,
        json={"language": "ja", "mode": "invalid", "topic": "Greetings"},
    )
    assert response.status_code == 422

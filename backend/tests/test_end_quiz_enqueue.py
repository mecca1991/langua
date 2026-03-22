import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.user import User
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
        "email": "enqueue@example.com",
        "user_metadata": {"full_name": "Enqueue User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def quiz_session(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="enqueue@example.com", name="Enqueue User")
        db.add(user)
        await db.flush()
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Ordering Food", status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id

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
async def test_end_quiz_enqueues_feedback_job(client, auth_headers, quiz_session):
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("app.api.conversation.get_arq_pool", return_value=mock_pool):
        response = await client.post(
            "/conversation/end",
            headers=auth_headers,
            json={"session_id": str(quiz_session)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_status"] == "pending"
        mock_pool.enqueue_job.assert_called_once_with(
            "generate_feedback", str(quiz_session)
        )

@pytest.mark.anyio
async def test_end_quiz_no_double_enqueue(client, auth_headers, quiz_session):
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("app.api.conversation.get_arq_pool", return_value=mock_pool):
        await client.post(
            "/conversation/end",
            headers=auth_headers,
            json={"session_id": str(quiz_session)},
        )
        response2 = await client.post(
            "/conversation/end",
            headers=auth_headers,
            json={"session_id": str(quiz_session)},
        )
        assert response2.status_code == 200
        assert mock_pool.enqueue_job.call_count == 1

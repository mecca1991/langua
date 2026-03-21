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
        "email": "feedback@example.com",
        "user_metadata": {"full_name": "Feedback User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def _create_user(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="feedback@example.com", name="Feedback User")
        db.add(user)
        await db.commit()


@pytest.fixture
async def pending_session(session_factory, user_id, _create_user):
    async with session_factory() as db:
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="pending",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
async def ready_session(session_factory, user_id, _create_user):
    async with session_factory() as db:
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="ready",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
async def failed_session(session_factory, user_id, _create_user):
    async with session_factory() as db:
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="failed",
            feedback_error="API timeout",
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
        supabase_jwt_secret=TEST_SECRET,
        supabase_project_url="https://test.supabase.co",
        database_url=TEST_DATABASE_URL,
    )
    monkeypatch.setattr("app.core.auth.settings", test_settings)
    monkeypatch.setattr("app.core.database.engine", engine)
    monkeypatch.setattr("app.core.database.async_session", session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_feedback_status_pending(client, auth_headers, pending_session):
    response = await client.get(
        f"/sessions/{pending_session}/feedback-status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["feedback_status"] == "pending"


@pytest.mark.anyio
async def test_feedback_status_ready(client, auth_headers, ready_session):
    response = await client.get(
        f"/sessions/{ready_session}/feedback-status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["feedback_status"] == "ready"


@pytest.mark.anyio
async def test_retry_feedback_on_failed(client, auth_headers, failed_session):
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("app.api.sessions.get_arq_pool", return_value=mock_pool):
        response = await client.post(
            f"/sessions/{failed_session}/retry-feedback",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "retrying"
        mock_pool.enqueue_job.assert_called_once_with(
            "generate_feedback", str(failed_session)
        )


@pytest.mark.anyio
async def test_retry_feedback_on_pending_returns_409(client, auth_headers, pending_session):
    response = await client.post(
        f"/sessions/{pending_session}/retry-feedback",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_retry_feedback_on_ready_returns_409(client, auth_headers, ready_session):
    response = await client.post(
        f"/sessions/{ready_session}/retry-feedback",
        headers=auth_headers,
    )
    assert response.status_code == 409

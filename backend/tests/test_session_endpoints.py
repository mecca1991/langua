import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.feedback import Feedback

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
        "email": "sessions@example.com",
        "user_metadata": {"full_name": "Sessions User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def sessions_with_data(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="sessions@example.com", name="Sessions User")
        db.add(user)
        await db.flush()

        s1 = Session(
            user_id=user_id, language="ja", mode="learn",
            topic="Greetings", status="ended",
        )
        s2 = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Ordering Food", status="ended",
            feedback_status="ready",
        )
        db.add_all([s1, s2])
        await db.flush()

        entry = TranscriptEntry(
            session_id=s1.id, idempotency_key=uuid.uuid4(),
            turn_index=0, role="user", text_en="Hello",
        )
        feedback = Feedback(
            session_id=s2.id,
            correct=["konnichiwa"],
            revisit=["sumimasen"],
            drills=["Practice greetings"],
        )
        db.add_all([entry, feedback])
        await db.commit()
        await db.refresh(s1)
        await db.refresh(s2)
        return s1.id, s2.id

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
async def test_list_sessions(client, auth_headers, sessions_with_data):
    response = await client.get("/sessions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert len(data["sessions"]) >= 2

@pytest.mark.anyio
async def test_list_sessions_pagination(client, auth_headers, sessions_with_data):
    response = await client.get("/sessions?limit=1&offset=0", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1

@pytest.mark.anyio
async def test_get_session_detail(client, auth_headers, sessions_with_data):
    learn_id, quiz_id = sessions_with_data
    response = await client.get(f"/sessions/{learn_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(learn_id)
    assert len(data["transcript"]) >= 1

@pytest.mark.anyio
async def test_get_session_with_feedback(client, auth_headers, sessions_with_data):
    _, quiz_id = sessions_with_data
    response = await client.get(f"/sessions/{quiz_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["feedback"]) >= 1
    assert "konnichiwa" in data["feedback"][0]["correct"]

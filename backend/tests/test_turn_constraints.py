import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.session import Session
from app.services.protocols import CoachResponse

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
        "email": "constraint@example.com",
        "user_metadata": {"full_name": "Constraint User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def active_session(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="constraint@example.com", name="Constraint User")
        db.add(user)
        await db.flush()
        session = Session(
            user_id=user_id, language="ja", mode="learn",
            topic="Greetings", status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
async def ended_session(session_factory, user_id):
    async with session_factory() as db:
        from sqlalchemy import select as sa_select
        existing = await db.execute(sa_select(User).where(User.id == user_id))
        if not existing.scalar_one_or_none():
            user = User(id=user_id, email="constraint@example.com", name="Constraint User")
            db.add(user)
            await db.flush()
        session = Session(
            user_id=user_id, language="ja", mode="learn",
            topic="Greetings", status="ended",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
def mock_stt():
    stt = AsyncMock()
    stt.transcribe = AsyncMock(return_value="hello")
    return stt


@pytest.fixture
def mock_coach():
    coach = AsyncMock()
    coach.respond = AsyncMock(
        return_value=CoachResponse(
            text_en="Hi",
            text_native="\u3053\u3093\u306b\u3061\u306f",
            text_reading="\u3053\u3093\u306b\u3061\u306f",
            text_romanized="konnichiwa",
            pronunciation_note="note",
            next_prompt="try again",
        )
    )
    return coach


@pytest.fixture
def mock_tts(tmp_path):
    tts = AsyncMock()
    async def fake_synth(text, lang, tid):
        p = tmp_path / f"{tid}.mp3"
        p.write_bytes(b"audio")
        return p
    tts.synthesize = AsyncMock(side_effect=fake_synth)
    return tts


@pytest.fixture
async def client(monkeypatch, engine, session_factory, mock_stt, mock_coach, mock_tts):
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
    monkeypatch.setattr("app.services.dependencies.stt_service", mock_stt)
    monkeypatch.setattr("app.services.dependencies.coach_service", mock_coach)
    monkeypatch.setattr("app.services.dependencies.tts_service", mock_tts)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_oversized_audio_rejected(client, auth_headers, active_session):
    oversized = b"x" * (1024 * 1024 + 1)
    response = await client.post(
        "/conversation/turn",
        headers={**auth_headers, "X-Idempotency-Key": str(uuid.uuid4())},
        files={"audio": ("audio.webm", oversized, "audio/webm")},
        data={"session_id": str(active_session)},
    )
    assert response.status_code == 413


@pytest.mark.anyio
async def test_turn_on_ended_session_rejected(client, auth_headers, ended_session):
    response = await client.post(
        "/conversation/turn",
        headers={**auth_headers, "X-Idempotency-Key": str(uuid.uuid4())},
        files={"audio": ("audio.webm", b"audio", "audio/webm")},
        data={"session_id": str(ended_session)},
    )
    assert response.status_code == 409

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
        "email": "turn@example.com",
        "user_metadata": {"full_name": "Turn User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_session(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="turn@example.com", name="Turn User")
        db.add(user)
        await db.flush()
        session = Session(
            user_id=user_id,
            language="ja",
            mode="learn",
            topic="Greetings",
            status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
def mock_stt():
    stt = AsyncMock()
    stt.transcribe = AsyncMock(return_value="I want to say hello")
    return stt


@pytest.fixture
def mock_coach():
    coach = AsyncMock()
    coach.respond = AsyncMock(
        return_value=CoachResponse(
            text_en="Here is how to say hello:",
            text_native="\u3053\u3093\u306b\u3061\u306f",
            text_reading="\u3053\u3093\u306b\u3061\u306f",
            text_romanized="konnichiwa",
            pronunciation_note="Natural greeting",
            next_prompt="Try saying it back to me",
        )
    )
    return coach


@pytest.fixture
def mock_tts(tmp_path):
    tts = AsyncMock()
    async def fake_synthesize(text, language, turn_id):
        path = tmp_path / f"{turn_id}.mp3"
        path.write_bytes(b"fake-audio")
        return path
    tts.synthesize = AsyncMock(side_effect=fake_synthesize)
    return tts


@pytest.fixture
async def client(monkeypatch, engine, session_factory, mock_stt, mock_coach, mock_tts):
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
    monkeypatch.setattr("app.services.dependencies.stt_service", mock_stt)
    monkeypatch.setattr("app.services.dependencies.coach_service", mock_coach)
    monkeypatch.setattr("app.services.dependencies.tts_service", mock_tts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_turn_success(client, auth_headers, test_session):
    idempotency_key = str(uuid.uuid4())
    files = {"audio": ("audio.webm", b"fake-audio-data", "audio/webm")}
    data = {"session_id": str(test_session)}

    response = await client.post(
        "/conversation/turn",
        headers={**auth_headers, "X-Idempotency-Key": idempotency_key},
        files=files,
        data=data,
    )
    assert response.status_code == 200
    body = response.json()
    assert "turn_id" in body
    assert body["user_entry"]["text_en"] == "I want to say hello"
    assert body["assistant_entry"]["text_native"] == "\u3053\u3093\u306b\u3061\u306f"
    assert body["assistant_entry"]["text_romanized"] == "konnichiwa"
    assert body["audio_url"].endswith(".mp3")


@pytest.mark.anyio
async def test_turn_idempotency(client, auth_headers, test_session):
    idempotency_key = str(uuid.uuid4())
    files = {"audio": ("audio.webm", b"fake-audio-data", "audio/webm")}
    data = {"session_id": str(test_session)}
    headers = {**auth_headers, "X-Idempotency-Key": idempotency_key}

    response1 = await client.post(
        "/conversation/turn", headers=headers, files=files, data=data
    )
    assert response1.status_code == 200

    response2 = await client.post(
        "/conversation/turn", headers=headers, files=files, data=data
    )
    assert response2.status_code == 200
    assert response1.json()["turn_id"] == response2.json()["turn_id"]


@pytest.mark.anyio
async def test_turn_wrong_session_owner(client, test_session, session_factory):
    other_user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(other_user_id),
        "email": "other@example.com",
        "user_metadata": {"full_name": "Other"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }

    async with session_factory() as db:
        user = User(id=other_user_id, email="other@example.com", name="Other")
        db.add(user)
        await db.commit()

    files = {"audio": ("audio.webm", b"fake-audio", "audio/webm")}
    data = {"session_id": str(test_session)}
    response = await client.post(
        "/conversation/turn", headers=headers, files=files, data=data
    )
    assert response.status_code == 403

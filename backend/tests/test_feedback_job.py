import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.user import User
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.feedback import Feedback

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
async def quiz_session_with_transcript(session_factory):
    user_id = uuid.uuid4()
    async with session_factory() as db:
        user = User(id=user_id, email="quiz@example.com", name="Quiz User")
        db.add(user)
        await db.flush()

        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="pending",
        )
        db.add(session)
        await db.flush()

        entry1 = TranscriptEntry(
            session_id=session.id, idempotency_key=uuid.uuid4(),
            turn_index=0, role="user", text_en="How do I say hello",
        )
        entry2 = TranscriptEntry(
            session_id=session.id, idempotency_key=uuid.uuid4(),
            turn_index=1, role="assistant",
            text_en="Here is hello:",
            text_native="\u3053\u3093\u306b\u3061\u306f",
            text_reading="\u3053\u3093\u306b\u3061\u306f",
            text_romanized="konnichiwa",
            pronunciation_note="Natural greeting",
            next_prompt="Say it back",
        )
        db.add_all([entry1, entry2])
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.mark.anyio
async def test_feedback_generation_success(quiz_session_with_transcript, session_factory, monkeypatch):
    session_id = quiz_session_with_transcript

    mock_coach_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "correct": ["konnichiwa"],
        "revisit": ["sumimasen"],
        "drills": ["Practice basic greetings"],
    })
    mock_coach_response.content = [mock_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_coach_response)

    with patch("app.worker.tasks.AsyncAnthropic", return_value=mock_client):
        monkeypatch.setattr(
            "app.worker.tasks.DATABASE_URL", TEST_DATABASE_URL
        )

        from app.worker.tasks import run_feedback_generation
        ctx = {}
        await run_feedback_generation(ctx, str(session_id))

    async with session_factory() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one()
        assert session.feedback_status == "ready"
        assert session.feedback_generated_at is not None

        fb_result = await db.execute(
            select(Feedback).where(Feedback.session_id == session_id)
        )
        feedback = fb_result.scalar_one()
        assert "konnichiwa" in feedback.correct
        assert "sumimasen" in feedback.revisit

import uuid

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
async def db(session_factory):
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.mark.anyio
async def test_create_user(db: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
    )
    db.add(user)
    await db.commit()

    result = await db.execute(select(User).where(User.email == "test@example.com"))
    fetched = result.scalar_one()
    assert fetched.email == "test@example.com"
    assert fetched.name == "Test User"


@pytest.mark.anyio
async def test_create_session_with_transcript(db: AsyncSession):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="session@example.com", name="Session User")
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
    await db.flush()

    entry = TranscriptEntry(
        session_id=session.id,
        idempotency_key=uuid.uuid4(),
        turn_index=0,
        role="user",
        text_en="Hello",
    )
    db.add(entry)
    await db.commit()

    result = await db.execute(
        select(TranscriptEntry).where(TranscriptEntry.session_id == session.id)
    )
    fetched = result.scalar_one()
    assert fetched.text_en == "Hello"
    assert fetched.turn_index == 0


@pytest.mark.anyio
async def test_create_feedback(db: AsyncSession):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="feedback@example.com", name="Feedback User")
    db.add(user)
    await db.flush()

    session = Session(
        user_id=user_id,
        language="ja",
        mode="quiz",
        topic="Ordering Food",
        status="ended",
        feedback_status="ready",
    )
    db.add(session)
    await db.flush()

    feedback = Feedback(
        session_id=session.id,
        correct=["konnichiwa", "arigatou"],
        revisit=["sumimasen"],
        drills=["Practice greetings", "Role-play ordering"],
    )
    db.add(feedback)
    await db.commit()

    result = await db.execute(
        select(Feedback).where(Feedback.session_id == session.id)
    )
    fetched = result.scalar_one()
    assert fetched.correct == ["konnichiwa", "arigatou"]
    assert len(fetched.drills) == 2

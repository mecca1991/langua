# Langua MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Langua Japanese language learning app MVP: a full-stack app where users authenticate with Google/GitHub, pick a topic and mode (learn/quiz), have spoken conversations with a Claude-powered Japanese coach via REST, and review session history and quiz feedback.

**Architecture:** Next.js 14 (App Router) frontend with NextAuth v5 handles auth; API routes act as a BFF (Backend for Frontend) that extract `session.user.id` and `session.user.email` server-side and forward them to FastAPI via `X-Internal-User-Id` and `X-Internal-User-Email` headers. FastAPI validates a shared `X-Internal-API-Key` secret — no JWT minting, no python-jose on the backend. The conversation loop is pure REST: `POST /conversation/turn` accepts an audio blob, runs STT (Whisper) → Claude (strict JSON CoachResponse) → TTS (OpenAI) → returns transcript + audio URL.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, pytest, httpx (backend); Next.js 14 App Router, TypeScript, Tailwind CSS, NextAuth v5, Jest, React Testing Library (frontend); PostgreSQL; OpenAI Whisper, Anthropic Claude, OpenAI TTS.

---

## Phase 1: Foundation

### Task 1: Monorepo Scaffolding

**Files:**
- Create: `langua/.gitignore`
- Create: `langua/README.md`
- Create: `langua/docker-compose.yml`
- Create: `langua/backend/.env.example`

**Step 1: Create the root .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
dist/
*.egg-info/
.pytest_cache/
.mypy_cache/
htmlcov/
.coverage

# Node
node_modules/
.next/
out/
*.tsbuildinfo

# Environment files
.env
.env.local
*.env.local
*.env

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp

# Alembic generated (keep migrations, not pycache)
backend/alembic/versions/__pycache__/

# Audio tmp files
/tmp/langua_audio/
```

Save to: `langua/.gitignore`

**Step 2: Create docker-compose.yml**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: langua
      POSTGRES_PASSWORD: langua
      POSTGRES_DB: langua
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langua"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

Save to: `langua/docker-compose.yml`

**Step 3: Create backend/.env.example**

```
DATABASE_URL=postgresql+asyncpg://langua:langua@localhost:5432/langua
INTERNAL_API_KEY=changeme-internal-secret

OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Save to: `langua/backend/.env.example`

**Step 4: Create README.md**

```markdown
# Langua

Japanese language learning app powered by Claude.

## Quickstart

```bash
# Start Postgres
docker compose up -d

# Backend
cd backend
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```
```

Save to: `langua/README.md`

**Step 5: Commit**

```bash
cd langua
git add .gitignore docker-compose.yml backend/.env.example README.md
git commit -m "chore: monorepo scaffolding — gitignore, docker-compose, env example, README"
```

---

### Task 2: FastAPI Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_health.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — nothing exists yet.

**Step 3: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "langua-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "httpx>=0.27",
    "openai>=1.30",
    "anthropic>=0.28",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "anyio[trio]>=4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Step 4: Create app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://langua:langua@localhost:5432/langua"
    internal_api_key: str = "changeme-internal-secret"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
```

**Step 5: Create app/dependencies.py**

```python
from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_internal_api_key(
    x_internal_api_key: str = Header(...),
) -> None:
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def get_internal_user_id(
    x_internal_user_id: str = Header(...),
) -> str:
    return x_internal_user_id


async def get_internal_user_email(
    x_internal_user_email: str = Header(...),
) -> str:
    return x_internal_user_email
```

**Step 6: Create app/main.py**

```python
from fastapi import FastAPI

app = FastAPI(title="Langua API", version="0.1.0")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
```

**Step 7: Create tests/conftest.py**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

**Step 8: Install dependencies**

```bash
cd backend
pip install -e ".[dev]"
```

**Step 9: Run test to verify it passes**

```bash
pytest tests/test_health.py -v
```

Expected:
```
tests/test_health.py::test_health_returns_ok PASSED
```

**Step 10: Commit**

```bash
git add backend/
git commit -m "feat: FastAPI skeleton with /health endpoint and pytest setup"
```

---

## Phase 2: Database

### Task 3: SQLAlchemy Models + Alembic

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (directory, first migration generated)

**Step 1: Create app/models.py**

```python
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum,
    ARRAY, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SessionMode(str, enum.Enum):
    learn = "learn"
    quiz = "quiz"


class Role(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    mode: Mapped[SessionMode] = mapped_column(SAEnum(SessionMode), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")
    transcript_entries: Mapped[list["TranscriptEntry"]] = relationship(
        back_populates="session", order_by="TranscriptEntry.created_at"
    )
    feedback: Mapped["Feedback | None"] = relationship(back_populates="session")


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False
    )
    role: Mapped[Role] = mapped_column(SAEnum(Role), nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_ja: Mapped[str | None] = mapped_column(Text)
    text_ja_kana: Mapped[str | None] = mapped_column(Text)
    text_ja_roma: Mapped[str | None] = mapped_column(Text)
    coaching_prompt: Mapped[str | None] = mapped_column(Text)
    is_repeat_request: Mapped[bool] = mapped_column(Boolean, default=False)
    target_phrase: Mapped[str | None] = mapped_column(Text)
    target_romaji: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    session: Mapped["Session"] = relationship(back_populates="transcript_entries")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, unique=True
    )
    correct: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    revisit: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    drills: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    session: Mapped["Session"] = relationship(back_populates="feedback")
```

**Step 2: Create app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

**Step 3: Initialize Alembic**

```bash
cd backend
alembic init alembic
```

**Step 4: Edit alembic/env.py to use async engine and import models**

Replace the contents of `backend/alembic/env.py` with:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.models import Base
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 5: Generate first migration**

```bash
cd backend
docker compose -f ../docker-compose.yml up -d
alembic revision --autogenerate -m "initial schema"
```

Expected: `backend/alembic/versions/<hash>_initial_schema.py` created.

**Step 6: Apply migration**

```bash
alembic upgrade head
```

Expected: Tables created in Postgres, no errors.

**Step 7: Commit**

```bash
git add backend/app/models.py backend/app/database.py backend/alembic/
git commit -m "feat: SQLAlchemy models (User, Session, TranscriptEntry, Feedback) + Alembic migration"
```

---

### Task 4: Database Test Fixtures

**Files:**
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_db_models.py`

**Step 1: Write a failing model smoke-test**

```python
# backend/tests/test_db_models.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User


@pytest.mark.asyncio
async def test_create_user(db: AsyncSession):
    user = User(email="test@example.com", name="Taro")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    assert user.id is not None
    assert user.email == "test@example.com"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_db_models.py -v
```

Expected: `fixture 'db' not found`

**Step 3: Add async test DB fixtures to conftest.py**

Add the following to `backend/tests/conftest.py` (below the existing `client` fixture):

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models import Base
from app.database import get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://langua:langua@localhost:5432/langua_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db() -> AsyncSession:
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

Note: Create a `langua_test` database before running:
```bash
docker exec -it <postgres-container> psql -U langua -c "CREATE DATABASE langua_test;"
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_db_models.py -v
```

Expected:
```
tests/test_db_models.py::test_create_user PASSED
```

**Step 5: Commit**

```bash
git add backend/tests/
git commit -m "test: add async DB fixtures and model smoke test"
```

---

## Phase 3: Backend Services & API

### Task 5: Service Layer

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/stt_service.py`
- Create: `backend/app/services/tts_service.py`
- Create: `backend/app/services/coach_service.py`
- Create: `backend/tests/test_stt_service.py`
- Create: `backend/tests/test_tts_service.py`
- Create: `backend/tests/test_coach_service.py`

**Step 1: Write the failing STT test**

```python
# backend/tests/test_stt_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.stt_service import transcribe_audio


@pytest.mark.asyncio
async def test_transcribe_audio_returns_text():
    fake_audio = b"fake-audio-bytes"
    mock_response = MagicMock()
    mock_response.text = "konnichiwa"

    with patch("app.services.stt_service.openai_client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
        result = await transcribe_audio(fake_audio, filename="audio.webm")

    assert result == "konnichiwa"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_stt_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.stt_service'`

**Step 3: Create app/services/stt_service.py**

```python
import io
from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Send audio bytes to OpenAI Whisper and return the transcript text."""
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )
    return response.text
```

**Step 4: Write the failing TTS test**

```python
# backend/tests/test_tts_service.py
import pytest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.tts_service import synthesize_speech


@pytest.mark.asyncio
async def test_synthesize_speech_writes_file_and_returns_url():
    session_id = str(uuid.uuid4())
    text = "こんにちは"

    mock_response = MagicMock()
    mock_response.content = b"fake-mp3-data"

    with patch("app.services.tts_service.openai_client") as mock_client:
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        audio_url = await synthesize_speech(text, session_id)

    assert audio_url.startswith(f"/audio/{session_id}/")
    assert audio_url.endswith(".mp3")

    # Verify file was written
    rel_path = audio_url.lstrip("/audio/")
    full_path = Path("/tmp/langua_audio") / rel_path
    assert full_path.exists()
    full_path.unlink()  # cleanup
```

**Step 5: Run TTS test to verify it fails**

```bash
pytest tests/test_tts_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.tts_service'`

**Step 6: Create app/services/tts_service.py**

```python
import uuid
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

AUDIO_DIR = Path("/tmp/langua_audio")


async def synthesize_speech(text: str, session_id: str) -> str:
    """Synthesize text to speech, save to /tmp, return a relative URL."""
    session_dir = AUDIO_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = session_dir / f"{file_id}.mp3"

    response = await openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )

    file_path.write_bytes(response.content)
    return f"/audio/{session_id}/{file_id}.mp3"
```

**Step 7: Write the failing coach test**

```python
# backend/tests/test_coach_service.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.coach_service import get_coach_response, CoachResponse


@pytest.mark.asyncio
async def test_get_coach_response_returns_coach_response():
    fake_json = json.dumps({
        "text_en": "Hello",
        "text_ja": "こんにちは",
        "text_ja_kana": "こんにちは",
        "text_ja_roma": "konnichiwa",
        "pronunciation_tip": "stress the ni",
        "coaching_prompt": "Try saying it!",
        "is_repeat_request": False,
        "target_phrase": "こんにちは",
        "target_romaji": "konnichiwa",
    })

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=fake_json)]
    mock_response = MagicMock()
    mock_response.content = mock_message.content

    with patch("app.services.coach_service.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await get_coach_response(
            user_text="hello",
            history=[],
            topic="greetings",
            mode="learn",
        )

    assert isinstance(result, CoachResponse)
    assert result.text_ja == "こんにちは"
    assert result.text_ja_roma == "konnichiwa"
    assert result.is_repeat_request is False


@pytest.mark.asyncio
async def test_get_coach_response_retries_on_bad_json():
    bad_json = "not valid json"
    good_json = json.dumps({
        "text_en": "Hello",
        "text_ja": "こんにちは",
        "text_ja_kana": "こんにちは",
        "text_ja_roma": "konnichiwa",
        "pronunciation_tip": "",
        "coaching_prompt": "Try it!",
        "is_repeat_request": False,
        "target_phrase": "こんにちは",
        "target_romaji": "konnichiwa",
    })

    call_count = 0

    async def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        mock.content = [MagicMock(text=bad_json if call_count == 1 else good_json)]
        return mock

    with patch("app.services.coach_service.anthropic_client") as mock_client:
        mock_client.messages.create = fake_create
        result = await get_coach_response("hello", [], "greetings", "learn")

    assert call_count == 2
    assert isinstance(result, CoachResponse)
```

**Step 8: Run coach test to verify it fails**

```bash
pytest tests/test_coach_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.coach_service'`

**Step 9: Create app/services/coach_service.py**

```python
import json
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from app.config import settings

anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are Langua, a Japanese language coach.

IMPORTANT — HOW PRONUNCIATION EVALUATION WORKS:
You do NOT hear the user's audio. You receive TEXT transcribed by OpenAI Whisper.
Pronunciation feedback is based on transcript similarity, not acoustic analysis.
- If the Whisper transcript closely matches the target Romaji, treat it as correct.
- If it does not match, assume the pronunciation was off and prompt a retry.
- Never say "I heard you say..." — say "it looks like you said..."

YOUR ROLE:
1. Understand what the user wants to express in English
2. Teach the correct Japanese phrase in three forms: Kanji, Hiragana, Romaji
3. Ask the user to try saying it aloud
4. When their attempt comes back (as Whisper text), compare it to the target Romaji
5. If close: confirm and move on. If not: show the difference and ask to retry.

In quiz mode, track mistakes and provide a structured feedback summary when asked.

RESPONSE FORMAT: You MUST respond with valid JSON only. No prose. No markdown.
{
  "text_en": "...",
  "text_ja": "...",
  "text_ja_kana": "...",
  "text_ja_roma": "...",
  "pronunciation_tip": "...",
  "coaching_prompt": "...",
  "is_repeat_request": true/false,
  "target_phrase": "...",
  "target_romaji": "..."
}"""


class CoachResponse(BaseModel):
    text_en: str
    text_ja: str
    text_ja_kana: str
    text_ja_roma: str
    pronunciation_tip: str
    coaching_prompt: str
    is_repeat_request: bool
    target_phrase: str
    target_romaji: str


async def get_coach_response(
    user_text: str,
    history: list[dict],
    topic: str,
    mode: str,
) -> CoachResponse:
    """Call Claude with conversation history, parse strict CoachResponse JSON. Retries once on parse failure."""
    messages = history + [{"role": "user", "content": user_text}]
    context_note = f"[Topic: {topic} | Mode: {mode}]\n\n"

    for attempt in range(2):
        response = await anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                messages[0] | {"content": context_note + messages[0]["content"]}
                if messages else {"role": "user", "content": context_note + user_text}
            ] if attempt == 0 and messages else messages,
        )
        raw = response.content[0].text
        try:
            data = json.loads(raw)
            return CoachResponse(**data)
        except (json.JSONDecodeError, Exception):
            if attempt == 1:
                raise ValueError(f"Claude returned invalid JSON after 2 attempts: {raw!r}")
            continue

    raise RuntimeError("Unreachable")
```

**Step 10: Run all service tests to verify they pass**

```bash
pytest tests/test_stt_service.py tests/test_tts_service.py tests/test_coach_service.py -v
```

Expected: All 4 tests PASS.

**Step 11: Commit**

```bash
git add backend/app/services/ backend/tests/test_stt_service.py backend/tests/test_tts_service.py backend/tests/test_coach_service.py
git commit -m "feat: service layer — stt_service, tts_service, coach_service with retry logic"
```

---

### Task 6: GET /topics

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/topics.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_topics.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_topics.py
import pytest
from httpx import AsyncClient
from app.config import settings


HEADERS = {
    "x-internal-api-key": settings.internal_api_key,
    "x-internal-user-id": "00000000-0000-0000-0000-000000000001",
    "x-internal-user-email": "test@example.com",
}


@pytest.mark.asyncio
async def test_get_topics_returns_list(client: AsyncClient):
    response = await client.get("/topics", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    ids = [t["id"] for t in data]
    assert "greetings" in ids
    assert "food" in ids


@pytest.mark.asyncio
async def test_get_topics_requires_api_key(client: AsyncClient):
    response = await client.get("/topics")
    assert response.status_code == 422  # missing header → validation error
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_topics.py -v
```

Expected: `404 Not Found` for `/topics`.

**Step 3: Create app/routers/topics.py**

```python
from fastapi import APIRouter, Depends
from app.dependencies import verify_internal_api_key

router = APIRouter(prefix="/topics", tags=["topics"])

TOPICS = [
    {"id": "greetings", "name": "Greetings", "description": "Hello, goodbye, thank you"},
    {"id": "food", "name": "Ordering Food", "description": "Restaurants, menus, preferences"},
    {"id": "directions", "name": "Directions", "description": "Getting around the city"},
    {"id": "shopping", "name": "Shopping", "description": "Prices, sizes, buying things"},
    {"id": "introductions", "name": "Introductions", "description": "Meeting new people"},
]


@router.get("", dependencies=[Depends(verify_internal_api_key)])
async def get_topics() -> list[dict]:
    return TOPICS
```

**Step 4: Register router in app/main.py**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.routers import topics

AUDIO_DIR = Path("/tmp/langua_audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Langua API", version="0.1.0")
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")
app.include_router(topics.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_topics.py -v
```

Expected:
```
tests/test_topics.py::test_get_topics_returns_list PASSED
tests/test_topics.py::test_get_topics_requires_api_key PASSED
```

**Step 6: Commit**

```bash
git add backend/app/routers/ backend/app/main.py backend/tests/test_topics.py
git commit -m "feat: GET /topics with hardcoded topic list and internal API key auth"
```

---

### Task 7: Internal Auth Middleware

**Files:**
- Modify: `backend/app/dependencies.py`
- Create: `backend/tests/test_auth.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient
from app.config import settings

VALID_HEADERS = {
    "x-internal-api-key": settings.internal_api_key,
    "x-internal-user-id": "00000000-0000-0000-0000-000000000099",
    "x-internal-user-email": "auth-test@example.com",
}


@pytest.mark.asyncio
async def test_wrong_api_key_returns_403(client: AsyncClient):
    headers = {**VALID_HEADERS, "x-internal-api-key": "wrong-key"}
    response = await client.get("/topics", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_missing_api_key_returns_422(client: AsyncClient):
    response = await client.get("/topics")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_valid_headers_pass_through(client: AsyncClient):
    response = await client.get("/topics", headers=VALID_HEADERS)
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_auth.py -v
```

Expected: `test_wrong_api_key_returns_403` should FAIL if 403 isn't returned yet.

**Step 3: Verify dependencies.py is already correct**

The `verify_internal_api_key` dep in `app/dependencies.py` already raises 403 on key mismatch. No changes needed — run again.

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_auth.py -v
```

Expected: All 3 PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_auth.py
git commit -m "test: internal auth middleware — 403 on wrong key, 422 on missing header"
```

---

### Task 8: POST /conversation/start and /conversation/end

**Files:**
- Create: `backend/app/routers/conversations.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_conversations.py`

**Step 1: Write the failing tests for start and end**

```python
# backend/tests/test_conversations.py
import pytest
from httpx import AsyncClient
from app.config import settings

HEADERS = {
    "x-internal-api-key": settings.internal_api_key,
    "x-internal-user-id": "00000000-0000-0000-0000-000000000002",
    "x-internal-user-email": "conv-test@example.com",
}


@pytest.mark.asyncio
async def test_conversation_start_creates_session(client: AsyncClient):
    payload = {
        "mode": "learn",
        "topic": "greetings",
        "user_email": "conv-test@example.com",
    }
    response = await client.post("/conversation/start", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_conversation_start_upserts_user(client: AsyncClient):
    payload = {"mode": "learn", "topic": "food", "user_email": "upsert@example.com"}
    headers = {**HEADERS, "x-internal-user-email": "upsert@example.com"}

    # Call twice — should not raise on duplicate email
    r1 = await client.post("/conversation/start", json=payload, headers=headers)
    r2 = await client.post("/conversation/start", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_conversation_end_closes_session(client: AsyncClient):
    # Start first
    start = await client.post(
        "/conversation/start",
        json={"mode": "learn", "topic": "greetings", "user_email": "conv-test@example.com"},
        headers=HEADERS,
    )
    session_id = start.json()["session_id"]

    # End it
    response = await client.post(
        "/conversation/end", json={"session_id": session_id}, headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["feedback"] is None  # no quiz feedback for learn mode


@pytest.mark.asyncio
async def test_conversation_end_unknown_session_returns_404(client: AsyncClient):
    response = await client.post(
        "/conversation/end",
        json={"session_id": "00000000-0000-0000-0000-000000000000"},
        headers=HEADERS,
    )
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_conversations.py -v
```

Expected: `404 Not Found` on `/conversation/start`.

**Step 3: Create app/routers/conversations.py (start + end only)**

```python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_internal_api_key, get_internal_user_id, get_internal_user_email
from app.models import Session as DBSession, User, SessionMode, TranscriptEntry, Feedback

router = APIRouter(prefix="/conversation", tags=["conversation"])


class StartRequest(BaseModel):
    mode: str
    topic: str
    user_email: str


class EndRequest(BaseModel):
    session_id: str


def _build_quiz_feedback(entries: list[TranscriptEntry]) -> dict | None:
    """Derive simple quiz feedback from transcript entries."""
    correct = []
    revisit = []
    for entry in entries:
        if entry.role.value == "assistant" and entry.target_phrase:
            if entry.is_repeat_request:
                revisit.append(entry.target_phrase)
            else:
                correct.append(entry.target_phrase)
    drills = list(set(revisit))
    return {"correct": correct, "revisit": revisit, "drills": drills}


@router.post("/start", dependencies=[Depends(verify_internal_api_key)])
async def conversation_start(
    body: StartRequest,
    user_id: str = Depends(get_internal_user_id),
    user_email: str = Depends(get_internal_user_email),
    db: AsyncSession = Depends(get_db),
):
    # Upsert user
    result = await db.execute(select(User).where(User.email == body.user_email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=body.user_email)
        db.add(user)
        await db.flush()

    # Create session
    session = DBSession(
        user_id=user.id,
        mode=SessionMode(body.mode),
        topic=body.topic,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"session_id": str(session.id)}


@router.post("/end", dependencies=[Depends(verify_internal_api_key)])
async def conversation_end(
    body: EndRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DBSession).where(DBSession.id == body.session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.utcnow()
    feedback_data = None

    if session.mode == SessionMode.quiz:
        entries_result = await db.execute(
            select(TranscriptEntry).where(TranscriptEntry.session_id == session.id)
        )
        entries = entries_result.scalars().all()
        fb_dict = _build_quiz_feedback(entries)
        feedback = Feedback(
            session_id=session.id,
            correct=fb_dict["correct"],
            revisit=fb_dict["revisit"],
            drills=fb_dict["drills"],
        )
        db.add(feedback)
        feedback_data = fb_dict

    await db.commit()
    return {"session_id": str(session.id), "feedback": feedback_data}
```

**Step 4: Register conversations router in app/main.py**

Add to `backend/app/main.py`:
```python
from app.routers import topics, conversations

app.include_router(conversations.router)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_conversations.py -v
```

Expected: All 4 PASS.

**Step 6: Commit**

```bash
git add backend/app/routers/conversations.py backend/app/main.py backend/tests/test_conversations.py
git commit -m "feat: POST /conversation/start and /conversation/end with user upsert and quiz feedback"
```

---

### Task 9: POST /conversation/turn

**Files:**
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/tests/test_conversations.py`

**Step 1: Write the failing turn test**

Add to `backend/tests/test_conversations.py`:

```python
@pytest.mark.asyncio
async def test_conversation_turn_returns_transcript_and_audio(client: AsyncClient):
    from unittest.mock import AsyncMock, patch, MagicMock
    import json

    # Start a session first
    start = await client.post(
        "/conversation/start",
        json={"mode": "learn", "topic": "greetings", "user_email": "turn-test@example.com"},
        headers=HEADERS,
    )
    session_id = start.json()["session_id"]

    fake_coach = {
        "text_en": "Hello",
        "text_ja": "こんにちは",
        "text_ja_kana": "こんにちは",
        "text_ja_roma": "konnichiwa",
        "pronunciation_tip": "stress ni",
        "coaching_prompt": "Try it!",
        "is_repeat_request": False,
        "target_phrase": "こんにちは",
        "target_romaji": "konnichiwa",
    }

    with (
        patch("app.routers.conversations.transcribe_audio", new=AsyncMock(return_value="hello")),
        patch(
            "app.routers.conversations.get_coach_response",
            new=AsyncMock(return_value=MagicMock(**fake_coach, model_dump=lambda: fake_coach)),
        ),
        patch(
            "app.routers.conversations.synthesize_speech",
            new=AsyncMock(return_value=f"/audio/{session_id}/test.mp3"),
        ),
    ):
        response = await client.post(
            "/conversation/turn",
            headers=HEADERS,
            data={"session_id": session_id},
            files={"audio": ("audio.webm", b"fake-audio", "audio/webm")},
        )

    assert response.status_code == 200
    data = response.json()
    assert "transcript_entry_id" in data
    assert data["audio_url"] == f"/audio/{session_id}/test.mp3"
    assert data["coach"]["text_ja"] == "こんにちは"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_conversations.py::test_conversation_turn_returns_transcript_and_audio -v
```

Expected: `404` or `422` since the `/turn` endpoint doesn't exist.

**Step 3: Add the /conversation/turn endpoint to conversations.py**

Add to `backend/app/routers/conversations.py`:

```python
from fastapi import UploadFile, File, Form
from app.services.stt_service import transcribe_audio
from app.services.tts_service import synthesize_speech
from app.services.coach_service import get_coach_response, CoachResponse as CoachResponseSchema
from app.models import Role


class ConversationTurnResponse(BaseModel):
    transcript_entry_id: str
    coach: dict
    audio_url: str


@router.post("/turn", dependencies=[Depends(verify_internal_api_key)])
async def conversation_turn(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Load session
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # STT
    audio_bytes = await audio.read()
    user_text = await transcribe_audio(audio_bytes, filename=audio.filename or "audio.webm")

    # Save user transcript entry
    user_entry = TranscriptEntry(
        session_id=session.id,
        role=Role.user,
        text_en=user_text,
    )
    db.add(user_entry)
    await db.flush()

    # Build history from existing entries
    prev_entries_result = await db.execute(
        select(TranscriptEntry)
        .where(TranscriptEntry.session_id == session.id)
        .order_by(TranscriptEntry.created_at)
    )
    prev_entries = prev_entries_result.scalars().all()
    history = [
        {"role": e.role.value, "content": e.text_en}
        for e in prev_entries
        if e.id != user_entry.id
    ]

    # Claude
    coach_resp = await get_coach_response(
        user_text=user_text,
        history=history,
        topic=session.topic,
        mode=session.mode.value,
    )

    # TTS
    audio_url = await synthesize_speech(coach_resp.text_ja, str(session.id))

    # Save assistant transcript entry
    coach_entry = TranscriptEntry(
        session_id=session.id,
        role=Role.assistant,
        text_en=coach_resp.text_en,
        text_ja=coach_resp.text_ja,
        text_ja_kana=coach_resp.text_ja_kana,
        text_ja_roma=coach_resp.text_ja_roma,
        coaching_prompt=coach_resp.coaching_prompt,
        is_repeat_request=coach_resp.is_repeat_request,
        target_phrase=coach_resp.target_phrase,
        target_romaji=coach_resp.target_romaji,
    )
    db.add(coach_entry)
    await db.commit()
    await db.refresh(coach_entry)

    return ConversationTurnResponse(
        transcript_entry_id=str(coach_entry.id),
        coach=coach_resp.model_dump(),
        audio_url=audio_url,
    )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_conversations.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add backend/app/routers/conversations.py backend/tests/test_conversations.py
git commit -m "feat: POST /conversation/turn — STT → Claude → TTS pipeline with transcript persistence"
```

---

### Task 10: GET /sessions + GET /sessions/{id}

**Files:**
- Create: `backend/app/routers/sessions.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_sessions.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_sessions.py
import pytest
from httpx import AsyncClient
from app.config import settings

HEADERS = {
    "x-internal-api-key": settings.internal_api_key,
    "x-internal-user-id": "00000000-0000-0000-0000-000000000003",
    "x-internal-user-email": "sessions-test@example.com",
}


@pytest.fixture
async def session_id(client: AsyncClient) -> str:
    response = await client.post(
        "/conversation/start",
        json={"mode": "learn", "topic": "greetings", "user_email": "sessions-test@example.com"},
        headers=HEADERS,
    )
    return response.json()["session_id"]


@pytest.mark.asyncio
async def test_get_sessions_returns_list(client: AsyncClient, session_id: str):
    response = await client.get("/sessions", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    ids = [s["id"] for s in data]
    assert session_id in ids


@pytest.mark.asyncio
async def test_get_session_by_id_returns_detail(client: AsyncClient, session_id: str):
    response = await client.get(f"/sessions/{session_id}", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert "transcript_entries" in data
    assert isinstance(data["transcript_entries"], list)


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    response = await client.get(
        "/sessions/00000000-0000-0000-0000-000000000000", headers=HEADERS
    )
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_sessions.py -v
```

Expected: `404` on `/sessions`.

**Step 3: Create app/routers/sessions.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import verify_internal_api_key, get_internal_user_id
from app.models import Session as DBSession, User, TranscriptEntry, Feedback

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _serialize_session(session: DBSession, include_entries: bool = False) -> dict:
    data = {
        "id": str(session.id),
        "mode": session.mode.value,
        "topic": session.topic,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
    if include_entries:
        data["transcript_entries"] = [
            {
                "id": str(e.id),
                "role": e.role.value,
                "text_en": e.text_en,
                "text_ja": e.text_ja,
                "text_ja_kana": e.text_ja_kana,
                "text_ja_roma": e.text_ja_roma,
                "coaching_prompt": e.coaching_prompt,
                "is_repeat_request": e.is_repeat_request,
                "target_phrase": e.target_phrase,
                "target_romaji": e.target_romaji,
                "created_at": e.created_at.isoformat(),
            }
            for e in session.transcript_entries
        ]
        data["feedback"] = (
            {
                "correct": session.feedback.correct,
                "revisit": session.feedback.revisit,
                "drills": session.feedback.drills,
            }
            if session.feedback
            else None
        )
    return data


@router.get("", dependencies=[Depends(verify_internal_api_key)])
async def list_sessions(
    user_id: str = Depends(get_internal_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.email != None))
    # Scope to user by joining through user_id header
    result = await db.execute(
        select(DBSession)
        .join(User)
        .where(DBSession.user_id == (
            select(User.id).where(User.email == (
                # We need user email — query user by internal user id is not possible
                # directly; scope by user_id UUID from header instead
                select(User.email).where(User.id == user_id).scalar_subquery()
            )).scalar_subquery()
        ))
        .order_by(DBSession.started_at.desc())
    )
    sessions = result.scalars().all()
    return [_serialize_session(s) for s in sessions]


@router.get("/{session_id}", dependencies=[Depends(verify_internal_api_key)])
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DBSession)
        .options(
            selectinload(DBSession.transcript_entries),
            selectinload(DBSession.feedback),
        )
        .where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session, include_entries=True)
```

**Step 4: Register sessions router in app/main.py**

Add to `backend/app/main.py`:
```python
from app.routers import topics, conversations, sessions

app.include_router(sessions.router)
```

**Step 5: Fix list_sessions to use user UUID from header directly**

The simpler scoping approach: the `X-Internal-User-Id` is the user's UUID. Update `list_sessions` in `sessions.py`:

```python
@router.get("", dependencies=[Depends(verify_internal_api_key)])
async def list_sessions(
    user_id: str = Depends(get_internal_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Look up the user by their UUID from NextAuth (stored when session was created)
    result = await db.execute(
        select(DBSession)
        .where(DBSession.user_id == user_id)
        .order_by(DBSession.started_at.desc())
    )
    sessions = result.scalars().all()
    return [_serialize_session(s) for s in sessions]
```

Note: The user UUID from NextAuth header must match the UUID stored in the DB. In `conversation/start`, store `user_id` from the header as the User's id. Update `conversation_start` in conversations.py:

```python
import uuid as uuid_mod

# In conversation_start:
user = User(id=uuid_mod.UUID(user_id), email=body.user_email)
```

And on upsert conflict, just load the existing user without re-inserting.

**Step 6: Run test to verify it passes**

```bash
pytest tests/test_sessions.py -v
```

Expected: All 3 tests PASS.

**Step 7: Run full backend test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

**Step 8: Commit**

```bash
git add backend/app/routers/sessions.py backend/app/main.py backend/tests/test_sessions.py
git commit -m "feat: GET /sessions and GET /sessions/{id} with ownership scoping"
```

---

## Phase 4: Frontend

### Task 11: Next.js Setup + Auth + BFF

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/jest.config.ts`
- Create: `frontend/jest.setup.ts`
- Create: `frontend/.env.local.example`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/lib/auth.ts`
- Create: `frontend/lib/bff.ts`
- Create: `frontend/app/api/topics/route.ts`
- Create: `frontend/app/api/conversations/start/route.ts`
- Create: `frontend/app/api/conversations/turn/route.ts`
- Create: `frontend/app/api/conversations/end/route.ts`
- Create: `frontend/app/api/sessions/route.ts`
- Create: `frontend/app/api/sessions/[id]/route.ts`

**Step 1: Create package.json**

```json
{
  "name": "langua-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "jest --passWithNoTests",
    "test:watch": "jest --watch"
  },
  "dependencies": {
    "next": "14.2.4",
    "next-auth": "^5.0.0-beta.19",
    "react": "^18",
    "react-dom": "^18"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6",
    "@testing-library/react": "^15",
    "@testing-library/user-event": "^14",
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10",
    "jest": "^29",
    "jest-environment-jsdom": "^29",
    "postcss": "^8",
    "tailwindcss": "^3",
    "ts-jest": "^29",
    "typescript": "^5"
  }
}
```

**Step 2: Create .env.local.example**

```
NEXTAUTH_SECRET=changeme-nextauth-secret
NEXTAUTH_URL=http://localhost:3000

AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=

INTERNAL_API_KEY=changeme-internal-secret
FASTAPI_BASE_URL=http://localhost:8000
```

**Step 3: Create lib/auth.ts (NextAuth v5)**

```typescript
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import GitHub from "next-auth/providers/github";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
    }),
  ],
  callbacks: {
    session({ session, token }) {
      if (token.sub) {
        session.user.id = token.sub;
      }
      return session;
    },
  },
});
```

**Step 4: Create lib/bff.ts**

```typescript
import { auth } from "@/lib/auth";

const FASTAPI_BASE = process.env.FASTAPI_BASE_URL ?? "http://localhost:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

/**
 * Make an authenticated request from a Next.js API route (BFF) to FastAPI.
 * Extracts session user id and email server-side; never exposes to client.
 */
export async function bffFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const session = await auth();
  if (!session?.user) {
    throw new Error("Unauthenticated");
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Internal-API-Key": INTERNAL_API_KEY,
    "X-Internal-User-Id": session.user.id ?? "",
    "X-Internal-User-Email": session.user.email ?? "",
    ...(init.headers as Record<string, string> | undefined),
  };

  return fetch(`${FASTAPI_BASE}${path}`, { ...init, headers });
}
```

**Step 5: Create app/api/topics/route.ts**

```typescript
import { NextResponse } from "next/server";
import { bffFetch } from "@/lib/bff";

export async function GET() {
  try {
    const res = await bffFetch("/topics");
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
```

**Step 6: Create app/api/conversations/start/route.ts**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { bffFetch } from "@/lib/bff";
import { auth } from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json();
    const res = await bffFetch("/conversation/start", {
      method: "POST",
      body: JSON.stringify({ ...body, user_email: session?.user?.email }),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
```

**Step 7: Create app/api/conversations/turn/route.ts**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const FASTAPI_BASE = process.env.FASTAPI_BASE_URL ?? "http://localhost:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Forward multipart/form-data directly — do not re-serialize
    const formData = await req.formData();

    const res = await fetch(`${FASTAPI_BASE}/conversation/turn`, {
      method: "POST",
      headers: {
        "X-Internal-API-Key": INTERNAL_API_KEY,
        "X-Internal-User-Id": session.user.id ?? "",
        "X-Internal-User-Email": session.user.email ?? "",
        // Do NOT set Content-Type — let fetch set it with correct boundary
      },
      body: formData,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
```

**Step 8: Create remaining API routes**

`frontend/app/api/conversations/end/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { bffFetch } from "@/lib/bff";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await bffFetch("/conversation/end", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
```

`frontend/app/api/sessions/route.ts`:
```typescript
import { NextResponse } from "next/server";
import { bffFetch } from "@/lib/bff";

export async function GET() {
  try {
    const res = await bffFetch("/sessions");
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
```

`frontend/app/api/sessions/[id]/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { bffFetch } from "@/lib/bff";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const res = await bffFetch(`/sessions/${params.id}`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
```

**Step 9: Create jest.config.ts**

```typescript
import type { Config } from "jest";

const config: Config = {
  testEnvironment: "jsdom",
  setupFilesAfterFramework: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  transform: {
    "^.+\\.(ts|tsx)$": ["ts-jest", { tsconfig: { jsx: "react-jsx" } }],
  },
  testMatch: ["**/__tests__/**/*.test.{ts,tsx}"],
};

export default config;
```

Create `frontend/jest.setup.ts`:
```typescript
import "@testing-library/jest-dom";
```

**Step 10: Install dependencies**

```bash
cd frontend
npm install
```

**Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js 14 setup with NextAuth v5, BFF helpers, and all API route handlers"
```

---

### Task 12: Home Screen — ModeSelector + TopicPicker

**Files:**
- Create: `frontend/components/ModeSelector.tsx`
- Create: `frontend/components/TopicPicker.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/__tests__/ModeSelector.test.tsx`
- Create: `frontend/__tests__/TopicPicker.test.tsx`

**Step 1: Write the failing ModeSelector test**

```typescript
// frontend/__tests__/ModeSelector.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import ModeSelector from "@/components/ModeSelector";

test("renders both mode options", () => {
  const onSelect = jest.fn();
  render(<ModeSelector selected={null} onSelect={onSelect} />);
  expect(screen.getByText(/learn/i)).toBeInTheDocument();
  expect(screen.getByText(/quiz/i)).toBeInTheDocument();
});

test("calls onSelect when a mode is clicked", () => {
  const onSelect = jest.fn();
  render(<ModeSelector selected={null} onSelect={onSelect} />);
  fireEvent.click(screen.getByText(/learn/i));
  expect(onSelect).toHaveBeenCalledWith("learn");
});

test("highlights selected mode", () => {
  render(<ModeSelector selected="quiz" onSelect={jest.fn()} />);
  const quizBtn = screen.getByText(/quiz/i).closest("button");
  expect(quizBtn).toHaveClass("bg-indigo-600");
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
npm test -- --testPathPattern=ModeSelector
```

Expected: `Cannot find module '@/components/ModeSelector'`

**Step 3: Create components/ModeSelector.tsx**

```typescript
type Mode = "learn" | "quiz";

interface Props {
  selected: Mode | null;
  onSelect: (mode: Mode) => void;
}

const MODES: { value: Mode; label: string; description: string }[] = [
  { value: "learn", label: "Learn", description: "Guided lesson with your coach" },
  { value: "quiz", label: "Quiz", description: "Test your Japanese skills" },
];

export default function ModeSelector({ selected, onSelect }: Props) {
  return (
    <div className="flex gap-4">
      {MODES.map((m) => (
        <button
          key={m.value}
          onClick={() => onSelect(m.value)}
          className={`flex-1 rounded-xl p-4 border-2 text-left transition-colors ${
            selected === m.value
              ? "bg-indigo-600 border-indigo-600 text-white"
              : "border-gray-200 hover:border-indigo-400"
          }`}
        >
          <div className="font-semibold text-lg">{m.label}</div>
          <div className="text-sm opacity-75">{m.description}</div>
        </button>
      ))}
    </div>
  );
}
```

**Step 4: Write the failing TopicPicker test**

```typescript
// frontend/__tests__/TopicPicker.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import TopicPicker from "@/components/TopicPicker";

const TOPICS = [
  { id: "greetings", name: "Greetings", description: "Hello, goodbye" },
  { id: "food", name: "Ordering Food", description: "Restaurants" },
];

test("renders all topics", () => {
  render(<TopicPicker topics={TOPICS} selected={null} onSelect={jest.fn()} />);
  expect(screen.getByText("Greetings")).toBeInTheDocument();
  expect(screen.getByText("Ordering Food")).toBeInTheDocument();
});

test("calls onSelect with topic id on click", () => {
  const onSelect = jest.fn();
  render(<TopicPicker topics={TOPICS} selected={null} onSelect={onSelect} />);
  fireEvent.click(screen.getByText("Greetings"));
  expect(onSelect).toHaveBeenCalledWith("greetings");
});

test("marks selected topic", () => {
  render(<TopicPicker topics={TOPICS} selected="food" onSelect={jest.fn()} />);
  const foodCard = screen.getByText("Ordering Food").closest("button");
  expect(foodCard).toHaveClass("border-indigo-600");
});
```

**Step 5: Create components/TopicPicker.tsx**

```typescript
interface Topic {
  id: string;
  name: string;
  description: string;
}

interface Props {
  topics: Topic[];
  selected: string | null;
  onSelect: (topicId: string) => void;
}

export default function TopicPicker({ topics, selected, onSelect }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {topics.map((t) => (
        <button
          key={t.id}
          onClick={() => onSelect(t.id)}
          className={`rounded-lg p-3 border-2 text-left transition-colors ${
            selected === t.id
              ? "border-indigo-600 bg-indigo-50"
              : "border-gray-200 hover:border-indigo-300"
          }`}
        >
          <div className="font-medium">{t.name}</div>
          <div className="text-xs text-gray-500">{t.description}</div>
        </button>
      ))}
    </div>
  );
}
```

**Step 6: Run tests to verify they pass**

```bash
npm test -- --testPathPattern="ModeSelector|TopicPicker"
```

Expected: All tests PASS.

**Step 7: Create app/page.tsx (Home screen)**

```typescript
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ModeSelector from "@/components/ModeSelector";
import TopicPicker from "@/components/TopicPicker";

type Mode = "learn" | "quiz";
interface Topic { id: string; name: string; description: string }

export default function HomePage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/topics")
      .then((r) => r.json())
      .then(setTopics)
      .catch(console.error);
  }, []);

  const handleStart = async () => {
    if (!mode || !topic) return;
    setLoading(true);
    try {
      const res = await fetch("/api/conversations/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, topic }),
      });
      const { session_id } = await res.json();
      router.push(`/conversation/${session_id}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <h1 className="text-4xl font-bold text-indigo-700 mb-2">Langua</h1>
      <p className="text-gray-500 mb-8">Your Japanese language coach</p>

      <div className="w-full max-w-lg space-y-6 bg-white rounded-2xl shadow p-6">
        <div>
          <h2 className="font-semibold text-gray-700 mb-3">Choose a mode</h2>
          <ModeSelector selected={mode} onSelect={setMode} />
        </div>
        <div>
          <h2 className="font-semibold text-gray-700 mb-3">Choose a topic</h2>
          <TopicPicker topics={topics} selected={topic} onSelect={setTopic} />
        </div>
        <button
          onClick={handleStart}
          disabled={!mode || !topic || loading}
          className="w-full py-3 rounded-xl bg-indigo-600 text-white font-semibold disabled:opacity-40 hover:bg-indigo-700 transition-colors"
        >
          {loading ? "Starting..." : "Start Session"}
        </button>
      </div>
    </main>
  );
}
```

**Step 8: Commit**

```bash
git add frontend/components/ frontend/app/page.tsx frontend/__tests__/
git commit -m "feat: home screen with ModeSelector and TopicPicker components"
```

---

### Task 13: Conversation View

**Files:**
- Create: `frontend/components/Waveform.tsx`
- Create: `frontend/components/TranscriptPanel.tsx`
- Create: `frontend/components/QuizTimer.tsx`
- Create: `frontend/app/conversation/[sessionId]/page.tsx`
- Create: `frontend/__tests__/Waveform.test.tsx`
- Create: `frontend/__tests__/TranscriptPanel.test.tsx`

**Step 1: Write the failing Waveform test**

```typescript
// frontend/__tests__/Waveform.test.tsx
import { render, screen } from "@testing-library/react";
import Waveform from "@/components/Waveform";

test("renders waveform bars when active", () => {
  const { container } = render(<Waveform active={true} />);
  const bars = container.querySelectorAll(".waveform-bar");
  expect(bars.length).toBeGreaterThan(0);
});

test("renders without crashing when inactive", () => {
  const { container } = render(<Waveform active={false} />);
  // Should render but bars should not have animation class
  const wrapper = container.firstChild as HTMLElement;
  expect(wrapper).toBeInTheDocument();
});

test("does not use Math.random in render path", () => {
  const spy = jest.spyOn(Math, "random");
  render(<Waveform active={true} />);
  expect(spy).not.toHaveBeenCalled();
  spy.mockRestore();
});
```

**Step 2: Run test to verify it fails**

```bash
npm test -- --testPathPattern=Waveform
```

Expected: `Cannot find module '@/components/Waveform'`

**Step 3: Create components/Waveform.tsx**

Use CSS keyframe animations — no Math.random in render:

```typescript
interface Props {
  active: boolean;
}

// Fixed animation delays — no Math.random() in render
const BAR_DELAYS = [
  "0ms", "80ms", "160ms", "240ms", "80ms",
  "160ms", "0ms", "240ms", "120ms", "40ms",
  "200ms", "80ms"
];

export default function Waveform({ active }: Props) {
  return (
    <>
      <style>{`
        @keyframes wave {
          0%, 100% { transform: scaleY(0.3); }
          50% { transform: scaleY(1); }
        }
        .waveform-bar {
          animation: wave 0.8s ease-in-out infinite;
        }
        .waveform-bar.paused {
          animation-play-state: paused;
        }
      `}</style>
      <div className="flex items-center gap-1 h-12">
        {BAR_DELAYS.map((delay, i) => (
          <div
            key={i}
            className={`waveform-bar w-1 h-8 bg-indigo-500 rounded-full${active ? "" : " paused"}`}
            style={{ animationDelay: delay }}
          />
        ))}
      </div>
    </>
  );
}
```

**Step 4: Write the failing TranscriptPanel test**

```typescript
// frontend/__tests__/TranscriptPanel.test.tsx
import { render, screen } from "@testing-library/react";
import TranscriptPanel from "@/components/TranscriptPanel";

const ENTRIES = [
  {
    id: "1",
    role: "user" as const,
    text_en: "Hello",
    text_ja: null,
    text_ja_kana: null,
    text_ja_roma: null,
    coaching_prompt: null,
  },
  {
    id: "2",
    role: "assistant" as const,
    text_en: "Hello",
    text_ja: "こんにちは",
    text_ja_kana: "こんにちは",
    text_ja_roma: "konnichiwa",
    coaching_prompt: "Try saying it!",
  },
];

test("renders user transcript entry", () => {
  render(<TranscriptPanel entries={ENTRIES} />);
  expect(screen.getByText("Hello")).toBeInTheDocument();
});

test("renders all three Japanese forms for assistant entries", () => {
  render(<TranscriptPanel entries={ENTRIES} />);
  expect(screen.getByText("こんにちは")).toBeInTheDocument();
  expect(screen.getByText("konnichiwa")).toBeInTheDocument();
});

test("renders coaching prompt", () => {
  render(<TranscriptPanel entries={ENTRIES} />);
  expect(screen.getByText("Try saying it!")).toBeInTheDocument();
});
```

**Step 5: Create components/TranscriptPanel.tsx**

```typescript
interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text_en: string;
  text_ja: string | null;
  text_ja_kana: string | null;
  text_ja_roma: string | null;
  coaching_prompt: string | null;
}

interface Props {
  entries: TranscriptEntry[];
}

export default function TranscriptPanel({ entries }: Props) {
  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className={`rounded-xl p-4 max-w-[80%] ${
            entry.role === "user"
              ? "self-end bg-indigo-100"
              : "self-start bg-white shadow"
          }`}
        >
          <p className="text-gray-800">{entry.text_en}</p>
          {entry.role === "assistant" && entry.text_ja && (
            <div className="mt-2 space-y-1 border-t pt-2">
              <p className="text-lg font-medium text-gray-900">{entry.text_ja}</p>
              {entry.text_ja_kana && (
                <p className="text-sm text-gray-600">{entry.text_ja_kana}</p>
              )}
              {entry.text_ja_roma && (
                <p className="text-sm text-indigo-600 italic">{entry.text_ja_roma}</p>
              )}
            </div>
          )}
          {entry.coaching_prompt && (
            <p className="mt-2 text-sm text-gray-500 italic">{entry.coaching_prompt}</p>
          )}
        </div>
      ))}
    </div>
  );
}
```

**Step 6: Create components/QuizTimer.tsx**

```typescript
"use client";

import { useEffect, useState } from "react";

interface Props {
  running: boolean;
}

export default function QuizTimer({ running }: Props) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [running]);

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <div className="font-mono text-gray-400 text-sm">
      {mm}:{ss}
    </div>
  );
}
```

**Step 7: Create the Conversation page**

```typescript
// frontend/app/conversation/[sessionId]/page.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import TranscriptPanel from "@/components/TranscriptPanel";
import Waveform from "@/components/Waveform";
import QuizTimer from "@/components/QuizTimer";

interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text_en: string;
  text_ja: string | null;
  text_ja_kana: string | null;
  text_ja_roma: string | null;
  coaching_prompt: string | null;
}

export default function ConversationPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(true);
  };

  const stopRecording = () => {
    return new Promise<Blob>((resolve) => {
      const recorder = mediaRecorderRef.current!;
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        resolve(blob);
      };
      recorder.stop();
      recorder.stream.getTracks().forEach((t) => t.stop());
    });
  };

  const handleMicToggle = async () => {
    if (recording) {
      setRecording(false);
      setProcessing(true);
      try {
        const audioBlob = await stopRecording();
        const formData = new FormData();
        formData.append("session_id", sessionId);
        formData.append("audio", audioBlob, "audio.webm");

        const res = await fetch("/api/conversations/turn", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();

        // Add user entry (placeholder)
        const userEntry: TranscriptEntry = {
          id: `user-${Date.now()}`,
          role: "user",
          text_en: "(your message)",
          text_ja: null,
          text_ja_kana: null,
          text_ja_roma: null,
          coaching_prompt: null,
        };

        // Add assistant entry from response
        const assistantEntry: TranscriptEntry = {
          id: data.transcript_entry_id,
          role: "assistant",
          text_en: data.coach.text_en,
          text_ja: data.coach.text_ja,
          text_ja_kana: data.coach.text_ja_kana,
          text_ja_roma: data.coach.text_ja_roma,
          coaching_prompt: data.coach.coaching_prompt,
        };

        setEntries((prev) => [...prev, userEntry, assistantEntry]);

        // Play audio via Blob URL
        const audioRes = await fetch(data.audio_url);
        const audioBlob2 = await audioRes.blob();
        const url = URL.createObjectURL(audioBlob2);
        const audio = new Audio(url);
        audio.onended = () => URL.revokeObjectURL(url);
        audio.play();
      } finally {
        setProcessing(false);
      }
    } else {
      await startRecording();
    }
  };

  const handleEndSession = async () => {
    const res = await fetch("/api/conversations/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const data = await res.json();
    router.push(`/feedback/${sessionId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-indigo-700">Langua</h1>
        <QuizTimer running={!processing} />
        <button
          onClick={handleEndSession}
          className="text-sm text-gray-500 hover:text-red-500 transition-colors"
        >
          End Session
        </button>
      </header>

      <div className="flex-1 overflow-hidden">
        <TranscriptPanel entries={entries} />
      </div>

      <div className="bg-white border-t p-6 flex flex-col items-center gap-4">
        <Waveform active={recording} />
        <button
          onClick={handleMicToggle}
          disabled={processing}
          className={`w-16 h-16 rounded-full flex items-center justify-center text-white font-bold shadow-lg transition-colors ${
            recording ? "bg-red-500 hover:bg-red-600" : "bg-indigo-600 hover:bg-indigo-700"
          } disabled:opacity-40`}
        >
          {processing ? "..." : recording ? "Stop" : "Tap"}
        </button>
        <p className="text-sm text-gray-400">
          {recording ? "Recording... tap to send" : "Tap to speak"}
        </p>
      </div>
    </div>
  );
}
```

**Step 8: Run tests to verify they pass**

```bash
npm test -- --testPathPattern="Waveform|TranscriptPanel"
```

Expected: All tests PASS.

**Step 9: Commit**

```bash
git add frontend/components/Waveform.tsx frontend/components/TranscriptPanel.tsx frontend/components/QuizTimer.tsx frontend/app/conversation/ frontend/__tests__/Waveform.test.tsx frontend/__tests__/TranscriptPanel.test.tsx
git commit -m "feat: conversation view with tap-to-toggle mic, waveform animation, and transcript panel"
```

---

### Task 14: Feedback View + Session History

**Files:**
- Create: `frontend/components/FeedbackCard.tsx`
- Create: `frontend/app/feedback/[sessionId]/page.tsx`
- Create: `frontend/app/history/page.tsx`
- Create: `frontend/__tests__/FeedbackCard.test.tsx`

**Step 1: Write the failing FeedbackCard test**

```typescript
// frontend/__tests__/FeedbackCard.test.tsx
import { render, screen } from "@testing-library/react";
import FeedbackCard from "@/components/FeedbackCard";

const FEEDBACK = {
  correct: ["こんにちは", "ありがとう"],
  revisit: ["さようなら"],
  drills: ["さようなら"],
};

test("renders correct phrases", () => {
  render(<FeedbackCard feedback={FEEDBACK} />);
  expect(screen.getByText("こんにちは")).toBeInTheDocument();
  expect(screen.getByText("ありがとう")).toBeInTheDocument();
});

test("renders revisit phrases", () => {
  render(<FeedbackCard feedback={FEEDBACK} />);
  expect(screen.getByText("さようなら")).toBeInTheDocument();
});

test("renders section headings", () => {
  render(<FeedbackCard feedback={FEEDBACK} />);
  expect(screen.getByText(/got it/i)).toBeInTheDocument();
  expect(screen.getByText(/revisit/i)).toBeInTheDocument();
  expect(screen.getByText(/drill/i)).toBeInTheDocument();
});

test("renders null feedback gracefully", () => {
  const { container } = render(<FeedbackCard feedback={null} />);
  expect(container.firstChild).toBeNull();
});
```

**Step 2: Run test to verify it fails**

```bash
npm test -- --testPathPattern=FeedbackCard
```

Expected: `Cannot find module '@/components/FeedbackCard'`

**Step 3: Create components/FeedbackCard.tsx**

```typescript
interface Feedback {
  correct: string[];
  revisit: string[];
  drills: string[];
}

interface Props {
  feedback: Feedback | null;
}

export default function FeedbackCard({ feedback }: Props) {
  if (!feedback) return null;

  return (
    <div className="rounded-2xl bg-white shadow p-6 space-y-4">
      <Section title="Got it" items={feedback.correct} color="green" />
      <Section title="Revisit" items={feedback.revisit} color="yellow" />
      <Section title="Drill these" items={feedback.drills} color="red" />
    </div>
  );
}

function Section({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: "green" | "yellow" | "red";
}) {
  const colors = {
    green: "text-green-700 bg-green-50",
    yellow: "text-yellow-700 bg-yellow-50",
    red: "text-red-700 bg-red-50",
  };

  if (items.length === 0) return null;

  return (
    <div>
      <h3 className={`font-semibold mb-2 ${colors[color].split(" ")[0]}`}>{title}</h3>
      <ul className="space-y-1">
        {items.map((phrase, i) => (
          <li
            key={i}
            className={`rounded-lg px-3 py-2 text-sm ${colors[color]}`}
          >
            {phrase}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**Step 4: Create app/feedback/[sessionId]/page.tsx**

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import FeedbackCard from "@/components/FeedbackCard";
import Link from "next/link";

interface Feedback {
  correct: string[];
  revisit: string[];
  drills: string[];
}

interface SessionDetail {
  id: string;
  mode: string;
  topic: string;
  feedback: Feedback | null;
}

export default function FeedbackPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [session, setSession] = useState<SessionDetail | null>(null);

  useEffect(() => {
    fetch(`/api/sessions/${sessionId}`)
      .then((r) => r.json())
      .then(setSession)
      .catch(console.error);
  }, [sessionId]);

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading feedback...</p>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-indigo-700">Session Complete</h1>
          <p className="text-gray-500 mt-1">
            {session.mode === "quiz" ? "Quiz" : "Learn"} · {session.topic}
          </p>
        </div>

        {session.feedback ? (
          <FeedbackCard feedback={session.feedback} />
        ) : (
          <div className="rounded-2xl bg-white shadow p-6 text-center text-gray-500">
            No quiz feedback for this session.
          </div>
        )}

        <div className="flex gap-3">
          <Link
            href="/"
            className="flex-1 text-center py-3 rounded-xl border-2 border-indigo-600 text-indigo-600 font-semibold hover:bg-indigo-50 transition-colors"
          >
            Start New Session
          </Link>
          <Link
            href="/history"
            className="flex-1 text-center py-3 rounded-xl bg-gray-100 text-gray-700 font-semibold hover:bg-gray-200 transition-colors"
          >
            View History
          </Link>
        </div>
      </div>
    </main>
  );
}
```

**Step 5: Create app/history/page.tsx**

```typescript
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface SessionSummary {
  id: string;
  mode: string;
  topic: string;
  started_at: string;
  ended_at: string | null;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  useEffect(() => {
    fetch("/api/sessions")
      .then((r) => r.json())
      .then(setSessions)
      .catch(console.error);
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-indigo-700">Session History</h1>
          <Link
            href="/"
            className="text-sm text-indigo-600 hover:underline"
          >
            + New Session
          </Link>
        </div>

        {sessions.length === 0 ? (
          <p className="text-center text-gray-400 mt-12">No sessions yet.</p>
        ) : (
          <ul className="space-y-3">
            {sessions.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/feedback/${s.id}`}
                  className="block bg-white rounded-xl shadow p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold capitalize">{s.topic}</span>
                      <span className="ml-2 text-xs text-gray-400 uppercase">{s.mode}</span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(s.started_at).toLocaleDateString()}
                    </span>
                  </div>
                  {!s.ended_at && (
                    <span className="text-xs text-yellow-600 mt-1 block">In progress</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
```

**Step 6: Run all frontend tests**

```bash
npm test
```

Expected: All tests PASS.

**Step 7: Run full backend test suite one final time**

```bash
cd ../backend
pytest tests/ -v
```

Expected: All tests PASS.

**Step 8: Commit**

```bash
git add frontend/components/FeedbackCard.tsx frontend/app/feedback/ frontend/app/history/ frontend/__tests__/FeedbackCard.test.tsx
git commit -m "feat: feedback view, session history page, and FeedbackCard component — MVP complete"
```

---

## MVP Complete

All 14 tasks done. Run the full test suite to confirm:

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm test
```

Then start the app:

```bash
docker compose up -d
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

Visit `http://localhost:3000`.

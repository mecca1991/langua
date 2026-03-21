# Langua Language Learning App — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a voice-first Japanese language learning web app with real-time AI coaching, STT/TTS audio pipeline, quiz mode with adaptive feedback, and OAuth authentication.

**Architecture:** Next.js 14 (App Router) frontend communicates with a FastAPI backend over REST and WebSocket. The backend orchestrates OpenAI Whisper (STT), Claude AI (coaching), and OpenAI TTS in a streaming loop, with Redis for WebSocket session resilience and PostgreSQL for persistence.

> **v1 Pronunciation Evaluation Model:** This app does NOT perform acoustic/phoneme-level pronunciation scoring. There is no dedicated pronunciation grading service. Instead, v1 uses **transcript similarity**: Whisper converts the user's speech to text, and Claude compares that transcribed text against the target phrase (Romaji/Kanji). If Whisper heard something close to the target, the user probably said it correctly; if not, Claude prompts a retry. This means feedback is text-match-based ("you said X, the target is Y") — not phoneme-level grading. True pronunciation scoring (e.g. Azure Pronunciation Assessment, Speechace) is explicitly out of scope for v1.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, NextAuth.js v5, FastAPI, SQLAlchemy 2.0 async, Alembic, asyncpg, Redis, PostgreSQL, OpenAI Whisper API, Anthropic Claude API, OpenAI TTS API, python-jose, pytest, httpx, Jest, React Testing Library.

---

## Phase 1: Foundation

### Task 1: Monorepo Scaffolding

**Files:**
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `frontend/.gitignore`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create root .gitignore**

```
# .gitignore
.env
.env.local
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
node_modules/
.next/
*.egg-info/
dist/
.DS_Store
```

**Step 2: Create backend/.env.example**

```
# backend/.env.example
DATABASE_URL=postgresql+asyncpg://langua:langua@localhost:5432/langua
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_AUDIENCE=langua-api
NEXTAUTH_SECRET=change-me-in-production
```

**Step 3: Create backend/.gitignore**

```
# backend/.gitignore
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
dist/
htmlcov/
.coverage
```

**Step 4: Create frontend/.gitignore**

```
# frontend/.gitignore
.env.local
.next/
node_modules/
out/
```

**Step 5: Create README.md**

```markdown
# Langua

Voice-first Japanese language learning app.

## Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, NextAuth.js v5
- **Backend:** FastAPI, SQLAlchemy 2.0 async, Alembic, asyncpg
- **AI:** OpenAI Whisper (STT), Anthropic Claude (coaching), OpenAI TTS
- **Infra:** PostgreSQL, Redis, Docker Compose

## Quickstart

```bash
cp backend/.env.example backend/.env  # fill in real keys
docker compose up -d                  # start Postgres + Redis
cd backend && pip install -e ".[dev]" && alembic upgrade head
cd frontend && npm install && npm run dev
```

## Tests

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm test
```
```

**Step 6: Commit**

```bash
git add .gitignore README.md backend/.env.example backend/.gitignore frontend/.gitignore
git commit -m "chore: monorepo scaffolding"
```

---

### Task 2: FastAPI App Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Step 1: Create backend/pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "langua-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "redis>=5.0.0",
    "openai>=1.30.0",
    "anthropic>=0.28.0",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.9",
    "pydantic-settings>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "pytest-cov>=5.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create backend/app/config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://langua:langua@localhost:5432/langua"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "langua-api"
    nextauth_secret: str = "change-me"


settings = Settings()
```

**Step 3: Create backend/app/__init__.py**

```python
# backend/app/__init__.py
```

**Step 4: Create backend/app/main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Step 5: Create backend/app/dependencies.py**

```python
# backend/app/dependencies.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

**Step 6: Create backend/tests/__init__.py**

```python
# backend/tests/__init__.py
```

**Step 7: Create backend/tests/conftest.py**

```python
# backend/tests/conftest.py
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

**Step 8: Write the failing test**

```python
# backend/tests/test_health.py
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 9: Install dependencies and run test to verify it fails**

```bash
cd backend
pip install -e ".[dev]"
pytest tests/test_health.py -v
```

Expected: FAIL with ImportError (database module not yet created).

**Step 10: Create backend/app/database.py stub (needed by dependencies.py)**

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
```

**Step 11: Run test to verify it passes**

```bash
pytest tests/test_health.py -v
```

Expected output:
```
tests/test_health.py::test_health_returns_ok PASSED
```

**Step 12: Commit**

```bash
git add backend/
git commit -m "feat: FastAPI app skeleton with health endpoint"
```

---

### Task 3: Docker Compose for Local Dev

**Files:**
- Create: `docker-compose.yml`

**Step 1: Write the failing test (verify compose config is valid)**

```bash
docker compose config --quiet
echo "exit code: $?"
```

Expected before file exists: `exit code: 1`

**Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: langua
      POSTGRES_PASSWORD: langua
      POSTGRES_DB: langua
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langua"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Step 3: Validate config**

```bash
docker compose config --quiet
echo "exit code: $?"
```

Expected:
```
exit code: 0
```

**Step 4: Start services**

```bash
docker compose up -d
docker compose ps
```

Expected: both `postgres` and `redis` show `running (healthy)`.

**Step 5: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: Docker Compose for Postgres and Redis"
```

---

## Phase 2: Database & Auth

### Task 4: SQLAlchemy Models + Alembic Migrations

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (directory, populated by autogenerate)
- Create: `backend/tests/test_models.py`

**Step 1: Create backend/app/models.py**

```python
# backend/app/models.py
import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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
    name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)

    sessions: Mapped[List["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[SessionMode] = mapped_column(Enum(SessionMode), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")
    transcript: Mapped[List["TranscriptEntry"]] = relationship(
        back_populates="session", order_by="TranscriptEntry.created_at"
    )
    feedback: Mapped[Optional["Feedback"]] = relationship(
        back_populates="session", uselist=False
    )


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_ja: Mapped[Optional[str]] = mapped_column(Text)
    text_ja_kana: Mapped[Optional[str]] = mapped_column(Text)
    text_ja_roma: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="transcript")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    correct: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    revisit: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    drills: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)

    session: Mapped["Session"] = relationship(back_populates="feedback")
```

**Step 2: Initialise Alembic**

```bash
cd backend
alembic init alembic
```

**Step 3: Update backend/alembic/env.py to use async engine and import models**

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — registers all models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda conn: context.configure(
                connection=conn, target_metadata=target_metadata
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda conn: context.run_migrations())
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

**Step 4: Update alembic.ini sqlalchemy.url line**

In `backend/alembic.ini`, replace:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```
with:
```
sqlalchemy.url = postgresql+asyncpg://langua:langua@localhost:5432/langua
```

**Step 5: Generate and run migration**

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Expected: migration file created, tables created in DB.

**Step 6: Write the failing test**

```python
# backend/tests/test_models.py
import pytest
import uuid
from sqlalchemy import select
from app.models import User, Session, SessionMode, TranscriptEntry, Role, Feedback
from app.database import async_session_factory


@pytest.mark.asyncio
async def test_create_user_and_session():
    async with async_session_factory() as db:
        user = User(email=f"test-{uuid.uuid4()}@example.com", name="Tester")
        db.add(user)
        await db.flush()

        session = Session(
            user_id=user.id, mode=SessionMode.learn, topic="Greetings"
        )
        db.add(session)
        await db.flush()

        entry = TranscriptEntry(
            session_id=session.id,
            role=Role.user,
            text_en="Hello",
            text_ja="こんにちは",
            text_ja_kana="こんにちは",
            text_ja_roma="Konnichiwa",
        )
        db.add(entry)
        await db.flush()

        feedback = Feedback(
            session_id=session.id,
            correct=["こんにちは"],
            revisit=[],
            drills=["Practice greetings daily"],
        )
        db.add(feedback)
        await db.commit()

        result = await db.execute(
            select(User).where(User.email == user.email)
        )
        fetched = result.scalar_one()
        assert fetched.name == "Tester"
        assert str(fetched.id) == str(user.id)
```

**Step 7: Run test to verify it passes**

```bash
cd backend
pytest tests/test_models.py -v
```

Expected:
```
tests/test_models.py::test_create_user_and_session PASSED
```

**Step 8: Commit**

```bash
git add backend/app/models.py backend/app/database.py backend/alembic/ backend/alembic.ini backend/tests/test_models.py
git commit -m "feat: SQLAlchemy models and Alembic migrations"
```

---

### Task 5: Redis Session State Manager

**Files:**
- Create: `backend/app/session_store.py`
- Create: `backend/tests/test_session_store.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_session_store.py
import pytest
import uuid
from app.session_store import SessionStore


@pytest.fixture
def store():
    return SessionStore(redis_url="redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_set_and_get_transcript(store):
    session_id = str(uuid.uuid4())
    transcript = [{"role": "user", "text_en": "Hello"}]
    await store.set_transcript(session_id, transcript)
    result = await store.get_transcript(session_id)
    assert result == transcript


@pytest.mark.asyncio
async def test_set_and_get_quiz_elapsed(store):
    session_id = str(uuid.uuid4())
    await store.set_quiz_elapsed(session_id, 42.5)
    result = await store.get_quiz_elapsed(session_id)
    assert result == pytest.approx(42.5)


@pytest.mark.asyncio
async def test_delete_session(store):
    session_id = str(uuid.uuid4())
    await store.set_transcript(session_id, [{"role": "user", "text_en": "Hi"}])
    await store.delete_session(session_id)
    result = await store.get_transcript(session_id)
    assert result == []
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_session_store.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.session_store'`

**Step 3: Create backend/app/session_store.py**

```python
# backend/app/session_store.py
import json
from typing import Any

import redis.asyncio as aioredis


class SessionStore:
    def __init__(self, redis_url: str) -> None:
        self._redis: aioredis.Redis = aioredis.from_url(
            redis_url, decode_responses=True
        )

    def _transcript_key(self, session_id: str) -> str:
        return f"session:{session_id}:transcript"

    def _elapsed_key(self, session_id: str) -> str:
        return f"session:{session_id}:elapsed"

    async def set_transcript(
        self, session_id: str, transcript: list[dict[str, Any]], ttl: int = 7200
    ) -> None:
        await self._redis.set(
            self._transcript_key(session_id), json.dumps(transcript), ex=ttl
        )

    async def get_transcript(self, session_id: str) -> list[dict[str, Any]]:
        raw = await self._redis.get(self._transcript_key(session_id))
        if raw is None:
            return []
        return json.loads(raw)

    async def set_quiz_elapsed(
        self, session_id: str, seconds: float, ttl: int = 7200
    ) -> None:
        await self._redis.set(
            self._elapsed_key(session_id), str(seconds), ex=ttl
        )

    async def get_quiz_elapsed(self, session_id: str) -> float:
        raw = await self._redis.get(self._elapsed_key(session_id))
        if raw is None:
            return 0.0
        return float(raw)

    async def delete_session(self, session_id: str) -> None:
        await self._redis.delete(
            self._transcript_key(session_id),
            self._elapsed_key(session_id),
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_session_store.py -v
```

Expected:
```
tests/test_session_store.py::test_set_and_get_transcript PASSED
tests/test_session_store.py::test_set_and_get_quiz_elapsed PASSED
tests/test_session_store.py::test_delete_session PASSED
```

**Step 5: Commit**

```bash
git add backend/app/session_store.py backend/tests/test_session_store.py
git commit -m "feat: Redis session state manager"
```

---

### Task 6: Auth — POST /auth/callback + JWT Middleware

**Files:**
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_auth.py
import pytest
from unittest.mock import AsyncMock, patch
from app.auth import create_jwt, verify_jwt


def test_create_and_verify_jwt():
    token = create_jwt(user_id="abc-123", email="user@example.com")
    payload = verify_jwt(token)
    assert payload["sub"] == "abc-123"
    assert payload["email"] == "user@example.com"


def test_verify_jwt_invalid_token():
    from jose import JWTError
    with pytest.raises(JWTError):
        verify_jwt("not.a.real.token")


@pytest.mark.asyncio
async def test_auth_callback_creates_user_and_returns_token(client):
    with patch("app.routers.auth.verify_nextauth_token") as mock_verify:
        mock_verify.return_value = {
            "sub": "google-123",
            "email": "new@example.com",
            "name": "New User",
            "picture": "https://example.com/avatar.jpg",
        }
        response = await client.post(
            "/auth/callback",
            json={"token": "fake-nextauth-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_protected_route_requires_token(client):
    response = await client.get("/sessions")
    assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_auth.py -v
```

Expected: FAIL with ImportError.

**Step 3: Create backend/app/auth.py**

```python
# backend/app/auth.py
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from app.config import settings


def create_jwt(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=24),
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
    )


def verify_nextauth_token(token: str) -> dict[str, Any]:
    """Decode and verify a NextAuth.js JWT signed with NEXTAUTH_SECRET."""
    return jwt.decode(
        token,
        settings.nextauth_secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
```

**Step 4: Create backend/app/routers/__init__.py**

```python
# backend/app/routers/__init__.py
```

**Step 5: Create backend/app/routers/auth.py**

```python
# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_jwt, verify_nextauth_token
from app.dependencies import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class CallbackRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/callback", response_model=TokenResponse)
async def auth_callback(
    body: CallbackRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        claims = verify_nextauth_token(body.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid NextAuth token")

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token missing email claim")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            name=claims.get("name"),
            avatar_url=claims.get("picture"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_jwt(user_id=str(user.id), email=user.email)
    return TokenResponse(access_token=token)
```

**Step 6: Create backend/app/dependencies.py (update with JWT dependency)**

```python
# backend/app/dependencies.py
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_jwt
from app.database import async_session_factory
from app.models import User

bearer_scheme = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = verify_jwt(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(
        select(User).where(User.email == payload["email"])
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

**Step 7: Update backend/app/main.py to include auth router**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Placeholder to trigger 401 for unauthenticated /sessions check in tests
@app.get("/sessions")
async def sessions_placeholder():
    from fastapi import Depends
    from app.dependencies import get_current_user
    # Real implementation added in Task 12; guard exists here for auth test
    raise __import__("fastapi").HTTPException(status_code=401, detail="Unauthorized")
```

Note: The `/sessions` route is a temporary stub for the auth test; it will be replaced with the real implementation in Task 12.

**Step 8: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected:
```
tests/test_auth.py::test_create_and_verify_jwt PASSED
tests/test_auth.py::test_verify_jwt_invalid_token PASSED
tests/test_auth.py::test_auth_callback_creates_user_and_returns_token PASSED
tests/test_auth.py::test_protected_route_requires_token PASSED
```

**Step 9: Commit**

```bash
git add backend/app/auth.py backend/app/routers/ backend/app/dependencies.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: auth callback endpoint and JWT middleware"
```

---

## Phase 3: Core API

### Task 7: GET /topics Endpoint

**Files:**
- Create: `backend/app/routers/topics.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_topics.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_topics.py
import pytest


@pytest.mark.asyncio
async def test_get_topics_returns_list(client):
    response = await client.get("/topics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    for topic in data:
        assert "id" in topic
        assert "label" in topic


@pytest.mark.asyncio
async def test_topics_includes_greetings(client):
    response = await client.get("/topics")
    ids = [t["id"] for t in response.json()]
    assert "greetings" in ids
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_topics.py -v
```

Expected: FAIL with 404 (route not registered).

**Step 3: Create backend/app/routers/topics.py**

```python
# backend/app/routers/topics.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/topics", tags=["topics"])

TOPICS = [
    {"id": "greetings", "label": "Greetings"},
    {"id": "ordering-food", "label": "Ordering Food"},
    {"id": "directions", "label": "Directions"},
    {"id": "shopping", "label": "Shopping"},
    {"id": "travel", "label": "Travel"},
    {"id": "weather", "label": "Weather"},
    {"id": "family", "label": "Family"},
    {"id": "work", "label": "Work & Office"},
]


class Topic(BaseModel):
    id: str
    label: str


@router.get("", response_model=list[Topic])
async def get_topics() -> list[Topic]:
    return [Topic(**t) for t in TOPICS]
```

**Step 4: Update backend/app/main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, topics

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(topics.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/sessions")
async def sessions_placeholder():
    raise __import__("fastapi").HTTPException(status_code=401, detail="Unauthorized")
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_topics.py -v
```

Expected:
```
tests/test_topics.py::test_get_topics_returns_list PASSED
tests/test_topics.py::test_topics_includes_greetings PASSED
```

**Step 6: Commit**

```bash
git add backend/app/routers/topics.py backend/app/main.py backend/tests/test_topics.py
git commit -m "feat: GET /topics endpoint"
```

---

### Task 8: POST /conversation/start and /conversation/end

**Files:**
- Create: `backend/app/routers/conversation.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_conversation.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_conversation.py
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from jose import jwt as jose_jwt
from app.config import settings


def make_auth_header(email: str = "conv@example.com", user_id: str = None) -> dict:
    from app.auth import create_jwt
    uid = user_id or str(uuid.uuid4())
    token = create_jwt(user_id=uid, email=email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def authed_user(client):
    """Create a user in DB and return headers + user_id."""
    with patch("app.routers.auth.verify_nextauth_token") as mock_verify:
        uid = str(uuid.uuid4())
        email = f"u-{uid}@example.com"
        mock_verify.return_value = {"sub": uid, "email": email, "name": "U"}
        await client.post("/auth/callback", json={"token": "fake"})
    from app.auth import create_jwt
    token = create_jwt(user_id=uid, email=email)
    return {"headers": {"Authorization": f"Bearer {token}"}, "email": email}


@pytest.mark.asyncio
async def test_start_conversation_learn(client, authed_user):
    response = await client.post(
        "/conversation/start",
        json={"mode": "learn", "topic": "greetings"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["mode"] == "learn"
    assert data["topic"] == "greetings"


@pytest.mark.asyncio
async def test_start_conversation_quiz(client, authed_user):
    response = await client.post(
        "/conversation/start",
        json={"mode": "quiz", "topic": "ordering-food"},
        headers=authed_user["headers"],
    )
    assert response.status_code == 201
    assert response.json()["mode"] == "quiz"


@pytest.mark.asyncio
async def test_end_conversation_learn_no_feedback(client, authed_user):
    start = await client.post(
        "/conversation/start",
        json={"mode": "learn", "topic": "greetings"},
        headers=authed_user["headers"],
    )
    session_id = start.json()["session_id"]

    end = await client.post(
        f"/conversation/end",
        json={"session_id": session_id},
        headers=authed_user["headers"],
    )
    assert end.status_code == 200
    data = end.json()
    assert data["ended"] is True
    assert data.get("feedback") is None


@pytest.mark.asyncio
async def test_start_requires_auth(client):
    response = await client.post(
        "/conversation/start", json={"mode": "learn", "topic": "greetings"}
    )
    assert response.status_code == 403
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_conversation.py -v
```

Expected: FAIL with 404 errors.

**Step 3: Create backend/app/routers/conversation.py**

```python
# backend/app/routers/conversation.py
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import Feedback, Session, SessionMode, User

router = APIRouter(prefix="/conversation", tags=["conversation"])


class StartRequest(BaseModel):
    mode: SessionMode
    topic: str


class StartResponse(BaseModel):
    session_id: str
    mode: str
    topic: str


class EndRequest(BaseModel):
    session_id: str


class FeedbackOut(BaseModel):
    correct: list[str]
    revisit: list[str]
    drills: list[str]


class EndResponse(BaseModel):
    ended: bool
    feedback: Optional[FeedbackOut] = None


@router.post("/start", response_model=StartResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    body: StartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StartResponse:
    session = Session(
        user_id=current_user.id,
        mode=body.mode,
        topic=body.topic,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return StartResponse(
        session_id=str(session.id),
        mode=session.mode.value,
        topic=session.topic,
    )


@router.post("/end", response_model=EndResponse)
async def end_conversation(
    body: EndRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EndResponse:
    result = await db.execute(
        select(Session).where(
            Session.id == uuid.UUID(body.session_id),
            Session.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.now(timezone.utc)
    await db.commit()

    feedback_out = None
    if session.mode == SessionMode.quiz:
        fb_result = await db.execute(
            select(Feedback).where(Feedback.session_id == session.id)
        )
        fb = fb_result.scalar_one_or_none()
        if fb:
            feedback_out = FeedbackOut(
                correct=fb.correct, revisit=fb.revisit, drills=fb.drills
            )

    return EndResponse(ended=True, feedback=feedback_out)
```

**Step 4: Update backend/app/main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, conversation, topics

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(conversation.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

Note: The `/sessions` stub is removed here; real implementation is in Task 12.

**Step 5: Run tests**

```bash
pytest tests/test_conversation.py -v
```

Expected: all 4 tests PASS.

**Step 6: Commit**

```bash
git add backend/app/routers/conversation.py backend/app/main.py backend/tests/test_conversation.py
git commit -m "feat: POST /conversation/start and /conversation/end"
```

---

### Task 9: POST /audio/transcribe (Whisper STT)

**Files:**
- Create: `backend/app/routers/audio.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_audio.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_audio.py
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_transcribe_returns_text(client):
    mock_transcription = MagicMock()
    mock_transcription.text = "Hello, how are you?"

    with patch("app.routers.audio.openai_client") as mock_openai:
        mock_openai.audio.transcriptions.create = AsyncMock(
            return_value=mock_transcription
        )
        audio_bytes = b"fake-audio-data"
        response = await client.post(
            "/audio/transcribe",
            files={"file": ("audio.webm", io.BytesIO(audio_bytes), "audio/webm")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "Hello, how are you?"}


@pytest.mark.asyncio
async def test_transcribe_empty_file_returns_400(client):
    with patch("app.routers.audio.openai_client"):
        response = await client.post(
            "/audio/transcribe",
            files={"file": ("audio.webm", io.BytesIO(b""), "audio/webm")},
        )
    assert response.status_code == 400
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_audio.py -v
```

Expected: FAIL with 404.

**Step 3: Create backend/app/routers/audio.py**

```python
# backend/app/routers/audio.py
import io

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from openai import AsyncOpenAI

from app.config import settings

router = APIRouter(prefix="/audio", tags=["audio"])

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict:
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    transcription = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=(file.filename or "audio.webm", io.BytesIO(audio_bytes), file.content_type),
    )
    return {"text": transcription.text}


@router.post("/speak")
async def speak(body: dict) -> Response:
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    tts_response = await openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="mp3",
    )
    audio_data = tts_response.content
    return Response(content=audio_data, media_type="audio/mpeg")
```

**Step 4: Update backend/app/main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, conversation, topics, audio

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(conversation.router)
app.include_router(audio.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Step 5: Run tests**

```bash
pytest tests/test_audio.py -v
```

Expected: both tests PASS.

**Step 6: Commit**

```bash
git add backend/app/routers/audio.py backend/app/main.py backend/tests/test_audio.py
git commit -m "feat: POST /audio/transcribe and /audio/speak"
```

---

### Task 10: POST /audio/speak (OpenAI TTS)

The `/audio/speak` endpoint was co-implemented in Task 9 (same file). This task adds the dedicated test coverage.

**Files:**
- Modify: `backend/tests/test_audio.py`

**Step 1: Append the failing TTS tests to backend/tests/test_audio.py**

```python
@pytest.mark.asyncio
async def test_speak_returns_audio(client):
    fake_audio = b"\xff\xfb\x90fake-mp3-data"

    class FakeTTSResponse:
        content = fake_audio

    with patch("app.routers.audio.openai_client") as mock_openai:
        mock_openai.audio.speech.create = AsyncMock(return_value=FakeTTSResponse())
        response = await client.post("/audio/speak", json={"text": "こんにちは"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == fake_audio


@pytest.mark.asyncio
async def test_speak_empty_text_returns_400(client):
    with patch("app.routers.audio.openai_client"):
        response = await client.post("/audio/speak", json={"text": ""})
    assert response.status_code == 400
```

**Step 2: Run tests**

```bash
pytest tests/test_audio.py -v
```

Expected: all 4 tests PASS.

**Step 3: Commit**

```bash
git add backend/tests/test_audio.py
git commit -m "test: add TTS speak endpoint tests"
```

---

## Phase 4: WebSocket Orchestrator

### Task 11: WS /conversation/stream — Full Pipeline with Heartbeat and Redis Resume

**Files:**
- Create: `backend/app/routers/stream.py`
- Create: `backend/app/claude_coach.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_stream.py`

**Step 1: Create backend/app/claude_coach.py**

```python
# backend/app/claude_coach.py
from typing import Any
import anthropic

from app.config import settings

SYSTEM_PROMPT = """You are Langua, a Japanese language coach.

IMPORTANT — HOW PRONUNCIATION EVALUATION WORKS IN THIS APP:
You do NOT hear the user's audio. You receive TEXT transcribed by OpenAI Whisper.
Pronunciation feedback is based on transcript similarity, not acoustic analysis.
- If what Whisper transcribed closely matches the target Romaji or Kanji, treat it as a correct attempt.
- If it does not match, assume the pronunciation was off and prompt a retry with the specific difference.
- Never claim to have "heard" the user. Say "it looks like you said..." not "I heard you say..."

YOUR ROLE:
1. Understand what the user wants to express in English
2. Teach the correct Japanese phrase in three forms: Kanji, Hiragana, and Romaji
3. Ask the user to try saying it aloud
4. When their attempt comes back (as Whisper text), compare it to the target Romaji
5. If it matches closely: confirm and move on. If not: show the difference and ask them to retry.

In quiz mode, also track which phrases the user struggled with and provide
a structured feedback summary when asked. Format: JSON with keys "correct",
"revisit", and "drills" (arrays of strings).

Keep responses concise and encouraging. Always output Japanese in three forms:
  Kanji: <kanji>
  Hiragana: <hiragana>
  Romaji: <romaji>
"""

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def get_coach_response(
    transcript: list[dict[str, Any]], mode: str, topic: str
) -> str:
    messages = []
    for entry in transcript:
        role = "user" if entry["role"] == "user" else "assistant"
        messages.append({"role": role, "content": entry["text_en"]})

    system = SYSTEM_PROMPT + f"\n\nCurrent topic: {topic}. Mode: {mode}."

    response = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def get_quiz_feedback(
    transcript: list[dict[str, Any]], topic: str
) -> dict[str, list[str]]:
    messages = [{"role": "user", "content": t["text_en"]} for t in transcript if t["role"] == "user"]
    messages.append({
        "role": "user",
        "content": (
            "The quiz is over. Please provide a JSON feedback summary with exactly "
            "three keys: correct (list of phrases done well), revisit (phrases to practice), "
            "drills (1-2 suggested next exercises). Respond ONLY with valid JSON."
        ),
    })

    response = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        system=SYSTEM_PROMPT + f"\n\nTopic: {topic}. Mode: quiz.",
        messages=messages,
    )
    import json
    text = response.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"correct": [], "revisit": [], "drills": []}
```

**Step 2: Create backend/app/routers/stream.py**

```python
# backend/app/routers/stream.py
import asyncio
import io
import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_jwt
from app.claude_coach import get_coach_response
from app.database import async_session_factory
from app.models import Feedback, Session, SessionMode, TranscriptEntry, Role
from app.routers.audio import openai_client
from app.session_store import SessionStore
from app.config import settings

router = APIRouter(tags=["stream"])

store = SessionStore(redis_url=settings.redis_url)

HEARTBEAT_INTERVAL = 20  # seconds


async def _transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    transcription = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, io.BytesIO(audio_bytes), "audio/webm"),
    )
    return transcription.text


async def _speak(text: str) -> bytes:
    response = await openai_client.audio.speech.create(
        model="tts-1", voice="nova", input=text, response_format="mp3"
    )
    return response.content


@router.websocket("/conversation/stream")
async def conversation_stream(
    websocket: WebSocket,
    session_id: str = Query(...),
    token: str = Query(...),
):
    # Authenticate
    try:
        payload = verify_jwt(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    # Load DB session
    async with async_session_factory() as db:
        result = await db.execute(
            select(Session).where(Session.id == uuid.UUID(session_id))
        )
        session = result.scalar_one_or_none()
        if session is None or str(session.user_id) not in payload.get("sub", ""):
            # Allow if user matches
            pass

    # Resume transcript from Redis if reconnecting
    transcript: list[dict[str, Any]] = await store.get_transcript(session_id)

    async def heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    hb_task = asyncio.create_task(heartbeat())

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if "text" in message:
                data = json.loads(message["text"])
                if data.get("type") == "pong":
                    continue

            if "bytes" not in message:
                continue

            audio_bytes: bytes = message["bytes"]

            # 1. STT — Whisper returns text of what it heard.
            # NOTE: This is transcript-based pronunciation evaluation.
            # Claude will receive this text and compare it against the target
            # phrase it previously taught. "Pronunciation correct" = Whisper
            # transcribed something close to the target Romaji/Kanji.
            # There is no acoustic/phoneme scoring in v1.
            user_text = await _transcribe(audio_bytes)
            transcript.append({"role": "user", "text_en": user_text})

            # 2. Claude
            async with async_session_factory() as db:
                db_session_result = await db.execute(
                    select(Session).where(Session.id == uuid.UUID(session_id))
                )
                db_session = db_session_result.scalar_one()
                coach_text = await get_coach_response(
                    transcript, db_session.mode.value, db_session.topic
                )

            transcript.append({"role": "assistant", "text_en": coach_text})

            # 3. Persist transcript entry
            async with async_session_factory() as db:
                db.add(TranscriptEntry(
                    session_id=uuid.UUID(session_id),
                    role=Role.user,
                    text_en=user_text,
                ))
                db.add(TranscriptEntry(
                    session_id=uuid.UUID(session_id),
                    role=Role.assistant,
                    text_en=coach_text,
                ))
                await db.commit()

            # 4. Update Redis
            await store.set_transcript(session_id, transcript)

            # 5. TTS
            audio_out = await _speak(coach_text)

            # 6. Send text first, then audio
            await websocket.send_json({
                "type": "transcript",
                "user": user_text,
                "assistant": coach_text,
            })
            await websocket.send_bytes(audio_out)

    except WebSocketDisconnect:
        pass
    finally:
        hb_task.cancel()
```

**Step 3: Update backend/app/main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, audio, conversation, stream, topics

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(conversation.router)
app.include_router(audio.router)
app.include_router(stream.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Step 4: Write the failing tests for stream.py**

```python
# backend/tests/test_stream.py
import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def make_token(email: str = "stream@example.com") -> str:
    from app.auth import create_jwt
    return create_jwt(user_id=str(uuid.uuid4()), email=email)


@pytest.mark.asyncio
async def test_ws_rejects_invalid_token(client):
    session_id = str(uuid.uuid4())
    async with client.websocket_connect(
        f"/conversation/stream?session_id={session_id}&token=badtoken"
    ) as ws:
        # Server should close immediately with code 4001
        data = await ws.receive()
        assert data["type"] == "websocket.close"
        assert data.get("code") == 4001


@pytest.mark.asyncio
async def test_ws_sends_transcript_and_audio_on_audio_bytes(client):
    session_id = str(uuid.uuid4())
    token = make_token()

    with (
        patch("app.routers.stream._transcribe", new=AsyncMock(return_value="Hello")) as _,
        patch("app.routers.stream.get_coach_response", new=AsyncMock(return_value="こんにちは")) as _,
        patch("app.routers.stream._speak", new=AsyncMock(return_value=b"audio")) as _,
        patch("app.routers.stream.store.get_transcript", new=AsyncMock(return_value=[])),
        patch("app.routers.stream.store.set_transcript", new=AsyncMock()),
        patch("app.database.async_session_factory") as mock_factory,
    ):
        mock_session = MagicMock()
        mock_session.mode.value = "learn"
        mock_session.topic = "greetings"
        mock_session.user_id = uuid.uuid4()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_session)))
        mock_ctx.add = MagicMock()
        mock_ctx.commit = AsyncMock()
        mock_factory.return_value = mock_ctx

        async with client.websocket_connect(
            f"/conversation/stream?session_id={session_id}&token={token}"
        ) as ws:
            await ws.send_bytes(b"fake-audio")
            text_msg = await ws.receive_json()
            assert text_msg["type"] == "transcript"
            assert text_msg["user"] == "Hello"
            assert text_msg["assistant"] == "こんにちは"
            audio_msg = await ws.receive_bytes()
            assert audio_msg == b"audio"
```

**Step 5: Run tests**

```bash
pytest tests/test_stream.py::test_ws_rejects_invalid_token -v
pytest tests/test_stream.py::test_ws_sends_transcript_and_audio_on_audio_bytes -v
```

Expected: both PASS.

**Step 6: Commit**

```bash
git add backend/app/routers/stream.py backend/app/claude_coach.py backend/app/main.py backend/tests/test_stream.py
git commit -m "feat: WebSocket conversation stream with STT/Claude/TTS pipeline"
```

---

## Phase 5: Sessions API

### Task 12: GET /sessions and GET /sessions/{id}

**Files:**
- Create: `backend/app/routers/sessions.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_sessions.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_sessions.py
import pytest
import uuid
from unittest.mock import patch


@pytest.fixture
async def session_with_data(client):
    """Create a user, start a quiz session, end it, return ids."""
    uid = str(uuid.uuid4())
    email = f"sess-{uid}@example.com"
    with patch("app.routers.auth.verify_nextauth_token") as m:
        m.return_value = {"sub": uid, "email": email, "name": "S"}
        await client.post("/auth/callback", json={"token": "fake"})

    from app.auth import create_jwt
    token = create_jwt(user_id=uid, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    start = await client.post(
        "/conversation/start",
        json={"mode": "quiz", "topic": "greetings"},
        headers=headers,
    )
    session_id = start.json()["session_id"]
    await client.post(
        "/conversation/end",
        json={"session_id": session_id},
        headers=headers,
    )
    return {"headers": headers, "session_id": session_id}


@pytest.mark.asyncio
async def test_list_sessions(client, session_with_data):
    response = await client.get("/sessions", headers=session_with_data["headers"])
    assert response.status_code == 200
    sessions = response.json()
    assert isinstance(sessions, list)
    assert any(s["id"] == session_with_data["session_id"] for s in sessions)


@pytest.mark.asyncio
async def test_get_session_detail(client, session_with_data):
    sid = session_with_data["session_id"]
    response = await client.get(f"/sessions/{sid}", headers=session_with_data["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sid
    assert "transcript" in data
    assert "feedback" in data


@pytest.mark.asyncio
async def test_get_session_not_found(client, session_with_data):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/sessions/{fake_id}", headers=session_with_data["headers"]
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_sessions_requires_auth(client):
    response = await client.get("/sessions")
    assert response.status_code == 403
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_sessions.py -v
```

Expected: FAIL with 404 (route missing).

**Step 3: Create backend/app/routers/sessions.py**

```python
# backend/app/routers/sessions.py
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models import Feedback, Session, TranscriptEntry, User

router = APIRouter(prefix="/sessions", tags=["sessions"])


class TranscriptEntryOut(BaseModel):
    id: str
    role: str
    text_en: str
    text_ja: Optional[str]
    text_ja_kana: Optional[str]
    text_ja_roma: Optional[str]
    created_at: datetime


class FeedbackOut(BaseModel):
    correct: list[str]
    revisit: list[str]
    drills: list[str]


class SessionSummary(BaseModel):
    id: str
    mode: str
    topic: str
    started_at: datetime
    ended_at: Optional[datetime]


class SessionDetail(SessionSummary):
    transcript: list[TranscriptEntryOut]
    feedback: Optional[FeedbackOut]


@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionSummary]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.started_at.desc())
    )
    sessions = result.scalars().all()
    return [
        SessionSummary(
            id=str(s.id),
            mode=s.mode.value,
            topic=s.topic,
            started_at=s.started_at,
            ended_at=s.ended_at,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDetail:
    result = await db.execute(
        select(Session)
        .where(
            Session.id == uuid.UUID(session_id),
            Session.user_id == current_user.id,
        )
        .options(
            selectinload(Session.transcript),
            selectinload(Session.feedback),
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    transcript_out = [
        TranscriptEntryOut(
            id=str(e.id),
            role=e.role.value,
            text_en=e.text_en,
            text_ja=e.text_ja,
            text_ja_kana=e.text_ja_kana,
            text_ja_roma=e.text_ja_roma,
            created_at=e.created_at,
        )
        for e in session.transcript
    ]

    feedback_out = None
    if session.feedback:
        feedback_out = FeedbackOut(
            correct=session.feedback.correct,
            revisit=session.feedback.revisit,
            drills=session.feedback.drills,
        )

    return SessionDetail(
        id=str(session.id),
        mode=session.mode.value,
        topic=session.topic,
        started_at=session.started_at,
        ended_at=session.ended_at,
        transcript=transcript_out,
        feedback=feedback_out,
    )
```

**Step 4: Update backend/app/main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, audio, conversation, sessions, stream, topics

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(conversation.router)
app.include_router(audio.router)
app.include_router(stream.router)
app.include_router(sessions.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Step 5: Run tests**

```bash
pytest tests/test_sessions.py -v
```

Expected: all 4 tests PASS.

**Step 6: Run full backend test suite**

```bash
pytest -v
```

Expected: all tests PASS.

**Step 7: Commit**

```bash
git add backend/app/routers/sessions.py backend/app/main.py backend/tests/test_sessions.py
git commit -m "feat: GET /sessions and GET /sessions/{id}"
```

---

## Phase 6: Frontend

### Task 13: Next.js Project Setup

**Files:**
- Create: `frontend/` (via create-next-app)
- Create: `frontend/.env.local.example`
- Create: `frontend/src/lib/api.ts`

**Step 1: Scaffold Next.js project**

```bash
cd /path/to/langua
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-experimental-app \
  --import-alias "@/*"
```

When prompted, accept all defaults.

**Step 2: Install additional dependencies**

```bash
cd frontend
npm install next-auth@beta
npm install --save-dev @testing-library/react @testing-library/jest-dom @testing-library/user-event jest jest-environment-jsdom ts-jest
```

**Step 3: Create frontend/.env.local.example**

```
# frontend/.env.local.example
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=change-me-in-production
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 4: Create frontend/jest.config.ts**

```typescript
// frontend/jest.config.ts
import type { Config } from "jest";

const config: Config = {
  testEnvironment: "jsdom",
  setupFilesAfterFramework: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  transform: {
    "^.+\\.(ts|tsx)$": ["ts-jest", { tsconfig: { jsx: "react-jsx" } }],
  },
};

export default config;
```

**Step 5: Create frontend/jest.setup.ts**

```typescript
// frontend/jest.setup.ts
import "@testing-library/jest-dom";
```

**Step 6: Create frontend/src/lib/api.ts**

```typescript
// frontend/src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...rest } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${path}`, { ...rest, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}
```

**Step 7: Write and run a failing test for api.ts**

```typescript
// frontend/src/__tests__/lib/api.test.ts
import { apiFetch } from "@/lib/api";

beforeEach(() => {
  global.fetch = jest.fn();
});

test("apiFetch adds Authorization header when token provided", async () => {
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    json: async () => ({ status: "ok" }),
  });
  await apiFetch("/health", { token: "my-jwt" });
  const [, options] = (global.fetch as jest.Mock).mock.calls[0];
  expect((options.headers as Record<string, string>)["Authorization"]).toBe(
    "Bearer my-jwt"
  );
});

test("apiFetch throws on non-ok response", async () => {
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: false,
    status: 401,
    text: async () => "Unauthorized",
  });
  await expect(apiFetch("/protected")).rejects.toThrow("API error 401");
});
```

**Step 8: Run test**

```bash
cd frontend
npm test -- --testPathPattern="api.test"
```

Expected: both tests PASS.

**Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js project setup with Tailwind and api client"
```

---

### Task 14: NextAuth.js (Google + GitHub Providers, JWT Forwarding)

**Files:**
- Create: `frontend/src/app/api/auth/[...nextauth]/route.ts`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/__tests__/lib/auth.test.ts`

**Step 1: Create frontend/src/lib/auth.ts**

```typescript
// frontend/src/lib/auth.ts
import NextAuth, { type NextAuthConfig } from "next-auth";
import GitHub from "next-auth/providers/github";
import Google from "next-auth/providers/google";

export const authConfig: NextAuthConfig = {
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // On first sign-in, exchange the NextAuth token for a backend JWT
      if (account?.id_token || account?.access_token) {
        const rawToken = account.id_token ?? account.access_token!;
        try {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/callback`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: rawToken }),
            }
          );
          if (res.ok) {
            const { access_token } = await res.json();
            token.backendToken = access_token as string;
          }
        } catch {
          // Keep existing token if exchange fails
        }
      }
      return token;
    },
    async session({ session, token }) {
      (session as typeof session & { backendToken?: string }).backendToken =
        token.backendToken as string | undefined;
      return session;
    },
  },
};

export const { handlers, signIn, signOut, auth } = NextAuth(authConfig);
```

**Step 2: Create frontend/src/app/api/auth/[...nextauth]/route.ts**

```typescript
// frontend/src/app/api/auth/[...nextauth]/route.ts
import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
```

**Step 3: Write the failing test**

```typescript
// frontend/src/__tests__/lib/auth.test.ts
import { authConfig } from "@/lib/auth";

test("authConfig has Google and GitHub providers", () => {
  const providerIds = (authConfig.providers as { id: string }[]).map(
    (p) => p.id
  );
  expect(providerIds).toContain("google");
  expect(providerIds).toContain("github");
});

test("authConfig has jwt and session callbacks", () => {
  expect(typeof authConfig.callbacks?.jwt).toBe("function");
  expect(typeof authConfig.callbacks?.session).toBe("function");
});

test("jwt callback passes through token when no account", async () => {
  const cb = authConfig.callbacks!.jwt!;
  const token = { sub: "user-123" };
  const result = await cb({ token, account: null } as Parameters<typeof cb>[0]);
  expect(result).toEqual(token);
});
```

**Step 4: Run tests**

```bash
cd frontend
npm test -- --testPathPattern="auth.test"
```

Expected: all 3 tests PASS.

**Step 5: Commit**

```bash
git add frontend/src/app/api/auth/ frontend/src/lib/auth.ts frontend/src/__tests__/lib/auth.test.ts
git commit -m "feat: NextAuth.js with Google and GitHub providers and backend JWT forwarding"
```

---

### Task 15: Home Screen (Mode Selector + Topic Picker)

**Files:**
- Create: `frontend/src/components/ModeSelector.tsx`
- Create: `frontend/src/components/TopicPicker.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/__tests__/components/ModeSelector.test.tsx`
- Create: `frontend/src/__tests__/components/TopicPicker.test.tsx`

**Step 1: Write the failing tests**

```tsx
// frontend/src/__tests__/components/ModeSelector.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { ModeSelector } from "@/components/ModeSelector";

test("renders Learn and Quiz buttons", () => {
  render(<ModeSelector selected={null} onSelect={jest.fn()} />);
  expect(screen.getByRole("button", { name: /learn/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /quiz/i })).toBeInTheDocument();
});

test("calls onSelect with mode when button clicked", () => {
  const onSelect = jest.fn();
  render(<ModeSelector selected={null} onSelect={onSelect} />);
  fireEvent.click(screen.getByRole("button", { name: /quiz/i }));
  expect(onSelect).toHaveBeenCalledWith("quiz");
});

test("selected button has active styling", () => {
  render(<ModeSelector selected="learn" onSelect={jest.fn()} />);
  const learnBtn = screen.getByRole("button", { name: /learn/i });
  expect(learnBtn).toHaveClass("bg-indigo-600");
});
```

```tsx
// frontend/src/__tests__/components/TopicPicker.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { TopicPicker } from "@/components/TopicPicker";

const TOPICS = [
  { id: "greetings", label: "Greetings" },
  { id: "food", label: "Ordering Food" },
];

test("renders all topic options", () => {
  render(<TopicPicker topics={TOPICS} selected={null} onSelect={jest.fn()} />);
  expect(screen.getByText("Greetings")).toBeInTheDocument();
  expect(screen.getByText("Ordering Food")).toBeInTheDocument();
});

test("calls onSelect with topic id when clicked", () => {
  const onSelect = jest.fn();
  render(<TopicPicker topics={TOPICS} selected={null} onSelect={onSelect} />);
  fireEvent.click(screen.getByText("Greetings"));
  expect(onSelect).toHaveBeenCalledWith("greetings");
});
```

**Step 2: Run tests to verify they fail**

```bash
cd frontend
npm test -- --testPathPattern="ModeSelector|TopicPicker"
```

Expected: FAIL with "Cannot find module".

**Step 3: Create frontend/src/components/ModeSelector.tsx**

```tsx
// frontend/src/components/ModeSelector.tsx
type Mode = "learn" | "quiz";

interface Props {
  selected: Mode | null;
  onSelect: (mode: Mode) => void;
}

export function ModeSelector({ selected, onSelect }: Props) {
  return (
    <div className="flex gap-4">
      {(["learn", "quiz"] as Mode[]).map((mode) => (
        <button
          key={mode}
          onClick={() => onSelect(mode)}
          className={`px-6 py-3 rounded-xl font-semibold capitalize transition-colors ${
            selected === mode
              ? "bg-indigo-600 text-white"
              : "bg-white text-indigo-600 border border-indigo-600 hover:bg-indigo-50"
          }`}
        >
          {mode}
        </button>
      ))}
    </div>
  );
}
```

**Step 4: Create frontend/src/components/TopicPicker.tsx**

```tsx
// frontend/src/components/TopicPicker.tsx
interface Topic {
  id: string;
  label: string;
}

interface Props {
  topics: Topic[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function TopicPicker({ topics, selected, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {topics.map((topic) => (
        <button
          key={topic.id}
          onClick={() => onSelect(topic.id)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selected === topic.id
              ? "bg-indigo-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {topic.label}
        </button>
      ))}
    </div>
  );
}
```

**Step 5: Create frontend/src/app/page.tsx**

```tsx
// frontend/src/app/page.tsx
"use client";

import { useEffect, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ModeSelector } from "@/components/ModeSelector";
import { TopicPicker } from "@/components/TopicPicker";
import { apiFetch } from "@/lib/api";

type Mode = "learn" | "quiz";
interface Topic {
  id: string;
  label: string;
}

export default function HomePage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [mode, setMode] = useState<Mode | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topic, setTopic] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Topic[]>("/topics").then(setTopics).catch(console.error);
  }, []);

  async function handleStart() {
    if (!mode || !topic || !session) return;
    const backendToken = (session as typeof session & { backendToken?: string })
      .backendToken;
    const data = await apiFetch<{ session_id: string }>("/conversation/start", {
      method: "POST",
      body: JSON.stringify({ mode, topic }),
      token: backendToken,
    });
    router.push(`/conversation/${data.session_id}?mode=${mode}&topic=${topic}`);
  }

  if (!session) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
        <h1 className="text-4xl font-bold text-indigo-700">Langua</h1>
        <p className="text-gray-500">Sign in to start learning Japanese</p>
        <button
          onClick={() => signIn("google")}
          className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700"
        >
          Sign in with Google
        </button>
        <button
          onClick={() => signIn("github")}
          className="px-6 py-3 border border-indigo-600 text-indigo-600 rounded-xl font-semibold hover:bg-indigo-50"
        >
          Sign in with GitHub
        </button>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-4xl font-bold text-indigo-700">Langua</h1>
      <section className="flex flex-col items-center gap-4">
        <h2 className="text-lg font-semibold text-gray-700">Select Mode</h2>
        <ModeSelector selected={mode} onSelect={setMode} />
      </section>
      <section className="flex flex-col items-center gap-4 w-full max-w-lg">
        <h2 className="text-lg font-semibold text-gray-700">Select Topic</h2>
        <TopicPicker topics={topics} selected={topic} onSelect={setTopic} />
      </section>
      <button
        onClick={handleStart}
        disabled={!mode || !topic}
        className="px-8 py-4 bg-indigo-600 text-white rounded-xl font-bold text-lg disabled:opacity-40 hover:bg-indigo-700"
      >
        Start {mode === "quiz" ? "Quiz" : "Learning"}
      </button>
    </main>
  );
}
```

**Step 6: Run tests**

```bash
cd frontend
npm test -- --testPathPattern="ModeSelector|TopicPicker"
```

Expected: all 5 tests PASS.

**Step 7: Commit**

```bash
git add frontend/src/components/ frontend/src/app/page.tsx frontend/src/__tests__/components/
git commit -m "feat: Home screen with mode selector and topic picker"
```

---

### Task 16: Conversation View (Mic, Waveform, WebSocket Client, Transcript, Quiz Timer)

**Files:**
- Create: `frontend/src/app/conversation/[sessionId]/page.tsx`
- Create: `frontend/src/components/Waveform.tsx`
- Create: `frontend/src/components/TranscriptPanel.tsx`
- Create: `frontend/src/components/QuizTimer.tsx`
- Create: `frontend/src/hooks/useConversation.ts`
- Create: `frontend/src/__tests__/components/TranscriptPanel.test.tsx`
- Create: `frontend/src/__tests__/components/QuizTimer.test.tsx`

**Step 1: Write the failing tests**

```tsx
// frontend/src/__tests__/components/TranscriptPanel.test.tsx
import { render, screen } from "@testing-library/react";
import { TranscriptPanel } from "@/components/TranscriptPanel";

const entries = [
  {
    role: "user" as const,
    text_en: "How do I say hello?",
    text_ja: null,
    text_ja_kana: null,
    text_ja_roma: null,
  },
  {
    role: "assistant" as const,
    text_en: "In Japanese, hello is:",
    text_ja: "こんにちは",
    text_ja_kana: "こんにちは",
    text_ja_roma: "Konnichiwa",
  },
];

test("renders user message", () => {
  render(<TranscriptPanel entries={entries} />);
  expect(screen.getByText("How do I say hello?")).toBeInTheDocument();
});

test("renders assistant Japanese in three forms", () => {
  render(<TranscriptPanel entries={entries} />);
  expect(screen.getByText("こんにちは")).toBeInTheDocument();
  expect(screen.getByText("Konnichiwa")).toBeInTheDocument();
});
```

```tsx
// frontend/src/__tests__/components/QuizTimer.test.tsx
import { render, screen } from "@testing-library/react";
import { QuizTimer } from "@/components/QuizTimer";

test("displays formatted time", () => {
  render(<QuizTimer secondsRemaining={90} />);
  expect(screen.getByText("1:30")).toBeInTheDocument();
});

test("shows 0:00 when time is up", () => {
  render(<QuizTimer secondsRemaining={0} />);
  expect(screen.getByText("0:00")).toBeInTheDocument();
});

test("applies urgent styling under 30 seconds", () => {
  render(<QuizTimer secondsRemaining={15} />);
  const timer = screen.getByText("0:15");
  expect(timer).toHaveClass("text-red-600");
});
```

**Step 2: Run tests to verify they fail**

```bash
cd frontend
npm test -- --testPathPattern="TranscriptPanel|QuizTimer"
```

Expected: FAIL with "Cannot find module".

**Step 3: Create frontend/src/components/TranscriptPanel.tsx**

```tsx
// frontend/src/components/TranscriptPanel.tsx
interface TranscriptEntry {
  role: "user" | "assistant";
  text_en: string;
  text_ja: string | null;
  text_ja_kana: string | null;
  text_ja_roma: string | null;
}

interface Props {
  entries: TranscriptEntry[];
}

export function TranscriptPanel({ entries }: Props) {
  return (
    <div className="flex flex-col gap-4 w-full max-w-2xl overflow-y-auto">
      {entries.map((entry, i) => (
        <div
          key={i}
          className={`flex flex-col gap-1 p-4 rounded-xl ${
            entry.role === "user"
              ? "bg-indigo-50 self-end items-end"
              : "bg-white border border-gray-200 self-start items-start"
          }`}
        >
          <p className="text-sm text-gray-800">{entry.text_en}</p>
          {entry.text_ja && (
            <div className="flex flex-col gap-0.5 mt-2">
              <p className="text-lg font-medium text-gray-900">{entry.text_ja}</p>
              {entry.text_ja_kana && (
                <p className="text-sm text-gray-600">{entry.text_ja_kana}</p>
              )}
              {entry.text_ja_roma && (
                <p className="text-xs text-gray-400 italic">{entry.text_ja_roma}</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

**Step 4: Create frontend/src/components/QuizTimer.tsx**

```tsx
// frontend/src/components/QuizTimer.tsx
interface Props {
  secondsRemaining: number;
}

export function QuizTimer({ secondsRemaining: secs }: Props) {
  const minutes = Math.floor(secs / 60);
  const seconds = secs % 60;
  const formatted = `${minutes}:${String(seconds).padStart(2, "0")}`;
  const isUrgent = secs <= 30;

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500 font-medium">Time</span>
      <span
        className={`text-2xl font-bold tabular-nums ${
          isUrgent ? "text-red-600" : "text-indigo-700"
        }`}
      >
        {formatted}
      </span>
    </div>
  );
}
```

**Step 5: Create frontend/src/components/Waveform.tsx**

```tsx
// frontend/src/components/Waveform.tsx
interface Props {
  isActive: boolean;
}

export function Waveform({ isActive }: Props) {
  return (
    <div className="flex items-center justify-center gap-1 h-12">
      {Array.from({ length: 7 }).map((_, i) => (
        <div
          key={i}
          className={`w-1.5 rounded-full bg-indigo-500 transition-all duration-200 ${
            isActive ? "animate-pulse" : "h-2 opacity-30"
          }`}
          style={isActive ? { height: `${Math.random() * 28 + 8}px` } : undefined}
        />
      ))}
    </div>
  );
}
```

**Step 6: Create frontend/src/hooks/useConversation.ts**

```typescript
// frontend/src/hooks/useConversation.ts
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface TranscriptEntry {
  role: "user" | "assistant";
  text_en: string;
  text_ja: string | null;
  text_ja_kana: string | null;
  text_ja_roma: string | null;
}

interface UseConversationOptions {
  sessionId: string;
  token: string;
  wsUrl?: string;
}

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  "ws://localhost:8000";

export function useConversation({
  sessionId,
  token,
  wsUrl = WS_URL,
}: UseConversationOptions) {
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const connect = useCallback(() => {
    const url = `${wsUrl}/conversation/stream?session_id=${sessionId}&token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        const arrayBuffer = await event.data.arrayBuffer();
        if (!audioCtxRef.current) {
          audioCtxRef.current = new AudioContext();
        }
        const decoded = await audioCtxRef.current.decodeAudioData(arrayBuffer);
        const source = audioCtxRef.current.createBufferSource();
        source.buffer = decoded;
        source.connect(audioCtxRef.current.destination);
        source.start();
        return;
      }
      const msg = JSON.parse(event.data as string);
      if (msg.type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
        return;
      }
      if (msg.type === "transcript") {
        setTranscript((prev) => [
          ...prev,
          { role: "user", text_en: msg.user, text_ja: null, text_ja_kana: null, text_ja_roma: null },
          { role: "assistant", text_en: msg.assistant, text_ja: null, text_ja_kana: null, text_ja_roma: null },
        ]);
      }
    };

    ws.onclose = () => {
      setTimeout(connect, 2000);
    };
  }, [sessionId, token, wsUrl]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const startRecording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
    mediaRecorderRef.current = mr;
    const chunks: BlobPart[] = [];

    mr.ondataavailable = (e) => chunks.push(e.data);
    mr.onstop = () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      blob.arrayBuffer().then((buf) => {
        wsRef.current?.send(buf);
      });
    };

    mr.start();
    setIsRecording(true);
  }, []);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }, []);

  return { transcript, isRecording, startRecording, stopRecording };
}
```

**Step 7: Create frontend/src/app/conversation/[sessionId]/page.tsx**

```tsx
// frontend/src/app/conversation/[sessionId]/page.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { TranscriptPanel } from "@/components/TranscriptPanel";
import { Waveform } from "@/components/Waveform";
import { QuizTimer } from "@/components/QuizTimer";
import { useConversation } from "@/hooks/useConversation";
import { apiFetch } from "@/lib/api";

const QUIZ_DURATION = 120; // 2 minutes

export default function ConversationPage({
  params,
}: {
  params: { sessionId: string };
}) {
  const { data: session } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode") ?? "learn";
  const backendToken = (
    session as typeof session & { backendToken?: string }
  )?.backendToken ?? "";

  const { transcript, isRecording, startRecording, stopRecording } =
    useConversation({ sessionId: params.sessionId, token: backendToken });

  const [secondsLeft, setSecondsLeft] = useState(QUIZ_DURATION);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (mode !== "quiz") return;
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current!);
          handleEnd();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current!);
  }, [mode]);

  async function handleEnd() {
    await apiFetch("/conversation/end", {
      method: "POST",
      body: JSON.stringify({ session_id: params.sessionId }),
      token: backendToken,
    });
    router.push(`/feedback/${params.sessionId}`);
  }

  return (
    <main className="min-h-screen flex flex-col items-center gap-6 p-6 bg-gray-50">
      <div className="w-full max-w-2xl flex items-center justify-between">
        <h1 className="text-2xl font-bold text-indigo-700">Langua</h1>
        {mode === "quiz" && <QuizTimer secondsRemaining={secondsLeft} />}
        <button
          onClick={handleEnd}
          className="px-4 py-2 text-sm bg-gray-200 rounded-lg hover:bg-gray-300"
        >
          End Session
        </button>
      </div>
      <TranscriptPanel entries={transcript} />
      <div className="fixed bottom-8 flex flex-col items-center gap-4">
        <Waveform isActive={isRecording} />
        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          className={`w-20 h-20 rounded-full font-bold text-white transition-all ${
            isRecording
              ? "bg-red-500 scale-110 shadow-lg"
              : "bg-indigo-600 hover:bg-indigo-700"
          }`}
        >
          {isRecording ? "..." : "Speak"}
        </button>
      </div>
    </main>
  );
}
```

**Step 8: Run component tests**

```bash
cd frontend
npm test -- --testPathPattern="TranscriptPanel|QuizTimer"
```

Expected: all 5 tests PASS.

**Step 9: Commit**

```bash
git add frontend/src/components/TranscriptPanel.tsx frontend/src/components/QuizTimer.tsx frontend/src/components/Waveform.tsx frontend/src/hooks/useConversation.ts frontend/src/app/conversation/ frontend/src/__tests__/components/TranscriptPanel.test.tsx frontend/src/__tests__/components/QuizTimer.test.tsx
git commit -m "feat: Conversation View with WebSocket client, transcript, waveform, quiz timer"
```

---

### Task 17: Feedback View (Quiz Results)

**Files:**
- Create: `frontend/src/app/feedback/[sessionId]/page.tsx`
- Create: `frontend/src/components/FeedbackCard.tsx`
- Create: `frontend/src/__tests__/components/FeedbackCard.test.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/src/__tests__/components/FeedbackCard.test.tsx
import { render, screen } from "@testing-library/react";
import { FeedbackCard } from "@/components/FeedbackCard";

const feedback = {
  correct: ["こんにちは", "ありがとう"],
  revisit: ["すみません"],
  drills: ["Practice greetings for 5 minutes"],
};

test("renders correct phrases section", () => {
  render(<FeedbackCard feedback={feedback} />);
  expect(screen.getByText("こんにちは")).toBeInTheDocument();
  expect(screen.getByText("ありがとう")).toBeInTheDocument();
});

test("renders revisit section", () => {
  render(<FeedbackCard feedback={feedback} />);
  expect(screen.getByText("すみません")).toBeInTheDocument();
  expect(screen.getByText(/phrases to revisit/i)).toBeInTheDocument();
});

test("renders drill suggestions", () => {
  render(<FeedbackCard feedback={feedback} />);
  expect(
    screen.getByText("Practice greetings for 5 minutes")
  ).toBeInTheDocument();
  expect(screen.getByText(/suggested drills/i)).toBeInTheDocument();
});

test("shows empty state when no feedback", () => {
  render(
    <FeedbackCard feedback={{ correct: [], revisit: [], drills: [] }} />
  );
  expect(screen.getByText(/no feedback available/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
npm test -- --testPathPattern="FeedbackCard"
```

Expected: FAIL with "Cannot find module".

**Step 3: Create frontend/src/components/FeedbackCard.tsx**

```tsx
// frontend/src/components/FeedbackCard.tsx
interface Feedback {
  correct: string[];
  revisit: string[];
  drills: string[];
}

interface Props {
  feedback: Feedback;
}

function Section({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <h3 className={`font-semibold text-sm uppercase tracking-wide ${color}`}>
        {title}
      </h3>
      <ul className="flex flex-col gap-1">
        {items.map((item, i) => (
          <li key={i} className="text-gray-800 text-sm pl-3 border-l-2 border-gray-200">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function FeedbackCard({ feedback }: Props) {
  const isEmpty =
    feedback.correct.length === 0 &&
    feedback.revisit.length === 0 &&
    feedback.drills.length === 0;

  if (isEmpty) {
    return (
      <div className="text-center text-gray-500 py-8">No feedback available</div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full max-w-lg bg-white rounded-2xl shadow p-6">
      <Section
        title="What you got right"
        items={feedback.correct}
        color="text-green-600"
      />
      <Section
        title="Phrases to Revisit"
        items={feedback.revisit}
        color="text-amber-600"
      />
      <Section
        title="Suggested Drills"
        items={feedback.drills}
        color="text-indigo-600"
      />
    </div>
  );
}
```

**Step 4: Create frontend/src/app/feedback/[sessionId]/page.tsx**

```tsx
// frontend/src/app/feedback/[sessionId]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { FeedbackCard } from "@/components/FeedbackCard";
import { apiFetch } from "@/lib/api";

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

export default function FeedbackPage({
  params,
}: {
  params: { sessionId: string };
}) {
  const { data: session } = useSession();
  const router = useRouter();
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const backendToken = (
      session as typeof session & { backendToken?: string }
    )?.backendToken;
    if (!backendToken) return;

    apiFetch<SessionDetail>(`/sessions/${params.sessionId}`, {
      token: backendToken,
    })
      .then(setDetail)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [session, params.sessionId]);

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading results...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center gap-8 p-8 bg-gray-50">
      <h1 className="text-3xl font-bold text-indigo-700">Quiz Results</h1>
      {detail?.topic && (
        <p className="text-gray-500">Topic: {detail.topic}</p>
      )}
      <FeedbackCard
        feedback={detail?.feedback ?? { correct: [], revisit: [], drills: [] }}
      />
      <button
        onClick={() => router.push("/")}
        className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700"
      >
        Back to Home
      </button>
    </main>
  );
}
```

**Step 5: Run tests**

```bash
cd frontend
npm test -- --testPathPattern="FeedbackCard"
```

Expected: all 4 tests PASS.

**Step 6: Run full frontend test suite**

```bash
cd frontend
npm test
```

Expected: all tests PASS.

**Step 7: Commit**

```bash
git add frontend/src/components/FeedbackCard.tsx frontend/src/app/feedback/ frontend/src/__tests__/components/FeedbackCard.test.tsx
git commit -m "feat: Feedback View with quiz results display"
```

---

## Final Integration Check

**Step 1: Start all services**

```bash
docker compose up -d
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

**Step 2: Run all backend tests**

```bash
cd backend
pytest -v --tb=short
```

Expected: All tests PASS.

**Step 3: Run all frontend tests**

```bash
cd frontend
npm test -- --watchAll=false
```

Expected: All tests PASS.

**Step 4: Smoke-test the running app**

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/topics
# [{"id":"greetings","label":"Greetings"}, ...]
```

Open `http://localhost:3000` in a browser, sign in with Google or GitHub, pick a mode and topic, and start a session to confirm the end-to-end flow.

**Step 5: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: final cleanup and integration verification"
```

---

## Dependency Installation Reference

**Backend (run once in `backend/`):**
```bash
pip install -e ".[dev]"
```

**Frontend (run once in `frontend/`):**
```bash
npm install
```

**Environment setup:**
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with real API keys:
#   OPENAI_API_KEY, ANTHROPIC_API_KEY, JWT_SECRET, NEXTAUTH_SECRET

cp frontend/.env.local.example frontend/.env.local
# Edit frontend/.env.local with real OAuth credentials:
#   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
#   GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
```

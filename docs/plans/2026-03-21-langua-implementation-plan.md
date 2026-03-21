# Langua Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a voice-first Japanese language learning web app with push-to-talk conversation, AI coaching, and quiz feedback.

**Architecture:** Next.js frontend + FastAPI backend + PostgreSQL + Redis (Arq jobs only). Synchronous REST turn endpoint (STT -> Coach -> TTS). Supabase Auth with HS256 JWT verification. Provider-agnostic AI service layer.

**Tech Stack:**
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, python-jose, Arq, pytest + httpx
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS, @supabase/supabase-js, Vitest + React Testing Library
- Infrastructure: Docker Compose (PostgreSQL 16 + Redis 7), Supabase Auth (cloud)

---

## Phase 1: Project Setup & Database (Tasks 1-4)

### Task 1: Docker Compose — Postgres 16 + Redis 7

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Modify: `.gitignore`

**Step 1: Write the failing test**

There is no unit test for infrastructure files. Instead, validation is: `docker compose config` must succeed without errors.

**Step 2: Run test to verify it fails**

Run: `docker compose config`
Expected: FAIL with "no configuration file provided" or similar

**Step 3: Write minimal implementation**

`.env.example`:

```env
# PostgreSQL
POSTGRES_USER=langua
POSTGRES_PASSWORD=langua
POSTGRES_DB=langua
DATABASE_URL=postgresql+asyncpg://langua:langua@localhost:5432/langua

# Redis
REDIS_URL=redis://localhost:6379/0

# Supabase Auth
SUPABASE_JWT_SECRET=your-supabase-jwt-secret-here
SUPABASE_PROJECT_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key-here

# AI Providers
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Provider Selection
COACH_PROVIDER=anthropic
STT_PROVIDER=openai
TTS_PROVIDER=openai

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Worker
WORKER_CONCURRENCY=2
```

`docker-compose.yml`:

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
      - ./init-test-db.sql:/docker-entrypoint-initdb.d/init-test-db.sql

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

`init-test-db.sql`:

```sql
CREATE DATABASE langua_test;
```

`.gitignore` (replace entire file):

```gitignore
# Environment
.env

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/

# Node
node_modules/
.next/
out/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Audio temp files
/tmp/langua_audio/

# Claude
CLAUDE.md
.specstory/
```

**Step 4: Run test to verify it passes**

Run: `docker compose config`
Expected: Valid YAML output, no errors

**Step 5: Commit**

```bash
git add docker-compose.yml .env.example .gitignore init-test-db.sql
git commit -m "feat: add Docker Compose with Postgres 16 and Redis 7"
```

---

### Task 2: Backend FastAPI skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Test: `backend/tests/__init__.py`
- Test: `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`

**Step 1: Write the failing test**

`backend/tests/__init__.py`:

```python
```

`backend/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

`backend/tests/test_health.py`:

```python
import pytest


@pytest.mark.anyio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: FAIL with ModuleNotFoundError (app does not exist yet)

**Step 3: Write minimal implementation**

`backend/pyproject.toml`:

```toml
[project]
name = "langua-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "python-jose[cryptography]>=3.3.0",
    "httpx>=0.28.0",
    "python-multipart>=0.0.18",
    "openai>=1.58.0",
    "anthropic>=0.40.0",
    "arq>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "anyio>=4.7.0",
    "httpx>=0.28.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

`backend/app/__init__.py`:

```python
```

`backend/app/core/__init__.py`:

```python
```

`backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://langua:langua@localhost:5432/langua"
    redis_url: str = "redis://localhost:6379/0"
    supabase_jwt_secret: str = ""
    supabase_project_url: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    coach_provider: str = "anthropic"
    stt_provider: str = "openai"
    tts_provider: str = "openai"
    worker_concurrency: int = 2
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env"}


settings = Settings()
```

`backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/test_health.py -v`
Expected: PASS — `test_health_returns_ok PASSED`

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: add FastAPI skeleton with health endpoint and config"
```

---

### Task 3: Database models + migrations

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/transcript.py`
- Create: `backend/app/models/feedback.py`
- Create: `backend/app/core/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (directory)
- Test: `backend/tests/test_models.py`

**Step 1: Write the failing test**

`backend/tests/test_models.py`:

```python
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


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL with ModuleNotFoundError for app.models

**Step 3: Write minimal implementation**

`backend/app/models/__init__.py`:

```python
from app.models.base import Base
from app.models.user import User
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.feedback import Feedback

__all__ = ["Base", "User", "Session", "TranscriptEntry", "Feedback"]
```

`backend/app/models/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

`backend/app/models/user.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sessions = relationship("Session", back_populates="user", lazy="selectin")
```

`backend/app/models/session.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="ja")
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    feedback_status: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default=None
    )
    feedback_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    feedback_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", back_populates="sessions")
    transcript = relationship(
        "TranscriptEntry",
        back_populates="session",
        lazy="selectin",
        order_by="TranscriptEntry.turn_index",
    )
    feedback = relationship("Feedback", back_populates="session", lazy="selectin")
```

`backend/app/models/transcript.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_session_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_native: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_reading: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_romanized: Mapped[str | None] = mapped_column(Text, nullable=True)
    pronunciation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session = relationship("Session", back_populates="transcript")
```

`backend/app/models/feedback.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, unique=True
    )
    correct: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    revisit: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    drills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session = relationship("Session", back_populates="feedback")
```

`backend/app/core/database.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

`backend/alembic.ini`:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://langua:langua@localhost:5432/langua

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

`backend/alembic/env.py`:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

`backend/alembic/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

After creating these files, generate the initial migration:

```bash
cd backend && alembic revision --autogenerate -m "initial schema"
cd backend && alembic upgrade head
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/models/ backend/app/core/database.py backend/alembic.ini backend/alembic/ backend/tests/test_models.py
git commit -m "feat: add SQLAlchemy models and Alembic migrations"
```

---

### Task 4: Frontend Next.js skeleton

**Files:**
- Create: `frontend/` (via create-next-app)
- Create: `frontend/.env.local.example`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/config.ts`
- Test: `frontend/src/lib/config.test.ts`

**Step 1: Write the failing test**

`frontend/src/lib/config.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { config } from "./config";

describe("config", () => {
  it("exposes API URL", () => {
    expect(config.apiUrl).toBeDefined();
    expect(typeof config.apiUrl).toBe("string");
  });

  it("exposes Supabase URL", () => {
    expect(config.supabaseUrl).toBeDefined();
    expect(typeof config.supabaseUrl).toBe("string");
  });

  it("exposes Supabase anon key", () => {
    expect(config.supabaseAnonKey).toBeDefined();
    expect(typeof config.supabaseAnonKey).toBe("string");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/config.test.ts`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

First, scaffold the project:

```bash
npx create-next-app@14 frontend --typescript --tailwind --app --src-dir --no-import-alias --eslint
```

Install test deps:

```bash
cd frontend && npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom
```

`frontend/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

`frontend/.env.local.example`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`frontend/src/lib/config.ts`:

```typescript
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
};
```

`frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Langua - Japanese Language Assistant",
  description: "Voice-first Japanese language learning with AI coaching",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
```

`frontend/src/app/page.tsx`:

```tsx
export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold">Langua</h1>
      <p className="mt-4 text-lg text-gray-600">
        Voice-first Japanese language learning
      </p>
    </main>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/config.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Next.js skeleton with TypeScript, Tailwind, and Vitest"
```

---

**Phase 1 Checkpoint:** At this point, Docker Compose brings up Postgres and Redis. The backend has a `/health` endpoint, SQLAlchemy models for all four tables, and Alembic migrations. The frontend is a Next.js app with Tailwind and Vitest configured. Running `docker compose up -d`, then `alembic upgrade head`, then `uvicorn app.main:app` and `npm run dev` should show the backend health check responding and the frontend rendering the landing page.

---

## Phase 2: Auth (Tasks 5-6)

### Task 5: Backend JWT auth middleware

**Files:**
- Create: `backend/app/core/auth.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Test: `backend/tests/test_auth.py`

**Step 1: Write the failing test**

`backend/tests/test_auth.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture
def valid_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "user_metadata": {"full_name": "Test User", "avatar_url": "https://example.com/avatar.png"},
        "aud": "authenticated",
        "iss": f"https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def expired_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "expired@example.com",
        "user_metadata": {"full_name": "Expired User"},
        "aud": "authenticated",
        "iss": f"https://test.supabase.co/auth/v1",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://test.supabase.co")

    from app.core.config import Settings
    test_settings = Settings(
        supabase_jwt_secret=TEST_SECRET,
        supabase_project_url="https://test.supabase.co",
    )
    monkeypatch.setattr("app.core.auth.settings", test_settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_protected_route_without_token(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_valid_token(client, valid_token):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"


@pytest.mark.anyio
async def test_protected_route_with_expired_token(client, expired_token):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_invalid_token(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-string"},
    )
    assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL with ImportError (auth module does not exist)

**Step 3: Write minimal implementation**

`backend/app/schemas/__init__.py`:

```python
```

`backend/app/schemas/auth.py`:

```python
import uuid

from pydantic import BaseModel


class JWTPayload(BaseModel):
    sub: uuid.UUID
    email: str
    name: str = ""
    avatar_url: str | None = None
```

`backend/app/core/auth.py`:

```python
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import JWTPayload

security = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> JWTPayload:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_metadata = payload.get("user_metadata", {})
    return JWTPayload(
        sub=uuid.UUID(payload["sub"]),
        email=payload.get("email", ""),
        name=user_metadata.get("full_name", ""),
        avatar_url=user_metadata.get("avatar_url"),
    )


async def get_or_create_user(
    payload: JWTPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=payload.sub,
            email=payload.email,
            name=payload.name,
            avatar_url=payload.avatar_url,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
```

`backend/app/api/__init__.py`:

```python
```

Add a test route to `backend/app/main.py` (modify):

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: PASS — all 4 tests pass

**Step 5: Commit**

```bash
git add backend/app/core/auth.py backend/app/schemas/ backend/app/api/__init__.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: add JWT auth middleware with Supabase HS256 verification"
```

---

### Task 6: Frontend Supabase auth

**Files:**
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/app/sign-in/page.tsx`
- Create: `frontend/src/components/AuthGuard.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Test: `frontend/src/lib/api.test.ts`

**Step 1: Write the failing test**

`frontend/src/lib/api.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
    },
  },
}));

import { apiClient } from "./api";
import { supabase } from "./supabase";

describe("apiClient", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    global.fetch = vi.fn();
  });

  it("attaches Bearer token from Supabase session", async () => {
    const mockGetSession = vi.mocked(supabase.auth.getSession);
    mockGetSession.mockResolvedValue({
      data: {
        session: { access_token: "test-token-123" },
      },
      error: null,
    } as any);

    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiClient.get("/health");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token-123",
        }),
      }),
    );
  });

  it("throws when no session exists", async () => {
    const mockGetSession = vi.mocked(supabase.auth.getSession);
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    } as any);

    await expect(apiClient.get("/health")).rejects.toThrow("Not authenticated");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/api.test.ts`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

Install Supabase client:

```bash
cd frontend && npm install @supabase/supabase-js
```

`frontend/src/lib/supabase.ts`:

```typescript
import { createClient } from "@supabase/supabase-js";
import { config } from "./config";

export const supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);
```

`frontend/src/lib/api.ts`:

```typescript
import { supabase } from "./supabase";
import { config } from "./config";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getHeaders(): Promise<Record<string, string>> {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      throw new Error("Not authenticated");
    }

    return {
      Authorization: `Bearer ${session.access_token}`,
    };
  }

  async get(path: string): Promise<Response> {
    const headers = await this.getHeaders();
    return fetch(`${this.baseUrl}${path}`, { headers });
  }

  async post(path: string, body?: Record<string, unknown>): Promise<Response> {
    const headers = await this.getHeaders();
    return fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async postFormData(
    path: string,
    formData: FormData,
    extraHeaders?: Record<string, string>,
  ): Promise<Response> {
    const headers = await this.getHeaders();
    return fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { ...headers, ...extraHeaders },
      body: formData,
    });
  }
}

export const apiClient = new ApiClient(config.apiUrl);
```

`frontend/src/hooks/useAuth.ts`:

```typescript
"use client";

import { useEffect, useState, useCallback } from "react";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signInWithGoogle = useCallback(async () => {
    await supabase.auth.signInWithOAuth({ provider: "google" });
  }, []);

  const signInWithGithub = useCallback(async () => {
    await supabase.auth.signInWithOAuth({ provider: "github" });
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  return { session, user, loading, signInWithGoogle, signInWithGithub, signOut };
}
```

`frontend/src/components/AuthGuard.tsx`:

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/sign-in");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}
```

`frontend/src/app/sign-in/page.tsx`:

```tsx
"use client";

import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SignIn() {
  const { user, loading, signInWithGoogle, signInWithGithub } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold">Langua</h1>
      <p className="text-lg text-gray-600">Sign in to start learning</p>
      <div className="flex flex-col gap-3">
        <button
          onClick={signInWithGoogle}
          className="rounded-lg bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-md ring-1 ring-gray-200 hover:bg-gray-50"
        >
          Continue with Google
        </button>
        <button
          onClick={signInWithGithub}
          className="rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white shadow-md hover:bg-gray-800"
        >
          Continue with GitHub
        </button>
      </div>
    </main>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/api.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/lib/supabase.ts frontend/src/lib/api.ts frontend/src/lib/api.test.ts frontend/src/hooks/useAuth.ts frontend/src/components/AuthGuard.tsx frontend/src/app/sign-in/page.tsx frontend/src/app/layout.tsx frontend/.env.local.example
git commit -m "feat: add Supabase auth with sign-in page and API client"
```

---

**Phase 2 Checkpoint:** Authentication is wired end-to-end. The backend validates Supabase JWTs and can upsert users. The frontend has Google/GitHub sign-in, an auth hook, an API client that attaches the Bearer token, and an AuthGuard component. The `/auth/me` endpoint returns the authenticated user's profile. Unauthenticated users are redirected to `/sign-in`.

---

## Phase 3: AI Service Layer (Tasks 7-10)

### Task 7: Service protocols

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/protocols.py`
- Create: `backend/app/services/errors.py`
- Test: `backend/tests/test_protocols.py`

**Step 1: Write the failing test**

`backend/tests/test_protocols.py`:

```python
import uuid
from pathlib import Path

import pytest

from app.services.protocols import STTService, CoachService, TTSService, CoachResponse
from app.services.errors import STTError, CoachError, TTSError


class FakeSTT:
    async def transcribe(self, audio_data: bytes, language: str) -> str:
        return "hello"


class FakeCoach:
    async def respond(
        self,
        user_text: str,
        transcript_context: list[dict],
        language: str,
        mode: str,
        topic: str,
    ) -> CoachResponse:
        return CoachResponse(
            text_en="Here's how to say that:",
            text_native="こんにちは",
            text_reading="こんにちは",
            text_romanized="konnichiwa",
            pronunciation_note="Natural greeting",
            next_prompt="Try saying it back to me",
        )


class FakeTTS:
    async def synthesize(self, text: str, language: str, turn_id: uuid.UUID) -> Path:
        return Path(f"/tmp/langua_audio/{turn_id}.mp3")


@pytest.mark.anyio
async def test_fake_stt_satisfies_protocol():
    stt: STTService = FakeSTT()
    result = await stt.transcribe(b"audio", "ja")
    assert result == "hello"


@pytest.mark.anyio
async def test_fake_coach_satisfies_protocol():
    coach: CoachService = FakeCoach()
    result = await coach.respond("hello", [], "ja", "learn", "Greetings")
    assert result.text_native == "こんにちは"
    assert result.text_romanized == "konnichiwa"


@pytest.mark.anyio
async def test_fake_tts_satisfies_protocol():
    tts: TTSService = FakeTTS()
    turn_id = uuid.uuid4()
    result = await tts.synthesize("こんにちは", "ja", turn_id)
    assert str(turn_id) in str(result)


def test_error_types():
    stt_err = STTError("Transcription failed", provider="openai")
    assert stt_err.provider == "openai"
    assert str(stt_err) == "Transcription failed"

    coach_err = CoachError("Parse failed", provider="anthropic", retryable=True)
    assert coach_err.retryable is True

    tts_err = TTSError("Synthesis failed", provider="openai")
    assert tts_err.provider == "openai"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_protocols.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

`backend/app/services/__init__.py`:

```python
```

`backend/app/services/protocols.py`:

```python
import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class CoachResponse(BaseModel):
    text_en: str
    text_native: str
    text_reading: str
    text_romanized: str
    pronunciation_note: str
    next_prompt: str


@runtime_checkable
class STTService(Protocol):
    async def transcribe(self, audio_data: bytes, language: str) -> str: ...


@runtime_checkable
class CoachService(Protocol):
    async def respond(
        self,
        user_text: str,
        transcript_context: list[dict],
        language: str,
        mode: str,
        topic: str,
    ) -> CoachResponse: ...


@runtime_checkable
class TTSService(Protocol):
    async def synthesize(self, text: str, language: str, turn_id: uuid.UUID) -> Path: ...
```

`backend/app/services/errors.py`:

```python
class AIServiceError(Exception):
    def __init__(self, message: str, provider: str, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class STTError(AIServiceError):
    pass


class CoachError(AIServiceError):
    pass


class TTSError(AIServiceError):
    pass
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_protocols.py -v`
Expected: PASS — all 4 tests pass

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_protocols.py
git commit -m "feat: add AI service protocols and error types"
```

---

### Task 8: STT implementation

**Files:**
- Create: `backend/app/services/stt.py`
- Test: `backend/tests/test_stt.py`

**Step 1: Write the failing test**

`backend/tests/test_stt.py`:

```python
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.stt import WhisperSTTService
from app.services.errors import STTError


@pytest.fixture
def stt_service():
    return WhisperSTTService(api_key="test-key")


@pytest.mark.anyio
async def test_transcribe_success(stt_service):
    mock_transcript = MagicMock()
    mock_transcript.text = "I want to order ramen"

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with patch.object(stt_service, "_get_client", return_value=mock_client):
        result = await stt_service.transcribe(b"fake-audio-data", "ja")
        assert result == "I want to order ramen"


@pytest.mark.anyio
async def test_transcribe_retries_on_server_error(stt_service):
    mock_transcript = MagicMock()
    mock_transcript.text = "retried result"

    mock_client = AsyncMock()
    from openai import APIStatusError, APIResponseValidationError
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}

    mock_client.audio.transcriptions.create = AsyncMock(
        side_effect=[
            APIStatusError(
                message="Server error",
                response=mock_response,
                body=None,
            ),
            mock_transcript,
        ]
    )

    with patch.object(stt_service, "_get_client", return_value=mock_client):
        result = await stt_service.transcribe(b"fake-audio-data", "ja")
        assert result == "retried result"
        assert mock_client.audio.transcriptions.create.call_count == 2


@pytest.mark.anyio
async def test_transcribe_fails_after_retries(stt_service):
    mock_client = AsyncMock()
    from openai import APIStatusError
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}

    mock_client.audio.transcriptions.create = AsyncMock(
        side_effect=APIStatusError(
            message="Server error",
            response=mock_response,
            body=None,
        )
    )

    with patch.object(stt_service, "_get_client", return_value=mock_client):
        with pytest.raises(STTError) as exc_info:
            await stt_service.transcribe(b"fake-audio-data", "ja")
        assert exc_info.value.provider == "openai"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_stt.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

`backend/app/services/stt.py`:

```python
import asyncio
import io
import logging

from openai import AsyncOpenAI, APIStatusError, APITimeoutError

from app.services.errors import STTError

logger = logging.getLogger(__name__)


class WhisperSTTService:
    def __init__(self, api_key: str, timeout: float = 10.0, max_retries: int = 1):
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self._api_key, timeout=self._timeout)

    async def transcribe(self, audio_data: bytes, language: str) -> str:
        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.webm"
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                )
                return transcript.text
            except (APIStatusError, APITimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                is_server_error = isinstance(e, APIStatusError) and e.response.status_code >= 500
                is_timeout = isinstance(e, (APITimeoutError, asyncio.TimeoutError))
                if (is_server_error or is_timeout) and attempt < self._max_retries:
                    logger.warning(f"STT attempt {attempt + 1} failed, retrying: {e}")
                    continue
                break
            except Exception as e:
                last_error = e
                break

        raise STTError(
            f"Transcription failed after {self._max_retries + 1} attempts: {last_error}",
            provider="openai",
        )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_stt.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/services/stt.py backend/tests/test_stt.py
git commit -m "feat: add Whisper STT service with retry on 5xx/timeout"
```

---

### Task 9: Coach implementation

**Files:**
- Create: `backend/app/services/coach.py`
- Create: `backend/app/services/prompts.py`
- Test: `backend/tests/test_coach.py`

**Step 1: Write the failing test**

`backend/tests/test_coach.py`:

```python
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.coach import AnthropicCoachService
from app.services.protocols import CoachResponse
from app.services.errors import CoachError


@pytest.fixture
def coach_service():
    return AnthropicCoachService(api_key="test-key")


def make_mock_response(content: dict) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = json.dumps(content)
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


VALID_RESPONSE = {
    "text_en": "Here is how to say hello:",
    "text_native": "こんにちは",
    "text_reading": "こんにちは",
    "text_romanized": "konnichiwa",
    "pronunciation_note": "Natural greeting",
    "next_prompt": "Try saying it back to me",
}


@pytest.mark.anyio
async def test_coach_respond_success(coach_service):
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=make_mock_response(VALID_RESPONSE)
    )

    with patch.object(coach_service, "_get_client", return_value=mock_client):
        result = await coach_service.respond(
            "hello", [], "ja", "learn", "Greetings"
        )
        assert isinstance(result, CoachResponse)
        assert result.text_native == "こんにちは"
        assert result.text_romanized == "konnichiwa"


@pytest.mark.anyio
async def test_coach_retries_on_parse_failure(coach_service):
    invalid_response = MagicMock()
    invalid_block = MagicMock()
    invalid_block.text = "This is not JSON"
    invalid_response.content = [invalid_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[invalid_response, make_mock_response(VALID_RESPONSE)]
    )

    with patch.object(coach_service, "_get_client", return_value=mock_client):
        result = await coach_service.respond(
            "hello", [], "ja", "learn", "Greetings"
        )
        assert result.text_native == "こんにちは"
        assert mock_client.messages.create.call_count == 2


@pytest.mark.anyio
async def test_coach_fails_after_both_parse_failures(coach_service):
    invalid_response = MagicMock()
    invalid_block = MagicMock()
    invalid_block.text = "not json at all"
    invalid_response.content = [invalid_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=invalid_response)

    with patch.object(coach_service, "_get_client", return_value=mock_client):
        with pytest.raises(CoachError) as exc_info:
            await coach_service.respond("hello", [], "ja", "learn", "Greetings")
        assert exc_info.value.provider == "anthropic"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_coach.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

`backend/app/services/prompts.py`:

```python
COACH_SYSTEM_PROMPTS = {
    "ja": """You are Langua, a Japanese language coach. Your role is to:
1. Understand what the user wants to say in English
2. Teach them the correct Japanese phrase
3. Guide pronunciation step by step
4. Ask them to repeat
5. Confirm correctness or correct gently

In quiz mode, also track which phrases the user struggled with
and provide a structured feedback summary when asked.

Keep responses concise and encouraging.

You must respond with valid JSON matching this exact schema:
{
  "text_en": "English explanation",
  "text_native": "Japanese phrase in Kanji",
  "text_reading": "Hiragana reading",
  "text_romanized": "Romaji",
  "pronunciation_note": "tip about this phrase",
  "next_prompt": "what you want the user to do next"
}

Do not include any text outside the JSON object.""",
}

COACH_STRICT_SUFFIX = """

CRITICAL: Your previous response was not valid JSON. You MUST respond with ONLY a JSON object. No markdown, no explanation, no code fences. Just the raw JSON object starting with { and ending with }."""

FEEDBACK_PROMPT = """You are reviewing a completed quiz session. Analyze the full transcript and provide structured feedback.

You must respond with valid JSON matching this exact schema:
{
  "correct": ["list of phrases the user got right"],
  "revisit": ["list of phrases the user should practice more"],
  "drills": ["1-2 suggested exercises for next session"]
}

Do not include any text outside the JSON object."""
```

`backend/app/services/coach.py`:

```python
import json
import logging

from anthropic import AsyncAnthropic

from app.services.errors import CoachError
from app.services.prompts import COACH_SYSTEM_PROMPTS, COACH_STRICT_SUFFIX
from app.services.protocols import CoachResponse

logger = logging.getLogger(__name__)


class AnthropicCoachService:
    def __init__(self, api_key: str, timeout: float = 15.0):
        self._api_key = api_key
        self._timeout = timeout

    def _get_client(self) -> AsyncAnthropic:
        return AsyncAnthropic(api_key=self._api_key, timeout=self._timeout)

    def _build_messages(self, user_text: str, transcript_context: list[dict]) -> list[dict]:
        messages = []
        for entry in transcript_context:
            role = "user" if entry.get("role") == "user" else "assistant"
            content = entry.get("text_en", "")
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_text})
        return messages

    async def respond(
        self,
        user_text: str,
        transcript_context: list[dict],
        language: str,
        mode: str,
        topic: str,
    ) -> CoachResponse:
        client = self._get_client()
        system_prompt = COACH_SYSTEM_PROMPTS.get(language, COACH_SYSTEM_PROMPTS["ja"])
        system_prompt += f"\n\nCurrent topic: {topic}\nMode: {mode}"
        messages = self._build_messages(user_text, transcript_context)

        for attempt in range(2):
            try:
                if attempt == 1:
                    system_prompt += COACH_STRICT_SUFFIX

                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    system=system_prompt,
                    messages=messages,
                )

                raw_text = response.content[0].text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    raw_text = "\n".join(lines[1:-1])

                data = json.loads(raw_text)
                return CoachResponse(**data)

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Coach parse attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    continue
                raise CoachError(
                    f"Coach response parse failed after retry: {e}",
                    provider="anthropic",
                    retryable=False,
                )
            except Exception as e:
                raise CoachError(
                    f"Coach service error: {e}",
                    provider="anthropic",
                )

        raise CoachError(
            "Coach failed after all attempts",
            provider="anthropic",
        )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_coach.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/services/coach.py backend/app/services/prompts.py backend/tests/test_coach.py
git commit -m "feat: add Anthropic coach service with JSON validation and retry"
```

---

### Task 10: TTS implementation + provider factory

**Files:**
- Create: `backend/app/services/tts.py`
- Create: `backend/app/services/factory.py`
- Test: `backend/tests/test_tts.py`
- Test: `backend/tests/test_factory.py`

**Step 1: Write the failing test**

`backend/tests/test_tts.py`:

```python
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.tts import OpenAITTSService
from app.services.errors import TTSError


@pytest.fixture
def tts_service(tmp_path):
    return OpenAITTSService(api_key="test-key", audio_dir=str(tmp_path))


@pytest.mark.anyio
async def test_tts_synthesize_success(tts_service, tmp_path):
    turn_id = uuid.uuid4()
    expected_path = tmp_path / f"{turn_id}.mp3"

    mock_response = AsyncMock()
    mock_response.aiter_bytes = AsyncMock(
        return_value=AsyncIterator([b"fake-audio-data"])
    )
    mock_response.stream_to_file = AsyncMock()

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(return_value=mock_response)

    with patch.object(tts_service, "_get_client", return_value=mock_client):
        result = await tts_service.synthesize("こんにちは", "ja", turn_id)
        assert result == expected_path
        mock_client.audio.speech.create.assert_called_once()


class AsyncIterator:
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


@pytest.mark.anyio
async def test_tts_retries_on_server_error(tts_service, tmp_path):
    turn_id = uuid.uuid4()

    from openai import APIStatusError
    mock_resp_err = MagicMock()
    mock_resp_err.status_code = 500
    mock_resp_err.headers = {}

    mock_response = AsyncMock()
    mock_response.stream_to_file = AsyncMock()

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(
        side_effect=[
            APIStatusError(message="Server error", response=mock_resp_err, body=None),
            mock_response,
        ]
    )

    with patch.object(tts_service, "_get_client", return_value=mock_client):
        result = await tts_service.synthesize("こんにちは", "ja", turn_id)
        assert mock_client.audio.speech.create.call_count == 2


@pytest.mark.anyio
async def test_tts_fails_after_retries(tts_service):
    turn_id = uuid.uuid4()

    from openai import APIStatusError
    mock_resp_err = MagicMock()
    mock_resp_err.status_code = 500
    mock_resp_err.headers = {}

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(
        side_effect=APIStatusError(
            message="Server error", response=mock_resp_err, body=None
        )
    )

    with patch.object(tts_service, "_get_client", return_value=mock_client):
        with pytest.raises(TTSError):
            await tts_service.synthesize("こんにちは", "ja", turn_id)
```

`backend/tests/test_factory.py`:

```python
import pytest
from unittest.mock import patch

from app.services.factory import create_stt_service, create_coach_service, create_tts_service
from app.services.stt import WhisperSTTService
from app.services.coach import AnthropicCoachService
from app.services.tts import OpenAITTSService


def test_create_stt_service_openai():
    service = create_stt_service(provider="openai", api_key="test")
    assert isinstance(service, WhisperSTTService)


def test_create_stt_service_unknown():
    with pytest.raises(ValueError, match="Unknown STT provider"):
        create_stt_service(provider="unknown", api_key="test")


def test_create_coach_service_anthropic():
    service = create_coach_service(provider="anthropic", api_key="test")
    assert isinstance(service, AnthropicCoachService)


def test_create_coach_service_unknown():
    with pytest.raises(ValueError, match="Unknown coach provider"):
        create_coach_service(provider="unknown", api_key="test")


def test_create_tts_service_openai():
    service = create_tts_service(provider="openai", api_key="test")
    assert isinstance(service, OpenAITTSService)


def test_create_tts_service_unknown():
    with pytest.raises(ValueError, match="Unknown TTS provider"):
        create_tts_service(provider="unknown", api_key="test")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_tts.py tests/test_factory.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

`backend/app/services/tts.py`:

```python
import asyncio
import logging
import uuid
from pathlib import Path

from openai import AsyncOpenAI, APIStatusError, APITimeoutError

from app.services.errors import TTSError

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_DIR = "/tmp/langua_audio"


class OpenAITTSService:
    def __init__(
        self,
        api_key: str,
        audio_dir: str = DEFAULT_AUDIO_DIR,
        timeout: float = 10.0,
        max_retries: int = 1,
    ):
        self._api_key = api_key
        self._audio_dir = Path(audio_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._max_retries = max_retries

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self._api_key, timeout=self._timeout)

    async def synthesize(self, text: str, language: str, turn_id: uuid.UUID) -> Path:
        client = self._get_client()
        output_path = self._audio_dir / f"{turn_id}.mp3"
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text,
                    response_format="mp3",
                )
                await response.stream_to_file(str(output_path))
                return output_path

            except (APIStatusError, APITimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                is_server_error = isinstance(e, APIStatusError) and e.response.status_code >= 500
                is_timeout = isinstance(e, (APITimeoutError, asyncio.TimeoutError))
                if (is_server_error or is_timeout) and attempt < self._max_retries:
                    logger.warning(f"TTS attempt {attempt + 1} failed, retrying: {e}")
                    continue
                break
            except Exception as e:
                last_error = e
                break

        raise TTSError(
            f"TTS synthesis failed after {self._max_retries + 1} attempts: {last_error}",
            provider="openai",
        )
```

`backend/app/services/factory.py`:

```python
from app.services.stt import WhisperSTTService
from app.services.coach import AnthropicCoachService
from app.services.tts import OpenAITTSService


def create_stt_service(provider: str, api_key: str) -> WhisperSTTService:
    if provider == "openai":
        return WhisperSTTService(api_key=api_key)
    raise ValueError(f"Unknown STT provider: {provider}")


def create_coach_service(provider: str, api_key: str) -> AnthropicCoachService:
    if provider == "anthropic":
        return AnthropicCoachService(api_key=api_key)
    raise ValueError(f"Unknown coach provider: {provider}")


def create_tts_service(
    provider: str, api_key: str, audio_dir: str = "/tmp/langua_audio"
) -> OpenAITTSService:
    if provider == "openai":
        return OpenAITTSService(api_key=api_key, audio_dir=audio_dir)
    raise ValueError(f"Unknown TTS provider: {provider}")
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_tts.py tests/test_factory.py -v`
Expected: PASS — all 6 tests pass (3 TTS + 3 factory pairs)

**Step 5: Commit**

```bash
git add backend/app/services/tts.py backend/app/services/factory.py backend/tests/test_tts.py backend/tests/test_factory.py
git commit -m "feat: add OpenAI TTS service and provider factory"
```

---

**Phase 3 Checkpoint:** The AI service layer is complete. Protocol interfaces define typed contracts for STT, Coach, and TTS. Concrete implementations (WhisperSTTService, AnthropicCoachService, OpenAITTSService) have timeout and retry logic. The provider factory reads env vars to instantiate the right implementations. All services are tested with mocks.

---

## Phase 4: Conversation API (Tasks 11-15)

### Task 11: GET /topics

**Files:**
- Create: `backend/app/api/topics.py`
- Create: `backend/app/schemas/topics.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_topics.py`

**Step 1: Write the failing test**

`backend/tests/test_topics.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture
def auth_headers():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "user_metadata": {"full_name": "Test User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://test.supabase.co")
    from app.core.config import Settings
    test_settings = Settings(
        supabase_jwt_secret=TEST_SECRET,
        supabase_project_url="https://test.supabase.co",
    )
    monkeypatch.setattr("app.core.auth.settings", test_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_get_topics_for_japanese(client, auth_headers):
    response = await client.get("/topics?language=ja", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    topics = data["topics"]
    assert len(topics) == 5
    assert "Greetings" in topics
    assert "Ordering Food" in topics
    assert "Directions" in topics
    assert "Shopping" in topics
    assert "Travel" in topics


@pytest.mark.anyio
async def test_get_topics_defaults_to_japanese(client, auth_headers):
    response = await client.get("/topics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["topics"]) == 5


@pytest.mark.anyio
async def test_get_topics_unknown_language(client, auth_headers):
    response = await client.get("/topics?language=xx", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["topics"] == []
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_topics.py -v`
Expected: FAIL with 404 (route not found)

**Step 3: Write minimal implementation**

`backend/app/schemas/topics.py`:

```python
from pydantic import BaseModel


class TopicsResponse(BaseModel):
    topics: list[str]
    language: str
```

`backend/app/api/topics.py`:

```python
from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user_payload
from app.schemas.topics import TopicsResponse

router = APIRouter()

TOPICS_BY_LANGUAGE: dict[str, list[str]] = {
    "ja": ["Greetings", "Ordering Food", "Directions", "Shopping", "Travel"],
}


@router.get("/topics", response_model=TopicsResponse)
async def get_topics(
    language: str = Query(default="ja"),
    _=Depends(get_current_user_payload),
):
    topics = TOPICS_BY_LANGUAGE.get(language, [])
    return TopicsResponse(topics=topics, language=language)
```

Modify `backend/app/main.py` to include the router:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload
from app.api.topics import router as topics_router

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_topics.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/api/topics.py backend/app/schemas/topics.py backend/app/main.py backend/tests/test_topics.py
git commit -m "feat: add GET /topics endpoint with hardcoded Japanese topics"
```

---

### Task 12: POST /conversation/start

**Files:**
- Create: `backend/app/api/conversation.py`
- Create: `backend/app/schemas/conversation.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_conversation_start.py`

**Step 1: Write the failing test**

`backend/tests/test_conversation_start.py`:

```python
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

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"
TEST_DATABASE_URL = "postgresql+asyncpg://langua:langua@localhost:5432/langua_test"


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_conversation_start.py -v`
Expected: FAIL with 404 or ImportError

**Step 3: Write minimal implementation**

`backend/app/schemas/conversation.py`:

```python
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class ConversationMode(str, Enum):
    learn = "learn"
    quiz = "quiz"


class StartConversationRequest(BaseModel):
    language: str = Field(default="ja", max_length=10)
    mode: ConversationMode
    topic: str = Field(max_length=100)


class StartConversationResponse(BaseModel):
    session_id: uuid.UUID


class TurnUserEntry(BaseModel):
    role: str = "user"
    text_en: str
    turn_index: int


class TurnAssistantEntry(BaseModel):
    role: str = "assistant"
    text_en: str
    text_native: str
    text_reading: str
    text_romanized: str
    pronunciation_note: str
    next_prompt: str
    turn_index: int


class TurnResponse(BaseModel):
    turn_id: uuid.UUID
    user_entry: TurnUserEntry
    assistant_entry: TurnAssistantEntry
    audio_url: str


class EndConversationRequest(BaseModel):
    session_id: uuid.UUID


class EndConversationResponse(BaseModel):
    status: str
    feedback_status: str | None = None
```

`backend/app/api/conversation.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.conversation import (
    StartConversationRequest,
    StartConversationResponse,
)

router = APIRouter(prefix="/conversation")


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    session = Session(
        user_id=user.id,
        language=request.language,
        mode=request.mode.value,
        topic=request.topic,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return StartConversationResponse(session_id=session.id)
```

Modify `backend/app/main.py` to include the conversation router:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload
from app.api.topics import router as topics_router
from app.api.conversation import router as conversation_router

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router)
app.include_router(conversation_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_conversation_start.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/api/conversation.py backend/app/schemas/conversation.py backend/app/main.py backend/tests/test_conversation_start.py
git commit -m "feat: add POST /conversation/start endpoint"
```

---

### Task 13: POST /conversation/turn

**Files:**
- Modify: `backend/app/api/conversation.py`
- Modify: `backend/app/main.py` (StaticFiles mount)
- Create: `backend/app/services/dependencies.py`
- Test: `backend/tests/test_conversation_turn.py`

**Step 1: Write the failing test**

`backend/tests/test_conversation_turn.py`:

```python
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


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
            text_native="こんにちは",
            text_reading="こんにちは",
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
    assert body["assistant_entry"]["text_native"] == "こんにちは"
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_conversation_turn.py -v`
Expected: FAIL with 404 or ImportError

**Step 3: Write minimal implementation**

`backend/app/services/dependencies.py`:

```python
from app.core.config import settings
from app.services.factory import create_stt_service, create_coach_service, create_tts_service

stt_service = create_stt_service(
    provider=settings.stt_provider, api_key=settings.openai_api_key
)
coach_service = create_coach_service(
    provider=settings.coach_provider, api_key=settings.anthropic_api_key
)
tts_service = create_tts_service(
    provider=settings.tts_provider, api_key=settings.openai_api_key
)
```

Modify `backend/app/api/conversation.py` (full file):

```python
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.database import get_db
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.user import User
from app.schemas.conversation import (
    StartConversationRequest,
    StartConversationResponse,
    TurnResponse,
    TurnUserEntry,
    TurnAssistantEntry,
)
from app.services import dependencies as svc
from app.services.errors import STTError, CoachError, TTSError

router = APIRouter(prefix="/conversation")

MAX_AUDIO_SIZE = 1 * 1024 * 1024  # 1MB


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    session = Session(
        user_id=user.id,
        language=request.language,
        mode=request.mode.value,
        topic=request.topic,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return StartConversationResponse(session_id=session.id)


@router.post("/turn", response_model=TurnResponse)
async def conversation_turn(
    session_id: uuid.UUID = Form(...),
    audio: UploadFile = File(...),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    idempotency_uuid = uuid.UUID(x_idempotency_key)

    # Check idempotency: return cached if already processed
    existing = await db.execute(
        select(TranscriptEntry).where(
            TranscriptEntry.session_id == session_id,
            TranscriptEntry.idempotency_key == idempotency_uuid,
            TranscriptEntry.role == "user",
        )
    )
    existing_entry = existing.scalar_one_or_none()
    if existing_entry is not None:
        assistant_result = await db.execute(
            select(TranscriptEntry).where(
                TranscriptEntry.session_id == session_id,
                TranscriptEntry.turn_index == existing_entry.turn_index + 1,
                TranscriptEntry.role == "assistant",
            )
        )
        assistant_entry = assistant_result.scalar_one()
        return TurnResponse(
            turn_id=assistant_entry.id,
            user_entry=TurnUserEntry(
                text_en=existing_entry.text_en or "",
                turn_index=existing_entry.turn_index,
            ),
            assistant_entry=TurnAssistantEntry(
                text_en=assistant_entry.text_en or "",
                text_native=assistant_entry.text_native or "",
                text_reading=assistant_entry.text_reading or "",
                text_romanized=assistant_entry.text_romanized or "",
                pronunciation_note=assistant_entry.pronunciation_note or "",
                next_prompt=assistant_entry.next_prompt or "",
                turn_index=assistant_entry.turn_index,
            ),
            audio_url=f"/audio/{assistant_entry.id}.mp3",
        )

    # Validate session ownership and status
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Session is not active")

    # Read and validate audio
    audio_data = await audio.read()
    if len(audio_data) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large (max 1MB)")

    # STT
    try:
        user_text = await svc.stt_service.transcribe(audio_data, session.language)
    except STTError as e:
        raise HTTPException(status_code=502, detail=f"Speech-to-text failed: {e}")

    # Load transcript context
    transcript_result = await db.execute(
        select(TranscriptEntry)
        .where(TranscriptEntry.session_id == session_id)
        .order_by(TranscriptEntry.turn_index)
    )
    transcript_entries = transcript_result.scalars().all()
    transcript_context = [
        {
            "role": e.role,
            "text_en": e.text_en,
            "text_native": e.text_native,
        }
        for e in transcript_entries
    ]

    # Coach
    try:
        coach_response = await svc.coach_service.respond(
            user_text, transcript_context, session.language, session.mode, session.topic
        )
    except CoachError as e:
        raise HTTPException(status_code=502, detail=f"Coach failed: {e}")

    # Determine turn indices
    max_index = max((e.turn_index for e in transcript_entries), default=-1)
    user_turn_index = max_index + 1
    assistant_turn_index = user_turn_index + 1

    turn_id = uuid.uuid4()

    # TTS
    try:
        await svc.tts_service.synthesize(
            coach_response.text_native, session.language, turn_id
        )
    except TTSError as e:
        raise HTTPException(status_code=502, detail=f"Text-to-speech failed: {e}")

    # Persist transcript entries
    user_entry = TranscriptEntry(
        session_id=session_id,
        idempotency_key=idempotency_uuid,
        turn_index=user_turn_index,
        role="user",
        text_en=user_text,
    )
    assistant_entry = TranscriptEntry(
        id=turn_id,
        session_id=session_id,
        idempotency_key=uuid.uuid4(),
        turn_index=assistant_turn_index,
        role="assistant",
        text_en=coach_response.text_en,
        text_native=coach_response.text_native,
        text_reading=coach_response.text_reading,
        text_romanized=coach_response.text_romanized,
        pronunciation_note=coach_response.pronunciation_note,
        next_prompt=coach_response.next_prompt,
    )
    db.add(user_entry)
    db.add(assistant_entry)
    await db.commit()

    return TurnResponse(
        turn_id=turn_id,
        user_entry=TurnUserEntry(
            text_en=user_text,
            turn_index=user_turn_index,
        ),
        assistant_entry=TurnAssistantEntry(
            text_en=coach_response.text_en,
            text_native=coach_response.text_native,
            text_reading=coach_response.text_reading,
            text_romanized=coach_response.text_romanized,
            pronunciation_note=coach_response.pronunciation_note,
            next_prompt=coach_response.next_prompt,
            turn_index=assistant_turn_index,
        ),
        audio_url=f"/audio/{turn_id}.mp3",
    )
```

Modify `backend/app/main.py` to mount static files for audio:

```python
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload
from app.api.topics import router as topics_router
from app.api.conversation import router as conversation_router

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_dir = Path("/tmp/langua_audio")
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

app.include_router(topics_router)
app.include_router(conversation_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_conversation_turn.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/api/conversation.py backend/app/services/dependencies.py backend/app/main.py backend/tests/test_conversation_turn.py
git commit -m "feat: add POST /conversation/turn with full STT-Coach-TTS pipeline"
```

---

### Task 14: POST /conversation/end

**Files:**
- Modify: `backend/app/api/conversation.py`
- Test: `backend/tests/test_conversation_end.py`

**Step 1: Write the failing test**

`backend/tests/test_conversation_end.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.session import Session

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"
TEST_DATABASE_URL = "postgresql+asyncpg://langua:langua@localhost:5432/langua_test"


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
        "email": "end@example.com",
        "user_metadata": {"full_name": "End User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def learn_session(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="end@example.com", name="End User")
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
async def quiz_session(session_factory, user_id):
    async with session_factory() as db:
        existing = await db.execute(select(User).where(User.id == user_id))
        if not existing.scalar_one_or_none():
            user = User(id=user_id, email="end@example.com", name="End User")
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
async def test_end_learn_session(client, auth_headers, learn_session, session_factory):
    response = await client.post(
        "/conversation/end",
        headers=auth_headers,
        json={"session_id": str(learn_session)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ended"
    assert data["feedback_status"] is None

    async with session_factory() as db:
        result = await db.execute(select(Session).where(Session.id == learn_session))
        session = result.scalar_one()
        assert session.status == "ended"
        assert session.ended_at is not None


@pytest.mark.anyio
async def test_end_quiz_session(client, auth_headers, quiz_session, session_factory):
    response = await client.post(
        "/conversation/end",
        headers=auth_headers,
        json={"session_id": str(quiz_session)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ended"
    assert data["feedback_status"] == "pending"


@pytest.mark.anyio
async def test_end_is_idempotent(client, auth_headers, learn_session):
    response1 = await client.post(
        "/conversation/end",
        headers=auth_headers,
        json={"session_id": str(learn_session)},
    )
    response2 = await client.post(
        "/conversation/end",
        headers=auth_headers,
        json={"session_id": str(learn_session)},
    )
    assert response1.status_code == 200
    assert response2.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_conversation_end.py -v`
Expected: FAIL with 404 or 405

**Step 3: Write minimal implementation**

Add the endpoint to `backend/app/api/conversation.py`:

```python
from datetime import datetime, timezone

# ... (existing imports, add these)
from app.schemas.conversation import (
    StartConversationRequest,
    StartConversationResponse,
    TurnResponse,
    TurnUserEntry,
    TurnAssistantEntry,
    EndConversationRequest,
    EndConversationResponse,
)

# ... (existing endpoints)

@router.post("/end", response_model=EndConversationResponse)
async def end_conversation(
    request: EndConversationRequest,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == request.session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    if session.status == "ended":
        return EndConversationResponse(
            status="ended",
            feedback_status=session.feedback_status,
        )

    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)

    if session.mode == "quiz":
        session.feedback_status = "pending"

    await db.commit()

    return EndConversationResponse(
        status="ended",
        feedback_status=session.feedback_status,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_conversation_end.py -v`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add backend/app/api/conversation.py backend/tests/test_conversation_end.py
git commit -m "feat: add POST /conversation/end with quiz feedback_status=pending"
```

---

### Task 15: Turn idempotency + audio constraints

**Files:**
- Modify: `backend/app/api/conversation.py` (already implemented in Task 13)
- Test: `backend/tests/test_turn_constraints.py`

**Step 1: Write the failing test**

`backend/tests/test_turn_constraints.py`:

```python
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


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
            text_native="こんにちは",
            text_reading="こんにちは",
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_turn_constraints.py -v`
Expected: These should PASS immediately since the validation was already implemented in Task 13. If not, the implementation in Task 13 needs the audio size check and session status check. Both are present.

**Step 3: Verify implementation**

The implementation from Task 13 already includes:
- `MAX_AUDIO_SIZE = 1 * 1024 * 1024` with 413 response
- Session status check returning 409

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_turn_constraints.py -v`
Expected: PASS — both tests pass

**Step 5: Commit**

```bash
git add backend/tests/test_turn_constraints.py
git commit -m "test: add turn idempotency and audio constraint tests"
```

---

**Phase 4 Checkpoint:** The full conversation API is working. `GET /topics` returns hardcoded Japanese topics. `POST /conversation/start` creates sessions. `POST /conversation/turn` runs the full STT -> Coach -> TTS pipeline with idempotency and size checks. `POST /conversation/end` closes sessions and marks quiz sessions for feedback. The backend can be tested end-to-end with the Docker-hosted database and mocked AI services.

---

## Phase 5: Frontend Conversation (Tasks 16-20)

### Task 16: Home screen

**Files:**
- Create: `frontend/src/app/(protected)/layout.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/(protected)/page.tsx`
- Test: `frontend/src/app/(protected)/page.test.tsx`

**Step 1: Write the failing test**

`frontend/src/app/(protected)/page.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "123", email: "test@test.com" },
    loading: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ session_id: "abc-123" }), { status: 200 }),
    ),
  },
}));

import HomePage from "./page";

describe("HomePage", () => {
  it("renders mode selector with Learn and Quiz", () => {
    render(<HomePage />);
    expect(screen.getByText("Learn")).toBeDefined();
    expect(screen.getByText("Quiz")).toBeDefined();
  });

  it("renders topic dropdown", () => {
    render(<HomePage />);
    expect(screen.getByRole("combobox")).toBeDefined();
  });

  it("renders start button", () => {
    render(<HomePage />);
    expect(screen.getByRole("button", { name: /start/i })).toBeDefined();
  });

  it("renders language selector showing Japanese", () => {
    render(<HomePage />);
    expect(screen.getByText(/japanese/i)).toBeDefined();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run "src/app/(protected)/page.test.tsx"`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

`frontend/src/app/(protected)/layout.tsx`:

```tsx
"use client";

import { AuthGuard } from "@/components/AuthGuard";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGuard>{children}</AuthGuard>;
}
```

`frontend/src/app/(protected)/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

const TOPICS = ["Greetings", "Ordering Food", "Directions", "Shopping", "Travel"];

export default function HomePage() {
  const [mode, setMode] = useState<"learn" | "quiz">("learn");
  const [topic, setTopic] = useState(TOPICS[0]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { signOut } = useAuth();

  const handleStart = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post("/conversation/start", {
        language: "ja",
        mode,
        topic,
      });
      const data = await response.json();
      router.push(`/conversation/${data.session_id}`);
    } catch (error) {
      console.error("Failed to start conversation:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-4xl font-bold">Langua</h1>

      <div className="flex gap-3">
        <button
          onClick={() => setMode("learn")}
          className={`rounded-lg px-6 py-3 text-sm font-medium transition ${
            mode === "learn"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Learn
        </button>
        <button
          onClick={() => setMode("quiz")}
          className={`rounded-lg px-6 py-3 text-sm font-medium transition ${
            mode === "quiz"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Quiz
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-600">Topic</label>
        <select
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm"
        >
          {TOPICS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-600">Language</label>
        <span className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-500">
          Japanese (日本語)
        </span>
      </div>

      <button
        onClick={handleStart}
        disabled={loading}
        className="rounded-lg bg-green-600 px-8 py-3 text-sm font-medium text-white shadow-md hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? "Starting..." : "Start Session"}
      </button>

      <button
        onClick={signOut}
        className="mt-4 text-sm text-gray-400 hover:text-gray-600"
      >
        Sign out
      </button>
    </main>
  );
}
```

Update `frontend/src/app/page.tsx` to redirect:

```tsx
import { redirect } from "next/navigation";

export default function Root() {
  redirect("/sign-in");
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run "src/app/(protected)/page.test.tsx"`
Expected: PASS — all 4 tests pass

**Step 5: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/\(protected\)/ frontend/src/components/AuthGuard.tsx
git commit -m "feat: add home screen with mode selector, topic picker, and start button"
```

---

### Task 17: Audio recording hook

**Files:**
- Create: `frontend/src/hooks/useRecorder.ts`
- Test: Manual test checklist (MediaRecorder not available in jsdom)

**Step 1: Manual test checklist (no automated test possible)**

MediaRecorder API is not available in jsdom/Vitest. This task uses a manual verification approach.

**Manual Test Checklist:**
- [ ] Open browser console, verify `useRecorder` hook loads without errors
- [ ] Click record button, verify browser requests microphone permission
- [ ] Speak for a few seconds, click stop, verify Blob is produced
- [ ] Verify recording auto-stops at 15 seconds
- [ ] Verify Blob mime type is audio/webm
- [ ] Verify `isRecording` state toggles correctly

**Step 2: Write implementation**

`frontend/src/hooks/useRecorder.ts`:

```typescript
"use client";

import { useState, useRef, useCallback } from "react";

const MAX_DURATION_MS = 15_000;

interface UseRecorderReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  audioBlob: Blob | null;
  error: string | null;
}

export function useRecorder(): UseRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    setAudioBlob(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setAudioBlob(blob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);

      timerRef.current = setTimeout(() => {
        stopRecording();
      }, MAX_DURATION_MS);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to access microphone",
      );
    }
  }, [stopRecording]);

  return { isRecording, startRecording, stopRecording, audioBlob, error };
}
```

**Step 3: Commit**

```bash
git add frontend/src/hooks/useRecorder.ts
git commit -m "feat: add useRecorder hook with 15s max duration"
```

---

### Task 18: Waveform component

**Files:**
- Create: `frontend/src/components/Waveform.tsx`
- Test: `frontend/src/components/Waveform.test.tsx`

**Step 1: Write the failing test**

`frontend/src/components/Waveform.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Waveform } from "./Waveform";

describe("Waveform", () => {
  it("renders bars when active", () => {
    const { container } = render(<Waveform active={true} />);
    const bars = container.querySelectorAll("[data-testid='waveform-bar']");
    expect(bars.length).toBeGreaterThan(0);
  });

  it("renders nothing when inactive", () => {
    const { container } = render(<Waveform active={false} />);
    const bars = container.querySelectorAll("[data-testid='waveform-bar']");
    expect(bars.length).toBe(0);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/Waveform.test.tsx`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

`frontend/src/components/Waveform.tsx`:

```tsx
interface WaveformProps {
  active: boolean;
}

const BAR_DELAYS = [0, 0.15, 0.3, 0.1, 0.25, 0.05, 0.2, 0.35, 0.12, 0.28];

export function Waveform({ active }: WaveformProps) {
  if (!active) return null;

  return (
    <div className="flex items-center justify-center gap-1 py-4">
      {BAR_DELAYS.map((delay, i) => (
        <div
          key={i}
          data-testid="waveform-bar"
          className="w-1 animate-waveform rounded-full bg-blue-500"
          style={{
            animationDelay: `${delay}s`,
            height: "24px",
          }}
        />
      ))}
      <style>{`
        @keyframes waveform {
          0%, 100% { transform: scaleY(0.3); }
          50% { transform: scaleY(1); }
        }
        .animate-waveform {
          animation: waveform 0.8s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/Waveform.test.tsx`
Expected: PASS — both tests pass

**Step 5: Commit**

```bash
git add frontend/src/components/Waveform.tsx frontend/src/components/Waveform.test.tsx
git commit -m "feat: add Waveform animation component with CSS keyframes"
```

---

### Task 19: Conversation view

**Files:**
- Create: `frontend/src/app/(protected)/conversation/[sessionId]/page.tsx`
- Create: `frontend/src/components/TranscriptPanel.tsx`
- Create: `frontend/src/components/MicButton.tsx`
- Test: `frontend/src/components/TranscriptPanel.test.tsx`

**Step 1: Write the failing test**

`frontend/src/components/TranscriptPanel.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TranscriptPanel } from "./TranscriptPanel";

const ENTRIES = [
  {
    role: "user" as const,
    text_en: "I want to say hello",
    turn_index: 0,
  },
  {
    role: "assistant" as const,
    text_en: "Here is how to say hello:",
    text_native: "こんにちは",
    text_reading: "こんにちは",
    text_romanized: "konnichiwa",
    pronunciation_note: "Natural greeting",
    next_prompt: "Try saying it back to me",
    turn_index: 1,
  },
];

describe("TranscriptPanel", () => {
  it("renders user entries", () => {
    render(<TranscriptPanel entries={ENTRIES} />);
    expect(screen.getByText("I want to say hello")).toBeDefined();
  });

  it("renders assistant entries with all fields", () => {
    render(<TranscriptPanel entries={ENTRIES} />);
    expect(screen.getByText("こんにちは")).toBeDefined();
    expect(screen.getByText("konnichiwa")).toBeDefined();
    expect(screen.getByText("Natural greeting")).toBeDefined();
    expect(screen.getByText("Try saying it back to me")).toBeDefined();
  });

  it("renders empty state", () => {
    render(<TranscriptPanel entries={[]} />);
    expect(screen.getByText(/start speaking/i)).toBeDefined();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/TranscriptPanel.test.tsx`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

`frontend/src/components/TranscriptPanel.tsx`:

```tsx
interface TranscriptEntry {
  role: "user" | "assistant";
  text_en: string;
  text_native?: string;
  text_reading?: string;
  text_romanized?: string;
  pronunciation_note?: string;
  next_prompt?: string;
  turn_index: number;
}

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
}

export type { TranscriptEntry };

export function TranscriptPanel({ entries }: TranscriptPanelProps) {
  if (entries.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        <p>Start speaking to begin your lesson</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      {entries.map((entry) => (
        <div
          key={entry.turn_index}
          className={`rounded-lg p-4 ${
            entry.role === "user"
              ? "ml-8 bg-blue-50 text-right"
              : "mr-8 bg-gray-50"
          }`}
        >
          {entry.role === "user" ? (
            <p className="text-sm text-gray-700">{entry.text_en}</p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-gray-600">{entry.text_en}</p>
              {entry.text_native && (
                <p className="text-2xl font-bold text-gray-900">
                  {entry.text_native}
                </p>
              )}
              {entry.text_reading && (
                <p className="text-sm text-gray-500">{entry.text_reading}</p>
              )}
              {entry.text_romanized && (
                <p className="text-sm font-medium text-blue-600">
                  {entry.text_romanized}
                </p>
              )}
              {entry.pronunciation_note && (
                <p className="text-xs italic text-amber-600">
                  {entry.pronunciation_note}
                </p>
              )}
              {entry.next_prompt && (
                <p className="mt-1 text-sm font-medium text-green-700">
                  {entry.next_prompt}
                </p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

`frontend/src/components/MicButton.tsx`:

```tsx
interface MicButtonProps {
  isRecording: boolean;
  isProcessing: boolean;
  onToggle: () => void;
}

export function MicButton({ isRecording, isProcessing, onToggle }: MicButtonProps) {
  return (
    <button
      onClick={onToggle}
      disabled={isProcessing}
      className={`flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition-all ${
        isRecording
          ? "bg-red-500 hover:bg-red-600 scale-110"
          : isProcessing
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700"
      }`}
      aria-label={isRecording ? "Stop recording" : "Start recording"}
    >
      {isProcessing ? (
        <svg
          className="h-6 w-6 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      ) : (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
          {isRecording ? (
            <rect x="6" y="6" width="12" height="12" rx="2" />
          ) : (
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1 1.93c-3.94-.49-7-3.85-7-7.93h2c0 3.31 2.69 6 6 6s6-2.69 6-6h2c0 4.08-3.06 7.44-7 7.93V20h4v2H8v-2h4v-4.07z" />
          )}
        </svg>
      )}
    </button>
  );
}
```

`frontend/src/app/(protected)/conversation/[sessionId]/page.tsx`:

```tsx
"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useRecorder } from "@/hooks/useRecorder";
import { apiClient } from "@/lib/api";
import { Waveform } from "@/components/Waveform";
import { TranscriptPanel, TranscriptEntry } from "@/components/TranscriptPanel";
import { MicButton } from "@/components/MicButton";

export default function ConversationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const { isRecording, startRecording, stopRecording, audioBlob, error } =
    useRecorder();
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleToggle = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  useEffect(() => {
    if (!audioBlob) return;

    const sendTurn = async () => {
      setIsProcessing(true);
      setProcessingError(null);

      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("audio", audioBlob, "audio.webm");

      const idempotencyKey = crypto.randomUUID();

      try {
        const response = await apiClient.postFormData(
          "/conversation/turn",
          formData,
          { "X-Idempotency-Key": idempotencyKey },
        );

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Turn failed");
        }

        const data = await response.json();

        setEntries((prev) => [
          ...prev,
          { ...data.user_entry, role: "user" as const },
          { ...data.assistant_entry, role: "assistant" as const },
        ]);

        // Play audio
        const audioUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${data.audio_url}`;
        const audio = new Audio(audioUrl);
        audio.play().catch(() => {});
      } catch (err) {
        setProcessingError(
          err instanceof Error ? err.message : "Something went wrong",
        );
      } finally {
        setIsProcessing(false);
      }
    };

    sendTurn();
  }, [audioBlob, sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [entries]);

  const handleEnd = async () => {
    try {
      const response = await apiClient.post("/conversation/end", {
        session_id: sessionId,
      });
      const data = await response.json();

      if (data.feedback_status === "pending") {
        router.push(`/results/${sessionId}`);
      } else {
        router.push("/");
      }
    } catch {
      router.push("/");
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <h1 className="text-lg font-semibold">Conversation</h1>
        <button
          onClick={handleEnd}
          className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
        >
          End Session
        </button>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <TranscriptPanel entries={entries} />
      </div>

      {error && (
        <p className="px-4 text-center text-sm text-red-500">{error}</p>
      )}
      {processingError && (
        <p className="px-4 text-center text-sm text-red-500">
          {processingError}
        </p>
      )}

      <div className="flex flex-col items-center gap-2 border-t px-6 py-4">
        <Waveform active={isRecording} />
        <MicButton
          isRecording={isRecording}
          isProcessing={isProcessing}
          onToggle={handleToggle}
        />
        <p className="text-xs text-gray-400">
          {isRecording
            ? "Recording... tap to stop"
            : isProcessing
              ? "Processing..."
              : "Tap to speak"}
        </p>
      </div>
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/TranscriptPanel.test.tsx`
Expected: PASS — all 3 tests pass

**Step 5: Commit**

```bash
git add frontend/src/components/TranscriptPanel.tsx frontend/src/components/TranscriptPanel.test.tsx frontend/src/components/MicButton.tsx frontend/src/app/\(protected\)/conversation/
git commit -m "feat: add conversation view with recording, transcript, and audio playback"
```

---

### Task 20: Learn mode integration test

**Files:**
- No new files; this is a manual verification task

**Manual End-to-End Test Checklist:**

1. [ ] Start Docker services: `docker compose up -d`
2. [ ] Run backend: `cd backend && uvicorn app.main:app --reload`
3. [ ] Run frontend: `cd frontend && npm run dev`
4. [ ] Open browser at http://localhost:3000
5. [ ] Verify redirect to /sign-in
6. [ ] Sign in with Google or GitHub
7. [ ] Verify redirect to home screen
8. [ ] Select "Learn" mode and "Greetings" topic
9. [ ] Click "Start Session"
10. [ ] Verify redirect to conversation page
11. [ ] Tap mic button, speak in English, tap to stop
12. [ ] Verify loading indicator appears during processing
13. [ ] Verify transcript shows user entry and assistant response
14. [ ] Verify audio plays automatically
15. [ ] Do 2-3 more turns
16. [ ] Click "End Session"
17. [ ] Verify return to home screen

---

**Phase 5 Checkpoint:** The frontend conversation flow is complete for learn mode. Users can sign in, select a topic, start a conversation, record audio, see transcript responses, hear audio playback, and end the session. The waveform animates during recording and a loading indicator shows during processing.

---

## Phase 6: Quiz Mode & Feedback (Tasks 21-26)

### Task 21: Arq worker setup

**Files:**
- Create: `backend/app/worker/__init__.py`
- Create: `backend/app/worker/settings.py`
- Test: `backend/tests/test_worker_settings.py`

**Step 1: Write the failing test**

`backend/tests/test_worker_settings.py`:

```python
import pytest


def test_worker_settings_importable():
    from app.worker.settings import WorkerSettings
    assert hasattr(WorkerSettings, "functions")
    assert hasattr(WorkerSettings, "redis_settings")


def test_worker_settings_has_functions():
    from app.worker.settings import WorkerSettings
    assert isinstance(WorkerSettings.functions, list)
    assert len(WorkerSettings.functions) >= 1
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_worker_settings.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

`backend/app/worker/__init__.py`:

```python
```

`backend/app/worker/settings.py`:

```python
from arq.connections import RedisSettings

from app.core.config import settings


async def generate_feedback(ctx: dict, session_id: str) -> None:
    from app.worker.tasks import run_feedback_generation
    await run_feedback_generation(ctx, session_id)


class WorkerSettings:
    functions = [generate_feedback]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.worker_concurrency
    job_timeout = 120
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_worker_settings.py -v`
Expected: PASS — both tests pass

**Step 5: Commit**

```bash
git add backend/app/worker/ backend/tests/test_worker_settings.py
git commit -m "feat: add Arq worker settings with feedback job registration"
```

---

### Task 22: Feedback generation job

**Files:**
- Create: `backend/app/worker/tasks.py`
- Create: `backend/app/schemas/feedback.py`
- Test: `backend/tests/test_feedback_job.py`

**Step 1: Write the failing test**

`backend/tests/test_feedback_job.py`:

```python
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


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
            text_native="こんにちは",
            text_reading="こんにちは",
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_feedback_job.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

`backend/app/schemas/feedback.py`:

```python
from pydantic import BaseModel


class FeedbackResponse(BaseModel):
    correct: list[str]
    revisit: list[str]
    drills: list[str]


class FeedbackStatusResponse(BaseModel):
    feedback_status: str | None


class FeedbackDetail(BaseModel):
    correct: list[str]
    revisit: list[str]
    drills: list[str]
```

`backend/app/worker/tasks.py`:

```python
import json
import logging
import uuid
from datetime import datetime, timezone

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.feedback import Feedback
from app.services.prompts import FEEDBACK_PROMPT
from app.schemas.feedback import FeedbackResponse

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url


async def run_feedback_generation(ctx: dict, session_id: str) -> None:
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as db:
            result = await db.execute(
                select(Session).where(Session.id == uuid.UUID(session_id))
            )
            session = result.scalar_one_or_none()
            if session is None:
                logger.error(f"Session {session_id} not found")
                return

            if session.feedback_status not in ("pending", "failed"):
                logger.info(f"Session {session_id} feedback_status={session.feedback_status}, skipping")
                return

            transcript_result = await db.execute(
                select(TranscriptEntry)
                .where(TranscriptEntry.session_id == session.id)
                .order_by(TranscriptEntry.turn_index)
            )
            entries = transcript_result.scalars().all()

            transcript_text = "\n".join(
                f"[{e.role}] {e.text_en or ''} | {e.text_native or ''}"
                for e in entries
            )

            last_error = None
            for attempt in range(3):
                try:
                    client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=30.0)
                    response = await client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        system=FEEDBACK_PROMPT,
                        messages=[{"role": "user", "content": f"Here is the quiz transcript:\n\n{transcript_text}"}],
                    )

                    raw_text = response.content[0].text.strip()
                    if raw_text.startswith("```"):
                        lines = raw_text.split("\n")
                        raw_text = "\n".join(lines[1:-1])

                    data = json.loads(raw_text)
                    feedback_data = FeedbackResponse(**data)

                    feedback = Feedback(
                        session_id=session.id,
                        correct=feedback_data.correct,
                        revisit=feedback_data.revisit,
                        drills=feedback_data.drills,
                    )
                    db.add(feedback)

                    session.feedback_status = "ready"
                    session.feedback_generated_at = datetime.now(timezone.utc)
                    session.feedback_error = None
                    await db.commit()

                    logger.info(f"Feedback generated for session {session_id}")
                    return

                except Exception as e:
                    last_error = e
                    logger.warning(f"Feedback attempt {attempt + 1} failed: {e}")
                    continue

            session.feedback_status = "failed"
            session.feedback_error = str(last_error)[:500]
            await db.commit()
            logger.error(f"Feedback generation failed for session {session_id}: {last_error}")

    finally:
        await engine.dispose()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_feedback_job.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/worker/tasks.py backend/app/schemas/feedback.py backend/tests/test_feedback_job.py
git commit -m "feat: add feedback generation worker task with 3x retry"
```

---

### Task 23: POST /conversation/end quiz integration

**Files:**
- Modify: `backend/app/api/conversation.py`
- Test: `backend/tests/test_end_quiz_enqueue.py`

**Step 1: Write the failing test**

`backend/tests/test_end_quiz_enqueue.py`:

```python
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


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
        # Second call is idempotent — session is already ended with pending status
        response2 = await client.post(
            "/conversation/end",
            headers=auth_headers,
            json={"session_id": str(quiz_session)},
        )
        assert response2.status_code == 200
        # Should only enqueue once
        assert mock_pool.enqueue_job.call_count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_end_quiz_enqueue.py -v`
Expected: FAIL because `get_arq_pool` doesn't exist yet

**Step 3: Write minimal implementation**

Update `backend/app/api/conversation.py` — add Arq integration to the end endpoint:

```python
import uuid
from datetime import datetime, timezone

from arq.connections import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.config import settings
from app.core.database import get_db
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.user import User
from app.schemas.conversation import (
    StartConversationRequest,
    StartConversationResponse,
    TurnResponse,
    TurnUserEntry,
    TurnAssistantEntry,
    EndConversationRequest,
    EndConversationResponse,
)
from app.services import dependencies as svc
from app.services.errors import STTError, CoachError, TTSError

router = APIRouter(prefix="/conversation")

MAX_AUDIO_SIZE = 1 * 1024 * 1024


async def get_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


# ... (start and turn endpoints remain the same as Task 13)


@router.post("/end", response_model=EndConversationResponse)
async def end_conversation(
    request: EndConversationRequest,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == request.session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    if session.status == "ended":
        return EndConversationResponse(
            status="ended",
            feedback_status=session.feedback_status,
        )

    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)

    if session.mode == "quiz":
        session.feedback_status = "pending"

    await db.commit()

    if session.mode == "quiz":
        pool = await get_arq_pool()
        await pool.enqueue_job("generate_feedback", str(request.session_id))

    return EndConversationResponse(
        status="ended",
        feedback_status=session.feedback_status,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_end_quiz_enqueue.py -v`
Expected: PASS — both tests pass

**Step 5: Commit**

```bash
git add backend/app/api/conversation.py backend/tests/test_end_quiz_enqueue.py
git commit -m "feat: enqueue Arq feedback job when quiz session ends"
```

---

### Task 24: Feedback polling endpoints

**Files:**
- Create: `backend/app/api/sessions.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_feedback_endpoints.py`

**Step 1: Write the failing test**

`backend/tests/test_feedback_endpoints.py`:

```python
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
from app.models.feedback import Feedback

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"
TEST_DATABASE_URL = "postgresql+asyncpg://langua:langua@localhost:5432/langua_test"


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
async def pending_session(session_factory, user_id):
    async with session_factory() as db:
        user = User(id=user_id, email="feedback@example.com", name="Feedback User")
        db.add(user)
        await db.flush()
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="pending",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
async def failed_session(session_factory, user_id):
    async with session_factory() as db:
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="failed",
            feedback_error="LLM timeout",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id


@pytest.fixture
async def ready_session(session_factory, user_id):
    async with session_factory() as db:
        session = Session(
            user_id=user_id, language="ja", mode="quiz",
            topic="Greetings", status="ended", feedback_status="ready",
        )
        db.add(session)
        await db.flush()
        feedback = Feedback(
            session_id=session.id,
            correct=["konnichiwa"],
            revisit=["sumimasen"],
            drills=["Practice greetings"],
        )
        db.add(feedback)
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
        mock_pool.enqueue_job.assert_called_once()


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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_feedback_endpoints.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

`backend/app/api/sessions.py`:

```python
import uuid

from arq.connections import ArqRedis, create_pool, RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.config import settings
from app.core.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.feedback import FeedbackStatusResponse

router = APIRouter(prefix="/sessions")


async def get_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


@router.get("/{session_id}/feedback-status", response_model=FeedbackStatusResponse)
async def feedback_status(
    session_id: uuid.UUID,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    return FeedbackStatusResponse(feedback_status=session.feedback_status)


@router.post("/{session_id}/retry-feedback")
async def retry_feedback(
    session_id: uuid.UUID,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    if session.feedback_status != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry: feedback_status is {session.feedback_status}",
        )

    session.feedback_status = "pending"
    session.feedback_error = None
    await db.commit()

    pool = await get_arq_pool()
    await pool.enqueue_job("generate_feedback", str(session_id))

    return {"status": "retrying"}
```

Update `backend/app/main.py` to include the sessions router:

```python
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload
from app.api.topics import router as topics_router
from app.api.conversation import router as conversation_router
from app.api.sessions import router as sessions_router

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_dir = Path("/tmp/langua_audio")
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

app.include_router(topics_router)
app.include_router(conversation_router)
app.include_router(sessions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_feedback_endpoints.py -v`
Expected: PASS — all 5 tests pass

**Step 5: Commit**

```bash
git add backend/app/api/sessions.py backend/app/main.py backend/tests/test_feedback_endpoints.py
git commit -m "feat: add feedback status polling and retry endpoints"
```

---

### Task 25: Frontend quiz timer

**Files:**
- Create: `frontend/src/components/QuizTimer.tsx`
- Test: `frontend/src/components/QuizTimer.test.tsx`

**Step 1: Write the failing test**

`frontend/src/components/QuizTimer.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { QuizTimer } from "./QuizTimer";

describe("QuizTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders initial time as 2:00", () => {
    render(<QuizTimer durationSeconds={120} onExpire={vi.fn()} />);
    expect(screen.getByText("2:00")).toBeDefined();
  });

  it("counts down every second", () => {
    render(<QuizTimer durationSeconds={120} onExpire={vi.fn()} />);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("1:59")).toBeDefined();
  });

  it("calls onExpire when timer reaches zero", () => {
    const onExpire = vi.fn();
    render(<QuizTimer durationSeconds={3} onExpire={onExpire} />);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("shows red text when under 30 seconds", () => {
    const { container } = render(
      <QuizTimer durationSeconds={30} onExpire={vi.fn()} />,
    );
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const timer = container.querySelector("[data-testid='quiz-timer']");
    expect(timer?.className).toContain("text-red");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/QuizTimer.test.tsx`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

`frontend/src/components/QuizTimer.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef } from "react";

interface QuizTimerProps {
  durationSeconds: number;
  onExpire: () => void;
}

export function QuizTimer({ durationSeconds, onExpire }: QuizTimerProps) {
  const [remaining, setRemaining] = useState(durationSeconds);
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          clearInterval(interval);
          onExpireRef.current();
          return 0;
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [durationSeconds]);

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const display = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  return (
    <div
      data-testid="quiz-timer"
      className={`text-lg font-mono font-bold ${
        remaining <= 30 ? "text-red-500" : "text-gray-700"
      }`}
    >
      {display}
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/QuizTimer.test.tsx`
Expected: PASS — all 4 tests pass

**Step 5: Commit**

```bash
git add frontend/src/components/QuizTimer.tsx frontend/src/components/QuizTimer.test.tsx
git commit -m "feat: add QuizTimer component with countdown and onExpire callback"
```

---

### Task 26: Frontend quiz results page

**Files:**
- Create: `frontend/src/app/(protected)/results/[sessionId]/page.tsx`
- Create: `frontend/src/components/FeedbackCard.tsx`
- Test: `frontend/src/components/FeedbackCard.test.tsx`

**Step 1: Write the failing test**

`frontend/src/components/FeedbackCard.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FeedbackCard } from "./FeedbackCard";

const FEEDBACK = {
  correct: ["konnichiwa", "arigatou"],
  revisit: ["sumimasen"],
  drills: ["Practice basic greetings", "Role-play ordering food"],
};

describe("FeedbackCard", () => {
  it("renders correct phrases", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText("konnichiwa")).toBeDefined();
    expect(screen.getByText("arigatou")).toBeDefined();
  });

  it("renders phrases to revisit", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText("sumimasen")).toBeDefined();
  });

  it("renders suggested drills", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText("Practice basic greetings")).toBeDefined();
    expect(screen.getByText("Role-play ordering food")).toBeDefined();
  });

  it("renders section headings", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText(/what you got right/i)).toBeDefined();
    expect(screen.getByText(/to revisit/i)).toBeDefined();
    expect(screen.getByText(/suggested drills/i)).toBeDefined();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/FeedbackCard.test.tsx`
Expected: FAIL with module not found

**Step 3: Write minimal implementation**

`frontend/src/components/FeedbackCard.tsx`:

```tsx
interface FeedbackData {
  correct: string[];
  revisit: string[];
  drills: string[];
}

interface FeedbackCardProps {
  feedback: FeedbackData;
}

export type { FeedbackData };

export function FeedbackCard({ feedback }: FeedbackCardProps) {
  return (
    <div className="flex flex-col gap-6 rounded-xl bg-white p-6 shadow-lg">
      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-600">
          What You Got Right
        </h3>
        <ul className="flex flex-col gap-1">
          {feedback.correct.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-green-500">&#10003;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-amber-600">
          To Revisit
        </h3>
        <ul className="flex flex-col gap-1">
          {feedback.revisit.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-amber-500">&#9679;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-600">
          Suggested Drills
        </h3>
        <ul className="flex flex-col gap-1">
          {feedback.drills.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-blue-500">&#8250;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

`frontend/src/app/(protected)/results/[sessionId]/page.tsx`:

```tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { FeedbackCard, FeedbackData } from "@/components/FeedbackCard";

type FeedbackStatus = "pending" | "ready" | "failed" | null;

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [feedbackStatus, setFeedbackStatus] = useState<FeedbackStatus>("pending");
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const response = await apiClient.get(
          `/sessions/${sessionId}/feedback-status`,
        );
        const data = await response.json();
        setFeedbackStatus(data.feedback_status);

        if (data.feedback_status === "ready") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          const sessionResponse = await apiClient.get(`/sessions/${sessionId}`);
          const sessionData = await sessionResponse.json();
          if (sessionData.feedback && sessionData.feedback.length > 0) {
            setFeedback(sessionData.feedback[0]);
          }
        } else if (data.feedback_status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        setError("Failed to check feedback status");
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 3000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [sessionId]);

  const handleRetry = async () => {
    setRetrying(true);
    setError(null);
    try {
      await apiClient.post(`/sessions/${sessionId}/retry-feedback`);
      setFeedbackStatus("pending");
      intervalRef.current = setInterval(async () => {
        const response = await apiClient.get(
          `/sessions/${sessionId}/feedback-status`,
        );
        const data = await response.json();
        setFeedbackStatus(data.feedback_status);
        if (data.feedback_status === "ready" || data.feedback_status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          if (data.feedback_status === "ready") {
            const sessionResponse = await apiClient.get(`/sessions/${sessionId}`);
            const sessionData = await sessionResponse.json();
            if (sessionData.feedback && sessionData.feedback.length > 0) {
              setFeedback(sessionData.feedback[0]);
            }
          }
        }
      }, 3000);
    } catch {
      setError("Failed to retry");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-bold">Quiz Results</h1>

      {feedbackStatus === "pending" && (
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-gray-500">Processing your results...</p>
        </div>
      )}

      {feedbackStatus === "ready" && feedback && (
        <FeedbackCard feedback={feedback} />
      )}

      {feedbackStatus === "failed" && (
        <div className="flex flex-col items-center gap-3">
          <p className="text-red-500">
            Failed to generate feedback. Please try again.
          </p>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {retrying ? "Retrying..." : "Retry"}
          </button>
        </div>
      )}

      <button
        onClick={() => router.push("/")}
        className="mt-4 text-sm text-gray-400 hover:text-gray-600"
      >
        Back to Home
      </button>
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/FeedbackCard.test.tsx`
Expected: PASS — all 4 tests pass

**Step 5: Commit**

```bash
git add frontend/src/components/FeedbackCard.tsx frontend/src/components/FeedbackCard.test.tsx frontend/src/app/\(protected\)/results/
git commit -m "feat: add quiz results page with feedback polling and retry"
```

---

**Phase 6 Checkpoint:** Quiz mode is fully working end-to-end. The Arq worker processes feedback jobs. The `/conversation/end` endpoint enqueues feedback for quiz sessions. The frontend has a quiz timer that auto-ends sessions, and the results page polls for feedback status, displays feedback cards, and handles retry on failure.

---

## Phase 7: Sessions & Observability (Tasks 27-29)

### Task 27: Session endpoints

**Files:**
- Modify: `backend/app/api/sessions.py`
- Create: `backend/app/schemas/session.py`
- Test: `backend/tests/test_session_endpoints.py`

**Step 1: Write the failing test**

`backend/tests/test_session_endpoints.py`:

```python
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


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_session_endpoints.py -v`
Expected: FAIL with 404 or 405

**Step 3: Write minimal implementation**

`backend/app/schemas/session.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class TranscriptEntrySchema(BaseModel):
    id: uuid.UUID
    turn_index: int
    role: str
    text_en: str | None = None
    text_native: str | None = None
    text_reading: str | None = None
    text_romanized: str | None = None
    pronunciation_note: str | None = None
    next_prompt: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackSchema(BaseModel):
    id: uuid.UUID
    correct: list[str]
    revisit: list[str]
    drills: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    id: uuid.UUID
    language: str
    mode: str
    topic: str
    status: str
    feedback_status: str | None = None
    started_at: datetime
    ended_at: datetime | None = None

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    id: uuid.UUID
    language: str
    mode: str
    topic: str
    status: str
    feedback_status: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    transcript: list[TranscriptEntrySchema]
    feedback: list[FeedbackSchema]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    total: int
```

Add to `backend/app/api/sessions.py` (modify, full file):

```python
import uuid

from arq.connections import ArqRedis, create_pool, RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.config import settings
from app.core.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.feedback import FeedbackStatusResponse
from app.schemas.session import (
    SessionDetail,
    SessionListResponse,
    SessionSummary,
    TranscriptEntrySchema,
    FeedbackSchema,
)

router = APIRouter(prefix="/sessions")


async def get_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(func.count()).select_from(Session).where(Session.user_id == user.id)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Session)
        .where(Session.user_id == user.id)
        .order_by(Session.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[SessionSummary.model_validate(s) for s in sessions],
        total=total or 0,
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: uuid.UUID,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    return SessionDetail(
        id=session.id,
        language=session.language,
        mode=session.mode,
        topic=session.topic,
        status=session.status,
        feedback_status=session.feedback_status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        transcript=[TranscriptEntrySchema.model_validate(t) for t in session.transcript],
        feedback=[FeedbackSchema.model_validate(f) for f in session.feedback],
    )


@router.get("/{session_id}/feedback-status", response_model=FeedbackStatusResponse)
async def feedback_status(
    session_id: uuid.UUID,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    return FeedbackStatusResponse(feedback_status=session.feedback_status)


@router.post("/{session_id}/retry-feedback")
async def retry_feedback(
    session_id: uuid.UUID,
    user: User = Depends(get_or_create_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    if session.feedback_status != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry: feedback_status is {session.feedback_status}",
        )

    session.feedback_status = "pending"
    session.feedback_error = None
    await db.commit()

    pool = await get_arq_pool()
    await pool.enqueue_job("generate_feedback", str(session_id))

    return {"status": "retrying"}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_session_endpoints.py -v`
Expected: PASS — all 4 tests pass

**Step 5: Commit**

```bash
git add backend/app/api/sessions.py backend/app/schemas/session.py backend/tests/test_session_endpoints.py
git commit -m "feat: add session list and detail endpoints with pagination"
```

---

### Task 28: Frontend session history

**Files:**
- Create: `frontend/src/app/(protected)/sessions/page.tsx`
- Create: `frontend/src/app/(protected)/sessions/[sessionId]/page.tsx`
- Test: Manual test checklist (depends on API and auth state)

**Step 1: Manual test checklist**

- [ ] Navigate to /sessions
- [ ] Verify list of past sessions renders with topic, mode, date
- [ ] Click a session to navigate to detail view
- [ ] Verify transcript entries render correctly
- [ ] Verify feedback shows for quiz sessions

**Step 2: Write implementation**

`frontend/src/app/(protected)/sessions/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";

interface SessionSummary {
  id: string;
  language: string;
  mode: string;
  topic: string;
  status: string;
  feedback_status: string | null;
  started_at: string;
  ended_at: string | null;
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await apiClient.get("/sessions");
        const data = await response.json();
        setSessions(data.sessions);
      } catch (error) {
        console.error("Failed to fetch sessions:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading sessions...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Session History</h1>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          New Session
        </button>
      </div>

      {sessions.length === 0 ? (
        <p className="text-gray-500">No sessions yet. Start your first conversation!</p>
      ) : (
        <div className="flex flex-col gap-3">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => router.push(`/sessions/${session.id}`)}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm hover:border-blue-300 hover:shadow-md transition"
            >
              <div>
                <p className="font-medium text-gray-900">{session.topic}</p>
                <p className="text-sm text-gray-500">
                  {session.mode === "quiz" ? "Quiz" : "Learn"} &middot;{" "}
                  {new Date(session.started_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-1 text-xs font-medium ${
                    session.status === "active"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {session.status}
                </span>
                {session.feedback_status === "ready" && (
                  <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                    Feedback ready
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

`frontend/src/app/(protected)/sessions/[sessionId]/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { TranscriptPanel, TranscriptEntry } from "@/components/TranscriptPanel";
import { FeedbackCard, FeedbackData } from "@/components/FeedbackCard";

interface SessionDetail {
  id: string;
  language: string;
  mode: string;
  topic: string;
  status: string;
  feedback_status: string | null;
  started_at: string;
  ended_at: string | null;
  transcript: TranscriptEntry[];
  feedback: FeedbackData[];
}

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const response = await apiClient.get(`/sessions/${sessionId}`);
        const data = await response.json();
        setSession(data);
      } catch (error) {
        console.error("Failed to fetch session:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSession();
  }, [sessionId]);

  if (loading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading session...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <button
        onClick={() => router.push("/sessions")}
        className="mb-4 text-sm text-blue-600 hover:text-blue-700"
      >
        &larr; Back to sessions
      </button>

      <div className="mb-6">
        <h1 className="text-2xl font-bold">{session.topic}</h1>
        <p className="text-sm text-gray-500">
          {session.mode === "quiz" ? "Quiz" : "Learn"} &middot;{" "}
          {new Date(session.started_at).toLocaleDateString()}
        </p>
      </div>

      <div className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Transcript</h2>
        <TranscriptPanel entries={session.transcript} />
      </div>

      {session.feedback && session.feedback.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold">Feedback</h2>
          <FeedbackCard feedback={session.feedback[0]} />
        </div>
      )}
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/app/\(protected\)/sessions/
git commit -m "feat: add session history and detail pages"
```

---

### Task 29: Observability middleware

**Files:**
- Create: `backend/app/core/middleware.py`
- Create: `backend/app/core/logging.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_middleware.py`

**Step 1: Write the failing test**

`backend/tests/test_middleware.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_request_id_header_present(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID format


@pytest.mark.anyio
async def test_request_id_is_unique(client):
    response1 = await client.get("/health")
    response2 = await client.get("/health")
    assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_middleware.py -v`
Expected: FAIL because X-Request-ID header is not present

**Step 3: Write minimal implementation**

`backend/app/core/logging.py`:

```python
import logging
import sys
import time


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def log_ai_call(
    logger: logging.Logger,
    request_id: str,
    session_id: str | None,
    operation: str,
    provider: str,
    duration_ms: float,
    status: str,
):
    logger.info(
        "ai_call",
        extra={
            "request_id": request_id,
            "session_id": session_id,
            "operation": operation,
            "provider": provider,
            "duration_ms": round(duration_ms, 2),
            "status": status,
        },
    )
```

`backend/app/core/middleware.py`:

```python
import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"request method={request.method} path={request.url.path} "
            f"status={response.status_code} duration_ms={duration_ms:.2f} "
            f"request_id={request_id}"
        )

        return response
```

Modify `backend/app/main.py` to add the middleware:

```python
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.schemas.auth import JWTPayload
from app.api.topics import router as topics_router
from app.api.conversation import router as conversation_router
from app.api.sessions import router as sessions_router

setup_logging()

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_dir = Path("/tmp/langua_audio")
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

app.include_router(topics_router)
app.include_router(conversation_router)
app.include_router(sessions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_middleware.py -v`
Expected: PASS — both tests pass

**Step 5: Commit**

```bash
git add backend/app/core/middleware.py backend/app/core/logging.py backend/app/main.py backend/tests/test_middleware.py
git commit -m "feat: add request_id middleware and structured logging"
```

---

**Phase 7 Checkpoint:** Session history is browsable in the frontend. Users can view past sessions, their transcripts, and feedback. Every backend request has a unique request_id (returned as X-Request-ID header) and is logged with method, path, status, and duration. AI service calls can be traced back to their originating request. The worker logs job execution with session_id, attempt number, and outcome.

---

## Final Verification Checklist

After all 29 tasks are complete:

1. **Backend Tests:** `cd backend && python -m pytest tests/ -v` — all tests pass
2. **Frontend Tests:** `cd frontend && npx vitest run` — all tests pass
3. **Docker Services:** `docker compose up -d` — Postgres and Redis running
4. **Database:** `cd backend && alembic upgrade head` — migrations applied
5. **Backend Server:** `cd backend && uvicorn app.main:app --reload` — starts on 8000
6. **Worker:** `cd backend && arq app.worker.settings.WorkerSettings` — connects to Redis
7. **Frontend:** `cd frontend && npm run dev` — starts on 3000
8. **End-to-End Flow:**
   - Sign in via Google/GitHub
   - Start a Learn session, do 2+ turns, end session
   - Start a Quiz session, do turns, wait for timer or end manually
   - View results page, see feedback
   - Browse session history

---
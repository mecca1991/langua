# Langua

Voice-first Japanese language learning app. Users speak into the app and get spoken AI responses back in real time.

Supports two modes: `learn` (open conversation practice) and `quiz` (structured speaking exercises with async feedback).

## How It Works

1. User signs in via Supabase OAuth.
2. Starts a `learn` or `quiz` session.
3. Speaks into the app — audio is sent to the FastAPI backend.
4. Backend runs speech-to-text → generates a response → runs text-to-speech.
5. Frontend plays back the response and updates the transcript.
6. Completed quiz sessions trigger background feedback generation via an ARQ worker.

Users can resume active sessions, review transcripts, and retry failed feedback jobs.

## Tech Stack

**Frontend:** Next.js 14, React 18, TypeScript, Supabase Auth, Tailwind CSS, Vitest

**Backend:** FastAPI, SQLAlchemy (async), PostgreSQL, Redis, ARQ, Alembic, OpenAI + Anthropic APIs

## Architecture

### Backend

Layered monolith — routes handle transport, services handle orchestration, repositories handle data access. Structured error responses with request IDs. Background worker handles deferred feedback processing.

### Frontend

App Router with protected and public route groups. Shared auth provider, typed API client with normalized errors, and a reusable async query hook for data loading.

## Repo Structure

```
├── backend/           # FastAPI app, services, repos, worker, tests
├── frontend/          # Next.js app, auth, conversation UI, tests
├── docs/              # Planning and design notes
├── docker-compose.yml
└── .env.example
```

## Setup

### Prerequisites

- Node.js 18+
- Python 3.12+
- Docker
- Supabase project (for OAuth)
- OpenAI and Anthropic API keys

### Environment Variables

```bash
cp .env.example .env
cp .env.example backend/.env
```

The root `.env` covers backend and infrastructure config. Create `frontend/.env` separately:

```env
NEXT_PUBLIC_SUPABASE_URL=<your-supabase-url>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=<your-supabase-key>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run

```bash
# Start backend, Postgres, Redis, and worker
docker compose up --build

# Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Backend: `http://localhost:8000`
Frontend: `http://localhost:3000`

## Tests

```bash
# Frontend
cd frontend && npm test

# Backend
cd backend && pytest
```

## Status

Working end-to-end: auth, voice loop, session management, transcript history, quiz feedback with polling and retry.

## **Next up:** expanded language support, deployment story, learning analytics.
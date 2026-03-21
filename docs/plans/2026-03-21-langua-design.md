# Langua Language Assistant — Design Document

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

Langua is a voice-first language learning assistant. Users have spoken conversations with an AI coach that guides pronunciation, corrects mistakes, and adapts to their learning gaps. The initial release targets Japanese learners, with a web app first and mobile to follow. The architecture supports adding languages without structural changes — session and transcript models carry a language field, and language-specific behavior (script forms, coach system prompt, topic lists) is driven by configuration rather than code.

---

## Goals

- Help users build spoken confidence in Japanese through interactive voice conversation
- Provide push-to-talk pronunciation coaching (speak, get corrected, repeat)
- Offer a timed quiz mode that evaluates performance and gives adaptive feedback
- Track progress across sessions per user

---

## Architecture

```
Next.js (Frontend)
     ↓ REST only (no WebSocket in v1)
FastAPI (Backend)
     ├── Auth: Supabase JWT verification (python-jose, SUPABASE_JWT_SECRET)
     ├── Conversation API: synchronous turn handling (STT → Coach → TTS)
     ├── AI Service Layer: Whisper / Claude / TTS wrappers with timeouts
     ├── Feedback Worker: Arq (Redis-backed) — async quiz feedback
     └── DB: PostgreSQL + SQLAlchemy + Alembic

Supabase Auth
     ├── Google + GitHub OAuth providers
     ├── Issues signed JWTs to frontend
     └── Backend verifies JWT via shared secret (HS256, SUPABASE_JWT_SECRET)

Redis
     └── Arq worker queue only — no session state, no transcript cache

PostgreSQL
     └── Users, Sessions, TranscriptEntries, Feedback (single source of truth)
```

### Project Structure

```
langua/
  ├── frontend/                # Next.js app
  ├── backend/                 # FastAPI app
  │     ├── app/
  │     │     ├── api/         # Route handlers
  │     │     ├── services/    # AI service interfaces + implementations
  │     │     ├── models/      # SQLAlchemy models
  │     │     ├── schemas/     # Pydantic request/response schemas
  │     │     └── core/        # Config, auth, middleware
  │     └── tests/
  └── worker/                  # Arq background worker
```

---

## Extensibility: Multi-Language

The v1 ships Japanese only. Multi-language support is deferred but the schema is ready:

- Session carries a `language` field (default: `"ja"`)
- TranscriptEntry uses generic field names: `text_native`, `text_reading`, `text_romanized` — which map to Kanji/Hiragana/Romaji for Japanese and adapt naturally to other scripts (e.g., Hangul/romanization for Korean, Hanzi/Pinyin for Chinese)
- Coach system prompt is selected per language from a config map
- Topic lists are scoped per language
- Adding a language means: new prompt config, new topic list, no schema migration

### Transcript Field Caveat

`text_native`, `text_reading`, and `text_romanized` are a pragmatic teaching schema, not a linguistically universal one. They map cleanly to Japanese (Kanji / Hiragana / Romaji) and reasonably to Korean (Hangul / romanization) and Chinese (Hanzi / Pinyin).

Languages with multiple scripts, no standard romanization, or variant readings may need schema evolution. This is acceptable — v1 optimizes for shipping Japanese, and the field names are generic enough that migration cost will be low when a second language is added.

---

## Modes

### Learn Mode
- Open-ended practice session
- User selects a topic (e.g., Greetings, Ordering Food, Directions)
- User speaks in English; the coach teaches the target language equivalent
- Coach models pronunciation cues, asks user to repeat
- When the user ends the session, the app returns to the Home screen. No feedback is generated.

### Quiz Mode
- 2-minute timed conversation on a selected topic
- Coach tracks pronunciation accuracy and vocabulary usage throughout
- At the end, the session is closed and a background job is enqueued to generate adaptive feedback
- The frontend transitions to a Quiz Results page that polls for feedback readiness
- Feedback shows: what the user got right, phrases to revisit, 1–2 suggested drills for next session
- If feedback generation fails, the results page shows an error state with a retry option

---

## UI (Frontend — Next.js)

### Screens

1. **Home**
   - Mode selector (Learn / Quiz), topic picker, language selector (Japanese only in v1, but the UI element exists)
   - Sign in with Supabase Auth (Google / GitHub)
   - Unauthenticated users see only the sign-in prompt

2. **Conversation View**
   - Push-to-talk mic button (tap to start, tap to stop)
   - Loading indicator during turn processing (STT → Coach → TTS)
   - Animated waveform while recording (CSS keyframes, no Math.random() in render)
   - Transcript panel: English input + native script / reading / romanized response
   - Audio playback after each turn (Blob URL + new Audio())
   - Quiz mode: countdown timer
   - Auth-required: redirect to sign-in if no session

3. **Quiz Results** (quiz mode only)
   - Shows "Processing your results..." while `feedback_status` is `pending`
   - Shows full feedback card when `ready`
   - Shows error state with retry button on `failed`
   - Auth-required

---

## Auth

- **Provider:** Supabase Auth (Google + GitHub OAuth)
- Frontend signs in via Supabase client SDK; receives a signed JWT
- Frontend sends JWT as `Authorization: Bearer <token>` on all requests
- Backend verifies JWT using `SUPABASE_JWT_SECRET` (HS256, python-jose) with issuer and audience checks
- No JWKS endpoint, no public key fetching — single verification model
- No guest mode — auth required before any protected route renders
- In App Router: auth checked server-side in layouts/pages; unauthenticated users redirected to `/sign-in` before render

### Auth Verification: v1 Operational Choice

v1 verifies Supabase JWTs using the shared `SUPABASE_JWT_SECRET` (HS256) rather than fetching Supabase's JWKS public keys. This is simpler (no network call on every request, no key caching) but means:

- Secret rotation requires redeploying the backend
- The backend trusts any token signed with this secret, not just tokens from a specific Supabase endpoint

This is acceptable for v1. Post-v1 may migrate to JWKS verification for zero-downtime key rotation and tighter issuer binding.

---

## Data Model

```
User
  ├── id
  ├── email
  ├── name
  ├── avatar_url
  └── sessions[]

Session
  ├── id
  ├── user_id
  ├── language              (default: "ja")
  ├── mode                  (learn | quiz)
  ├── topic
  ├── status                (active | ended)
  ├── feedback_status       (null | pending | ready | failed)
  ├── feedback_generated_at (null | timestamp)
  ├── feedback_error        (null | string)
  ├── started_at
  ├── ended_at
  ├── transcript[]
  └── feedback[]

TranscriptEntry
  ├── id
  ├── session_id
  ├── idempotency_key       (client-generated UUID, unique per session)
  ├── turn_index            (integer, monotonically increasing per session)
  ├── role                  (user | assistant)
  ├── text_en               (English)
  ├── text_native           (target script — Kanji for Japanese)
  ├── text_reading          (phonetic script — Hiragana for Japanese)
  ├── text_romanized        (Romaji for Japanese)
  ├── pronunciation_note    (optional coaching note)
  ├── next_prompt           (what the coach asked user to do next)
  └── created_at

Feedback
  ├── id
  ├── session_id
  ├── correct[]             (phrases done well)
  ├── revisit[]             (phrases to practice)
  └── drills[]              (suggested next exercises)
```

### Data Integrity Rules

- All LLM output is validated against its Pydantic schema before persistence. No unvalidated AI response is ever written to PostgreSQL.
- `turn_index` is assigned server-side, not client-provided, for stable ordering independent of timestamp precision.
- `idempotency_key` has a unique constraint scoped to the session to prevent duplicate turn processing.

---

## AI Service Layer

All AI dependencies are accessed through provider-agnostic service interfaces with concrete implementations swapped via configuration:

```
coach_service    → LLM provider (Claude, GPT, Gemini, etc.)
stt_service      → speech-to-text (OpenAI Whisper, Deepgram, etc.)
tts_service      → text-to-speech (OpenAI TTS, ElevenLabs, etc.)
```

Each service defines:
- A Python protocol (interface) with typed inputs/outputs
- A concrete implementation per provider
- Timeout and retry policy
- Structured error types

Provider selection is driven by env var (e.g., `COACH_PROVIDER=anthropic`). Switching providers requires: new implementation class, no schema change, no API change.

### Provider Timeout and Retry Policy

| Service | Provider (v1) | Timeout | Retries | Retry condition          |
|---------|---------------|---------|---------|--------------------------|
| STT     | OpenAI Whisper| 10s     | 1       | 5xx or timeout           |
| Coach   | Anthropic     | 15s     | 1       | JSON parse failure       |
| Coach   | Anthropic     | 15s     | 0       | 5xx or timeout (fail)    |
| TTS     | OpenAI TTS    | 10s     | 1       | 5xx or timeout           |

Coach retry on parse failure uses a stricter prompt on second attempt. All other retries are immediate (no backoff) — single retry only.

---

## API Endpoints (FastAPI)

All endpoints require `Authorization: Bearer <supabase_jwt>`.

### Conversation
| Method | Path                    | Description                                                          |
|--------|-------------------------|----------------------------------------------------------------------|
| POST   | `/conversation/start`   | Create session. Returns session_id.                                  |
| POST   | `/conversation/turn`    | Audio blob in → transcript + coach response + audio URL out. Sync.   |
| POST   | `/conversation/end`     | End session (idempotent). If quiz mode, enqueues feedback job.        |

### Sessions
| Method | Path                    | Description                                      |
|--------|-------------------------|--------------------------------------------------|
| GET    | `/sessions`             | List user's past sessions                        |
| GET    | `/sessions/{id}`        | Session with transcript + feedback (if ready)    |

### Feedback
| Method | Path                              | Description                            |
|--------|-----------------------------------|----------------------------------------|
| GET    | `/sessions/{id}/feedback-status`  | Poll for feedback_status               |
| POST   | `/sessions/{id}/retry-feedback`   | Re-enqueue failed feedback job         |

### Topics
| Method | Path                    | Description                                      |
|--------|-------------------------|--------------------------------------------------|
| GET    | `/topics`               | List available topics (scoped by language)        |

No separate `/audio/transcribe` or `/audio/speak` endpoints — STT and TTS are internal to the turn pipeline, not exposed directly.

---

## Conversation Turn Flow

```
POST /conversation/turn (multipart/form-data)
  Request:  { session_id, audio_blob }
  Headers:  Authorization, X-Idempotency-Key
  Response: { turn_id, user_entry, assistant_entry, audio_url }

  1. Check X-Idempotency-Key — if already processed, return cached response
  2. Validate session ownership and status=active
  3. STT: audio blob → english text                    (timeout: 10s)
  4. Load session transcript from PostgreSQL for context
  5. Coach: transcript + user text → structured JSON    (timeout: 15s)
  6. Validate coach response against Pydantic schema
     - On parse failure: retry once with stricter prompt
     - On second failure: return error response to client
  7. TTS: coach text_native → audio file               (timeout: 10s)
  8. Persist TranscriptEntry to PostgreSQL (both user + assistant)
  9. Return transcript entry + audio URL

  Total worst-case: ~35s. Typical: 5-8s.
  Frontend shows a loading indicator for the duration.
```

### Turn Idempotency

Every turn request must include a client-generated idempotency key (`X-Idempotency-Key` header, UUID). The backend checks this key against a unique constraint on TranscriptEntry before processing.

- If the key already exists: return the existing turn response, no reprocessing, no duplicate AI billing
- If new: process normally, persist with the key
- Key is scoped to the session — duplicates across sessions are allowed

### Audio Constraints

- Max recording length per turn: 15 seconds
- Frontend enforces via MediaRecorder maxDuration
- Backend rejects audio blobs exceeding 15s / 1MB with 413

### TTS Audio Delivery

The turn endpoint returns an `audio_url`, not inline bytes.

- Backend saves TTS output to a served path: `/tmp/langua_audio/{turn_id}.mp3` (v1)
- Turn response includes `audio_url: "/audio/{turn_id}.mp3"`
- FastAPI serves the audio directory via StaticFiles mount
- Frontend fetches audio separately via the URL
- Swap to object storage (S3/GCS) later by changing the storage backend — API contract (`audio_url` field) stays the same

### POST /conversation/turn — Full Contract

```
Request (multipart/form-data):
  Headers:
    Authorization: Bearer <supabase_jwt>
    X-Idempotency-Key: <client-generated UUID>
  Body:
    session_id: string (UUID)
    audio: binary (webm/opus or wav, max 1MB)

Response (200 OK):
  {
    "turn_id": "uuid",
    "user_entry": {
      "role": "user",
      "text_en": "I would like to order ramen",
      "turn_index": 3
    },
    "assistant_entry": {
      "role": "assistant",
      "text_en": "Here's how to say that:",
      "text_native": "ラーメンを注文したいです",
      "text_reading": "らーめんをちゅうもんしたいです",
      "text_romanized": "raamen o chuumon shitai desu",
      "pronunciation_note": "Stretch the 'aa' in raamen — it is a long vowel",
      "next_prompt": "Try saying it back to me",
      "turn_index": 4
    },
    "audio_url": "/audio/uuid.mp3"
  }

Error responses:
  422: malformed audio or missing fields
  413: audio exceeds size/duration limit
  409: session not active (or idempotency conflict)
  502: upstream AI provider failure after retries
```

---

## Coach System Prompt (Sketch)

The system prompt is selected per language from a config map. The v1 Japanese prompt:

```
You are Langua, a Japanese language coach. Your role is to:
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

Do not include any text outside the JSON object.
```

Adding a new language requires a new entry in the prompt config map with language-appropriate field descriptions (e.g., `text_native` becomes Hangul for Korean, Hanzi for Chinese).

---

## Background Job: Quiz Feedback

When `/conversation/end` is called with `mode=quiz`:
1. Session status set to `ended`, `feedback_status` set to `pending`
2. Feedback generation job enqueued to Arq worker queue (Redis)
3. Job is idempotent — if `feedback_status` is already `pending` or `ready`, no new job is enqueued
4. Worker loads full transcript from PostgreSQL, sends to coach service for structured feedback JSON
5. On success: Feedback row written, `feedback_status` set to `ready`, `feedback_generated_at` set
6. On failure: `feedback_status` set to `failed`, `feedback_error` stores last error message
7. Worker retries up to 3 times before marking failed

### Feedback Job Deduplication

- `POST /sessions/{id}/retry-feedback` is allowed only when `feedback_status=failed`
- If `feedback_status` is `pending` or `ready`, the endpoint returns 409 Conflict with no new job enqueued
- The Arq job itself checks `feedback_status` on entry — if it is no longer `failed`/`pending` (race condition), it exits without processing

### Frontend Polling

- After `/conversation/end`, frontend redirects to `/results/[sessionId]`
- Results page polls `GET /sessions/{id}/feedback-status` every 3 seconds
- On `ready`: fetches `GET /sessions/{id}` for full feedback, renders feedback card
- On `failed`: shows error state with retry button (calls `POST /sessions/{id}/retry-feedback`)
- Polling stops after `ready`, `failed`, or component unmount

---

## Observability

Every request carries a `request_id` (UUID, set in middleware). STT, coach, TTS, and feedback generation calls are individually timed and logged with:
- request_id
- session_id
- operation name
- duration_ms
- success/error status
- provider name (e.g., `anthropic`, `openai`)

Worker jobs log job_id, session_id, attempt number, duration, and outcome. Errors are structured (not raw tracebacks) in production logs.

---

## Local Development

### Required services
- PostgreSQL (via Docker Compose)
- Redis (via Docker Compose)
- Supabase project (cloud — for Auth only in dev)

### Required env vars (backend)
```
DATABASE_URL=postgresql+asyncpg://langua:langua@localhost:5432/langua
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_JWT_SECRET=<from Supabase dashboard → Project Settings → API>
SUPABASE_PROJECT_URL=https://<project-ref>.supabase.co
COACH_PROVIDER=anthropic
STT_PROVIDER=openai
TTS_PROVIDER=openai
WORKER_CONCURRENCY=2
```

### Required env vars (frontend)
```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<from Supabase dashboard>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Start all services
```bash
docker compose up -d                              # Postgres + Redis
cd backend && arq app.worker.WorkerSettings &      # background worker
cd backend && uvicorn app.main:app --reload        # FastAPI
cd frontend && npm run dev                         # Next.js
```

---

## Out of Scope (v1)

- Multi-language support (schema ready, implementation deferred)
- Mobile app
- Gamification (streaks, badges)
- Social features
- Spaced repetition scheduling
- Offline mode
- Acoustic/phoneme-level pronunciation scoring (v1 uses Whisper transcript similarity only)
- Push notifications for feedback readiness
- Real-time streaming TTS (v1 plays audio after full synthesis)
- WebSocket conversation streaming (v1 is synchronous REST)
- Multiple simultaneous AI providers per service (v1 is one provider per service, switchable via config)

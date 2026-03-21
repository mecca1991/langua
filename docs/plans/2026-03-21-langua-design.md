# Langua Language Assistant — Design Document

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

Langua is a voice-first language learning assistant. Users have real-time spoken conversations with an AI coach that guides pronunciation, corrects mistakes, and adapts to their learning gaps. The initial release targets Japanese learners, with a web app first and mobile to follow.

---

## Goals

- Help users build spoken confidence in Japanese through interactive voice conversation
- Provide real-time pronunciation coaching (speak, get corrected, repeat)
- Offer a timed quiz mode that evaluates performance and gives adaptive feedback
- Track progress across sessions per user

---

## Architecture

```
Next.js (Frontend)
     ↓ REST / WebSocket
FastAPI (Backend)
     ├── Auth: OAuth (Google + GitHub) via NextAuth.js → JWT validation
     ├── STT: OpenAI Whisper API
     ├── AI Brain: Claude API (Anthropic)
     ├── TTS: OpenAI TTS API
     └── DB: PostgreSQL + SQLAlchemy + Alembic
```

### Project Structure

```
langua/
  ├── frontend/       # Next.js app
  └── backend/        # FastAPI app
```

---

## Modes

### Learn Mode
- Open-ended practice session
- User selects a topic (e.g., Greetings, Ordering Food, Directions)
- User speaks in English; Claude teaches the Japanese equivalent
- Claude models pronunciation cues, asks user to repeat
- Loop continues until user ends the session

### Quiz Mode
- 2-minute timed conversation on a selected topic
- Claude tracks pronunciation accuracy and vocabulary usage throughout
- At the end, adaptive feedback is shown:
  - What the user got right
  - Specific phrases to revisit
  - 1–2 drills suggested for the next session

---

## UI (Frontend — Next.js)

### Screens

1. **Home**
   - Mode selector: Learn / Quiz
   - Topic picker
   - Sign in with Google / GitHub

2. **Conversation View**
   - Animated waveform (mic active indicator)
   - Transcript panel: English input + Japanese response side by side
   - Japanese displayed in 3 lines: Kanji → Hiragana → Romaji
   - Audio plays automatically after each Claude response
   - Quiz mode: countdown timer visible

3. **Feedback View** (Quiz mode only)
   - Summary of performance
   - Phrases to revisit
   - Suggested drills for next session

---

## Auth

- **Provider:** NextAuth.js (Google + GitHub OAuth)
- Frontend handles OAuth flow, receives session token
- Backend validates JWT on all protected routes via `python-jose`
- No guest mode — auth required to use the app

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
  ├── mode          (learn | quiz)
  ├── topic
  ├── started_at
  ├── ended_at
  ├── transcript[]
  └── feedback[]

TranscriptEntry
  ├── id
  ├── session_id
  ├── role          (user | assistant)
  ├── text_en       (English)
  ├── text_ja       (Japanese — Kanji)
  ├── text_ja_kana  (Hiragana reading)
  ├── text_ja_roma  (Romaji)
  └── created_at

Feedback
  ├── id
  ├── session_id
  ├── correct[]     (phrases done well)
  ├── revisit[]     (phrases to practice)
  └── drills[]      (suggested next exercises)
```

---

## API Endpoints (FastAPI)

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/callback` | Handle OAuth token, return JWT |

### Conversation
| Method | Path | Description |
|--------|------|-------------|
| WS | `/conversation/stream` | WebSocket: real-time voice conversation loop |
| POST | `/conversation/start` | Create new session (mode, topic) |
| POST | `/conversation/end` | Close session; trigger quiz feedback if quiz mode |

### Audio
| Method | Path | Description |
|--------|------|-------------|
| POST | `/audio/transcribe` | Audio blob → Whisper → return text |
| POST | `/audio/speak` | Text → OpenAI TTS → return audio |

### Sessions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions` | List user's past sessions |
| GET | `/sessions/{id}` | Get full transcript + feedback for a session |

### Topics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/topics` | List available topics |

---

## Conversation WebSocket Flow

```
Client sends audio chunk
  → Backend transcribes via Whisper
  → Text sent to Claude with session context + system prompt
  → Claude returns coaching response (EN explanation + JA phrase + pronunciation cues)
  → Backend converts response to speech via OpenAI TTS
  → Audio streamed back to client
  → Client plays audio, displays transcript
```

---

## Claude System Prompt (Sketch)

```
You are Langua, a Japanese language coach. Your role is to:
1. Understand what the user wants to say in English
2. Teach them the correct Japanese phrase (Kanji, Hiragana, Romaji)
3. Guide pronunciation step by step
4. Ask them to repeat
5. Confirm correctness or correct gently

In quiz mode, also track which phrases the user struggled with
and provide a structured feedback summary when asked.

Keep responses concise and encouraging. Always output Japanese in
three forms: Kanji, Hiragana reading, and Romaji.
```

---

## Out of Scope (v1)

- Multi-language support (Spanish, Arabic — post-v1)
- Mobile app (post-v1)
- Gamification (streaks, badges)
- Social features
- Spaced repetition scheduling
- Offline mode

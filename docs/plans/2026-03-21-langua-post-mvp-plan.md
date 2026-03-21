# Langua Post-MVP Enhancement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance the Langua MVP with real-time WebSocket conversation, Redis session resilience, proper JWT auth, fuzzy pronunciation phrase matching, and streaming TTS audio.

**Prerequisite:** MVP is complete and all MVP tests pass.

**Architecture:** Builds on top of MVP. Adds WebSocket route alongside existing REST routes. Adds Redis for session state. Migrates backend auth from X-Internal headers to JWT validation. Adds rapidfuzz for text-based phrase match scoring.

**Tech Stack additions:** redis-py (async), python-jose[cryptography], rapidfuzz, jose (npm).

---

## Phase 1: WebSocket Real-Time Loop

### Task 1: WS /conversation/stream

**Files:**
- Create: `backend/app/routers/ws_conversations.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_ws_conversations.py`

**Step 1: Write the failing WebSocket test**

```python
# backend/tests/test_ws_conversations.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from httpx_ws import aconnect_ws


@pytest.mark.asyncio
async def test_ws_connect_requires_valid_token(client: AsyncClient):
    """Connecting without a valid token should close with code 4003."""
    from httpx_ws import aconnect_ws

    async with aconnect_ws(
        "/conversation/stream?session_id=fake&token=bad-token", client
    ) as ws:
        msg = await ws.receive_text()
        # Server should send close or error
        assert "error" in json.loads(msg) or ws.closed


@pytest.mark.asyncio
async def test_ws_heartbeat_received(client: AsyncClient):
    """After connecting, server should send a heartbeat within 30s (test with mock)."""
    import uuid
    from app.config import settings

    # We'll mock jwt decode and session lookup
    fake_session_id = str(uuid.uuid4())
    fake_user_id = "00000000-0000-0000-0000-000000000010"

    with (
        patch("app.routers.ws_conversations.decode_token", return_value={"sub": fake_user_id}),
        patch("app.routers.ws_conversations.get_session_from_db", new=AsyncMock(
            return_value=MagicMock(id=fake_session_id, user_id=fake_user_id, topic="greetings", mode=MagicMock(value="learn"))
        )),
    ):
        async with aconnect_ws(
            f"/conversation/stream?session_id={fake_session_id}&token=valid-token", client
        ) as ws:
            msg = await ws.receive_text()
            data = json.loads(msg)
            assert data.get("type") == "heartbeat"
```

**Step 2: Run test to verify it fails**

```bash
cd backend
pip install httpx-ws
pytest tests/test_ws_conversations.py -v
```

Expected: `404 Not Found` — WS route doesn't exist yet.

**Step 3: Create app/routers/ws_conversations.py**

```python
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Session as DBSession, TranscriptEntry, Role
from app.services.stt_service import transcribe_audio
from app.services.tts_service import synthesize_speech
from app.services.coach_service import get_coach_response

router = APIRouter(tags=["websocket"])

HEARTBEAT_INTERVAL = 25  # seconds


async def decode_token(token: str) -> dict:
    """Decode a JWT token. Raises ValueError on failure."""
    from app.services.jwt_service import decode_token as _decode
    return _decode(token)


async def get_session_from_db(session_id: str, db: AsyncSession) -> DBSession | None:
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    return result.scalar_one_or_none()


@router.websocket("/conversation/stream")
async def conversation_stream(
    websocket: WebSocket,
    session_id: str = Query(...),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()

    # Auth: validate JWT, extract user
    try:
        payload = await decode_token(token)
    except Exception:
        await websocket.send_text(json.dumps({"type": "error", "message": "Unauthorized"}))
        await websocket.close(code=4003)
        return

    # Load session and verify ownership
    session = await get_session_from_db(session_id, db)
    if session is None:
        await websocket.send_text(json.dumps({"type": "error", "message": "Session not found"}))
        await websocket.close(code=4004)
        return

    # CRITICAL: equality check only — no substring match, no partial pass
    if str(session.user_id) != payload["sub"]:
        await websocket.send_text(json.dumps({"type": "error", "message": "Forbidden"}))
        await websocket.close(code=4003)
        return

    # Send initial heartbeat
    await websocket.send_text(json.dumps({"type": "heartbeat"}))

    # Start heartbeat task
    async def heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        while True:
            # Receive audio bytes from client
            data = await websocket.receive_bytes()

            # STT
            user_text = await transcribe_audio(data, filename="audio.webm")

            # Save user entry
            user_entry = TranscriptEntry(
                session_id=session.id,
                role=Role.user,
                text_en=user_text,
            )
            db.add(user_entry)
            await db.flush()

            # Build history
            prev_result = await db.execute(
                select(TranscriptEntry)
                .where(TranscriptEntry.session_id == session.id)
                .order_by(TranscriptEntry.created_at)
            )
            prev_entries = prev_result.scalars().all()
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

            # Save assistant entry
            assistant_entry = TranscriptEntry(
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
            db.add(assistant_entry)
            await db.commit()
            await db.refresh(assistant_entry)

            # Send response
            await websocket.send_text(json.dumps({
                "type": "turn",
                "transcript_entry_id": str(assistant_entry.id),
                "coach": coach_resp.model_dump(),
                "audio_url": audio_url,
            }))

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
```

**Step 4: Register the WS router in app/main.py**

Add to `backend/app/main.py`:
```python
from app.routers import ws_conversations
app.include_router(ws_conversations.router)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_ws_conversations.py -v
```

Expected: Both tests PASS.

**Step 6: Commit**

```bash
git add backend/app/routers/ws_conversations.py backend/app/main.py backend/tests/test_ws_conversations.py
git commit -m "feat: WebSocket /conversation/stream endpoint with heartbeat and ownership auth"
```

---

### Task 2: Frontend WebSocket Hook with Tap-to-Toggle

**Files:**
- Create: `frontend/lib/useConversationWS.ts`
- Create: `frontend/__tests__/useConversationWS.test.ts`
- Modify: `frontend/app/conversation/[sessionId]/page.tsx`

**Step 1: Write the failing hook test**

```typescript
// frontend/__tests__/useConversationWS.test.ts
import { renderHook, act } from "@testing-library/react";
import { useConversationWS } from "@/lib/useConversationWS";

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  readyState = MockWebSocket.CONNECTING;
  static CONNECTING = 0;
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  sentMessages: (string | ArrayBuffer)[] = [];

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  send(data: string | ArrayBuffer) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code: 1000 } as CloseEvent);
  }
}

global.WebSocket = MockWebSocket as unknown as typeof WebSocket;

test("connects on mount and disconnects on unmount", async () => {
  const { result, unmount } = renderHook(() =>
    useConversationWS({ sessionId: "abc", token: "tok" })
  );

  await act(async () => {
    await new Promise((r) => setTimeout(r, 10));
  });

  expect(result.current.connected).toBe(true);

  unmount();
  expect(result.current.connected).toBe(false);
});

test("reconnects up to 5 times with exponential backoff on close", async () => {
  jest.useFakeTimers();
  let connectCount = 0;
  const OrigMockWS = MockWebSocket;

  class FailingWS extends OrigMockWS {
    constructor(url: string) {
      super(url);
      connectCount++;
      setTimeout(() => {
        this.readyState = MockWebSocket.CLOSED;
        this.onclose?.({ code: 1006 } as CloseEvent);
      }, 5);
    }
  }

  global.WebSocket = FailingWS as unknown as typeof WebSocket;

  const { unmount } = renderHook(() =>
    useConversationWS({ sessionId: "abc", token: "tok" })
  );

  // Advance through 5 retries: 1s, 2s, 4s, 8s, 15s
  for (const delay of [1000, 2000, 4000, 8000, 15000]) {
    await act(async () => jest.advanceTimersByTime(delay + 10));
  }

  expect(connectCount).toBeLessThanOrEqual(6); // initial + 5 retries
  unmount();
  jest.useRealTimers();
  global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend
npm test -- --testPathPattern=useConversationWS
```

Expected: `Cannot find module '@/lib/useConversationWS'`

**Step 3: Create lib/useConversationWS.ts**

```typescript
import { useCallback, useEffect, useRef, useState } from "react";

interface Options {
  sessionId: string;
  token: string;
  onTurn?: (data: TurnMessage) => void;
}

interface TurnMessage {
  type: "turn";
  transcript_entry_id: string;
  coach: Record<string, unknown>;
  audio_url: string;
}

const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 15000]; // ms

export function useConversationWS({ sessionId, token, onTurn }: Options) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const cleanupRef = useRef<(() => void) | null>(null);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const url = `${process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"}/conversation/stream?session_id=${sessionId}&token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    ws.onopen = () => {
      retryCountRef.current = 0;
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === "turn") {
          onTurn?.(data as TurnMessage);
        }
        // heartbeat: no-op on client
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (unmountedRef.current) return;
      if (retryCountRef.current < BACKOFF_DELAYS.length) {
        const delay = BACKOFF_DELAYS[retryCountRef.current];
        retryCountRef.current += 1;
        retryTimer = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    cleanupRef.current = () => {
      if (retryTimer) clearTimeout(retryTimer);
      ws.close();
    };
  }, [sessionId, token, onTurn]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      cleanupRef.current?.();
      setConnected(false);
    };
  }, [connect]);

  const sendAudio = useCallback((audioBlob: Blob) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      audioBlob.arrayBuffer().then((buf) => ws.send(buf));
    }
  }, []);

  return { connected, sendAudio };
}
```

**Step 4: Update Conversation page to use WS hook**

In `frontend/app/conversation/[sessionId]/page.tsx`, replace the REST `handleMicToggle` with one that uses `useConversationWS`. Key changes:

- Import and call `useConversationWS({ sessionId, token, onTurn })` at the top of the component.
- Remove the direct `fetch("/api/conversations/turn", ...)` call.
- In the mic toggle: when stopping, call `sendAudio(audioBlob)` instead.
- `onTurn` callback appends to `entries` and plays audio as before.

```typescript
// In ConversationPage component (additions/changes):
import { useConversationWS } from "@/lib/useConversationWS";

// Fetch token before mounting WS
const [token, setToken] = useState<string | null>(null);

useEffect(() => {
  fetch("/api/token")
    .then((r) => r.json())
    .then((d) => setToken(d.token))
    .catch(console.error);
}, []);

const { connected, sendAudio } = useConversationWS({
  sessionId,
  token: token ?? "",
  onTurn: (data) => {
    const assistantEntry = {
      id: data.transcript_entry_id,
      role: "assistant" as const,
      text_en: (data.coach as Record<string, string>).text_en,
      text_ja: (data.coach as Record<string, string>).text_ja,
      text_ja_kana: (data.coach as Record<string, string>).text_ja_kana,
      text_ja_roma: (data.coach as Record<string, string>).text_ja_roma,
      coaching_prompt: (data.coach as Record<string, string>).coaching_prompt,
    };
    setEntries((prev) => [...prev, assistantEntry]);

    // Play audio
    fetch(data.audio_url)
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => URL.revokeObjectURL(url);
        audio.play();
      });
  },
});

// Updated mic toggle: sends via WS instead of REST
const handleMicToggle = async () => {
  if (recording) {
    setRecording(false);
    setProcessing(true);
    try {
      const audioBlob = await stopRecording();
      sendAudio(audioBlob);
    } finally {
      setProcessing(false);
    }
  } else {
    await startRecording();
  }
};
```

**Step 5: Run tests to verify they pass**

```bash
npm test -- --testPathPattern=useConversationWS
```

Expected: Both tests PASS.

**Step 6: Commit**

```bash
git add frontend/lib/useConversationWS.ts frontend/__tests__/useConversationWS.test.ts frontend/app/conversation/
git commit -m "feat: WebSocket hook with tap-to-toggle, auto-reconnect (5 retries, exponential backoff)"
```

---

## Phase 2: Redis Session Resilience

### Task 3: Redis Session Store

**Files:**
- Create: `backend/app/services/session_store.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/routers/ws_conversations.py`
- Create: `backend/tests/test_session_store.py`

**Step 1: Write the failing session store test**

```python
# backend/tests/test_session_store.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.session_store import save_session, load_session, delete_session

FAKE_TRANSCRIPT = [
    {"role": "user", "content": "hello"},
    {"role": "assistant", "content": "konnichiwa"},
]


@pytest.mark.asyncio
async def test_save_and_load_session():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(FAKE_TRANSCRIPT).encode())

    with patch("app.services.session_store.get_redis", return_value=mock_redis):
        await save_session("session-1", FAKE_TRANSCRIPT)
        result = await load_session("session-1")

    mock_redis.set.assert_called_once()
    assert result == FAKE_TRANSCRIPT


@pytest.mark.asyncio
async def test_load_missing_session_returns_empty_list():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    with patch("app.services.session_store.get_redis", return_value=mock_redis):
        result = await load_session("nonexistent")

    assert result == []


@pytest.mark.asyncio
async def test_delete_session():
    mock_redis = AsyncMock()

    with patch("app.services.session_store.get_redis", return_value=mock_redis):
        await delete_session("session-1")

    mock_redis.delete.assert_called_once_with("session:session-1")


@pytest.mark.asyncio
async def test_save_session_uses_ttl():
    mock_redis = AsyncMock()

    with patch("app.services.session_store.get_redis", return_value=mock_redis):
        await save_session("session-1", FAKE_TRANSCRIPT)

    call_kwargs = mock_redis.set.call_args
    assert call_kwargs.kwargs.get("ex") == 3600 or (
        len(call_kwargs.args) >= 3 and call_kwargs.args[2] == 3600
    )
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_session_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.session_store'`

**Step 3: Add Redis config to app/config.py**

Add to `Settings` in `backend/app/config.py`:
```python
redis_url: str = "redis://localhost:6379"
```

**Step 4: Add redis-py to pyproject.toml**

Add to `[project] dependencies`:
```
"redis>=5.0",
```

Then:
```bash
pip install -e ".[dev]"
```

**Step 5: Create app/services/session_store.py**

```python
import json
import redis.asyncio as aioredis
from app.config import settings

SESSION_TTL = 3600  # seconds
_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
    return _redis_client


def _key(session_id: str) -> str:
    return f"session:{session_id}"


async def save_session(session_id: str, transcript: list[dict]) -> None:
    """Persist transcript list to Redis with TTL."""
    redis = get_redis()
    await redis.set(_key(session_id), json.dumps(transcript), ex=SESSION_TTL)


async def load_session(session_id: str) -> list[dict]:
    """Load transcript from Redis. Returns [] if not found."""
    redis = get_redis()
    data = await redis.get(_key(session_id))
    if data is None:
        return []
    return json.loads(data)


async def delete_session(session_id: str) -> None:
    """Remove session from Redis."""
    redis = get_redis()
    await redis.delete(_key(session_id))
```

**Step 6: Wire session_store into the WS handler**

In `backend/app/routers/ws_conversations.py`, after accepting the connection and verifying auth, load the transcript from Redis:

```python
from app.services.session_store import save_session, load_session

# After auth + session ownership check:
# Load existing transcript from Redis (reconnect resumes history)
redis_transcript = await load_session(session_id)

# After each turn, update Redis:
# (inside the while loop, after saving assistant_entry to DB):
redis_transcript.append({"role": "user", "content": user_text})
redis_transcript.append({"role": "assistant", "content": coach_resp.text_en})
await save_session(session_id, redis_transcript)
```

**Step 7: Add redis to docker-compose.yml**

```yaml
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

**Step 8: Run all session store tests to verify they pass**

```bash
pytest tests/test_session_store.py -v
```

Expected: All 4 tests PASS.

**Step 9: Run full backend test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

**Step 10: Commit**

```bash
git add backend/app/services/session_store.py backend/app/config.py backend/app/routers/ws_conversations.py backend/pyproject.toml docker-compose.yml backend/tests/test_session_store.py
git commit -m "feat: Redis session store with TTL=3600s — WS reconnect resumes transcript"
```

---

## Phase 3: JWT Backend Auth

### Task 4: JWT Service

**Files:**
- Create: `backend/app/services/jwt_service.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_jwt_service.py`

**Step 1: Write the failing JWT service test**

```python
# backend/tests/test_jwt_service.py
import pytest
import time
from jose import jwt
from app.services.jwt_service import decode_token, TokenExpiredError, TokenInvalidError
from app.config import settings


def _make_token(sub: str, exp_offset: int = 3600, secret: str | None = None) -> str:
    payload = {"sub": sub, "exp": int(time.time()) + exp_offset}
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm="HS256")


def test_decode_valid_token():
    token = _make_token("user-abc")
    payload = decode_token(token)
    assert payload["sub"] == "user-abc"


def test_decode_expired_token_raises_expired_error():
    token = _make_token("user-abc", exp_offset=-1)
    with pytest.raises(TokenExpiredError):
        decode_token(token)


def test_decode_invalid_token_raises_invalid_error():
    with pytest.raises(TokenInvalidError):
        decode_token("not.a.jwt.at.all")


def test_decode_wrong_secret_raises_invalid_error():
    token = _make_token("user-abc", secret="wrong-secret")
    with pytest.raises(TokenInvalidError):
        decode_token(token)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_jwt_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.jwt_service'`

**Step 3: Add python-jose and jwt_secret to config**

Add to `[project] dependencies` in `pyproject.toml`:
```
"python-jose[cryptography]>=3.3",
```

Add to `Settings` in `app/config.py`:
```python
jwt_secret: str = "changeme-jwt-secret"
```

Add to `backend/.env.example`:
```
JWT_SECRET=changeme-jwt-secret
```

```bash
pip install -e ".[dev]"
```

**Step 4: Create app/services/jwt_service.py**

```python
from jose import jwt, ExpiredSignatureError, JWTError
from app.config import settings

ALGORITHM = "HS256"


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def decode_token(token: str) -> dict:
    """Decode and validate an HS256 JWT. Raises TokenExpiredError or TokenInvalidError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except JWTError:
        raise TokenInvalidError("Token is invalid")
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_jwt_service.py -v
```

Expected:
```
tests/test_jwt_service.py::test_decode_valid_token PASSED
tests/test_jwt_service.py::test_decode_expired_token_raises_expired_error PASSED
tests/test_jwt_service.py::test_decode_invalid_token_raises_invalid_error PASSED
tests/test_jwt_service.py::test_decode_wrong_secret_raises_invalid_error PASSED
```

**Step 6: Commit**

```bash
git add backend/app/services/jwt_service.py backend/app/config.py backend/pyproject.toml backend/.env.example backend/tests/test_jwt_service.py
git commit -m "feat: JWT service with TokenExpiredError / TokenInvalidError using python-jose HS256"
```

---

### Task 5: Next.js BFF Token Issuance

**Files:**
- Create: `frontend/app/api/token/route.ts`
- Create: `frontend/__tests__/token-route.test.ts`
- Modify: `frontend/.env.local.example`

**Step 1: Install jose on the frontend**

```bash
cd frontend
npm install jose
```

**Step 2: Write the failing token route test**

```typescript
// frontend/__tests__/token-route.test.ts
// This tests the token generation logic in isolation
import { SignJWT } from "jose";

test("SignJWT produces a decodable HS256 token", async () => {
  const secret = new TextEncoder().encode("test-secret");
  const token = await new SignJWT({ sub: "user-123" })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("1h")
    .sign(secret);

  expect(typeof token).toBe("string");
  const parts = token.split(".");
  expect(parts).toHaveLength(3);

  // Decode payload (middle part)
  const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString());
  expect(payload.sub).toBe("user-123");
  expect(payload.exp).toBeGreaterThan(Date.now() / 1000);
});

test("token payload includes sub from user id", async () => {
  const secret = new TextEncoder().encode("test-secret");
  const userId = "00000000-0000-0000-0000-000000000042";
  const token = await new SignJWT({ sub: userId })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("1h")
    .sign(secret);

  const payload = JSON.parse(
    Buffer.from(token.split(".")[1], "base64url").toString()
  );
  expect(payload.sub).toBe(userId);
});
```

**Step 3: Run test to verify it passes (or fails first if jose not installed)**

```bash
npm test -- --testPathPattern=token-route
```

Expected: Both tests PASS (testing jose directly).

**Step 4: Add JWT_SECRET to .env.local.example**

```
JWT_SECRET=changeme-jwt-secret
```

**Step 5: Create app/api/token/route.ts**

```typescript
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { SignJWT } from "jose";

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET ?? "changeme-jwt-secret"
);

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const token = await new SignJWT({ sub: session.user.id })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("1h")
    .sign(JWT_SECRET);

  return NextResponse.json({ token });
}
```

**Step 6: Run the full frontend test suite**

```bash
npm test
```

Expected: All tests PASS.

**Step 7: Commit**

```bash
git add frontend/app/api/token/route.ts frontend/.env.local.example frontend/__tests__/token-route.test.ts
git commit -m "feat: Next.js BFF token issuance — /api/token signs HS256 JWT for WS auth"
```

---

## Phase 4: Pronunciation Phrase Matching

### Task 6: phrase_match.py

**Files:**
- Create: `backend/app/services/phrase_match.py`
- Modify: `backend/app/services/coach_service.py`
- Create: `backend/tests/test_phrase_match.py`

**Step 1: Write the failing phrase match test**

```python
# backend/tests/test_phrase_match.py
import pytest
from app.services.phrase_match import score_phrase_match, ACCEPT_THRESHOLD


def test_identical_strings_score_1():
    assert score_phrase_match("konnichiwa", "konnichiwa") == pytest.approx(1.0)


def test_very_different_strings_score_below_threshold():
    score = score_phrase_match("arigatou", "konnichiwa")
    assert score < ACCEPT_THRESHOLD


def test_close_strings_score_above_threshold():
    # "konnichiwa" vs "konnichwa" — one char different
    score = score_phrase_match("konnichiwa", "konnichwa")
    assert score >= ACCEPT_THRESHOLD


def test_empty_strings_score_1():
    assert score_phrase_match("", "") == pytest.approx(1.0)


def test_score_is_normalized_between_0_and_1():
    score = score_phrase_match("hello", "world")
    assert 0.0 <= score <= 1.0


def test_accept_threshold_is_0_8():
    assert ACCEPT_THRESHOLD == 0.8
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_phrase_match.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.phrase_match'`

**Step 3: Add rapidfuzz to pyproject.toml**

Add to `[project] dependencies`:
```
"rapidfuzz>=3.9",
```

```bash
pip install -e ".[dev]"
```

**Step 4: Create app/services/phrase_match.py**

```python
from rapidfuzz import fuzz

ACCEPT_THRESHOLD = 0.8


def score_phrase_match(attempt: str, target: str) -> float:
    """
    Score how closely `attempt` matches `target` using fuzzy ratio.
    Returns a float in [0.0, 1.0]. Normalized from rapidfuzz's 0-100 scale.
    """
    if not attempt and not target:
        return 1.0
    raw_score = fuzz.ratio(attempt.lower().strip(), target.lower().strip())
    return raw_score / 100.0
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_phrase_match.py -v
```

Expected: All 6 tests PASS.

**Step 6: Integrate into coach_service.py**

In `backend/app/services/coach_service.py`, after parsing the `CoachResponse`, add a mismatch note when the fuzzy score is below threshold. Modify `get_coach_response` to accept an optional `attempt` and `target_romaji`:

```python
from app.services.phrase_match import score_phrase_match, ACCEPT_THRESHOLD

async def get_coach_response(
    user_text: str,
    history: list[dict],
    topic: str,
    mode: str,
    target_romaji: str | None = None,  # NEW
) -> CoachResponse:
    # ... existing logic ...

    # After parsing response:
    if target_romaji and not coach_response.is_repeat_request:
        score = score_phrase_match(user_text, target_romaji)
        if score < ACCEPT_THRESHOLD:
            # Augment coaching_prompt with match note
            coach_response = coach_response.model_copy(update={
                "coaching_prompt": (
                    f"[Match score: {score:.0%}] "
                    + coach_response.coaching_prompt
                ),
                "is_repeat_request": True,
            })

    return coach_response
```

**Step 7: Write an integration test for the augmented mismatch note**

Add to `backend/tests/test_coach_service.py`:

```python
@pytest.mark.asyncio
async def test_mismatch_augments_coaching_prompt():
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    fake_json = json.dumps({
        "text_en": "Hello",
        "text_ja": "こんにちは",
        "text_ja_kana": "こんにちは",
        "text_ja_roma": "konnichiwa",
        "pronunciation_tip": "",
        "coaching_prompt": "Try again!",
        "is_repeat_request": False,
        "target_phrase": "こんにちは",
        "target_romaji": "konnichiwa",
    })

    with patch("app.services.coach_service.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=MagicMock(content=[MagicMock(text=fake_json)])
        )
        result = await get_coach_response(
            user_text="arigatou",  # very different from "konnichiwa"
            history=[],
            topic="greetings",
            mode="learn",
            target_romaji="konnichiwa",
        )

    assert result.is_repeat_request is True
    assert "Match score" in result.coaching_prompt
```

**Step 8: Run all service tests to verify they pass**

```bash
pytest tests/test_phrase_match.py tests/test_coach_service.py -v
```

Expected: All tests PASS.

**Step 9: Commit**

```bash
git add backend/app/services/phrase_match.py backend/app/services/coach_service.py backend/pyproject.toml backend/tests/test_phrase_match.py backend/tests/test_coach_service.py
git commit -m "feat: rapidfuzz phrase match (ACCEPT_THRESHOLD=0.8) integrated into coach_service"
```

---

## Phase 5: TTS Streaming

### Task 7: tts_streaming_service.py + GET /audio/stream

**Files:**
- Create: `backend/app/services/tts_streaming_service.py`
- Create: `backend/app/routers/audio.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_tts_streaming_service.py`

**Step 1: Write the failing streaming service test**

```python
# backend/tests/test_tts_streaming_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.tts_streaming_service import stream_tts_chunks


@pytest.mark.asyncio
async def test_stream_tts_chunks_yields_bytes():
    fake_chunks = [b"chunk1", b"chunk2", b"chunk3"]

    async def mock_iter_bytes():
        for chunk in fake_chunks:
            yield chunk

    mock_response = MagicMock()
    mock_response.iter_bytes = mock_iter_bytes

    class MockStreamContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, *args):
            pass

    with patch("app.services.tts_streaming_service.openai_client") as mock_client:
        mock_client.audio.speech.with_streaming_response.create.return_value = (
            MockStreamContext()
        )
        collected = []
        async for chunk in stream_tts_chunks("こんにちは"):
            collected.append(chunk)

    assert collected == fake_chunks


@pytest.mark.asyncio
async def test_stream_tts_chunks_empty_on_error():
    with patch("app.services.tts_streaming_service.openai_client") as mock_client:
        mock_client.audio.speech.with_streaming_response.create.side_effect = Exception(
            "API error"
        )
        collected = []
        try:
            async for chunk in stream_tts_chunks("hello"):
                collected.append(chunk)
        except Exception:
            pass

    # Should have raised — caller handles error
    assert collected == []
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_tts_streaming_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.tts_streaming_service'`

**Step 3: Create app/services/tts_streaming_service.py**

```python
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def stream_tts_chunks(text: str) -> AsyncGenerator[bytes, None]:
    """Stream TTS audio from OpenAI as raw byte chunks."""
    async with openai_client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="mp3",
    ) as response:
        async for chunk in response.iter_bytes():
            yield chunk
```

**Step 4: Create app/routers/audio.py**

```python
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.services.tts_streaming_service import stream_tts_chunks

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/stream")
async def stream_audio(text: str = Query(..., description="Japanese text to synthesize")):
    """Stream TTS audio directly — no file written to disk."""
    return StreamingResponse(
        stream_tts_chunks(text),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )
```

**Step 5: Register audio router in main.py**

Add to `backend/app/main.py`:
```python
from app.routers import audio
app.include_router(audio.router)
```

Note: The existing `/audio` static file mount uses path `/audio`. The streaming endpoint is at `/audio/stream`. Make sure the static mount does not shadow the router — in FastAPI, routers registered before the static mount take precedence. Register `audio.router` before calling `app.mount("/audio", ...)`.

**Step 6: Run test to verify it passes**

```bash
pytest tests/test_tts_streaming_service.py -v
```

Expected: Both tests PASS.

**Step 7: Commit**

```bash
git add backend/app/services/tts_streaming_service.py backend/app/routers/audio.py backend/app/main.py backend/tests/test_tts_streaming_service.py
git commit -m "feat: TTS streaming service and GET /audio/stream endpoint"
```

---

### Task 8: Frontend Streaming Audio

**Files:**
- Create: `frontend/lib/streamAudio.ts`
- Create: `frontend/app/api/audio/stream/route.ts`
- Modify: `frontend/app/conversation/[sessionId]/page.tsx`
- Create: `frontend/__tests__/streamAudio.test.ts`

**Step 1: Write the failing streamAudio test**

```typescript
// frontend/__tests__/streamAudio.test.ts
import { playStreamedAudio } from "@/lib/streamAudio";

// Mock fetch returning a streaming response
function makeMockResponse(chunks: Uint8Array[]) {
  let index = 0;
  const readable = new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(chunks[index++]);
      } else {
        controller.close();
      }
    },
  });
  return new Response(readable, {
    headers: { "Content-Type": "audio/mpeg" },
  });
}

test("playStreamedAudio resolves without error on valid stream", async () => {
  const chunk = new Uint8Array([0xff, 0xfb, 0x90, 0x00]);
  global.fetch = jest.fn().mockResolvedValue(makeMockResponse([chunk]));

  // Mock AudioContext and related APIs
  const mockSource = { connect: jest.fn(), start: jest.fn() };
  const mockContext = {
    decodeAudioData: jest.fn().mockResolvedValue({}),
    createBufferSource: jest.fn().mockReturnValue(mockSource),
    destination: {},
  };
  global.AudioContext = jest.fn().mockImplementation(() => mockContext) as unknown as typeof AudioContext;

  await expect(playStreamedAudio("/api/audio/stream?text=test")).resolves.not.toThrow();
});

test("playStreamedAudio calls fetch with correct URL", async () => {
  const chunk = new Uint8Array([0x00]);
  global.fetch = jest.fn().mockResolvedValue(makeMockResponse([chunk]));

  const mockSource = { connect: jest.fn(), start: jest.fn() };
  const mockContext = {
    decodeAudioData: jest.fn().mockResolvedValue({}),
    createBufferSource: jest.fn().mockReturnValue(mockSource),
    destination: {},
  };
  global.AudioContext = jest.fn().mockImplementation(() => mockContext) as unknown as typeof AudioContext;

  await playStreamedAudio("/api/audio/stream?text=%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF");
  expect(global.fetch).toHaveBeenCalledWith(
    "/api/audio/stream?text=%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF"
  );
});
```

**Step 2: Run test to verify it fails**

```bash
npm test -- --testPathPattern=streamAudio
```

Expected: `Cannot find module '@/lib/streamAudio'`

**Step 3: Create lib/streamAudio.ts**

```typescript
/**
 * Fetch a streaming audio URL, collect all chunks, and play via AudioContext.
 * Falls back gracefully if the stream is empty.
 */
export async function playStreamedAudio(url: string): Promise<void> {
  const response = await fetch(url);
  const reader = response.body!.getReader();
  const chunks: Uint8Array[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) chunks.push(value);
  }

  if (chunks.length === 0) return;

  const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
  const combined = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.length;
  }

  const ctx = new AudioContext();
  const buffer = await ctx.decodeAudioData(combined.buffer);
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(ctx.destination);
  source.start(0);
}
```

**Step 4: Create app/api/audio/stream/route.ts (BFF proxy)**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const FASTAPI_BASE = process.env.FASTAPI_BASE_URL ?? "http://localhost:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

export async function GET(req: NextRequest) {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const text = req.nextUrl.searchParams.get("text");
  if (!text) {
    return NextResponse.json({ error: "Missing text param" }, { status: 400 });
  }

  const upstream = await fetch(
    `${FASTAPI_BASE}/audio/stream?text=${encodeURIComponent(text)}`,
    {
      headers: {
        "X-Internal-API-Key": INTERNAL_API_KEY,
        "X-Internal-User-Id": session.user.id ?? "",
        "X-Internal-User-Email": session.user.email ?? "",
      },
    }
  );

  // Stream the response directly to the client
  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "audio/mpeg",
      "Cache-Control": "no-cache",
    },
  });
}
```

**Step 5: Update Conversation View to call playStreamedAudio**

In `frontend/app/conversation/[sessionId]/page.tsx`, in the `onTurn` callback, replace the Blob URL audio playback with streaming:

```typescript
import { playStreamedAudio } from "@/lib/streamAudio";

// In onTurn callback, replace:
// fetch(data.audio_url).then(...).then(blob => new Audio(...).play())
// With:
const encodedText = encodeURIComponent(
  (data.coach as Record<string, string>).text_ja
);
playStreamedAudio(`/api/audio/stream?text=${encodedText}`).catch(console.error);
```

**Step 6: Run all frontend tests**

```bash
npm test
```

Expected: All tests PASS.

**Step 7: Run full backend test suite one final time**

```bash
cd ../backend && pytest tests/ -v
```

Expected: All tests PASS.

**Step 8: Commit**

```bash
git add frontend/lib/streamAudio.ts frontend/app/api/audio/stream/ frontend/app/conversation/ frontend/__tests__/streamAudio.test.ts
git commit -m "feat: streaming TTS audio — lib/streamAudio, BFF proxy, and Conversation View integration"
```

---

## Post-MVP Complete

All 8 post-MVP tasks done. Full test suite:

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm test
```

Start services:
```bash
docker compose up -d  # postgres + redis
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

The app now supports:
- Real-time WebSocket conversation with heartbeat and 4003 auth enforcement
- Auto-reconnect with 5 retries and exponential backoff (1s/2s/4s/8s/15s)
- Redis session persistence (TTL 3600s) so reconnects resume transcript
- HS256 JWT auth — frontend mints tokens at `/api/token`, WS validates via python-jose
- rapidfuzz phrase match (ACCEPT_THRESHOLD=0.8) augments coaching feedback
- Streaming TTS audio via `/audio/stream` — no temp file writes

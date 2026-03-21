import uuid
from datetime import datetime, timezone

from arq.connections import ArqRedis, create_pool, RedisSettings
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
    EndConversationRequest,
    EndConversationResponse,
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


async def get_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


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

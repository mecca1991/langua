import uuid
from datetime import datetime, timezone

from arq.connections import ArqRedis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.session import SessionRepository
from app.repositories.transcript import TranscriptRepository
from app.schemas.conversation import (
    EndConversationResponse,
    StartConversationRequest,
    StartConversationResponse,
    TurnAssistantEntry,
    TurnResponse,
    TurnUserEntry,
)
from app.services import dependencies as svc
from app.services.domain_errors import ConflictError, ForbiddenError, NotFoundError
from app.services.errors import CoachError, STTError, TTSError


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sessions = SessionRepository(db)
        self.transcripts = TranscriptRepository(db)

    async def start_conversation(
        self,
        *,
        user_id: uuid.UUID,
        request: StartConversationRequest,
    ) -> StartConversationResponse:
        session = await self.sessions.create(
            user_id=user_id,
            language=request.language,
            mode=request.mode.value,
            topic=request.topic,
            status="active",
        )
        await self.db.commit()
        return StartConversationResponse(session_id=session.id)

    async def process_turn(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        audio_data: bytes,
        idempotency_key: uuid.UUID,
    ) -> TurnResponse:
        existing_entry = await self.transcripts.get_user_entry_by_idempotency(
            session_id=session_id,
            idempotency_key=idempotency_key,
        )
        if existing_entry is not None:
            return await self._build_cached_response(
                session_id=session_id,
                user_entry=existing_entry,
            )

        session = await self._get_active_owned_session(
            session_id=session_id,
            user_id=user_id,
        )
        transcript_entries = await self.transcripts.list_by_session(session_id)
        transcript_context = [
            {
                "role": entry.role,
                "text_en": entry.text_en,
                "text_native": entry.text_native,
            }
            for entry in transcript_entries
        ]

        try:
            user_text = await svc.stt_service.transcribe(audio_data, session.language)
        except STTError:
            raise

        try:
            coach_response = await svc.coach_service.respond(
                user_text,
                transcript_context,
                session.language,
                session.mode,
                session.topic,
            )
        except CoachError:
            raise

        max_index = max((entry.turn_index for entry in transcript_entries), default=-1)
        user_turn_index = max_index + 1
        assistant_turn_index = user_turn_index + 1
        turn_id = uuid.uuid4()

        try:
            await svc.tts_service.synthesize(
                coach_response.text_native,
                session.language,
                turn_id,
            )
        except TTSError:
            raise

        try:
            await self.transcripts.add_pair(
                session_id=session_id,
                idempotency_key=idempotency_key,
                user_turn_index=user_turn_index,
                assistant_turn_index=assistant_turn_index,
                user_text=user_text,
                assistant_turn_id=turn_id,
                assistant_text_en=coach_response.text_en,
                assistant_text_native=coach_response.text_native,
                assistant_text_reading=coach_response.text_reading,
                assistant_text_romanized=coach_response.text_romanized,
                assistant_pronunciation_note=coach_response.pronunciation_note,
                assistant_next_prompt=coach_response.next_prompt,
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing_entry = await self.transcripts.get_user_entry_by_idempotency(
                session_id=session_id,
                idempotency_key=idempotency_key,
            )
            if existing_entry is None:
                raise
            return await self._build_cached_response(
                session_id=session_id,
                user_entry=existing_entry,
            )

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

    async def end_conversation(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        queue: ArqRedis | None = None,
    ) -> EndConversationResponse:
        session = await self._get_owned_session(session_id=session_id, user_id=user_id)
        if session.status == "ended":
            return EndConversationResponse(
                status="ended",
                feedback_status=session.feedback_status,
            )

        self.sessions.mark_ended(session, ended_at=datetime.now(timezone.utc))
        if session.mode == "quiz":
            self.sessions.set_feedback_pending(session)

        await self.db.commit()

        if session.mode == "quiz" and queue is not None:
            await queue.enqueue_job("generate_feedback", str(session_id))

        return EndConversationResponse(
            status="ended",
            feedback_status=session.feedback_status,
        )

    async def _build_cached_response(
        self,
        *,
        session_id: uuid.UUID,
        user_entry,
    ) -> TurnResponse:
        assistant_entry = await self.transcripts.get_assistant_entry_for_turn(
            session_id=session_id,
            turn_index=user_entry.turn_index + 1,
        )
        if assistant_entry is None:
            raise NotFoundError("Assistant response not found for cached turn")

        return TurnResponse(
            turn_id=assistant_entry.id,
            user_entry=TurnUserEntry(
                text_en=user_entry.text_en or "",
                turn_index=user_entry.turn_index,
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

    async def _get_owned_session(self, *, session_id: uuid.UUID, user_id: uuid.UUID):
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Session not found")
        if session.user_id != user_id:
            raise ForbiddenError("Not your session")
        return session

    async def _get_active_owned_session(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        session = await self._get_owned_session(session_id=session_id, user_id=user_id)
        if session.status != "active":
            raise ConflictError("Session is not active")
        return session

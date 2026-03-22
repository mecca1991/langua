import uuid

from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.session import SessionRepository
from app.schemas.session import (
    FeedbackSchema,
    SessionDetail,
    SessionListResponse,
    SessionSummary,
    TranscriptEntrySchema,
)
from app.services.domain_errors import ConflictError, ForbiddenError, NotFoundError


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sessions = SessionRepository(db)

    async def list_sessions(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> SessionListResponse:
        total = await self.sessions.count_by_user(user_id)
        sessions = await self.sessions.list_by_user(user_id, limit=limit, offset=offset)
        return SessionListResponse(
            sessions=[SessionSummary.model_validate(session) for session in sessions],
            total=total,
        )

    async def get_owned_session_detail(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SessionDetail:
        session = await self._get_owned_session(session_id=session_id, user_id=user_id)
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
            feedback=[FeedbackSchema.model_validate(session.feedback)] if session.feedback else [],
        )

    async def get_feedback_status(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> str | None:
        session = await self._get_owned_session(session_id=session_id, user_id=user_id)
        return session.feedback_status

    async def retry_feedback(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        queue: ArqRedis,
    ) -> dict[str, str]:
        session = await self._get_owned_session(session_id=session_id, user_id=user_id)
        if session.feedback_status != "failed":
            raise ConflictError(
                f"Cannot retry: feedback_status is {session.feedback_status}"
            )

        self.sessions.set_feedback_pending(session)
        await self.db.commit()
        await queue.enqueue_job("generate_feedback", str(session_id))
        return {"status": "retrying"}

    async def _get_owned_session(self, *, session_id: uuid.UUID, user_id: uuid.UUID):
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Session not found")
        if session.user_id != user_id:
            raise ForbiddenError("Not your session")
        return session

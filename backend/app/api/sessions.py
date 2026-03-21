import uuid

from arq.connections import ArqRedis, create_pool, RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.config import settings
from app.core.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.feedback import FeedbackStatusResponse
from app.schemas.session import (
    FeedbackSchema,
    SessionDetail,
    SessionListResponse,
    SessionSummary,
    TranscriptEntrySchema,
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
        feedback=[FeedbackSchema.model_validate(session.feedback)] if session.feedback else [],
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

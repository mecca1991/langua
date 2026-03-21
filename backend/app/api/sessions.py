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

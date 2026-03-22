import uuid

from fastapi import APIRouter, Depends, Query
from app.models.user import User
from app.schemas.feedback import FeedbackStatusResponse
from app.schemas.session import SessionDetail, SessionListResponse
from app.services import dependencies as service_deps
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions")


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(service_deps.get_current_user),
    session_service: SessionService = Depends(service_deps.get_session_service),
):
    return await session_service.list_sessions(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: uuid.UUID,
    user: User = Depends(service_deps.get_current_user),
    session_service: SessionService = Depends(service_deps.get_session_service),
):
    return await session_service.get_owned_session_detail(
        session_id=session_id,
        user_id=user.id,
    )


@router.get("/{session_id}/feedback-status", response_model=FeedbackStatusResponse)
async def feedback_status(
    session_id: uuid.UUID,
    user: User = Depends(service_deps.get_current_user),
    session_service: SessionService = Depends(service_deps.get_session_service),
):
    value = await session_service.get_feedback_status(
        session_id=session_id,
        user_id=user.id,
    )
    return FeedbackStatusResponse(feedback_status=value)


@router.post("/{session_id}/retry-feedback")
async def retry_feedback(
    session_id: uuid.UUID,
    user: User = Depends(service_deps.get_current_user),
    session_service: SessionService = Depends(service_deps.get_session_service),
    queue=Depends(service_deps.get_arq_pool),
):
    return await session_service.retry_feedback(
        session_id=session_id,
        user_id=user.id,
        queue=queue,
    )

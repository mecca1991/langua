from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_user
from app.core.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.conversation import (
    StartConversationRequest,
    StartConversationResponse,
)

router = APIRouter(prefix="/conversation")


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

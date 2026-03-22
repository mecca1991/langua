import uuid

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from app.models.user import User
from app.schemas.conversation import (
    EndConversationRequest,
    EndConversationResponse,
    StartConversationRequest,
    StartConversationResponse,
    TurnResponse,
)
from app.services import dependencies as service_deps
from app.services.conversation_service import ConversationService
from app.core.api_errors import BadRequestError

router = APIRouter(prefix="/conversation")

MAX_AUDIO_SIZE = 1 * 1024 * 1024  # 1MB


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    user: User = Depends(service_deps.get_current_user),
    conversation_service: ConversationService = Depends(
        service_deps.get_conversation_service
    ),
):
    return await conversation_service.start_conversation(
        user_id=user.id,
        request=request,
    )


@router.post("/turn", response_model=TurnResponse)
async def conversation_turn(
    session_id: uuid.UUID = Form(...),
    audio: UploadFile = File(...),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    user: User = Depends(service_deps.get_current_user),
    conversation_service: ConversationService = Depends(
        service_deps.get_conversation_service
    ),
):
    idempotency_uuid = uuid.UUID(x_idempotency_key)

    audio_data = await audio.read()
    if len(audio_data) > MAX_AUDIO_SIZE:
        raise BadRequestError(
            error_code="AUDIO_TOO_LARGE",
            error_message="The submitted audio file exceeds the 1 MB size limit.",
        )

    return await conversation_service.process_turn(
        session_id=session_id,
        user_id=user.id,
        audio_data=audio_data,
        idempotency_key=idempotency_uuid,
    )


@router.post("/end", response_model=EndConversationResponse)
async def end_conversation(
    request: EndConversationRequest,
    user: User = Depends(service_deps.get_current_user),
    conversation_service: ConversationService = Depends(
        service_deps.get_conversation_service
    ),
    queue=Depends(service_deps.get_arq_pool),
):
    return await conversation_service.end_conversation(
        session_id=request.session_id,
        user_id=user.id,
        queue=queue,
    )

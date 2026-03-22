from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_payload
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import JWTPayload
from app.services.conversation_service import ConversationService
from app.services.factory import create_stt_service, create_coach_service, create_tts_service
from app.services.feedback_service import FeedbackService
from app.services.session_service import SessionService
from app.services.user_service import UserService

stt_service = create_stt_service(
    provider=settings.stt_provider, api_key=settings.OPENAI_API_KEY
)
coach_service = create_coach_service(
    provider=settings.coach_provider, api_key=settings.ANTHROPIC_API_KEY
)
tts_service = create_tts_service(
    provider=settings.tts_provider, api_key=settings.OPENAI_API_KEY
)


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


def get_conversation_service(
    db: AsyncSession = Depends(get_db),
) -> ConversationService:
    return ConversationService(db)


def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


def get_feedback_service(db: AsyncSession = Depends(get_db)) -> FeedbackService:
    return FeedbackService(db)


async def get_current_user(
    payload: JWTPayload = Depends(get_current_user_payload),
    user_service: UserService = Depends(get_user_service),
) -> User:
    return await user_service.ensure_user(payload)


async def get_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

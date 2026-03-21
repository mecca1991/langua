from app.core.config import settings
from app.services.factory import create_stt_service, create_coach_service, create_tts_service

stt_service = create_stt_service(
    provider=settings.stt_provider, api_key=settings.openai_api_key
)
coach_service = create_coach_service(
    provider=settings.coach_provider, api_key=settings.anthropic_api_key
)
tts_service = create_tts_service(
    provider=settings.tts_provider, api_key=settings.openai_api_key
)

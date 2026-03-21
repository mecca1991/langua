from app.services.stt import WhisperSTTService
from app.services.coach import AnthropicCoachService
from app.services.tts import OpenAITTSService


def create_stt_service(provider: str, api_key: str) -> WhisperSTTService:
    if provider == "openai":
        return WhisperSTTService(api_key=api_key)
    raise ValueError(f"Unknown STT provider: {provider}")


def create_coach_service(provider: str, api_key: str) -> AnthropicCoachService:
    if provider == "anthropic":
        return AnthropicCoachService(api_key=api_key)
    raise ValueError(f"Unknown coach provider: {provider}")


def create_tts_service(
    provider: str, api_key: str, audio_dir: str = "/tmp/langua_audio"
) -> OpenAITTSService:
    if provider == "openai":
        return OpenAITTSService(api_key=api_key, audio_dir=audio_dir)
    raise ValueError(f"Unknown TTS provider: {provider}")

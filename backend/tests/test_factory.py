import pytest
from unittest.mock import patch

from app.services.factory import create_stt_service, create_coach_service, create_tts_service
from app.services.stt import WhisperSTTService
from app.services.coach import AnthropicCoachService
from app.services.tts import OpenAITTSService


def test_create_stt_service_openai():
    service = create_stt_service(provider="openai", api_key="test")
    assert isinstance(service, WhisperSTTService)


def test_create_stt_service_unknown():
    with pytest.raises(ValueError, match="Unknown STT provider"):
        create_stt_service(provider="unknown", api_key="test")


def test_create_coach_service_anthropic():
    service = create_coach_service(provider="anthropic", api_key="test")
    assert isinstance(service, AnthropicCoachService)


def test_create_coach_service_unknown():
    with pytest.raises(ValueError, match="Unknown coach provider"):
        create_coach_service(provider="unknown", api_key="test")


def test_create_tts_service_openai():
    service = create_tts_service(provider="openai", api_key="test")
    assert isinstance(service, OpenAITTSService)


def test_create_tts_service_unknown():
    with pytest.raises(ValueError, match="Unknown TTS provider"):
        create_tts_service(provider="unknown", api_key="test")

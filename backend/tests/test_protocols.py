import uuid
from pathlib import Path

import pytest

from app.services.protocols import STTService, CoachService, TTSService, CoachResponse
from app.services.errors import STTError, CoachError, TTSError


class FakeSTT:
    async def transcribe(self, audio_data: bytes, language: str) -> str:
        return "hello"


class FakeCoach:
    async def respond(
        self,
        user_text: str,
        transcript_context: list[dict],
        language: str,
        mode: str,
        topic: str,
    ) -> CoachResponse:
        return CoachResponse(
            text_en="Here's how to say that:",
            text_native="こんにちは",
            text_reading="こんにちは",
            text_romanized="konnichiwa",
            pronunciation_note="Natural greeting",
            next_prompt="Try saying it back to me",
        )


class FakeTTS:
    async def synthesize(self, text: str, language: str, turn_id: uuid.UUID) -> Path:
        return Path(f"/tmp/langua_audio/{turn_id}.mp3")


@pytest.mark.anyio
async def test_fake_stt_satisfies_protocol():
    stt: STTService = FakeSTT()
    result = await stt.transcribe(b"audio", "ja")
    assert result == "hello"


@pytest.mark.anyio
async def test_fake_coach_satisfies_protocol():
    coach: CoachService = FakeCoach()
    result = await coach.respond("hello", [], "ja", "learn", "Greetings")
    assert result.text_native == "こんにちは"
    assert result.text_romanized == "konnichiwa"


@pytest.mark.anyio
async def test_fake_tts_satisfies_protocol():
    tts: TTSService = FakeTTS()
    turn_id = uuid.uuid4()
    result = await tts.synthesize("こんにちは", "ja", turn_id)
    assert str(turn_id) in str(result)


def test_error_types():
    stt_err = STTError("Transcription failed", provider="openai")
    assert stt_err.provider == "openai"
    assert str(stt_err) == "Transcription failed"

    coach_err = CoachError("Parse failed", provider="anthropic", retryable=True)
    assert coach_err.retryable is True

    tts_err = TTSError("Synthesis failed", provider="openai")
    assert tts_err.provider == "openai"

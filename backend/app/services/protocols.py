import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class CoachResponse(BaseModel):
    text_en: str
    text_native: str
    text_reading: str
    text_romanized: str
    pronunciation_note: str
    next_prompt: str


@runtime_checkable
class STTService(Protocol):
    async def transcribe(self, audio_data: bytes, language: str) -> str: ...


@runtime_checkable
class CoachService(Protocol):
    async def respond(
        self,
        user_text: str,
        transcript_context: list[dict],
        language: str,
        mode: str,
        topic: str,
    ) -> CoachResponse: ...


@runtime_checkable
class TTSService(Protocol):
    async def synthesize(self, text: str, language: str, turn_id: uuid.UUID) -> Path: ...

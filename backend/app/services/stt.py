import asyncio
import io
import logging

from openai import AsyncOpenAI, APIStatusError, APITimeoutError

from app.services.errors import STTError

logger = logging.getLogger(__name__)


class WhisperSTTService:
    def __init__(self, api_key: str, timeout: float = 10.0, max_retries: int = 1):
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self._api_key, timeout=self._timeout)

    async def transcribe(self, audio_data: bytes, language: str) -> str:
        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.webm"
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                )
                return transcript.text
            except (APIStatusError, APITimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                is_server_error = isinstance(e, APIStatusError) and e.response.status_code >= 500
                is_timeout = isinstance(e, (APITimeoutError, asyncio.TimeoutError))
                if (is_server_error or is_timeout) and attempt < self._max_retries:
                    logger.warning(f"STT attempt {attempt + 1} failed, retrying: {e}")
                    continue
                break
            except Exception as e:
                last_error = e
                break

        raise STTError(
            f"Transcription failed after {self._max_retries + 1} attempts: {last_error}",
            provider="openai",
        )

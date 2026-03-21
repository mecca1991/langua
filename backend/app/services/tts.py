import asyncio
import logging
import uuid
from pathlib import Path

from openai import AsyncOpenAI, APIStatusError, APITimeoutError

from app.services.errors import TTSError

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_DIR = "/tmp/langua_audio"


class OpenAITTSService:
    def __init__(
        self,
        api_key: str,
        audio_dir: str = DEFAULT_AUDIO_DIR,
        timeout: float = 10.0,
        max_retries: int = 1,
    ):
        self._api_key = api_key
        self._audio_dir = Path(audio_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._max_retries = max_retries

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self._api_key, timeout=self._timeout)

    async def synthesize(self, text: str, _language: str, turn_id: uuid.UUID) -> Path:
        client = self._get_client()
        output_path = self._audio_dir / f"{turn_id}.mp3"
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text,
                    response_format="mp3",
                )
                await response.stream_to_file(str(output_path))  # pyright: ignore[reportDeprecated]
                return output_path

            except (APIStatusError, APITimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                is_server_error = isinstance(e, APIStatusError) and e.response.status_code >= 500
                is_timeout = isinstance(e, (APITimeoutError, asyncio.TimeoutError))
                if (is_server_error or is_timeout) and attempt < self._max_retries:
                    logger.warning(f"TTS attempt {attempt + 1} failed, retrying: {e}")
                    continue
                break
            except Exception as e:
                last_error = e
                break

        raise TTSError(
            f"TTS synthesis failed after {self._max_retries + 1} attempts: {last_error}",
            provider="openai",
        )

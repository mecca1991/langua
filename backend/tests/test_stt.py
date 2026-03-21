from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.stt import WhisperSTTService
from app.services.errors import STTError


@pytest.fixture
def stt_service():
    return WhisperSTTService(api_key="test-key")


@pytest.mark.anyio
async def test_transcribe_success(stt_service):
    mock_transcript = MagicMock()
    mock_transcript.text = "I want to order ramen"

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with patch.object(stt_service, "_get_client", return_value=mock_client):
        result = await stt_service.transcribe(b"fake-audio-data", "ja")
        assert result == "I want to order ramen"


@pytest.mark.anyio
async def test_transcribe_retries_on_server_error(stt_service):
    mock_transcript = MagicMock()
    mock_transcript.text = "retried result"

    mock_client = AsyncMock()
    from openai import APIStatusError
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}

    mock_client.audio.transcriptions.create = AsyncMock(
        side_effect=[
            APIStatusError(
                message="Server error",
                response=mock_response,
                body=None,
            ),
            mock_transcript,
        ]
    )

    with patch.object(stt_service, "_get_client", return_value=mock_client):
        result = await stt_service.transcribe(b"fake-audio-data", "ja")
        assert result == "retried result"
        assert mock_client.audio.transcriptions.create.call_count == 2


@pytest.mark.anyio
async def test_transcribe_fails_after_retries(stt_service):
    mock_client = AsyncMock()
    from openai import APIStatusError
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}

    mock_client.audio.transcriptions.create = AsyncMock(
        side_effect=APIStatusError(
            message="Server error",
            response=mock_response,
            body=None,
        )
    )

    with patch.object(stt_service, "_get_client", return_value=mock_client):
        with pytest.raises(STTError) as exc_info:
            await stt_service.transcribe(b"fake-audio-data", "ja")
        assert exc_info.value.provider == "openai"

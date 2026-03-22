import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.tts import OpenAITTSService
from app.services.errors import TTSError


@pytest.fixture
def tts_service(tmp_path):
    return OpenAITTSService(api_key="test-key", audio_dir=str(tmp_path))


@pytest.mark.anyio
async def test_tts_synthesize_success(tts_service, tmp_path):
    turn_id = uuid.uuid4()

    mock_response = MagicMock()
    mock_response.stream_to_file.side_effect = (
        lambda path: Path(path).write_bytes(b"fake-audio")
    )

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(return_value=mock_response)

    with patch.object(tts_service, "_get_client", return_value=mock_client):
        result = await tts_service.synthesize("こんにちは", "ja", turn_id)
        expected_path = tmp_path / f"{turn_id}.mp3"
        assert result == expected_path
        mock_client.audio.speech.create.assert_called_once()


@pytest.mark.anyio
async def test_tts_retries_on_server_error(tts_service, tmp_path):
    turn_id = uuid.uuid4()

    from openai import APIStatusError
    mock_resp_err = MagicMock()
    mock_resp_err.status_code = 500
    mock_resp_err.headers = {}

    mock_response = MagicMock()
    mock_response.stream_to_file.side_effect = (
        lambda path: Path(path).write_bytes(b"fake-audio")
    )

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(
        side_effect=[
            APIStatusError(message="Server error", response=mock_resp_err, body=None),
            mock_response,
        ]
    )

    with patch.object(tts_service, "_get_client", return_value=mock_client):
        result = await tts_service.synthesize("こんにちは", "ja", turn_id)
        expected_path = tmp_path / f"{turn_id}.mp3"
        assert result == expected_path
        assert expected_path.read_bytes() == b"fake-audio"
        assert mock_client.audio.speech.create.call_count == 2


@pytest.mark.anyio
async def test_tts_fails_after_retries(tts_service):
    turn_id = uuid.uuid4()

    from openai import APIStatusError
    mock_resp_err = MagicMock()
    mock_resp_err.status_code = 500
    mock_resp_err.headers = {}

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(
        side_effect=APIStatusError(
            message="Server error", response=mock_resp_err, body=None
        )
    )

    with patch.object(tts_service, "_get_client", return_value=mock_client):
        with pytest.raises(TTSError):
            await tts_service.synthesize("こんにちは", "ja", turn_id)

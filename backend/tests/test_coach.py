import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.coach import AnthropicCoachService
from app.services.protocols import CoachResponse
from app.services.errors import CoachError


@pytest.fixture
def coach_service():
    return AnthropicCoachService(api_key="test-key")


def make_mock_response(content: dict) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = json.dumps(content)
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


VALID_RESPONSE = {
    "text_en": "Here is how to say hello:",
    "text_native": "こんにちは",
    "text_reading": "こんにちは",
    "text_romanized": "konnichiwa",
    "pronunciation_note": "Natural greeting",
    "next_prompt": "Try saying it back to me",
}


@pytest.mark.anyio
async def test_coach_respond_success(coach_service):
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=make_mock_response(VALID_RESPONSE)
    )

    with patch.object(coach_service, "_get_client", return_value=mock_client):
        result = await coach_service.respond(
            "hello", [], "ja", "learn", "Greetings"
        )
        assert isinstance(result, CoachResponse)
        assert result.text_native == "こんにちは"
        assert result.text_romanized == "konnichiwa"


@pytest.mark.anyio
async def test_coach_retries_on_parse_failure(coach_service):
    invalid_response = MagicMock()
    invalid_block = MagicMock()
    invalid_block.text = "This is not JSON"
    invalid_response.content = [invalid_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[invalid_response, make_mock_response(VALID_RESPONSE)]
    )

    with patch.object(coach_service, "_get_client", return_value=mock_client):
        result = await coach_service.respond(
            "hello", [], "ja", "learn", "Greetings"
        )
        assert result.text_native == "こんにちは"
        assert mock_client.messages.create.call_count == 2


@pytest.mark.anyio
async def test_coach_fails_after_both_parse_failures(coach_service):
    invalid_response = MagicMock()
    invalid_block = MagicMock()
    invalid_block.text = "not json at all"
    invalid_response.content = [invalid_block]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=invalid_response)

    with patch.object(coach_service, "_get_client", return_value=mock_client):
        with pytest.raises(CoachError) as exc_info:
            await coach_service.respond("hello", [], "ja", "learn", "Greetings")
        assert exc_info.value.provider == "anthropic"

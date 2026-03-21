import json
import logging

from anthropic import AsyncAnthropic

from app.services.errors import CoachError
from app.services.prompts import COACH_SYSTEM_PROMPTS, COACH_STRICT_SUFFIX
from app.services.protocols import CoachResponse

logger = logging.getLogger(__name__)


class AnthropicCoachService:
    def __init__(self, api_key: str, timeout: float = 15.0):
        self._api_key = api_key
        self._timeout = timeout

    def _get_client(self) -> AsyncAnthropic:
        return AsyncAnthropic(api_key=self._api_key, timeout=self._timeout)

    def _build_messages(self, user_text: str, transcript_context: list[dict]) -> list[dict]:
        messages = []
        for entry in transcript_context:
            role = "user" if entry.get("role") == "user" else "assistant"
            content = entry.get("text_en", "")
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_text})
        return messages

    async def respond(
        self,
        user_text: str,
        transcript_context: list[dict],
        language: str,
        mode: str,
        topic: str,
    ) -> CoachResponse:
        client = self._get_client()
        system_prompt = COACH_SYSTEM_PROMPTS.get(language, COACH_SYSTEM_PROMPTS["ja"])
        system_prompt += f"\n\nCurrent topic: {topic}\nMode: {mode}"
        messages = self._build_messages(user_text, transcript_context)

        for attempt in range(2):
            try:
                if attempt == 1:
                    system_prompt += COACH_STRICT_SUFFIX

                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    system=system_prompt,
                    messages=messages,
                )

                raw_text = response.content[0].text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    raw_text = "\n".join(lines[1:-1])

                data = json.loads(raw_text)
                return CoachResponse(**data)

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Coach parse attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    continue
                raise CoachError(
                    f"Coach response parse failed after retry: {e}",
                    provider="anthropic",
                    retryable=False,
                )
            except Exception as e:
                raise CoachError(
                    f"Coach service error: {e}",
                    provider="anthropic",
                )

        raise CoachError(
            "Coach failed after all attempts",
            provider="anthropic",
        )

import json
import uuid
from datetime import datetime, timezone

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.feedback import FeedbackRepository
from app.repositories.session import SessionRepository
from app.repositories.transcript import TranscriptRepository
from app.schemas.feedback import FeedbackResponse
from app.services.prompts import FEEDBACK_PROMPT


class FeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sessions = SessionRepository(db)
        self.transcripts = TranscriptRepository(db)
        self.feedback = FeedbackRepository(db)

    async def generate_feedback(self, session_id: str) -> bool:
        session = await self.sessions.get_by_id(uuid.UUID(session_id))
        if session is None:
            return False

        if session.feedback_status not in ("pending", "failed"):
            return False

        entries = await self.transcripts.list_by_session(session.id)
        transcript_text = "\n".join(
            f"[{entry.role}] {entry.text_en or ''} | {entry.text_native or ''}"
            for entry in entries
        )

        last_error = None
        for _ in range(3):
            try:
                client = AsyncAnthropic(
                    api_key=settings.ANTHROPIC_API_KEY,
                    timeout=30.0,
                )
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    system=FEEDBACK_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Here is the quiz transcript:\n\n{transcript_text}",
                        }
                    ],
                )

                raw_text = response.content[0].text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    raw_text = "\n".join(lines[1:-1])

                data = json.loads(raw_text)
                feedback_data = FeedbackResponse(**data)
                await self.feedback.create(
                    session_id=session.id,
                    correct=feedback_data.correct,
                    revisit=feedback_data.revisit,
                    drills=feedback_data.drills,
                )

                session.feedback_status = "ready"
                session.feedback_generated_at = datetime.now(timezone.utc)
                session.feedback_error = None
                await self.db.commit()
                return True
            except Exception as exc:
                await self.db.rollback()
                last_error = exc

        session = await self.sessions.get_by_id(uuid.UUID(session_id))
        if session is None:
            return False

        session.feedback_status = "failed"
        session.feedback_error = str(last_error)[:500] if last_error else "Unknown error"
        await self.db.commit()
        return False

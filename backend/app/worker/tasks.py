import json
import logging
import uuid
from datetime import datetime, timezone

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.models.feedback import Feedback
from app.services.prompts import FEEDBACK_PROMPT
from app.schemas.feedback import FeedbackResponse

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url


async def run_feedback_generation(ctx: dict, session_id: str) -> None:
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as db:
            result = await db.execute(
                select(Session).where(Session.id == uuid.UUID(session_id))
            )
            session = result.scalar_one_or_none()
            if session is None:
                logger.error(f"Session {session_id} not found")
                return

            if session.feedback_status not in ("pending", "failed"):
                logger.info(f"Session {session_id} feedback_status={session.feedback_status}, skipping")
                return

            transcript_result = await db.execute(
                select(TranscriptEntry)
                .where(TranscriptEntry.session_id == session.id)
                .order_by(TranscriptEntry.turn_index)
            )
            entries = transcript_result.scalars().all()

            transcript_text = "\n".join(
                f"[{e.role}] {e.text_en or ''} | {e.text_native or ''}"
                for e in entries
            )

            last_error = None
            for attempt in range(3):
                try:
                    client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=30.0)
                    response = await client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        system=FEEDBACK_PROMPT,
                        messages=[{"role": "user", "content": f"Here is the quiz transcript:\n\n{transcript_text}"}],
                    )

                    raw_text = response.content[0].text.strip()
                    if raw_text.startswith("```"):
                        lines = raw_text.split("\n")
                        raw_text = "\n".join(lines[1:-1])

                    data = json.loads(raw_text)
                    feedback_data = FeedbackResponse(**data)

                    feedback = Feedback(
                        session_id=session.id,
                        correct=feedback_data.correct,
                        revisit=feedback_data.revisit,
                        drills=feedback_data.drills,
                    )
                    db.add(feedback)

                    session.feedback_status = "ready"
                    session.feedback_generated_at = datetime.now(timezone.utc)
                    session.feedback_error = None
                    await db.commit()

                    logger.info(f"Feedback generated for session {session_id}")
                    return

                except Exception as e:
                    last_error = e
                    logger.warning(f"Feedback attempt {attempt + 1} failed: {e}")
                    continue

            session.feedback_status = "failed"
            session.feedback_error = str(last_error)[:500]
            await db.commit()
            logger.error(f"Feedback generation failed for session {session_id}: {last_error}")

    finally:
        await engine.dispose()

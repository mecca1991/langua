import logging

from app.core.database import async_session
from app.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)


async def run_feedback_generation(ctx: dict, session_id: str) -> None:
    async with async_session() as db:
        try:
            generated = await FeedbackService(db).generate_feedback(session_id)
            if generated:
                logger.info(f"Feedback generated for session {session_id}")
            else:
                logger.info(f"Skipped feedback generation for session {session_id}")
        except Exception as exc:
            logger.error(f"Feedback generation failed for session {session_id}: {exc}")
            raise

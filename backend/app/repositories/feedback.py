from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback


class FeedbackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        session_id,
        correct: list[str],
        revisit: list[str],
        drills: list[str],
    ) -> Feedback:
        feedback = Feedback(
            session_id=session_id,
            correct=correct,
            revisit=revisit,
            drills=drills,
        )
        self.db.add(feedback)
        await self.db.flush()
        return feedback

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        language: str,
        mode: str,
        topic: str,
        status: str = "active",
    ) -> Session:
        session = Session(
            user_id=user_id,
            language=language,
            mode=mode,
            topic=topic,
            status=status,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Session).where(Session.user_id == user_id)
        )
        return result.scalar() or 0

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def mark_ended(self, session: Session, *, ended_at: datetime) -> Session:
        session.status = "ended"
        session.ended_at = ended_at
        return session

    async def set_feedback_pending(self, session: Session) -> Session:
        session.feedback_status = "pending"
        session.feedback_error = None
        return session

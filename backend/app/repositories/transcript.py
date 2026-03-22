import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import TranscriptEntry


class TranscriptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_entry_by_idempotency(
        self,
        *,
        session_id: uuid.UUID,
        idempotency_key: uuid.UUID,
    ) -> TranscriptEntry | None:
        result = await self.db.execute(
            select(TranscriptEntry).where(
                TranscriptEntry.session_id == session_id,
                TranscriptEntry.idempotency_key == idempotency_key,
                TranscriptEntry.role == "user",
            )
        )
        return result.scalar_one_or_none()

    async def get_assistant_entry_for_turn(
        self,
        *,
        session_id: uuid.UUID,
        turn_index: int,
    ) -> TranscriptEntry | None:
        result = await self.db.execute(
            select(TranscriptEntry).where(
                TranscriptEntry.session_id == session_id,
                TranscriptEntry.turn_index == turn_index,
                TranscriptEntry.role == "assistant",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> list[TranscriptEntry]:
        result = await self.db.execute(
            select(TranscriptEntry)
            .where(TranscriptEntry.session_id == session_id)
            .order_by(TranscriptEntry.turn_index)
        )
        return list(result.scalars().all())

    async def add_pair(
        self,
        *,
        session_id: uuid.UUID,
        idempotency_key: uuid.UUID,
        user_turn_index: int,
        assistant_turn_index: int,
        user_text: str,
        assistant_turn_id: uuid.UUID,
        assistant_text_en: str,
        assistant_text_native: str,
        assistant_text_reading: str,
        assistant_text_romanized: str,
        assistant_pronunciation_note: str,
        assistant_next_prompt: str,
    ) -> tuple[TranscriptEntry, TranscriptEntry]:
        user_entry = TranscriptEntry(
            session_id=session_id,
            idempotency_key=idempotency_key,
            turn_index=user_turn_index,
            role="user",
            text_en=user_text,
        )
        assistant_entry = TranscriptEntry(
            id=assistant_turn_id,
            session_id=session_id,
            idempotency_key=uuid.uuid4(),
            turn_index=assistant_turn_index,
            role="assistant",
            text_en=assistant_text_en,
            text_native=assistant_text_native,
            text_reading=assistant_text_reading,
            text_romanized=assistant_text_romanized,
            pronunciation_note=assistant_pronunciation_note,
            next_prompt=assistant_next_prompt,
        )
        self.db.add(user_entry)
        self.db.add(assistant_entry)
        await self.db.flush()
        return user_entry, assistant_entry

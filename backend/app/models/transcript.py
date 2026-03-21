import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_session_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_native: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_reading: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_romanized: Mapped[str | None] = mapped_column(Text, nullable=True)
    pronunciation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session = relationship("Session", back_populates="transcript")

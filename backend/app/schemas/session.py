import uuid
from datetime import datetime

from pydantic import BaseModel


class TranscriptEntrySchema(BaseModel):
    id: uuid.UUID
    turn_index: int
    role: str
    text_en: str | None = None
    text_native: str | None = None
    text_reading: str | None = None
    text_romanized: str | None = None
    pronunciation_note: str | None = None
    next_prompt: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackSchema(BaseModel):
    id: uuid.UUID
    correct: list[str]
    revisit: list[str]
    drills: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    id: uuid.UUID
    language: str
    mode: str
    topic: str
    status: str
    feedback_status: str | None = None
    started_at: datetime
    ended_at: datetime | None = None

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    id: uuid.UUID
    language: str
    mode: str
    topic: str
    status: str
    feedback_status: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    transcript: list[TranscriptEntrySchema]
    feedback: list[FeedbackSchema]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    total: int

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class ConversationMode(str, Enum):
    learn = "learn"
    quiz = "quiz"


class StartConversationRequest(BaseModel):
    language: str = Field(default="ja", max_length=10)
    mode: ConversationMode
    topic: str = Field(max_length=100)


class StartConversationResponse(BaseModel):
    session_id: uuid.UUID


class TurnUserEntry(BaseModel):
    role: str = "user"
    text_en: str
    turn_index: int


class TurnAssistantEntry(BaseModel):
    role: str = "assistant"
    text_en: str
    text_native: str
    text_reading: str
    text_romanized: str
    pronunciation_note: str
    next_prompt: str
    turn_index: int


class TurnResponse(BaseModel):
    turn_id: uuid.UUID
    user_entry: TurnUserEntry
    assistant_entry: TurnAssistantEntry
    audio_url: str


class EndConversationRequest(BaseModel):
    session_id: uuid.UUID


class EndConversationResponse(BaseModel):
    status: str
    feedback_status: str | None = None

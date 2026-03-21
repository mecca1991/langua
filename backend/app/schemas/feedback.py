from pydantic import BaseModel

class FeedbackResponse(BaseModel):
    correct: list[str]
    revisit: list[str]
    drills: list[str]

class FeedbackStatusResponse(BaseModel):
    feedback_status: str | None

class FeedbackDetail(BaseModel):
    correct: list[str]
    revisit: list[str]
    drills: list[str]

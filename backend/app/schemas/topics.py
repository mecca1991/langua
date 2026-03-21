from pydantic import BaseModel


class TopicsResponse(BaseModel):
    topics: list[str]
    language: str

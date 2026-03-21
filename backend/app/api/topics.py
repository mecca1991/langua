from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user_payload
from app.schemas.topics import TopicsResponse

router = APIRouter()

TOPICS_BY_LANGUAGE: dict[str, list[str]] = {
    "ja": ["Greetings", "Ordering Food", "Directions", "Shopping", "Travel"],
}


@router.get("/topics", response_model=TopicsResponse)
async def get_topics(
    language: str = Query(default="ja"),
    _=Depends(get_current_user_payload),
):
    topics = TOPICS_BY_LANGUAGE.get(language, [])
    return TopicsResponse(topics=topics, language=language)

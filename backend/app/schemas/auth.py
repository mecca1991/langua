import uuid

from pydantic import BaseModel


class JWTPayload(BaseModel):
    sub: uuid.UUID
    email: str
    name: str = ""
    avatar_url: str | None = None

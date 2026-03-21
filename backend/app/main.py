from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload

app = FastAPI(title="Langua API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}

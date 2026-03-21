from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.auth import get_current_user_payload
from app.schemas.auth import JWTPayload
from app.api.topics import router as topics_router
from app.api.conversation import router as conversation_router
from app.api.sessions import router as sessions_router

app = FastAPI(title="Langua API", version="0.1.0")

audio_dir = Path("/tmp/langua_audio")
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(topics_router)
app.include_router(conversation_router)
app.include_router(sessions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(payload: JWTPayload = Depends(get_current_user_payload)):
    return {"sub": str(payload.sub), "email": payload.email, "name": payload.name}

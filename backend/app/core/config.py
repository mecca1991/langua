from pathlib import Path

from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://langua:langua@localhost:5432/langua"
    REDIS_URL: str = "redis://localhost:6379/0"
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_PROJECT_URL: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    coach_provider: str = "anthropic"
    stt_provider: str = "openai"
    tts_provider: str = "openai"
    worker_concurrency: int = 2
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": BACKEND_DIR / ".env"}


settings = Settings()

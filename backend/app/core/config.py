from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://langua:langua@localhost:5432/langua"
    redis_url: str = "redis://localhost:6379/0"
    supabase_jwt_secret: str = ""
    supabase_project_url: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    coach_provider: str = "anthropic"
    stt_provider: str = "openai"
    tts_provider: str = "openai"
    worker_concurrency: int = 2
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env"}


settings = Settings()

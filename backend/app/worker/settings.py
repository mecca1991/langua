from arq.connections import RedisSettings

from app.core.config import settings


async def generate_feedback(ctx: dict, session_id: str) -> None:
    from app.worker.tasks import run_feedback_generation
    await run_feedback_generation(ctx, session_id)


class WorkerSettings:
    functions = [generate_feedback]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.worker_concurrency
    job_timeout = 120

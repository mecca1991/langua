import logging
import sys


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def log_ai_call(
    logger: logging.Logger,
    request_id: str,
    session_id: str | None,
    operation: str,
    provider: str,
    duration_ms: float,
    status: str,
):
    logger.info(
        "ai_call request_id=%s session_id=%s operation=%s provider=%s duration_ms=%.2f status=%s",
        request_id, session_id, operation, provider, duration_ms, status,
    )

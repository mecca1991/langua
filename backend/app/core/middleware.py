import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"request method={request.method} path={request.url.path} "
            f"status={response.status_code} duration_ms={duration_ms:.2f} "
            f"request_id={request_id}"
        )

        return response

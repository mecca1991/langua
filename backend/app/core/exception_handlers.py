import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.api_errors import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictAPIError,
    NotFoundAPIError,
    PermissionError,
    ProviderAPIError,
)
from app.services.domain_errors import ConflictError, ForbiddenError, NotFoundError
from app.services.errors import AIServiceError, CoachError, STTError, TTSError

logger = logging.getLogger(__name__)


def _error_response(request: Request, exc: APIError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_type": exc.error_type,
            "error_code": exc.error_code,
            "error_message": exc.error_message,
            "request_id": request_id,
        },
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    logger.warning(
        "client_error type=%s code=%s path=%s request_id=%s",
        exc.error_type,
        exc.error_code,
        request.url.path,
        getattr(request.state, "request_id", None),
    )
    return _error_response(request, exc)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    logger.info(
        "domain_not_found path=%s request_id=%s detail=%s",
        request.url.path,
        getattr(request.state, "request_id", None),
        str(exc),
    )
    return _error_response(
        request,
        NotFoundAPIError(
            error_code="RESOURCE_NOT_FOUND",
            error_message="The requested resource could not be found.",
        ),
    )


async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    logger.warning(
        "domain_forbidden path=%s request_id=%s detail=%s",
        request.url.path,
        getattr(request.state, "request_id", None),
        str(exc),
    )
    return _error_response(
        request,
        PermissionError(
            error_code="ACCESS_NOT_GRANTED",
            error_message="You do not have access to this resource.",
        ),
    )


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    logger.info(
        "domain_conflict path=%s request_id=%s detail=%s",
        request.url.path,
        getattr(request.state, "request_id", None),
        str(exc),
    )
    return _error_response(
        request,
        ConflictAPIError(
            error_code="RESOURCE_STATE_CONFLICT",
            error_message="The requested operation is not allowed in the resource's current state.",
        ),
    )


async def ai_service_error_handler(
    request: Request, exc: AIServiceError
) -> JSONResponse:
    logger.exception(
        "provider_error provider=%s retryable=%s path=%s request_id=%s",
        exc.provider,
        exc.retryable,
        request.url.path,
        getattr(request.state, "request_id", None),
    )

    if isinstance(exc, STTError):
        error = ProviderAPIError(
            error_code="SPEECH_TRANSCRIPTION_FAILED",
            error_message="We couldn't transcribe the submitted audio. Please try again.",
        )
    elif isinstance(exc, CoachError):
        error = ProviderAPIError(
            error_code="COACH_RESPONSE_FAILED",
            error_message="We couldn't generate a coaching response right now. Please try again.",
        )
    else:
        error = ProviderAPIError(
            error_code="AUDIO_SYNTHESIS_FAILED",
            error_message="We couldn't generate audio for this response right now. Please try again.",
        )

    return _error_response(request, error)


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "unhandled_error path=%s request_id=%s",
        request.url.path,
        getattr(request.state, "request_id", None),
    )
    return _error_response(
        request,
        ProviderAPIError(
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred. Please try again later.",
        ),
    )

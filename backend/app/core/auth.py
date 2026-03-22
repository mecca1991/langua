import logging
import time
import uuid
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jose import JWTError, jwt

from app.core.api_errors import AuthenticationError
from app.core.config import settings
from app.schemas.auth import JWTPayload

security = HTTPBearer()
logger = logging.getLogger(__name__)
ASYMMETRIC_ALGORITHMS = {"RS256", "ES256"}
JWKS_CACHE_TTL_SECONDS = 300
_jwks_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


async def _fetch_jwks(issuer: str) -> list[dict[str, Any]]:
    cached = _jwks_cache.get(issuer)
    now = time.time()
    if cached and now - cached[0] < JWKS_CACHE_TTL_SECONDS:
        return cached[1]

    jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()

    keys = response.json().get("keys", [])
    _jwks_cache[issuer] = (now, keys)
    return keys


def _resolve_jwk(keys: list[dict[str, Any]], kid: str | None) -> dict[str, Any]:
    if not kid:
        raise JWTError("Missing key id in token header")

    for key in keys:
        if key.get("kid") == kid:
            return key

    raise JWTError("Signing key not found for token")


async def _decode_supabase_jwt(token: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")

    if algorithm == "HS256":
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )

    if algorithm in ASYMMETRIC_ALGORITHMS:
        claims = jwt.get_unverified_claims(token)
        issuer = claims.get("iss")
        if not issuer:
            raise JWTError("Missing issuer in token claims")

        keys = await _fetch_jwks(issuer)
        signing_key = _resolve_jwk(keys, header.get("kid"))
        return jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=issuer,
        )

    raise JWTError(f"Unsupported JWT algorithm: {algorithm}")


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> JWTPayload:
    token = credentials.credentials
    try:
        payload = await _decode_supabase_jwt(token)
    except (JWTError, httpx.HTTPError) as exc:
        logger.error("jwt_validation_failed detail=%s", str(exc))
        raise AuthenticationError(
            error_code="INVALID_AUTH",
            error_message="The authentication token is missing, invalid, or expired.",
        )

    user_metadata = payload.get("user_metadata", {})
    return JWTPayload(
        sub=uuid.UUID(payload["sub"]),
        email=payload.get("email", ""),
        name=user_metadata.get("full_name", ""),
        avatar_url=user_metadata.get("avatar_url"),
    )

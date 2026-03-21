import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import JWTPayload

security = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> JWTPayload:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_metadata = payload.get("user_metadata", {})
    return JWTPayload(
        sub=uuid.UUID(payload["sub"]),
        email=payload.get("email", ""),
        name=user_metadata.get("full_name", ""),
        avatar_url=user_metadata.get("avatar_url"),
    )


async def get_or_create_user(
    payload: JWTPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=payload.sub,
            email=payload.email,
            name=payload.name,
            avatar_url=payload.avatar_url,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
